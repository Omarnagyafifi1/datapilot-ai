"""Storage service abstraction for file handling.

Provides a unified interface for storing uploaded files, supporting both
local filesystem storage (development) and Azure Blob Storage (production).
"""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class StorageService(ABC):
    """Abstract base class for file storage backends."""
    
    @abstractmethod
    async def store_file(self, content: bytes, filename: str, content_type: Optional[str] = None) -> str:
        """Store a file and return the stored path/filename."""
        pass
    
    @abstractmethod
    async def retrieve_file(self, filename: str) -> Optional[bytes]:
        """Retrieve file content by filename."""
        pass
    
    @abstractmethod
    async def delete_file(self, filename: str) -> bool:
        """Delete a file by filename. Returns True if deleted."""
        pass
    
    @abstractmethod
    def get_file_url(self, filename: str) -> str:
        """Get a URL or path to access the file."""
        pass
    
    @abstractmethod
    def get_storage_path(self, filename: str) -> str:
        """Get the full path where the file is stored."""
        pass


class LocalStorage(StorageService):
    """Local filesystem storage for development environments."""
    
    def __init__(self, base_dir: Optional[str] = None):
        """Initialize local storage with a base directory.
        
        Args:
            base_dir: Directory to store files. If None, uses settings.UPLOAD_DIR or defaults to ./uploads
        """
        from app.core.config import settings
        
        if base_dir is None:
            base_dir = settings.UPLOAD_DIR or "./uploads"
        
        # Resolve to absolute path if relative
        if not os.path.isabs(base_dir):
            # Get the project root (backend directory parent)
            _file = os.path.abspath(__file__)
            _dir1 = os.path.dirname(_file)
            _dir2 = os.path.dirname(_dir1)
            _dir3 = os.path.dirname(_dir2)
            project_root = _dir3
            base_dir = os.path.join(project_root, base_dir.lstrip("./"))
        
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal attacks."""
        # Remove any path components
        safe_name = os.path.basename(filename)
        # Keep only alphanumeric, dots, dashes, and underscores
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._-")
        # Ensure filename is not empty
        return safe_name if safe_name else "unnamed"
    
    def _generate_unique_filename(self, filename: str) -> str:
        """Generate a unique filename to prevent collisions."""
        name, ext = os.path.splitext(filename)
        # Add hash suffix for uniqueness
        hash_suffix = hashlib.sha256(os.urandom(8)).hexdigest()[:8]
        return f"{name}_{hash_suffix}{ext}"
    
    async def store_file(self, content: bytes, filename: str, content_type: Optional[str] = None) -> str:
        """Store file content in the local uploads directory."""
        safe_name = self._sanitize_filename(filename)
        unique_name = self._generate_unique_filename(safe_name)
        filepath = os.path.join(self.base_dir, unique_name)
        
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Write file
        with open(filepath, "wb") as f:
            f.write(content)
        
        return unique_name
    
    async def retrieve_file(self, filename: str) -> Optional[bytes]:
        """Retrieve file content from the local storage."""
        safe_name = self._sanitize_filename(filename)
        filepath = os.path.join(self.base_dir, safe_name)
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, "rb") as f:
            return f.read()
    
    async def delete_file(self, filename: str) -> bool:
        """Delete a file from local storage."""
        safe_name = self._sanitize_filename(filename)
        filepath = os.path.join(self.base_dir, safe_name)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    
    def get_file_url(self, filename: str) -> str:
        """Get the local file path for the stored file."""
        safe_name = self._sanitize_filename(filename)
        return os.path.join(self.base_dir, safe_name)
    
    def get_storage_path(self, filename: str) -> str:
        """Get the full filesystem path for the stored file."""
        safe_name = self._sanitize_filename(filename)
        return os.path.join(self.base_dir, safe_name)


class AzureBlobStorage(StorageService):
    """Azure Blob Storage backend for production environments.
    
    This is a stub implementation - actual migration will be done in Phase 2.
    """
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        account_name: Optional[str] = None,
        container_name: Optional[str] = None,
    ):
        """Initialize Azure Blob Storage client.
        
        Args:
            connection_string: Azure Storage connection string
            account_name: Azure Storage account name
            container_name: Blob container name for uploads
        """
        from app.core.config import settings
        
        self.connection_string = connection_string or settings.AZURE_STORAGE_CONNECTION_STRING
        self.account_name = account_name or settings.AZURE_STORAGE_ACCOUNT_NAME
        self.container_name = container_name or settings.AZURE_STORAGE_CONTAINER_NAME
        self._client = None
    
    def _get_client(self):
        """Get or create the Azure Blob Storage client."""
        if self._client is None:
            raise NotImplementedError(
                "Azure Blob Storage requires Azure Storage SDK installation "
                "and will be fully implemented in Phase 2 of Azure migration."
            )
        return self._client
    
    async def store_file(self, content: bytes, filename: str, content_type: Optional[str] = None) -> str:
        """Store file in Azure Blob Storage. Not yet implemented."""
        raise NotImplementedError(
            "Azure Blob Storage upload is not yet implemented. "
            "This will be completed in Phase 2 of Azure migration."
        )
    
    async def retrieve_file(self, filename: str) -> Optional[bytes]:
        """Retrieve file from Azure Blob Storage. Not yet implemented."""
        raise NotImplementedError(
            "Azure Blob Storage retrieval is not yet implemented. "
            "This will be completed in Phase 2 of Azure migration."
        )
    
    async def delete_file(self, filename: str) -> bool:
        """Delete file from Azure Blob Storage. Not yet implemented."""
        raise NotImplementedError(
            "Azure Blob Storage deletion is not yet implemented. "
            "This will be completed in Phase 2 of Azure migration."
        )
    
    def get_file_url(self, filename: str) -> str:
        """Get the blob URL for the stored file. Not yet implemented."""
        raise NotImplementedError(
            "Azure Blob Storage URL generation is not yet implemented. "
            "This will be completed in Phase 2 of Azure migration."
        )
    
    def get_storage_path(self, filename: str) -> str:
        """Get the blob path for the stored file. Not yet implemented."""
        raise NotImplementedError(
            "Azure Blob Storage path retrieval is not yet implemented. "
            "This will be completed in Phase 2 of Azure migration."
        )


def get_storage() -> StorageService:
    """Factory function to get the appropriate storage backend.
    
    Returns LocalStorage by default, AzureBlobStorage when STORAGE_TYPE=azure.
    """
    from app.core.config import settings
    
    storage_type = settings.STORAGE_TYPE.lower() if settings.STORAGE_TYPE else "local"
    
    if storage_type == "azure":
        return AzureBlobStorage(
            connection_string=settings.AZURE_STORAGE_CONNECTION_STRING,
            account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
            container_name=settings.AZURE_STORAGE_CONTAINER_NAME,
        )
    
    return LocalStorage()


# Convenience singleton for easy importing
_storage_instance: Optional[StorageService] = None


def get_storage_singleton() -> StorageService:
    """Get a cached storage instance (singleton pattern)."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = get_storage()
    return _storage_instance