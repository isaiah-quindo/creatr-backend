"""
Supabase Storage helpers.

Implemented with plain `requests` against the Supabase Storage REST API so we
don't pull in the supabase-py client (which transitively requires building
pydantic-core from Rust on Python 3.14).

Docs: https://supabase.com/docs/reference/api/introduction
"""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import PurePosixPath
from urllib.parse import quote

import requests
from django.conf import settings


def _require_config() -> tuple[str, str, str]:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "Supabase is not configured: set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY in backend/.env"
        )
    return (
        settings.SUPABASE_URL.rstrip("/"),
        settings.SUPABASE_SERVICE_ROLE_KEY,
        settings.SUPABASE_STORAGE_BUCKET,
    )


def _auth_headers(service_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
    }


def upload_file(
    file_obj,
    *,
    folder: str,
    filename: str | None = None,
    content_type: str | None = None,
    bucket: str | None = None,
) -> str:
    """
    Upload a file-like object to Supabase Storage; return its public URL.

    `folder` is a logical prefix inside the bucket (e.g. "avatars",
    "portfolio/<user_id>"). A random suffix is added to the filename so
    repeated uploads of the same name don't collide.
    """
    base_url, service_key, default_bucket = _require_config()
    bucket_name = bucket or default_bucket

    base_name = filename or getattr(file_obj, "name", "upload.bin")
    suffix = PurePosixPath(base_name).suffix or ""
    object_path = f"{folder.strip('/')}/{uuid.uuid4().hex}{suffix}"

    if content_type is None:
        guessed, _ = mimetypes.guess_type(base_name)
        content_type = guessed or "application/octet-stream"

    data = file_obj.read() if hasattr(file_obj, "read") else file_obj

    upload_url = f"{base_url}/storage/v1/object/{quote(bucket_name)}/{quote(object_path)}"
    resp = requests.post(
        upload_url,
        data=data,
        headers={**_auth_headers(service_key), "Content-Type": content_type},
        timeout=30,
    )
    resp.raise_for_status()
    return f"{base_url}/storage/v1/object/public/{quote(bucket_name)}/{quote(object_path)}"


def delete_file(object_path: str, *, bucket: str | None = None) -> None:
    """Delete a previously-uploaded object by its path inside the bucket."""
    base_url, service_key, default_bucket = _require_config()
    bucket_name = bucket or default_bucket
    delete_url = f"{base_url}/storage/v1/object/{quote(bucket_name)}/{quote(object_path)}"
    resp = requests.delete(delete_url, headers=_auth_headers(service_key), timeout=15)
    resp.raise_for_status()
