"""Pydantic schemas for File Streaming HTTP API."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from legacy2micro.models.manifest import LegacyFileType, StagingStatus


class FileUploadResponse(BaseModel):
    """Response returned upon successful file streaming and staging."""
    success: bool = True
    message: str = "File successfully streamed and staged for parsing."
    staging_id: str
    original_filename: str
    sanitized_filename: str
    file_type: LegacyFileType
    file_size_bytes: int
    sha256_checksum: str
    line_count: Optional[int] = None
    status: StagingStatus
    staged_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchFileUploadResponse(BaseModel):
    """Response returned for batch file uploads."""
    success: bool
    total_files: int
    successful_count: int
    failed_count: int
    files: List[FileUploadResponse]
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class StatusUpdateRequest(BaseModel):
    """Request body for updating staged file status."""
    status: StagingStatus


class ErrorResponse(BaseModel):
    """Standardized error response body."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
