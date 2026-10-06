"""Pytest fixtures for legacy2micro test suite."""

import pytest
from pathlib import Path
from legacy2micro.config import StreamingSettings
from legacy2micro.storage.staging import StagingStorageManager
from legacy2micro.streaming.service import FileStreamingService
from legacy2micro.validation.validator import FileStreamValidator


SAMPLE_COBOL_PROGRAM = b"""       IDENTIFICATION DIVISION.
       PROGRAM-ID. HELLO-WORLD.
       ENVIRONMENT DIVISION.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-GREETING PIC X(20) VALUE "HELLO MAINFRAME".
       PROCEDURE DIVISION.
       0000-MAIN.
           DISPLAY WS-GREETING.
           STOP RUN.
"""

SAMPLE_COPYBOOK = b"""      * CUSTOMER RECORD COPYBOOK
       01  CUSTOMER-RECORD.
           05  CUST-ID        PIC X(10).
           05  CUST-NAME      PIC X(30).
           05  CUST-BALANCE   PIC 9(7)V99.
"""


@pytest.fixture
def temp_settings(tmp_path: Path) -> StreamingSettings:
    """Create test settings using temporary directories with small limits for testing."""
    return StreamingSettings(
        base_storage_dir=tmp_path,
        staging_dir=tmp_path / "staging",
        temp_dir=tmp_path / "temp",
        chunk_size_bytes=64,  # Small chunk size to test multiple chunk iterations
        max_file_size_bytes=1024 * 1024,  # 1 MB max in tests
        min_file_size_bytes=1,
    )


@pytest.fixture
def test_storage(temp_settings: StreamingSettings) -> StagingStorageManager:
    """Staging storage manager with test settings."""
    return StagingStorageManager(temp_settings)


@pytest.fixture
def test_validator(temp_settings: StreamingSettings) -> FileStreamValidator:
    """Validator initialized with test settings."""
    return FileStreamValidator(temp_settings)


@pytest.fixture
def test_service(
    temp_settings: StreamingSettings,
    test_storage: StagingStorageManager,
    test_validator: FileStreamValidator
) -> FileStreamingService:
    """FileStreamingService initialized with temporary fixtures."""
    return FileStreamingService(
        settings=temp_settings,
        storage_manager=test_storage,
        validator=test_validator,
    )
