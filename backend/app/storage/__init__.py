"""Storage abstraction layer for DataPilot AI.

This module provides a unified interface for file storage operations,
supporting both local filesystem and Azure Blob Storage backends.

Usage:
    from app.storage import get_storage, StorageService
    
    storage = get_storage()
    # In development (local): stores to ./uploads/
    # In production (azure): stores to Azure Blob Storage
    
    await storage.store_file(content, filename, content_type)
    url = await storage.get_file_url(filename)
"""

from .storage_service import StorageService, LocalStorage, AzureBlobStorage, get_storage

__all__ = [
    "StorageService",
    "LocalStorage", 
    "AzureBlobStorage",
    "get_storage",
]