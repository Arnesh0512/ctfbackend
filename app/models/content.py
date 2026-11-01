import uuid

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.question import Question

__all__ = ["Path", "Question"]


class Path(Base):
    __tablename__ = "paths"

    path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    path_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    start_region: Mapped[str] = mapped_column(Text, nullable=False)
    questions: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False
    )
