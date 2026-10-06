"""Pydantic data models and schemas for staged legacy files and manifests."""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class LegacyFileType(str, Enum):
    """Classification of legacy source files."""
    COBOL_SOURCE = "COBOL_SOURCE"
    COBOL_COPYBOOK = "COBOL_COPYBOOK"
    PRECOMPILED_COBOL = "PRECOMPILED_COBOL"
    SQL_COBOL = "SQL_COBOL"
    JCL_SCRIPT = "JCL_SCRIPT"
    GENERIC_SOURCE = "GENERIC_SOURCE"
    TEXT_SOURCE = "TEXT_SOURCE"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_extension(cls, ext: str) -> "LegacyFileType":
        """Map file extension to legacy file type."""
        ext_lower = ext.lower().strip()
        mapping = {
            ".cbl": cls.COBOL_SOURCE,
            ".cob": cls.COBOL_SOURCE,
            ".prg": cls.COBOL_SOURCE,
            ".ccp": cls.COBOL_SOURCE,
            ".cpy": cls.COBOL_COPYBOOK,
            ".pco": cls.PRECOMPILED_COBOL,
            ".sqb": cls.SQL_COBOL,
            ".jcl": cls.JCL_SCRIPT,
            ".src": cls.GENERIC_SOURCE,
            ".txt": cls.TEXT_SOURCE,
        }
        return mapping.get(ext_lower, cls.UNKNOWN)


class StagingStatus(str, Enum):
    """Lifecycle status of staged files."""
    STAGING = "STAGING"
    STAGED = "STAGED"
    READY_FOR_PARSER = "READY_FOR_PARSER"
    IN_PARSING = "IN_PARSING"
    CONSUMED = "CONSUMED"
    FAILED = "FAILED"
    PURGED = "PURGED"


class StagedFileManifest(BaseModel):
    """Metadata manifest stored alongside each staged file for downstream Parser Service consumption."""

    staging_id: str = Field(..., description="Unique UUID for this staged legacy asset.")
    original_filename: str = Field(..., description="Original filename from upload.")
    sanitized_filename: str = Field(..., description="Safe sanitized filename without path traversal.")
    file_extension: str = Field(..., description="Normalized file extension (e.g. .cbl, .cpy).")
    file_type: LegacyFileType = Field(default=LegacyFileType.UNKNOWN, description="Legacy source classification.")
    file_size_bytes: int = Field(..., ge=1, description="Total size in bytes.")
    sha256_checksum: str = Field(..., description="SHA-256 hex digest for integrity verification.")
    staged_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when staging completed."
    )
    status: StagingStatus = Field(
        default=StagingStatus.READY_FOR_PARSER,
        description="Current state of the staged asset."
    )
    staged_file_path: str = Field(..., description="Relative or absolute path to the staged file.")
    line_count: Optional[int] = Field(default=None, description="Estimated or verified line count.")
    encoding_detected: str = Field(default="utf-8", description="Detected text encoding format.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional custom or dialect metadata.")

    def to_parser_input(self) -> Dict[str, Any]:
        """Convert manifest to standardized input contract for future Parser Service."""
        return {
            "staging_id": self.staging_id,
            "file_path": self.staged_file_path,
            "filename": self.sanitized_filename,
            "original_filename": self.original_filename,
            "file_type": self.file_type.value,
            "size_bytes": self.file_size_bytes,
            "sha256": self.sha256_checksum,
            "status": self.status.value,
            "staged_at": self.staged_at.isoformat(),
            "metadata": self.metadata,
        }
