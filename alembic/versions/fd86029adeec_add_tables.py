"""Add tables

Revision ID: fd86029adeec
Revises: 617287be881b
Create Date: 2025-06-24 06:03:50.639079

"""

from alembic import op
import sqlalchemy as sa

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'fd86029adeec'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('date', sa.String(), nullable=False),
    )
    op.create_table(
        'documents_text',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('id_doc', sa.Integer(), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('text', sa.String(), nullable=False),
    )


def downgrade():
    op.drop_table('documents_text')
    op.drop_table('documents')