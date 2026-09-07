from pydantic import BaseModel, Field


class LockStatus(BaseModel):
    """Whether the app currently has a password lock configured."""

    is_locked: bool


class SetPasswordRequest(BaseModel):
    """Payload to set the app lock password for the first time."""

    password: str = Field(min_length=4, max_length=255)


class UnlockRequest(BaseModel):
    """Payload to unlock the app with the existing password."""

    password: str


class ChangePasswordRequest(BaseModel):
    """Payload to change the existing app lock password."""

    current_password: str
    new_password: str = Field(min_length=4, max_length=255)
