import hashlib
import re
from pathlib import Path

from fastapi import HTTPException, status
import httpx

from app.core.config import settings


async def ensure_bucket_exists(client: httpx.AsyncClient, base_url: str, headers: dict[str, str], bucket: str) -> None:
    """Ensure the Supabase public storage bucket exists; creates it if not."""
    bucket_url = f"{base_url}/storage/v1/bucket"
    res = await client.get(f"{bucket_url}/{bucket}", headers=headers)
    if res.status_code == 404:
        create_res = await client.post(
            bucket_url,
            headers=headers,
            json={"id": bucket, "name": bucket, "public": True},
        )
        if create_res.status_code not in (200, 201):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to create Supabase storage bucket '{bucket}': {create_res.text}",
            )


def extract_s3_object_path(url: str) -> str | None:
    """Extract object path if url is a public Supabase S3 link for current bucket, else None."""
    if not settings.supabase_url:
        return None
    base = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/{settings.supabase_storage_bucket}/"
    if url.startswith(base):
        return url[len(base):]
    return None


async def upload_file_to_supabase(
    content: bytes,
    filename: str,
    state: str,
    monument: str,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload binary content to Supabase Storage in bucket 'monuments'.

    Hierarchy:
    monuments/<state-monument>/<sha256_16chars>/<filename>
    (replacing spaces and underscores in state and monument with '-')
    """
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase credentials (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) are not configured.",
        )

    clean_name = re.sub(r"[^\w\.-]", "_", Path(filename).name) or "file"

    # Format <state-monument> with spaces and underscores replaced by '-'
    raw_monument_path = f"{state.strip()}-{monument.strip()}"
    monument_folder = re.sub(r"[\s_]+", "-", raw_monument_path).strip("-")

    # Compute first 16 characters of SHA-256 of file content
    file_sha = hashlib.sha256(content).hexdigest()[:16]

    bucket = settings.supabase_storage_bucket
    object_path = f"{monument_folder}/{file_sha}/{clean_name}"

    base_url = settings.supabase_url.rstrip("/")
    upload_url = f"{base_url}/storage/v1/object/{bucket}/{object_path}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
        "x-upsert": "true",
        "Content-Type": content_type,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(upload_url, headers=headers, content=content)

        # Auto-create bucket if missing and retry once
        if res.status_code == 404:
            await ensure_bucket_exists(client, base_url, headers, bucket)
            res = await client.post(upload_url, headers=headers, content=content)

        if res.status_code not in (200, 201):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Supabase storage upload failed ({res.status_code}): {res.text}",
            )

    return f"{base_url}/storage/v1/object/public/{bucket}/{object_path}"


async def delete_files_from_supabase(object_paths: list[str]) -> bool:
    """Delete multiple objects from Supabase Storage bucket in a single batch call."""
    if not object_paths or not settings.supabase_url or not settings.supabase_service_role_key:
        return False

    base_url = settings.supabase_url.rstrip("/")
    bucket = settings.supabase_storage_bucket
    delete_url = f"{base_url}/storage/v1/object/{bucket}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.request("DELETE", delete_url, headers=headers, json={"prefixes": object_paths})
        return res.status_code in (200, 204)


async def delete_file_from_supabase(object_path: str) -> bool:
    """Delete an object from Supabase Storage bucket. Returns True if deleted."""
    return await delete_files_from_supabase([object_path])
