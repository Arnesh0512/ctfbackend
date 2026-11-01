import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.deps import DB
from app.models.question import Question
from app.routers.time import verify_admin
from app.schemas.question import FileUploadOut, QuestionUploadIn
from app.services.storage import upload_file_to_supabase

router = APIRouter(prefix="/question", tags=["question"], dependencies=[Depends(verify_admin)])


@router.post(
    "/upload",
    response_model=FileUploadOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload file to Supabase S3 and link to question in DB",
)
async def upload_question_file(
    db: DB,
    file: UploadFile = File(...),
    body: QuestionUploadIn = Form(),
) -> FileUploadOut:
    """Upload a file (e.g. image, zip) to Supabase S3 Storage.

    If question_id is provided in the body, links the returned public S3 URL into
    the question's file_path database array.
    """
    target_qid = body.question_id

    question: Question | None = None
    if target_qid is not None:
        question = await db.get(Question, target_qid)
        if question is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question '{target_qid}' not found in database.",
            )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    folder = str(target_qid) if target_qid else None
    public_url = await upload_file_to_supabase(
        content=content,
        filename=file.filename or "file",
        content_type=file.content_type or "application/octet-stream",
        folder=folder,
    )

    stored_files: list[str] | None = None
    if question is not None:
        current_files = list(question.file_path) if question.file_path else []
        if public_url not in current_files:
            current_files.append(public_url)
            question.file_path = current_files
        await db.commit()
        await db.refresh(question)
        stored_files = question.file_path

    return FileUploadOut(
        url=public_url,
        file_url=public_url,
        filename=file.filename or "file",
        question_id=target_qid,
        file_path=stored_files,
    )
