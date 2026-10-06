"""Storage package for legacy2micro."""

from legacy2micro.storage.base import BaseStorageBackend
from legacy2micro.storage.staging import StagingStorageManager

__all__ = [
    "BaseStorageBackend",
    "StagingStorageManager",
]
