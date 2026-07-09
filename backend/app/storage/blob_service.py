from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class BlobService:
    """Abstraction layer for file storage.

    Production: Azure Blob Storage (when AZURE_STORAGE_CONNECTION_STRING is set).
    Development: local filesystem under UPLOAD_DIR (default: ./uploads).
    """

    def __init__(self) -> None:
        self._conn_string = (settings.AZURE_STORAGE_CONNECTION_STRING or "").strip()
        self._container = (settings.AZURE_STORAGE_CONTAINER or "datasets").strip()
        self._use_azure = bool(self._conn_string)
        self._local_root = self._resolve_local_root()
        self._client = None
        if self._use_azure:
            self._init_azure_client()

    # ── Public API ─────────────────────────────────────────────────────

    async def upload(self, source_path: str, blob_name: str, content_type: Optional[str] = None) -> str:
        """Upload a file. Returns the URL or local path."""
        if self._use_azure:
            return await self._upload_azure(source_path, blob_name, content_type)
        return self._upload_local(source_path, blob_name)

    async def upload_bytes(self, data: bytes, blob_name: str, content_type: Optional[str] = None) -> str:
        """Upload raw bytes. Returns the URL or local path."""
        if self._use_azure:
            return await self._upload_bytes_azure(data, blob_name, content_type)
        return self._upload_bytes_local(data, blob_name)

    async def download(self, blob_name: str, destination: str) -> str:
        """Download a file to a local path. Returns the local path."""
        if self._use_azure:
            return await self._download_azure(blob_name, destination)
        return self._download_local(blob_name, destination)

    async def delete(self, blob_name: str) -> None:
        """Delete a stored file."""
        if self._use_azure:
            await self._delete_azure(blob_name)
        else:
            self._delete_local(blob_name)

    async def exists(self, blob_name: str) -> bool:
        """Check if a blob exists."""
        if self._use_azure:
            return await self._exists_azure(blob_name)
        return await self._exists_local(blob_name)

    def get_local_path(self, blob_name: str) -> str:
        """Get the full local path for a blob name (for direct filesystem access)."""
        return os.path.join(self._local_root, blob_name)

    @property
    def use_azure(self) -> bool:
        return self._use_azure

    # ── Azure Blob Storage implementation ─────────────────────────────

    def _init_azure_client(self) -> None:
        try:
            from azure.storage.blob import BlobServiceClient
            self._client = BlobServiceClient.from_connection_string(self._conn_string)
            # Ensure container exists
            try:
                self._client.create_container(self._container)
            except Exception:
                pass  # container already exists
            logger.info("BlobService: Azure Blob Storage initialized (container=%s)", self._container)
        except ImportError:
            logger.warning("BlobService: azure-storage-blob not installed, falling back to local filesystem")
            self._use_azure = False

    async def _upload_azure(self, source_path: str, blob_name: str, content_type: Optional[str] = None) -> str:
        from azure.storage.blob import ContentSettings
        blob_client = self._client.get_blob_client(container=self._container, blob=blob_name)
        with open(source_path, "rb") as data:
            kwargs = {"overwrite": True}
            if content_type:
                kwargs["content_settings"] = ContentSettings(content_type=content_type)
            blob_client.upload_blob(data, **kwargs)
        return blob_client.url

    async def _upload_bytes_azure(self, data: bytes, blob_name: str, content_type: Optional[str] = None) -> str:
        from azure.storage.blob import ContentSettings
        blob_client = self._client.get_blob_client(container=self._container, blob=blob_name)
        kwargs = {"overwrite": True}
        if content_type:
            kwargs["content_settings"] = ContentSettings(content_type=content_type)
        blob_client.upload_blob(data, **kwargs)
        return blob_client.url

    async def _download_azure(self, blob_name: str, destination: str) -> str:
        blob_client = self._client.get_blob_client(container=self._container, blob=blob_name)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, "wb") as f:
            stream = blob_client.download_blob()
            f.write(stream.readall())
        return destination

    async def _delete_azure(self, blob_name: str) -> None:
        blob_client = self._client.get_blob_client(container=self._container, blob=blob_name)
        blob_client.delete_blob()

    async def _exists_azure(self, blob_name: str) -> bool:
        blob_client = self._client.get_blob_client(container=self._container, blob=blob_name)
        try:
            blob_client.get_blob_properties()
            return True
        except Exception:
            return False

    # ── Local filesystem implementation ────────────────────────────────

    def _resolve_local_root(self) -> str:
        upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        if not os.path.isabs(upload_dir):
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            upload_dir = os.path.join(os.path.dirname(backend_dir), upload_dir.lstrip("./"))
        os.makedirs(upload_dir, exist_ok=True)
        return upload_dir

    def _upload_local(self, source_path: str, blob_name: str) -> str:
        dest = os.path.join(self._local_root, blob_name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(source_path, dest)
        return dest

    def _upload_bytes_local(self, data: bytes, blob_name: str) -> str:
        dest = os.path.join(self._local_root, blob_name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        return dest

    def _download_local(self, blob_name: str, destination: str) -> str:
        src = os.path.join(self._local_root, blob_name)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(src, destination)
        return destination

    def _delete_local(self, blob_name: str) -> None:
        path = os.path.join(self._local_root, blob_name)
        if os.path.exists(path):
            os.remove(path)

    async def _exists_local(self, blob_name: str) -> bool:
        return os.path.exists(os.path.join(self._local_root, blob_name))


# Module-level singleton (lazy init)
_blob_service: Optional[BlobService] = None


def get_blob_service() -> BlobService:
    global _blob_service
    if _blob_service is None:
        _blob_service = BlobService()
    return _blob_service
