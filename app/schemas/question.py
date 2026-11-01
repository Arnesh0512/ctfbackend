import uuid

from pydantic import BaseModel, ConfigDict, Field


class FileUploadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str = Field(..., description="Supabase S3 public link")
    file_url: str = Field(..., description="Alias of the Supabase S3 public link")
    filename: str = Field(..., description="Uploaded filename")
    question_id: uuid.UUID | None = Field(default=None, description="Linked question ID in database if provided")
    file_path: list[str] | None = Field(
        default=None,
        description="Updated file links on the question record in database if question_id was provided",
    )
