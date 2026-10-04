"""0001 greetings table.

Revision ID: 0001_greetings
Revises: None
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_greetings"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "greetings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 100", name="ck_greetings_name_length"
        ),
    )


def downgrade():
    op.drop_table("greetings")
