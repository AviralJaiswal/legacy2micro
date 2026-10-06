"""Staging storage manager implementation for safe file retention and parser handoff."""

import json
import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import BinaryIO, Optional, List, Generator
from contextlib import contextmanager

from legacy2micro.config import StreamingSettings, settings as default_settings
from legacy2micro.exceptions import (
    StagingStorageError,
    StagedFileNotFoundError,
)
from legacy2micro.models.manifest import StagedFileManifest, StagingStatus
from legacy2micro.storage.base import BaseStorageBackend


class StagingStorageManager(BaseStorageBackend):
    """
    Manages local staging storage for validated legacy files and manifests.
    
    Structure:
        storage/
        ├── temp/
        │   └── <staging_id>.tmp (in-flight write)
        └── staging/
            └── <staging_id>/
                ├── manifest.json
                └── <sanitized_filename> (committed asset)
    """

    def __init__(self, settings: Optional[StreamingSettings] = None):
        self.settings = settings or default_settings
        self.settings.ensure_directories()

    def get_temp_file_path(self, staging_id: str) -> Path:
        """Get path for in-flight temporary file during streaming."""
        return self.settings.temp_dir / f"{staging_id}.tmp"

    def get_staging_item_dir(self, staging_id: str) -> Path:
        """Get dedicated directory path for a staged asset."""
        return self.settings.staging_dir / staging_id

    def save_staged_file(
        self,
        staging_id: str,
        temp_file_path: Path,
        manifest: StagedFileManifest
    ) -> Path:
        """
        Atomically commit the temporary file and write manifest.json.
        """
        staging_item_dir = self.get_staging_item_dir(staging_id)
        staging_item_dir.mkdir(parents=True, exist_ok=True)

        destination_file_path = staging_item_dir / manifest.sanitized_filename

        try:
            # Move temporary file to final destination
            if not temp_file_path.exists():
                raise StagingStorageError(f"Temporary file '{temp_file_path}' does not exist.")

            shutil.move(str(temp_file_path), str(destination_file_path))
            
            # Update manifest with relative or absolute path
            manifest.staged_file_path = str(destination_file_path.resolve())

            # Write manifest.json
            manifest_path = staging_item_dir / "manifest.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest.model_dump(mode="json"), f, indent=2)

            return destination_file_path
        except Exception as e:
            # Clean up if move or manifest write fails
            if destination_file_path.exists():
                try:
                    destination_file_path.unlink()
                except Exception:
                    pass
            raise StagingStorageError(f"Failed to commit staged file '{staging_id}': {e}") from e

    def get_manifest(self, staging_id: str) -> StagedFileManifest:
        """
        Load and parse the manifest for a given staging ID.
        """
        manifest_path = self.get_staging_item_dir(staging_id) / "manifest.json"
        if not manifest_path.exists():
            raise StagedFileNotFoundError(f"Staged file manifest for ID '{staging_id}' was not found.")

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return StagedFileManifest.model_validate(data)
        except Exception as e:
            raise StagingStorageError(f"Error reading manifest for staging ID '{staging_id}': {e}") from e

    def update_manifest(self, manifest: StagedFileManifest) -> None:
        """Save updated manifest back to disk."""
        manifest_path = self.get_staging_item_dir(manifest.staging_id) / "manifest.json"
        if not manifest_path.parent.exists():
            raise StagedFileNotFoundError(f"Staged directory for ID '{manifest.staging_id}' does not exist.")

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(mode="json"), f, indent=2)

    def get_staged_file_path(self, staging_id: str) -> Path:
        """
        Resolve the path to the staged legacy source file.
        """
        manifest = self.get_manifest(staging_id)
        file_path = Path(manifest.staged_file_path)
        if not file_path.exists():
            # Fallback check inside staging folder
            fallback = self.get_staging_item_dir(staging_id) / manifest.sanitized_filename
            if fallback.exists():
                return fallback
            raise StagedFileNotFoundError(f"Staged file on disk for ID '{staging_id}' was not found at '{file_path}'.")
        return file_path

    @contextmanager
    def open_stream(self, staging_id: str) -> Generator[BinaryIO, None, None]:
        """
        Context manager for Parser Service or downstream consumers to stream the staged file.
        
        Usage:
            with storage.open_stream(staging_id) as stream:
                for chunk in iter(lambda: stream.read(65536), b''):
                    ...
        """
        file_path = self.get_staged_file_path(staging_id)
        with open(file_path, "rb") as f:
            yield f

    def mark_status(self, staging_id: str, new_status: StagingStatus) -> StagedFileManifest:
        """Update the lifecycle status of a staged file (e.g. READY_FOR_PARSER -> IN_PARSING -> CONSUMED)."""
        manifest = self.get_manifest(staging_id)
        manifest.status = new_status
        self.update_manifest(manifest)
        return manifest

    def list_staged(self, status: Optional[StagingStatus] = None) -> List[StagedFileManifest]:
        """List all staged files, optionally filtered by status."""
        results: List[StagedFileManifest] = []
        if not self.settings.staging_dir.exists():
            return results

        for entry in self.settings.staging_dir.iterdir():
            if entry.is_dir():
                manifest_path = entry / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        manifest = StagedFileManifest.model_validate(data)
                        if status is None or manifest.status == status:
                            results.append(manifest)
                    except Exception:
                        continue
        # Sort by staged_at descending
        results.sort(key=lambda m: m.staged_at, reverse=True)
        return results

    def delete_staged(self, staging_id: str) -> bool:
        """Delete a staged file, its manifest, and its container folder."""
        staging_item_dir = self.get_staging_item_dir(staging_id)
        if staging_item_dir.exists():
            shutil.rmtree(staging_item_dir, ignore_errors=True)
            return True
        return False

    def cleanup_temp_file(self, staging_id: str) -> None:
        """Safely remove any leftover temporary in-flight file."""
        temp_path = self.get_temp_file_path(staging_id)
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass

    def cleanup_expired(self, retention_hours: Optional[int] = None) -> int:
        """Remove staged assets older than the retention threshold."""
        hours = retention_hours if retention_hours is not None else self.settings.retention_hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        purged_count = 0

        for manifest in self.list_staged():
            if manifest.staged_at < cutoff:
                if self.delete_staged(manifest.staging_id):
                    purged_count += 1

        return purged_count
