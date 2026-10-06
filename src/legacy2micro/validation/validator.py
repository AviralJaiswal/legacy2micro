"""File streaming validator pipeline for legacy source code."""

from typing import Tuple, Optional, Set
from legacy2micro.config import StreamingSettings, settings as default_settings
from legacy2micro.exceptions import (
    EmptyFileError,
    FileSizeLimitExceededError,
)
from legacy2micro.models.manifest import LegacyFileType
from legacy2micro.validation.rules import (
    sanitize_and_validate_filename,
    validate_file_extension,
    inspect_chunk_for_binary_content,
)


class FileStreamValidator:
    """
    Stream-aware validator ensuring files comply with legacy ingestion rules
    prior to and during chunk processing.
    """

    def __init__(self, settings: Optional[StreamingSettings] = None):
        self.settings = settings or default_settings

    def validate_pre_stream(self, filename: str) -> Tuple[str, str, LegacyFileType]:
        """
        Validate filename and extension before streaming begins.
        
        Returns:
            Tuple[str, str, LegacyFileType]: (sanitized_filename, extension, legacy_type)
        """
        sanitized_name, ext = sanitize_and_validate_filename(filename)
        validate_file_extension(ext, self.settings.allowed_extensions)
        legacy_type = LegacyFileType.from_extension(ext)
        return sanitized_name, ext, legacy_type

    def validate_chunk(
        self,
        chunk: bytes,
        is_first_chunk: bool,
        current_total_bytes: int
    ) -> None:
        """
        Validate an incoming chunk during streaming.
        
        Raises:
            FileSizeLimitExceededError: If cumulative byte size exceeds limit.
            BinaryFileRejectedError: If initial chunk matches disallowed binary signatures.
        """
        # Check running size limit
        new_total = current_total_bytes + len(chunk)
        if new_total > self.settings.max_file_size_bytes:
            raise FileSizeLimitExceededError(
                f"File size exceeded maximum configured limit of {self.settings.max_file_size_bytes} bytes "
                f"({self.settings.max_file_size_bytes / (1024 * 1024):.2f} MB).",
                details={
                    "max_allowed_bytes": self.settings.max_file_size_bytes,
                    "exceeded_at_bytes": new_total,
                }
            )

        # Inspect initial chunk for non-text / binary payload
        if is_first_chunk and self.settings.enforce_text_content_check:
            inspect_chunk_for_binary_content(chunk)

    def validate_post_stream(self, total_bytes: int) -> None:
        """
        Validate stream properties once all chunks have been read.
        
        Raises:
            EmptyFileError: If 0 bytes were received.
            FileSizeLimitExceededError: If total size is invalid.
        """
        if total_bytes < self.settings.min_file_size_bytes:
            raise EmptyFileError(
                "Uploaded file is empty (0 bytes). Empty files cannot be ingested for parsing.",
                details={"total_bytes": total_bytes}
            )

        if total_bytes > self.settings.max_file_size_bytes:
            raise FileSizeLimitExceededError(
                f"File size exceeded maximum limit ({total_bytes} > {self.settings.max_file_size_bytes}).",
                details={
                    "total_bytes": total_bytes,
                    "max_allowed_bytes": self.settings.max_file_size_bytes
                }
            )
