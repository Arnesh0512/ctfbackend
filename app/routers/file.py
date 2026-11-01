import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.deps import DB
from app.models.content import Question
from app.routers.time import verify_admin
from app.schemas.file import (
    FileDeleteIn,
    FileDeleteOut,
    FileLinkIn,
    FileLinkOut,
    FileUploadIn,
    FileUploadOut,
)
from app.services.storage import (
    delete_file_from_supabase,
    extract_s3_object_path,
    upload_file_to_supabase,
)

router = APIRouter(prefix="/file", tags=["file"], dependencies=[Depends(verify_admin)])


@router.post(
    "/upload",
    response_model=FileUploadOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload file to Supabase S3 and link to question in DB",
)
async def upload_file(
    db: DB,
    file: UploadFile = File(...),
    body: FileUploadIn = Form(),
) -> FileUploadOut:
    """Upload a file to Supabase S3 Storage in bucket 'monuments'.

    Hierarchy: <state-monument>/<sha256_16chars>/<filename>
    Links the public S3 URL into the question's file_path database array.
    """
    question = await db.get(Question, body.question_id)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question '{body.question_id}' not found in database.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    public_url = await upload_file_to_supabase(
        content=content,
        filename=file.filename or "file",
        state=question.state,
        monument=question.monument,
        content_type=file.content_type or "application/octet-stream",
    )

    current_files = list(question.file_path) if question.file_path else []
    if public_url not in current_files:
        current_files.append(public_url)
        question.file_path = current_files

    await db.commit()
    await db.refresh(question)

    return FileUploadOut(
        url=public_url,
        filename=file.filename or "file",
        question_id=question.question_id,
    )


@router.get(
    "/{question_id}",
    response_model=list[str],
    summary="Get all file paths/links for a question",
)
async def get_question_files(
    question_id: uuid.UUID,
    db: DB,
) -> list[str]:
    """Return strictly the list of file links/paths for a question (Admin only)."""
    question = await db.get(Question, question_id)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question '{question_id}' not found in database.",
        )
    return question.file_path or []


@router.post(
    "/link",
    response_model=FileLinkOut,
    status_code=status.HTTP_201_CREATED,
    summary="Directly append a file link to question file_path",
)
async def add_file_link(
    body: FileLinkIn,
    db: DB,
) -> FileLinkOut:
    """Store a file link (S3 URL or external URL) directly in question's file_path list (Admin only)."""
    question = await db.get(Question, body.question_id)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question '{body.question_id}' not found in database.",
        )

    link = body.link.strip()
    current_files = list(question.file_path) if question.file_path else []
    if link not in current_files:
        current_files.append(link)
        question.file_path = current_files
        await db.commit()
        await db.refresh(question)

    return FileLinkOut(
        question_id=question.question_id,
        link=link,
    )


@router.delete(
    "",
    response_model=FileDeleteOut,
    summary="Delete file from question and Supabase S3",
)
async def delete_file(
    body: FileDeleteIn,
    db: DB,
) -> FileDeleteOut:
    """Remove a file URL from question's file_path list and delete from S3 if it's an S3 public link."""
    question = await db.get(Question, body.question_id)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question '{body.question_id}' not found in database.",
        )

    target_url = body.url.strip()
    current_files = list(question.file_path) if question.file_path else []
    if target_url not in current_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File URL '{target_url}' not found in question's file_path list.",
        )

    # 1. Remove from database file_path list
    current_files.remove(target_url)
    question.file_path = current_files
    await db.commit()
    await db.refresh(question)

    # 2. Check if it's a Supabase S3 public link and delete from S3 bucket
    s3_path = extract_s3_object_path(target_url)
    s3_deleted = False
    if s3_path:
        s3_deleted = await delete_file_from_supabase(s3_path)

    return FileDeleteOut(
        message="File removed from question and S3" if s3_deleted else "File removed from question (not an S3 file)",
        question_id=question.question_id,
        deleted_url=target_url,
        s3_deleted=s3_deleted,
    )
