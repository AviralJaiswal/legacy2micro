"""FastAPI router endpoints for File Streaming and Staging Service."""

import json
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse

from legacy2micro.config import settings
from legacy2micro.exceptions import StagedFileNotFoundError, FileValidationError
from legacy2micro.models.manifest import StagingStatus, StagedFileManifest
from legacy2micro.streaming.service import FileStreamingService
from legacy2micro.api.schemas import (
    FileUploadResponse,
    BatchFileUploadResponse,
    StatusUpdateRequest,
)

router = APIRouter(prefix="/api/v1/files", tags=["File Streaming"])
service = FileStreamingService()


async def stream_upload_file_chunks(upload_file: UploadFile, chunk_size: int):
    """Async generator yielding chunks from an uploaded file without loading all into RAM."""
    while True:
        chunk = await upload_file.read(chunk_size)
        if not chunk:
            break
        yield chunk


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_legacy_file(
    file: UploadFile = File(..., description="Legacy source file (COBOL, Copybook, JCL, etc.)"),
    metadata_json: Optional[str] = Form(None, description="Optional JSON string of custom metadata tags"),
):
    """
    Stream, validate, and stage a single legacy source file for Parser Service consumption.
    """
    custom_metadata = {}
    if metadata_json:
        try:
            custom_metadata = json.loads(metadata_json)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON formatted metadata: {e}"
            )

    filename = file.filename or "unknown.cbl"

    # Ingest using chunked async streaming
    manifest = await service.ingest_async_stream(
        filename=filename,
        async_chunk_iterator=stream_upload_file_chunks(file, settings.chunk_size_bytes),
        custom_metadata=custom_metadata,
    )

    return FileUploadResponse(
        success=True,
        message="Legacy file successfully streamed and staged for parsing.",
        staging_id=manifest.staging_id,
        original_filename=manifest.original_filename,
        sanitized_filename=manifest.sanitized_filename,
        file_type=manifest.file_type,
        file_size_bytes=manifest.file_size_bytes,
        sha256_checksum=manifest.sha256_checksum,
        line_count=manifest.line_count,
        status=manifest.status,
        staged_at=manifest.staged_at,
        metadata=manifest.metadata,
    )


@router.post("/upload-batch", response_model=BatchFileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_batch_legacy_files(
    files: List[UploadFile] = File(..., description="Multiple legacy source files"),
):
    """
    Batch stream and stage multiple legacy files.
    """
    successful_uploads: List[FileUploadResponse] = []
    errors: List[dict] = []

    for file in files:
        try:
            filename = file.filename or "unknown.cbl"
            manifest = await service.ingest_async_stream(
                filename=filename,
                async_chunk_iterator=stream_upload_file_chunks(file, settings.chunk_size_bytes),
            )
            successful_uploads.append(
                FileUploadResponse(
                    success=True,
                    staging_id=manifest.staging_id,
                    original_filename=manifest.original_filename,
                    sanitized_filename=manifest.sanitized_filename,
                    file_type=manifest.file_type,
                    file_size_bytes=manifest.file_size_bytes,
                    sha256_checksum=manifest.sha256_checksum,
                    line_count=manifest.line_count,
                    status=manifest.status,
                    staged_at=manifest.staged_at,
                    metadata=manifest.metadata,
                )
            )
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e),
                "error_type": type(e).__name__
            })

    is_overall_success = len(errors) == 0
    return BatchFileUploadResponse(
        success=is_overall_success,
        total_files=len(files),
        successful_count=len(successful_uploads),
        failed_count=len(errors),
        files=successful_uploads,
        errors=errors,
    )


@router.get("/staged", response_model=List[StagedFileManifest])
def list_staged_files(
    status_filter: Optional[StagingStatus] = Query(None, alias="status", description="Filter by staging status")
):
    """
    List all staged files and their metadata manifests.
    """
    return service.list_staged(status=status_filter)


@router.get("/staged/{staging_id}", response_model=StagedFileManifest)
def get_staged_file_manifest(staging_id: str):
    """
    Retrieve manifest and metadata for a specific staged file.
    """
    return service.get_manifest(staging_id)


@router.get("/staged/{staging_id}/download")
def download_staged_file(staging_id: str):
    """
    Stream the staged source file directly.
    """
    file_path = service.get_staged_file_path(staging_id)
    manifest = service.get_manifest(staging_id)
    return FileResponse(
        path=file_path,
        filename=manifest.sanitized_filename,
        media_type="text/plain"
    )


@router.patch("/staged/{staging_id}/status", response_model=StagedFileManifest)
def update_staged_status(staging_id: str, payload: StatusUpdateRequest):
    """
    Update the lifecycle status of a staged file (e.g. mark IN_PARSING or CONSUMED).
    """
    return service.storage_manager.mark_status(staging_id, payload.status)


@router.delete("/staged/{staging_id}", status_code=status.HTTP_200_OK)
def delete_staged_file(staging_id: str):
    """
    Delete a staged file and its metadata.
    """
    deleted = service.delete_staged(staging_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staged file '{staging_id}' not found."
        )
    return {"success": True, "staging_id": staging_id, "message": "Staged file deleted successfully."}
