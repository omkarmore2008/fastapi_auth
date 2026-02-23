"""Shared API response schemas."""

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with ORM support.

    Args:
        BaseModel: Pydantic base class.
    Returns:
        BaseSchema: Base schema config for API models.
    """

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseSchema):
    """Simple message response schema."""

    message: str
