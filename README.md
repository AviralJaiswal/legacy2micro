# legacy2micro: Mainframe Modernization Platform

## Module: File Streaming & Ingestion Subsystem

The **File Streaming & Ingestion Subsystem** is the entry-point data pipeline for the Mainframe Modernization Platform. It ingests legacy source files (such as COBOL programs `.cob`, `.cbl`, copybooks `.cpy`, SQL/precompiled COBOL `.pco`, `.sqb`, and JCL scripts `.jcl`) and prepares them safely as validated, staged inputs for downstream parsing.

---

### Architecture & Pipeline Flow

```text
  Source File (COBOL, Copybook, JCL)
                 │
                 ▼
  ┌─────────────────────────────────────────────────────────┐
  │ File Streaming API / Service (Async / Sync)             │
  └──────────────────────────────┬──────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────┐
  │ Pre-Stream & In-Stream Validation                       │
  │  • Filename sanitization & path-traversal prevention    │
  │  • Extension & legacy classification validation        │
  │  • Binary & executable header detection (MZ, ELF, Zip)  │
  │  • Empty file rejection & size limit enforcement       │
  └──────────────────────────────┬──────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────┐
  │ Chunk Stream Processor                                  │
  │  • Low-memory chunk-by-chunk piping (e.g. 64KB buffers) │
  │  • On-the-fly SHA-256 checksum computation              │
  │  • Real-time byte tracking & error rollback             │
  └──────────────────────────────┬──────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────┐
  │ Staging Storage & Manifest Manager                      │
  │  • Dedicated staging workspace storage/staging/<id>/    │
  │  • Atomic staging commit and rollback                   │
  │  • Metadata manifest generation (manifest.json)         │
  └──────────────────────────────┬──────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────┐
  │ Future Parser Service Interface                         │
  │  • Decoupled file handle & line/chunk stream access     │
  │  • Manifest metadata contract (to_parser_input)         │
  │  • Lifecycle status tracking (READY -> IN_PARSING ->    │
  │    CONSUMED)                                            │
  └─────────────────────────────────────────────────────────┘
```

---

### Key Features

1. **True Low-Memory Streaming**: Files are processed and staged chunk-by-chunk without loading large legacy codebases entirely into memory.
2. **Stream-Aware Validation**:
   - **Filename Sanitization**: Automatically cleanses filenames and neutralizes directory traversal (`../../`, reserved OS words).
   - **Legacy Type Detection**: Classifies `.cbl`, `.cob`, `.cpy`, `.pco`, `.sqb`, `.jcl` into appropriate `LegacyFileType` enums.
   - **Binary Rejection**: Inspects initial bytes to reject binary headers (PE, ELF, Mach-O, ZIP, etc.).
   - **Size Limits**: Configurable max file size, min file size, and streaming chunk buffer sizes.
3. **Safe Staging Storage & Manifests**:
   - Files are stored in isolated per-asset directories under `storage/staging/<staging_id>/`.
   - Alongside each source file, a structured `manifest.json` tracks checksums, line counts, encoding, original/sanitized names, and lifecycle states.
4. **Parser Service Consumer Contract**:
   - Downstream Parser Service can consume staged files directly via the Python API (`open_parser_stream(staging_id)`, `get_staged_file_path(staging_id)`, `mark_consumed(staging_id)`) or REST endpoints.
   - The file streaming logic is completely decoupled from future Tree-sitter / CST / IR parser implementations.

---

### Project Structure

```text
legacy2micro/
├── pyproject.toml               # Build configuration, metadata & pytest config
├── README.md                    # Subsystem documentation & architecture guide
├── .gitignore                   # Ignored files, temp storage, and caches
├── src/
│   └── legacy2micro/
│       ├── __init__.py          # Package root
│       ├── config.py            # Pydantic BaseSettings (directories, limits, extensions)
│       ├── exceptions.py        # Exception hierarchy for validation & storage errors
│       ├── models/
│       │   ├── __init__.py
│       │   └── manifest.py      # StagedFileManifest, LegacyFileType, StagingStatus
│       ├── validation/
│       │   ├── __init__.py
│       │   ├── rules.py         # Filename sanitization, binary checking, extension check
│       │   └── validator.py     # FileStreamValidator stream-aware validation pipeline
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── base.py          # BaseStorageBackend abstract interface
│       │   └── staging.py       # StagingStorageManager (manifests, atomic moves, streams)
│       ├── streaming/
│       │   ├── __init__.py
│       │   ├── processor.py     # Chunked stream processor with on-the-fly hashing
│       │   └── service.py       # FileStreamingService high-level orchestrator
│       └── api/
│           ├── __init__.py
│           ├── app.py           # FastAPI application & exception handlers
│           ├── routes.py        # REST API endpoints
│           └── schemas.py       # Request & response Pydantic schemas
└── tests/
    ├── conftest.py              # Pytest fixtures and sample legacy source files
    ├── unit/
    │   ├── test_validation.py   # Filename, extension, binary, size validation tests
    │   ├── test_storage.py      # Staging storage, manifest lifecycle, cleanup tests
    │   └── test_streaming.py    # Chunk stream processing, async stream, hash tests
    └── integration/
        └── test_api.py          # Full FastAPI REST endpoint integration tests
```

---

### REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/files/upload` | Stream, validate, and stage a single legacy source file |
| `POST` | `/api/v1/files/upload-batch` | Batch stream and stage multiple legacy source files |
| `GET` | `/api/v1/files/staged` | List all staged files (optional `?status=` filter) |
| `GET` | `/api/v1/files/staged/{staging_id}` | Retrieve metadata manifest for a staged file |
| `GET` | `/api/v1/files/staged/{staging_id}/download` | Download / stream the staged file |
| `PATCH`| `/api/v1/files/staged/{staging_id}/status` | Update staging lifecycle status (`IN_PARSING`, `CONSUMED`) |
| `DELETE`| `/api/v1/files/staged/{staging_id}` | Delete a staged file and its manifest |
| `GET` | `/health` | Service health check |

---

### Python Service / SDK Usage

The service can be imported directly into Python applications or services without running the HTTP server:

```python
from legacy2micro.streaming.service import FileStreamingService
from legacy2micro.models.manifest import StagingStatus

service = FileStreamingService()

# 1. Ingest from a local file path or stream
manifest = service.ingest_file_path(
    source_file_path="samples/PAYROLL.cbl",
    custom_metadata={"dialect": "IBM_ENTERPRISE_COBOL", "system": "CORE_BANKING"}
)

print(f"Staged Asset ID: {manifest.staging_id}")
print(f"Checksum SHA-256: {manifest.sha256_checksum}")
print(f"Status: {manifest.status}")

# 2. Downstream Parser Service Consumption:
# Retrieve manifest contract
parser_input = manifest.to_parser_input()

# Update status to IN_PARSING
service.mark_in_parsing(manifest.staging_id)

# Open chunk/line stream for Tree-sitter or custom parser
with service.open_parser_stream(manifest.staging_id) as stream:
    for line in stream:
        # Parser consumes line-by-line or buffer chunks
        pass

# Mark as CONSUMED after parsing completion
service.mark_consumed(manifest.staging_id)
```

---

### Running the Application and Tests

#### Running Tests
```bash
python -m pytest
```

#### Running the FastAPI Dev Server
```bash
uvicorn legacy2micro.api.app:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger API documentation will be available at `http://localhost:8000/docs`.
