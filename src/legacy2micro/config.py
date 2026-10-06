"""Configuration settings for legacy2micro file streaming subsystem."""

from pathlib import Path
from typing import Set
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StreamingSettings(BaseSettings):
    """File Streaming and Staging Configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LEGACY2MICRO_",
        env_file=".env",
        extra="ignore"
    )

    # Base Storage Paths
    base_storage_dir: Path = Field(
        default=Path("storage"),
        description="Base storage directory for file assets."
    )
    staging_dir: Path = Field(
        default=Path("storage/staging"),
        description="Directory where validated files are staged for the Parser Service."
    )
    temp_dir: Path = Field(
        default=Path("storage/temp"),
        description="Temporary directory used during in-flight stream processing."
    )

    # Streaming and Chunk Limits
    chunk_size_bytes: int = Field(
        default=64 * 1024,  # 64 KB
        gt=0,
        description="Buffer/chunk size used during streaming."
    )
    max_file_size_bytes: int = Field(
        default=100 * 1024 * 1024,  # 100 MB
        gt=0,
        description="Maximum allowed legacy source file size in bytes."
    )
    min_file_size_bytes: int = Field(
        default=1,
        ge=1,
        description="Minimum file size in bytes (rejects empty 0-byte files)."
    )

    # Allowed Legacy File Extensions (case-insensitive)
    allowed_extensions: Set[str] = Field(
        default={
            ".cob",   # COBOL source
            ".cbl",   # COBOL source
            ".cpy",   # COBOL Copybook
            ".pco",   # Precompiled COBOL
            ".sqb",   # Embedded SQL COBOL
            ".txt",   # Text/Source export
            ".src",   # Generic legacy source
            ".jcl",   # Job Control Language
            ".prg",   # Program source
            ".ccp",   # CICS COBOL Program
        },
        description="Set of valid legacy file extensions."
    )

    # Content Validation
    enforce_text_content_check: bool = Field(
        default=True,
        description="Verify initial chunk to reject non-text/binary/executable payloads."
    )

    # Staged Asset Retention
    retention_hours: int = Field(
        default=24,
        ge=1,
        description="Staging retention TTL in hours before automatic expiration."
    )

    def ensure_directories(self) -> None:
        """Create necessary staging and temporary directories if they don't exist."""
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)


# Global settings singleton
settings = StreamingSettings()
