"""Merge heads

Revision ID: 76e62a510a1e
Revises: 25059ecc75ff, 3b8c9a2b9e28, 6bd6f65c4c78
Create Date: 2024-06-25 10:48:04.254437

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '76e62a510a1e'
down_revision = ('25059ecc75ff', '3b8c9a2b9e28', '6bd6f65c4c78')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
