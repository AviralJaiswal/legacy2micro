"""Core chunked stream processor with on-the-fly hashing and validation."""

import hashlib
from pathlib import Path
from typing import BinaryIO, AsyncIterator, Iterator, Tuple, Optional, Any, Dict
from legacy2micro.config import StreamingSettings, settings as default_settings
from legacy2micro.validation.validator import FileStreamValidator


class StreamProcessingResult:
    """Encapsulates the output of streaming chunks to disk."""

    def __init__(
        self,
        total_bytes: int,
        sha256_checksum: str,
        line_count: int,
        encoding_detected: str = "utf-8"
    ):
        self.total_bytes = total_bytes
        self.sha256_checksum = sha256_checksum
        self.line_count = line_count
        self.encoding_detected = encoding_detected


class StreamProcessor:
    """
    Processes incoming byte streams chunk-by-chunk, piping to a temporary destination
    while performing running validations, size tracking, and SHA-256 hashing without
    loading the entire file into memory.
    """

    def __init__(
        self,
        validator: Optional[FileStreamValidator] = None,
        settings: Optional[StreamingSettings] = None
    ):
        self.settings = settings or default_settings
        self.validator = validator or FileStreamValidator(self.settings)

    def process_sync_stream(
        self,
        chunk_iterator: Iterator[bytes],
        destination_path: Path
    ) -> StreamProcessingResult:
        """
        Process synchronous chunk iterator to destination file.
        """
        hasher = hashlib.sha256()
        total_bytes = 0
        line_count = 0
        is_first = True

        # Open destination in binary write mode
        with open(destination_path, "wb") as dest_file:
            for chunk in chunk_iterator:
                if not chunk:
                    continue

                # Run chunk validation
                self.validator.validate_chunk(chunk, is_first, total_bytes)
                is_first = False

                # Update running state
                total_bytes += len(chunk)
                hasher.update(chunk)
                line_count += chunk.count(b"\n")

                # Write chunk to disk
                dest_file.write(chunk)

        # Post-stream validation (e.g. empty file check)
        self.validator.validate_post_stream(total_bytes)

        return StreamProcessingResult(
            total_bytes=total_bytes,
            sha256_checksum=hasher.hexdigest(),
            line_count=line_count,
            encoding_detected="utf-8"
        )

    async def process_async_stream(
        self,
        async_chunk_iterator: AsyncIterator[bytes],
        destination_path: Path
    ) -> StreamProcessingResult:
        """
        Process asynchronous chunk iterator (e.g. from FastAPI/Starlette UploadFile) to destination file.
        """
        hasher = hashlib.sha256()
        total_bytes = 0
        line_count = 0
        is_first = True

        with open(destination_path, "wb") as dest_file:
            async for chunk in async_chunk_iterator:
                if not chunk:
                    continue

                # Run chunk validation
                self.validator.validate_chunk(chunk, is_first, total_bytes)
                is_first = False

                # Update running state
                total_bytes += len(chunk)
                hasher.update(chunk)
                line_count += chunk.count(b"\n")

                # Write chunk to disk
                dest_file.write(chunk)

        # Post-stream validation
        self.validator.validate_post_stream(total_bytes)

        return StreamProcessingResult(
            total_bytes=total_bytes,
            sha256_checksum=hasher.hexdigest(),
            line_count=line_count,
            encoding_detected="utf-8"
        )
