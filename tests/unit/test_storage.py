"""Unit tests for staging storage, manifest serialization, and parser retrieval."""

import json
from pathlib import Path
import pytest
from legacy2micro.exceptions import StagedFileNotFoundError
from legacy2micro.models.manifest import StagedFileManifest, StagingStatus, LegacyFileType
from legacy2micro.storage.staging import StagingStorageManager


def test_staging_save_and_retrieve(test_storage: StagingStorageManager, tmp_path: Path):
    staging_id = "test-uuid-12345"
    temp_file = test_storage.get_temp_file_path(staging_id)
    temp_file.write_bytes(b"       IDENTIFICATION DIVISION.\n")

    manifest = StagedFileManifest(
        staging_id=staging_id,
        original_filename="DEMO.CBL",
        sanitized_filename="DEMO.CBL",
        file_extension=".cbl",
        file_type=LegacyFileType.COBOL_SOURCE,
        file_size_bytes=32,
        sha256_checksum="dummyhash123",
        status=StagingStatus.READY_FOR_PARSER,
        staged_file_path="",
        line_count=1,
    )

    dest_path = test_storage.save_staged_file(staging_id, temp_file, manifest)
    assert dest_path.exists()
    assert not temp_file.exists()

    # Retrieve manifest
    loaded_manifest = test_storage.get_manifest(staging_id)
    assert loaded_manifest.staging_id == staging_id
    assert loaded_manifest.sanitized_filename == "DEMO.CBL"
    assert loaded_manifest.status == StagingStatus.READY_FOR_PARSER

    # Open stream for parser
    with test_storage.open_stream(staging_id) as stream:
        content = stream.read()
        assert b"IDENTIFICATION DIVISION." in content


def test_update_status_lifecycle(test_storage: StagingStorageManager):
    staging_id = "lifecycle-uuid"
    temp_file = test_storage.get_temp_file_path(staging_id)
    temp_file.write_bytes(b"DATA DIVISION.")

    manifest = StagedFileManifest(
        staging_id=staging_id,
        original_filename="DATA.cpy",
        sanitized_filename="DATA.cpy",
        file_extension=".cpy",
        file_type=LegacyFileType.COBOL_COPYBOOK,
        file_size_bytes=14,
        sha256_checksum="hashxyz",
        staged_file_path="",
    )

    test_storage.save_staged_file(staging_id, temp_file, manifest)

    # Transition to IN_PARSING
    m1 = test_storage.mark_status(staging_id, StagingStatus.IN_PARSING)
    assert m1.status == StagingStatus.IN_PARSING

    # Transition to CONSUMED
    m2 = test_storage.mark_status(staging_id, StagingStatus.CONSUMED)
    assert m2.status == StagingStatus.CONSUMED


def test_list_and_delete_staged(test_storage: StagingStorageManager):
    staging_id = "delete-me-uuid"
    temp_file = test_storage.get_temp_file_path(staging_id)
    temp_file.write_bytes(b"PROCEDURE DIVISION.")

    manifest = StagedFileManifest(
        staging_id=staging_id,
        original_filename="PROC.cbl",
        sanitized_filename="PROC.cbl",
        file_extension=".cbl",
        file_type=LegacyFileType.COBOL_SOURCE,
        file_size_bytes=19,
        sha256_checksum="hashproc",
        staged_file_path="",
    )

    test_storage.save_staged_file(staging_id, temp_file, manifest)

    staged_list = test_storage.list_staged()
    assert any(m.staging_id == staging_id for m in staged_list)

    # Delete
    assert test_storage.delete_staged(staging_id) is True
    assert test_storage.delete_staged(staging_id) is False

    with pytest.raises(StagedFileNotFoundError):
        test_storage.get_manifest(staging_id)
