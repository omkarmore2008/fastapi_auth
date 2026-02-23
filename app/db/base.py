"""Database metadata registry for migrations."""

from app.db.base_class import Base
from app.models import auth  # noqa: F401

metadata = Base.metadata
