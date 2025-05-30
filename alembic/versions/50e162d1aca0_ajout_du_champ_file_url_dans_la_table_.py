"""Ajout du champ file_url dans la table messages

Revision ID: 50e162d1aca0
Revises: 95d223730a2e
Create Date: 2025-02-06 08:49:18.089133

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50e162d1aca0'
down_revision: Union[str, None] = '95d223730a2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('feedbacks', 'contenu',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('feedbacks', 'date',
               existing_type=sa.DATE(),
               nullable=False)
    op.alter_column('feedbacks', 'user_id',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.add_column('messages', sa.Column('file_url', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('messages', 'file_url')
    op.alter_column('feedbacks', 'user_id',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('feedbacks', 'date',
               existing_type=sa.DATE(),
               nullable=True)
    op.alter_column('feedbacks', 'contenu',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###
