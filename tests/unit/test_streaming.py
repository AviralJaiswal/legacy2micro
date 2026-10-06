"""Unit tests for chunked stream processor and FileStreamingService."""

import hashlib
import pytest
from pathlib import Path
from legacy2micro.exceptions import (
    EmptyFileError,
    FileSizeLimitExceededError,
    InvalidFileTypeError,
)
from legacy2micro.models.manifest import LegacyFileType, StagingStatus
from legacy2micro.streaming.service import FileStreamingService
from tests.conftest import SAMPLE_COBOL_PROGRAM, SAMPLE_COPYBOOK


def test_ingest_sync_stream(test_service: FileStreamingService):
    def chunk_gen():
        for i in range(0, len(SAMPLE_COBOL_PROGRAM), 32):
            yield SAMPLE_COBOL_PROGRAM[i:i+32]

    manifest = test_service.ingest_sync_stream(
        filename="HELLO.CBL",
        chunk_iterator=chunk_gen(),
        custom_metadata={"author": "modernization_team", "dialect": "IBM_ENTERPRISE_COBOL"},
    )

    expected_hash = hashlib.sha256(SAMPLE_COBOL_PROGRAM).hexdigest()

    assert manifest.sanitized_filename == "HELLO.CBL"
    assert manifest.file_type == LegacyFileType.COBOL_SOURCE
    assert manifest.file_size_bytes == len(SAMPLE_COBOL_PROGRAM)
    assert manifest.sha256_checksum == expected_hash
    assert manifest.status == StagingStatus.READY_FOR_PARSER
    assert manifest.metadata.get("dialect") == "IBM_ENTERPRISE_COBOL"

    # Verify parser stream access
    with test_service.open_parser_stream(manifest.staging_id) as stream:
        read_data = stream.read()
        assert read_data == SAMPLE_COBOL_PROGRAM


def test_ingest_async_stream(test_service: FileStreamingService):
    import asyncio

    async def run_test():
        async def async_chunk_gen():
            for i in range(0, len(SAMPLE_COPYBOOK), 20):
                yield SAMPLE_COPYBOOK[i:i+20]

        manifest = await test_service.ingest_async_stream(
            filename="CUSTOMER.CPY",
            async_chunk_iterator=async_chunk_gen(),
        )

        expected_hash = hashlib.sha256(SAMPLE_COPYBOOK).hexdigest()

        assert manifest.sanitized_filename == "CUSTOMER.CPY"
        assert manifest.file_type == LegacyFileType.COBOL_COPYBOOK
        assert manifest.file_size_bytes == len(SAMPLE_COPYBOOK)
        assert manifest.sha256_checksum == expected_hash

    asyncio.run(run_test())


def test_ingest_from_file_path(test_service: FileStreamingService, tmp_path: Path):
    source_file = tmp_path / "SAMPLE.cbl"
    source_file.write_bytes(SAMPLE_COBOL_PROGRAM)

    manifest = test_service.ingest_file_path(source_file)
    assert manifest.file_size_bytes == len(SAMPLE_COBOL_PROGRAM)
    assert manifest.sanitized_filename == "SAMPLE.cbl"


def test_reject_empty_stream(test_service: FileStreamingService):
    def empty_gen():
        yield b""

    with pytest.raises(EmptyFileError):
        test_service.ingest_sync_stream("EMPTY.CBL", empty_gen())


def test_reject_oversized_stream(test_service: FileStreamingService):
    # Set limit via test_service settings
    test_service.settings.max_file_size_bytes = 100

    def oversized_gen():
        yield b"A" * 60
        yield b"B" * 60  # Total 120 > 100

    with pytest.raises(FileSizeLimitExceededError):
        test_service.ingest_sync_stream("BIG.CBL", oversized_gen())


def test_reject_invalid_extension(test_service: FileStreamingService):
    def chunk_gen():
        yield b"print('hello')"

    with pytest.raises(InvalidFileTypeError):
        test_service.ingest_sync_stream("script.py", chunk_gen())
