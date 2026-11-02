from datetime import datetime

from fastapi import HTTPException, status


def validate_frontend_timestamp(
    frontend_timestamp: datetime,
    backend_timestamp: datetime,
    start_at: datetime,
    end_at: datetime,
    paused_until: datetime,
    frozen_until: datetime | None,
) -> None:
    """
    Validate frontend_timestamp against game clock and state conditions.
    Accepts all pre-fetched timestamps to eliminate redundant DB calls.
    """
    # Condition 1: Difference between frontend and backend timestamp must be less than 1 second
    if abs((backend_timestamp - frontend_timestamp).total_seconds()) >= 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Timestamp difference between frontend and backend must be less than 1 second.",
        )

    # Condition 2: frontend_timestamp must be between start_at and end_at
    if not (start_at <= frontend_timestamp <= end_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Timestamp must be between game start_at and end_at.",
        )

    # Condition 3: frontend_timestamp must not be less than paused_until
    if frontend_timestamp < paused_until:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game is currently paused.",
        )

    # Condition 4: If frozen_until is not None, frontend_timestamp must not be less than frozen_until
    if frozen_until is not None and frontend_timestamp < frozen_until:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team is currently frozen.",
        )
