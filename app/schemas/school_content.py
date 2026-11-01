"""Validation constants for school notices, events and public information."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ContentKind = Literal["notice", "activity", "gallery", "admission", "meal"]


class SchoolContentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: ContentKind
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=10000)
    event_date: str | None = None
    event_end_date: str | None = None
    location: str | None = Field(default=None, max_length=200)
    documents_required: str | None = Field(default=None, max_length=5000)
    scholarship_info: str | None = Field(default=None, max_length=5000)
    is_published: bool = True

    @model_validator(mode="after")
    def valid_dates(self):
        if self.event_date and self.event_end_date and self.event_end_date < self.event_date:
            raise ValueError("event_end_date cannot be before event_date")
        return self


class SchoolContentUpdate(SchoolContentCreate):
    """Validated school-content fields used by the edit endpoint."""
