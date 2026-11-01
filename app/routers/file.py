import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.deps import DB
from app.models.content import Question
from app.routers.time import verify_admin
from app.schemas.file import FileUploadIn, FileUploadOut
from app.services.storage import upload_file_to_supabase

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
    """Upload a file (e.g. image, zip) to Supabase S3 Storage.

    Hierarchy in 'monuments' bucket:
    <state-monument>/<sha256>/<filename>
    (replacing spaces and underscores in state and monument with '-')

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
