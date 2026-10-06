"""Base storage interface abstraction for legacy2micro."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional, List, Dict, Any
from legacy2micro.models.manifest import StagedFileManifest, StagingStatus


class BaseStorageBackend(ABC):
    """Abstract interface for staging legacy files and metadata manifests."""

    @abstractmethod
    def save_staged_file(
        self,
        staging_id: str,
        temp_file_path: Path,
        manifest: StagedFileManifest
    ) -> Path:
        """Commit an in-flight temporary file and its manifest to final staging storage."""
        pass

    @abstractmethod
    def get_staged_file_path(self, staging_id: str) -> Path:
        """Get absolute path to staged file by staging ID."""
        pass

    @abstractmethod
    def get_manifest(self, staging_id: str) -> StagedFileManifest:
        """Retrieve manifest for a given staging ID."""
        pass

    @abstractmethod
    def list_staged(self, status: Optional[StagingStatus] = None) -> List[StagedFileManifest]:
        """List all staged files, optionally filtered by status."""
        pass

    @abstractmethod
    def delete_staged(self, staging_id: str) -> bool:
        """Delete a staged file and its manifest."""
        pass
