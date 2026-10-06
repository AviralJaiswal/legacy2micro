"""Validation rules and utilities for legacy source file ingestion."""

import os
import re
from pathlib import Path
from typing import Set, Tuple
from legacy2micro.exceptions import (
    InvalidFilenameError,
    InvalidFileTypeError,
    BinaryFileRejectedError,
)

# Known binary headers to immediately reject (PE/EXE, ELF, Mach-O, Zip/Jar, PDF, etc.)
DISALLOWED_MAGIC_HEADERS = [
    (b"MZ", "Windows PE Executable / DLL"),
    (b"\x7fELF", "Linux ELF Executable / Binary"),
    (b"\xca\xfe\xba\xbe", "Mach-O Universal Binary / Java Class"),
    (b"\xfe\xed\xfa\xce", "Mach-O 32-bit Binary"),
    (b"\xfe\xed\xfa\xcf", "Mach-O 64-bit Binary"),
    (b"%PDF", "PDF Document"),
    (b"PK\x03\x04", "Zip Archive"),
    (b"\x1f\x8b\x08", "Gzip Archive"),
    (b"7z\xbc\xaf\x27\x1c", "7-Zip Archive"),
    (b"Rar!\x1a\x07", "RAR Archive"),
]

# Prohibited filename patterns & reserved Windows names
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

# Regex to strip non-safe filename characters
SAFE_FILENAME_REGEX = re.compile(r"[^\w\-. ]")


def sanitize_and_validate_filename(filename: str) -> Tuple[str, str]:
    """
    Validate and sanitize the raw filename.
    
    Returns:
        Tuple[str, str]: (sanitized_filename, normalized_extension)
    
    Raises:
        InvalidFilenameError: If filename is missing, blank, or violates safety rules.
    """
    if not filename or not str(filename).strip():
        raise InvalidFilenameError("Filename cannot be empty or blank.")

    raw_name = str(filename).strip()

    # Reject null byte injection
    if "\x00" in raw_name:
        raise InvalidFilenameError("Filename contains invalid null byte character.")

    # Extract base name to strip path traversal like ../../ or C:\path\
    base_name = os.path.basename(raw_name)
    # Also handle forward/backward slashes explicitly
    base_name = base_name.replace("/", os.sep).replace("\\", os.sep).split(os.sep)[-1].strip()

    if not base_name or base_name in {".", ".."}:
        raise InvalidFilenameError(f"Invalid filename: '{filename}' resolves to an empty or relative path.")

    # Check for reserved filenames on Windows
    root_name, ext = os.path.splitext(base_name)
    if root_name.upper() in RESERVED_NAMES:
        raise InvalidFilenameError(f"Filename '{base_name}' uses a reserved system identifier.")

    # Sanitize characters
    sanitized = SAFE_FILENAME_REGEX.sub("_", base_name).strip()
    if not sanitized:
        raise InvalidFilenameError(f"Filename '{filename}' does not contain any valid characters after sanitization.")

    # Ensure extension starts with a dot and is lowercase
    normalized_ext = ext.lower() if ext else ""

    return sanitized, normalized_ext


def validate_file_extension(extension: str, allowed_extensions: Set[str]) -> None:
    """
    Validate that the file extension is in the set of allowed legacy extensions.
    
    Raises:
        InvalidFileTypeError: If extension is not allowed.
    """
    normalized_allowed = {ext.lower() for ext in allowed_extensions}
    if not extension or extension.lower() not in normalized_allowed:
        allowed_list = sorted(list(normalized_allowed))
        raise InvalidFileTypeError(
            f"Unsupported file extension '{extension}'. "
            f"Allowed extensions for legacy source ingestion: {', '.join(allowed_list)}",
            details={"received_extension": extension, "allowed_extensions": allowed_list}
        )


def inspect_chunk_for_binary_content(chunk: bytes) -> None:
    """
    Inspect the initial chunk of data to verify it is text/source code
    and not an executable binary, archive, or corrupted binary payload.
    
    Raises:
        BinaryFileRejectedError: If disallowed binary headers or high null-byte density is detected.
    """
    if not chunk:
        return

    # Check known binary magic bytes
    for magic, desc in DISALLOWED_MAGIC_HEADERS:
        if chunk.startswith(magic):
            raise BinaryFileRejectedError(
                f"File content rejected: detected binary signature ({desc}). Only plaintext legacy source code is supported."
            )

    # Check null byte ratio in first chunk (text/COBOL files should not be dominated by null bytes)
    # Note: EBCDIC-converted or standard ASCII/UTF-8 COBOL code should be text.
    null_count = chunk.count(b"\x00")
    if len(chunk) > 0 and (null_count / len(chunk)) > 0.15:
        raise BinaryFileRejectedError(
            "File contains high concentration of null bytes (binary content detected). "
            "Only valid legacy text source files are permitted."
        )
