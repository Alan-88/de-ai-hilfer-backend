"""Rename WordEntry to WordPrototype and create WordAlias table

Revision ID: a31ff970950c
Revises: 
Create Date: 2025-09-10 21:03:17.124697

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a31ff970950c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### 手动调整开始 ###

    # 1. 使用 rename_table 保留数据，而不是 drop 和 create
    op.rename_table('word_entries', 'word_prototypes')

    # 2. 对于 SQLite，使用 "batch" 模式来修改列的约束
    with op.batch_alter_table('word_prototypes', schema=None) as batch_op:
        batch_op.alter_column('query', existing_type=sa.VARCHAR(), nullable=False)
        batch_op.create_index(batch_op.f('ix_word_prototypes_query'), ['query'], unique=True)
        batch_op.create_index(batch_op.f('ix_word_prototypes_id'), ['id'], unique=False)

    # 3. 创建全新的 word_aliases 表 (这部分是正确的，予以保留)
    op.create_table('word_aliases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('alias_query', sa.String(), nullable=False),
    sa.Column('prototype_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['prototype_id'], ['word_prototypes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_word_aliases_alias_query'), 'word_aliases', ['alias_query'], unique=True)
    op.create_index(op.f('ix_word_aliases_id'), 'word_aliases', ['id'], unique=False)
    # ### 手动调整结束 ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### 手动调整开始 ###

    # 1. 移除 word_aliases 表 (这是 upgrade 的逆操作)
    op.drop_index(op.f('ix_word_aliases_id'), table_name='word_aliases')
    op.drop_index(op.f('ix_word_aliases_alias_query'), table_name='word_aliases')
    op.drop_table('word_aliases')

    # 2. 将 word_prototypes 重命名回 word_entries
    with op.batch_alter_table('word_prototypes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_word_prototypes_id'))
        batch_op.drop_index(batch_op.f('ix_word_prototypes_query'))

    op.rename_table('word_prototypes', 'word_entries')

    # 3. 恢复旧表的 unique=False 约束
    with op.batch_alter_table('word_entries', schema=None) as batch_op:
        batch_op.alter_column('query', existing_type=sa.VARCHAR(), nullable=False)
        batch_op.create_index('ix_word_entries_query', ['query'], unique=False)
        batch_op.create_index('ix_word_entries_id', ['id'], unique=False)
    # ### 手动调整结束 ###
