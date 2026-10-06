"""Exception hierarchy for legacy2micro file streaming and staging subsystem."""

from typing import Optional, Dict, Any


class Legacy2MicroError(Exception):
    """Base exception for all legacy2micro errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class FileStreamingError(Legacy2MicroError):
    """Base exception for file streaming and staging operations."""
    pass


class FileValidationError(FileStreamingError):
    """Raised when an uploaded file fails one or more validation constraints."""
    pass


class InvalidFilenameError(FileValidationError):
    """Raised when a filename is malformed, blank, or contains path traversal attempts."""
    pass


class InvalidFileTypeError(FileValidationError):
    """Raised when a file extension is not an allowed legacy source format."""
    pass


class EmptyFileError(FileValidationError):
    """Raised when an uploaded file is empty (0 bytes)."""
    pass


class FileSizeLimitExceededError(FileValidationError):
    """Raised when a file exceeds the maximum allowed size limit."""
    pass


class BinaryFileRejectedError(FileValidationError):
    """Raised when a file contains disallowed binary or executable headers."""
    pass


class StagingStorageError(FileStreamingError):
    """Base exception for storage and file staging operations."""
    pass


class StagedFileNotFoundError(StagingStorageError):
    """Raised when a requested staged file ID or manifest cannot be found."""
    pass


class StagedFileCorruptedError(StagingStorageError):
    """Raised when a staged file fails checksum verification or integrity checks."""
    pass


class StagingPermissionError(StagingStorageError):
    """Raised when staging storage directory cannot be written or read."""
    pass
