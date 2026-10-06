"""Integration tests for File Streaming REST API."""

import io
import json
import pytest
from fastapi.testclient import TestClient
from legacy2micro.api.app import app
from tests.conftest import SAMPLE_COBOL_PROGRAM, SAMPLE_COPYBOOK

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "legacy2micro-file-streaming"


def test_upload_single_cobol_file():
    files = {
        "file": ("MAINPROG.cbl", io.BytesIO(SAMPLE_COBOL_PROGRAM), "text/plain")
    }
    data = {
        "metadata_json": json.dumps({"module": "PAYROLL", "author": "Modernization Team"})
    }

    response = client.post("/api/v1/files/upload", files=files, data=data)
    assert response.status_code == 201
    res = response.json()

    assert res["success"] is True
    assert res["sanitized_filename"] == "MAINPROG.cbl"
    assert res["file_type"] == "COBOL_SOURCE"
    assert res["file_size_bytes"] == len(SAMPLE_COBOL_PROGRAM)
    assert res["status"] == "READY_FOR_PARSER"
    assert res["metadata"]["module"] == "PAYROLL"

    staging_id = res["staging_id"]

    # Retrieve manifest
    get_res = client.get(f"/api/v1/files/staged/{staging_id}")
    assert get_res.status_code == 200
    assert get_res.json()["staging_id"] == staging_id

    # Download staged file
    down_res = client.get(f"/api/v1/files/staged/{staging_id}/download")
    assert down_res.status_code == 200
    assert down_res.content == SAMPLE_COBOL_PROGRAM

    # Update status to IN_PARSING
    status_res = client.patch(
        f"/api/v1/files/staged/{staging_id}/status",
        json={"status": "IN_PARSING"}
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "IN_PARSING"

    # Delete staged file
    del_res = client.delete(f"/api/v1/files/staged/{staging_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


def test_upload_batch_files():
    files = [
        ("files", ("PROG1.cob", io.BytesIO(SAMPLE_COBOL_PROGRAM), "text/plain")),
        ("files", ("COPY1.cpy", io.BytesIO(SAMPLE_COPYBOOK), "text/plain")),
    ]

    response = client.post("/api/v1/files/upload-batch", files=files)
    assert response.status_code == 201
    res = response.json()

    assert res["success"] is True
    assert res["total_files"] == 2
    assert res["successful_count"] == 2
    assert len(res["files"]) == 2

    # Cleanup created staged files
    for item in res["files"]:
        client.delete(f"/api/v1/files/staged/{item['staging_id']}")


def test_reject_unsupported_file_type():
    files = {
        "file": ("script.py", io.BytesIO(b"print('invalid')"), "text/x-python")
    }
    response = client.post("/api/v1/files/upload", files=files)
    assert response.status_code == 415
    res = response.json()
    assert res["error_code"] == "InvalidFileTypeError"


def test_reject_empty_file_upload():
    files = {
        "file": ("EMPTY.cbl", io.BytesIO(b""), "text/plain")
    }
    response = client.post("/api/v1/files/upload", files=files)
    assert response.status_code == 400
    res = response.json()
    assert res["error_code"] == "EmptyFileError"


def test_reject_binary_file_upload():
    # PE Header MZ
    binary_content = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 100
    files = {
        "file": ("MALICIOUS.cbl", io.BytesIO(binary_content), "application/octet-stream")
    }
    response = client.post("/api/v1/files/upload", files=files)
    assert response.status_code == 400
    res = response.json()
    assert res["error_code"] == "BinaryFileRejectedError"


def test_list_staged_endpoint():
    response = client.get("/api/v1/files/staged")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
