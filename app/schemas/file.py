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


class FileLinkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: uuid.UUID = Field(
        ...,
        description="Question ID to attach the link to",
    )
    link: str = Field(
        ...,
        min_length=1,
        description="File link (e.g. S3 link, external bucket link) to store directly in question file_path",
    )


class FileLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: uuid.UUID = Field(..., description="Linked question ID")
    link: str = Field(..., description="Attached file link")


class FileDeleteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: uuid.UUID = Field(
        ...,
        description="Question ID to remove the file link from",
    )
    url: str = Field(
        ...,
        min_length=1,
        description="Exact file URL to remove from question and delete from S3 if public link",
    )


class FileDeleteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(..., description="Operation result description")
    question_id: uuid.UUID = Field(..., description="Question ID")
    deleted_url: str = Field(..., description="Deleted file URL")
    s3_deleted: bool = Field(..., description="Whether the file was deleted from Supabase S3")
