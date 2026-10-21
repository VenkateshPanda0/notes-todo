from pydantic import BaseModel, Field


class LockStatus(BaseModel):
    """Whether the app currently has a password lock configured."""

    is_locked: bool
    encrypted: bool = False
    encryption_available: bool = False


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


class SessionToken(BaseModel):
    """A session token returned after a successful setup, unlock or password change."""

    token: str


class EncryptionRequest(BaseModel):
    """The App Lock password, re-entered to confirm turning encryption on or off."""

    password: str = Field(min_length=4, max_length=255)


class EncryptionResult(BaseModel):
    encrypted: bool
    removed_plain_backups: int = 0
