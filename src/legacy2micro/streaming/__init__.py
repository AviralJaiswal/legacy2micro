"""Streaming package for legacy2micro."""

from legacy2micro.streaming.processor import StreamProcessor, StreamProcessingResult
from legacy2micro.streaming.service import FileStreamingService

__all__ = [
    "StreamProcessor",
    "StreamProcessingResult",
    "FileStreamingService",
]
