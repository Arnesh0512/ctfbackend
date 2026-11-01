import uuid

from pydantic import BaseModel, ConfigDict, Field


class FileUploadIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question_id: uuid.UUID = Field(
        ...,
        description="Question ID to link the uploaded file in database",
    )


class FileUploadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str = Field(..., description="Supabase S3 public link")
    filename: str = Field(..., description="Uploaded filename")
    question_id: uuid.UUID = Field(..., description="Linked question ID in database")
    file_path: list[str] = Field(
        ...,
        description="Updated file links on the question record in database",
    )
