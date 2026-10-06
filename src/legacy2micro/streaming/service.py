"""FileStreamingService orchestrator for legacy source file ingestion and staging."""

import uuid
from pathlib import Path
from typing import BinaryIO, AsyncIterator, Iterator, Optional, Dict, Any, List
from contextlib import contextmanager

from legacy2micro.config import StreamingSettings, settings as default_settings
from legacy2micro.models.manifest import StagedFileManifest, StagingStatus
from legacy2micro.storage.staging import StagingStorageManager
from legacy2micro.streaming.processor import StreamProcessor
from legacy2micro.validation.validator import FileStreamValidator


class FileStreamingService:
    """
    High-level service orchestrating file streaming, validation, staging,
    and preparation for downstream Parser Services.
    """

    def __init__(
        self,
        settings: Optional[StreamingSettings] = None,
        storage_manager: Optional[StagingStorageManager] = None,
        validator: Optional[FileStreamValidator] = None,
        stream_processor: Optional[StreamProcessor] = None,
    ):
        self.settings = settings or default_settings
        self.storage_manager = storage_manager or StagingStorageManager(self.settings)
        self.validator = validator or FileStreamValidator(self.settings)
        self.stream_processor = stream_processor or StreamProcessor(self.validator, self.settings)

    def ingest_sync_stream(
        self,
        filename: str,
        chunk_iterator: Iterator[bytes],
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> StagedFileManifest:
        """
        Ingest a synchronous chunk iterator, validating and staging safely.
        """
        sanitized_name, ext, legacy_type = self.validator.validate_pre_stream(filename)
        staging_id = str(uuid.uuid4())
        temp_file_path = self.storage_manager.get_temp_file_path(staging_id)

        try:
            # Process stream to temporary file
            result = self.stream_processor.process_sync_stream(chunk_iterator, temp_file_path)

            # Build initial manifest
            manifest = StagedFileManifest(
                staging_id=staging_id,
                original_filename=filename,
                sanitized_filename=sanitized_name,
                file_extension=ext,
                file_type=legacy_type,
                file_size_bytes=result.total_bytes,
                sha256_checksum=result.sha256_checksum,
                status=StagingStatus.READY_FOR_PARSER,
                staged_file_path="",  # Populated during save_staged_file
                line_count=result.line_count,
                encoding_detected=result.encoding_detected,
                metadata=custom_metadata or {},
            )

            # Atomically commit to staging directory
            self.storage_manager.save_staged_file(staging_id, temp_file_path, manifest)
            return manifest

        except Exception:
            # Clean up temporary file on failure
            self.storage_manager.cleanup_temp_file(staging_id)
            raise

    async def ingest_async_stream(
        self,
        filename: str,
        async_chunk_iterator: AsyncIterator[bytes],
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> StagedFileManifest:
        """
        Ingest an asynchronous chunk stream (e.g. FastAPI / async HTTP payload),
        validating and staging safely.
        """
        sanitized_name, ext, legacy_type = self.validator.validate_pre_stream(filename)
        staging_id = str(uuid.uuid4())
        temp_file_path = self.storage_manager.get_temp_file_path(staging_id)

        try:
            result = await self.stream_processor.process_async_stream(
                async_chunk_iterator,
                temp_file_path
            )

            manifest = StagedFileManifest(
                staging_id=staging_id,
                original_filename=filename,
                sanitized_filename=sanitized_name,
                file_extension=ext,
                file_type=legacy_type,
                file_size_bytes=result.total_bytes,
                sha256_checksum=result.sha256_checksum,
                status=StagingStatus.READY_FOR_PARSER,
                staged_file_path="",
                line_count=result.line_count,
                encoding_detected=result.encoding_detected,
                metadata=custom_metadata or {},
            )

            self.storage_manager.save_staged_file(staging_id, temp_file_path, manifest)
            return manifest

        except Exception:
            self.storage_manager.cleanup_temp_file(staging_id)
            raise

    def ingest_file_path(
        self,
        source_file_path: Path,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> StagedFileManifest:
        """
        Ingest a local source file by streaming it in chunks.
        """
        source_path = Path(source_file_path)
        if not source_path.is_file():
            raise FileNotFoundError(f"Source file '{source_file_path}' does not exist.")

        def file_chunk_generator() -> Iterator[bytes]:
            with open(source_path, "rb") as f:
                while True:
                    chunk = f.read(self.settings.chunk_size_bytes)
                    if not chunk:
                        break
                    yield chunk

        return self.ingest_sync_stream(
            filename=source_path.name,
            chunk_iterator=file_chunk_generator(),
            custom_metadata=custom_metadata,
        )

    # --- Parser Service Handoff APIs ---

    def get_manifest(self, staging_id: str) -> StagedFileManifest:
        """Retrieve staging metadata and parser contract for a given staging ID."""
        return self.storage_manager.get_manifest(staging_id)

    def get_staged_file_path(self, staging_id: str) -> Path:
        """Get absolute path to staged file for Parser Service ingestion."""
        return self.storage_manager.get_staged_file_path(staging_id)

    @contextmanager
    def open_parser_stream(self, staging_id: str) -> Iterator[BinaryIO]:
        """
        Provide a clean stream handle for the future Parser Service to consume the file.
        """
        with self.storage_manager.open_stream(staging_id) as stream:
            yield stream

    def mark_in_parsing(self, staging_id: str) -> StagedFileManifest:
        """Update status to IN_PARSING when the Parser Service starts processing."""
        return self.storage_manager.mark_status(staging_id, StagingStatus.IN_PARSING)

    def mark_consumed(self, staging_id: str) -> StagedFileManifest:
        """Update status to CONSUMED once parsing finishes."""
        return self.storage_manager.mark_status(staging_id, StagingStatus.CONSUMED)

    def list_staged(self, status: Optional[StagingStatus] = None) -> List[StagedFileManifest]:
        """List staged legacy source files ready for parsing."""
        return self.storage_manager.list_staged(status)

    def delete_staged(self, staging_id: str) -> bool:
        """Delete staged file and manifest."""
        return self.storage_manager.delete_staged(staging_id)
