"""Schemas for login."""

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import Password, StrictModel


class LoginRequest(BaseModel):
    """
    Email + password. The email is a plain string here (not EmailStr): a
    login form should just say "wrong email or password", without hints.
    """
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=128)


class PasswordChangeRequest(StrictModel):
    """Request to replace the authenticated user's password."""
    current_password: str = Field(min_length=1, max_length=128)
    new_password: Password
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordChangeRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("New passwords do not match")
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from the current password")
        return self
