"""FastAPI Application instance and global error handlers for legacy2micro."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from legacy2micro.api.routes import router as files_router
from legacy2micro.exceptions import (
    FileValidationError,
    InvalidFilenameError,
    InvalidFileTypeError,
    EmptyFileError,
    FileSizeLimitExceededError,
    BinaryFileRejectedError,
    StagedFileNotFoundError,
    StagingStorageError,
    Legacy2MicroError,
)

app = FastAPI(
    title="legacy2micro - Mainframe Modernization File Streaming Service",
    description=(
        "Stream-oriented file ingestion and staging service for legacy COBOL and mainframe assets, "
        "preparing them safely as inputs for the downstream Parser Service."
    ),
    version="0.1.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(files_router)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for container orchestrators and load balancers."""
    return {
        "status": "healthy",
        "service": "legacy2micro-file-streaming",
        "version": "0.1.0"
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "service": "legacy2micro - Mainframe Modernization Platform",
        "module": "File Streaming & Ingestion Service",
        "documentation": "/docs"
    }


# Exception Handlers
@app.exception_handler(FileValidationError)
async def file_validation_exception_handler(request: Request, exc: FileValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, FileSizeLimitExceededError):
        status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    elif isinstance(exc, InvalidFileTypeError):
        status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE

    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": type(exc).__name__,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(StagedFileNotFoundError)
async def staged_not_found_exception_handler(request: Request, exc: StagedFileNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error_code": "StagedFileNotFoundError",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(StagingStorageError)
async def staging_storage_exception_handler(request: Request, exc: StagingStorageError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "StagingStorageError",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(Legacy2MicroError)
async def legacy_error_handler(request: Request, exc: Legacy2MicroError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": type(exc).__name__,
            "message": exc.message,
            "details": exc.details,
        },
    )
