"""Initial migration

Revision ID: 95d223730a2e
Revises: 
Create Date: 2025-01-06 19:05:49.373467

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95d223730a2e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
                    sa.Column("id", sa.String, primary_key=True, index=True, default=uuid.uuid4()),
                    sa.Column("firstname", sa.String),
                    sa.Column("lastname", sa.String),
                    sa.Column("email", sa.String, unique=True, index=True),
                    sa.Column("password", sa.String),
                    sa.Column("status", sa.Integer)
                    )
    op.create_table('histories',
                    sa.Column("id", sa.Integer, primary_key=True, index=True),
                    sa.Column("label", sa.String),
                    sa.Column("date", sa.DateTime),
                    sa.Column("context", sa.String),
                    sa.Column('user_id', sa.String, sa.ForeignKey('users.id'))
                    )
    op.create_table(
        'feedbacks',
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("contenu", sa.String),
        sa.Column("date", sa.Date),
        sa.Column('user_id', sa.String, sa.ForeignKey('users.id'))
        
    )
    op.create_table(
        'messages',
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("version", sa.String),
        sa.Column("contenu", sa.String),
        sa.Column("file_url", sa.String),#vient d'être ajouter
        sa.Column("type_message", sa.String),
        sa.Column("date", sa.Date),
        sa.Column('history_id', sa.Integer, sa.ForeignKey('histories.id'))
    )


def downgrade() -> None:
    op.drop_table('messages')
    op.drop_table('feedbacks')
    op.drop_table('histories')
    op.drop_table('users')



