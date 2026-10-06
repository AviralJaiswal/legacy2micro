"""Unit tests for filename, extension, binary inspection, and size validation."""

import pytest
from legacy2micro.config import StreamingSettings
from legacy2micro.exceptions import (
    InvalidFilenameError,
    InvalidFileTypeError,
    BinaryFileRejectedError,
    EmptyFileError,
    FileSizeLimitExceededError,
)
from legacy2micro.models.manifest import LegacyFileType
from legacy2micro.validation.rules import (
    sanitize_and_validate_filename,
    validate_file_extension,
    inspect_chunk_for_binary_content,
)
from legacy2micro.validation.validator import FileStreamValidator


def test_sanitize_valid_filenames():
    sanitized, ext = sanitize_and_validate_filename("PAYROLL.CBL")
    assert sanitized == "PAYROLL.CBL"
    assert ext == ".cbl"

    sanitized, ext = sanitize_and_validate_filename("cust_rec.cpy")
    assert sanitized == "cust_rec.cpy"
    assert ext == ".cpy"


def test_sanitize_path_traversal():
    sanitized, ext = sanitize_and_validate_filename("../../etc/passwd/MAINPROG.cob")
    assert sanitized == "MAINPROG.cob"
    assert ext == ".cob"

    sanitized, ext = sanitize_and_validate_filename("..\\..\\Windows\\System32\\TEST.CBL")
    assert sanitized == "TEST.CBL"
    assert ext == ".cbl"


def test_sanitize_invalid_or_blank_filenames():
    with pytest.raises(InvalidFilenameError):
        sanitize_and_validate_filename("")

    with pytest.raises(InvalidFilenameError):
        sanitize_and_validate_filename("   ")

    with pytest.raises(InvalidFilenameError):
        sanitize_and_validate_filename("../")

    with pytest.raises(InvalidFilenameError):
        sanitize_and_validate_filename("file\x00name.cbl")


def test_validate_allowed_file_extensions():
    allowed = {".cbl", ".cob", ".cpy", ".jcl"}
    validate_file_extension(".cbl", allowed)
    validate_file_extension(".COB", allowed)
    validate_file_extension(".cpy", allowed)

    with pytest.raises(InvalidFileTypeError):
        validate_file_extension(".exe", allowed)

    with pytest.raises(InvalidFileTypeError):
        validate_file_extension(".pdf", allowed)


def test_legacy_file_type_mapping():
    assert LegacyFileType.from_extension(".cbl") == LegacyFileType.COBOL_SOURCE
    assert LegacyFileType.from_extension(".cob") == LegacyFileType.COBOL_SOURCE
    assert LegacyFileType.from_extension(".cpy") == LegacyFileType.COBOL_COPYBOOK
    assert LegacyFileType.from_extension(".jcl") == LegacyFileType.JCL_SCRIPT
    assert LegacyFileType.from_extension(".unknown") == LegacyFileType.UNKNOWN


def test_inspect_binary_headers():
    # Valid text
    inspect_chunk_for_binary_content(b"IDENTIFICATION DIVISION.")

    # Windows PE EXE
    with pytest.raises(BinaryFileRejectedError):
        inspect_chunk_for_binary_content(b"MZ\x90\x00\x03\x00\x00\x00")

    # ELF Binary
    with pytest.raises(BinaryFileRejectedError):
        inspect_chunk_for_binary_content(b"\x7fELF\x02\x01\x01\x00")

    # Zip Archive
    with pytest.raises(BinaryFileRejectedError):
        inspect_chunk_for_binary_content(b"PK\x03\x04\x14\x00\x00\x00")


def test_validator_size_limits(temp_settings: StreamingSettings):
    validator = FileStreamValidator(temp_settings)

    # Pre-stream
    sanitized, ext, legacy_type = validator.validate_pre_stream("ACCOUNT.cbl")
    assert sanitized == "ACCOUNT.cbl"
    assert ext == ".cbl"
    assert legacy_type == LegacyFileType.COBOL_SOURCE

    # Running chunk within limit
    validator.validate_chunk(b"A" * 500, is_first_chunk=True, current_total_bytes=0)

    # Exceeding limit
    with pytest.raises(FileSizeLimitExceededError):
        validator.validate_chunk(b"B" * (temp_settings.max_file_size_bytes + 1), is_first_chunk=False, current_total_bytes=0)

    # Empty file post-stream
    with pytest.raises(EmptyFileError):
        validator.validate_post_stream(0)
