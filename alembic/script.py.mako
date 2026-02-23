"""${message}"""

revision = ${repr(revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}


def upgrade() -> None:
    """Apply schema changes.

    Args:
        None
    Returns:
        None: Upgrades schema.
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Revert schema changes.

    Args:
        None
    Returns:
        None: Downgrades schema.
    """
    ${downgrades if downgrades else "pass"}
