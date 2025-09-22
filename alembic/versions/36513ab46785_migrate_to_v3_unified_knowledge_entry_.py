"""Migrate to V3 unified knowledge entry model

Revision ID: 36513ab46785
Revises: a31ff970950c
Create Date: 2025-09-11 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36513ab46785' # 请将这里替换为你的实际 revision id
down_revision: Union[str, Sequence[str], None] = 'a31ff970950c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### 手动编写的 V3.0 数据迁移脚本 ###

    # 1. 创建新表结构
    op.create_table('knowledge_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('query_text', sa.String(), nullable=False),
        sa.Column('entry_type', sa.String(length=50), nullable=False),
        sa.Column('analysis_markdown', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_entries_id'), 'knowledge_entries', ['id'], unique=False)
    op.create_index(op.f('ix_knowledge_entries_query_text'), 'knowledge_entries', ['query_text'], unique=True)

    op.create_table('follow_ups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entry_id', sa.Integer(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['entry_id'], ['knowledge_entries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_follow_ups_id'), 'follow_ups', ['id'], unique=False)

    op.create_table('entry_aliases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alias_text', sa.String(), nullable=False),
        sa.Column('entry_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['entry_id'], ['knowledge_entries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_entry_aliases_alias_text'), 'entry_aliases', ['alias_text'], unique=True)
    op.create_index(op.f('ix_entry_aliases_id'), 'entry_aliases', ['id'], unique=False)

    # 2. 将旧表数据迁移到新表
    # 将 word_prototypes 的数据迁移到 knowledge_entries
    op.execute("""
        INSERT INTO knowledge_entries (id, query_text, entry_type, analysis_markdown, timestamp)
        SELECT id, query, 'WORD', analysis, timestamp FROM word_prototypes
    """)

    # 将 word_aliases 的数据迁移到 entry_aliases
    op.execute("""
        INSERT INTO entry_aliases (id, alias_text, entry_id)
        SELECT id, alias_query, prototype_id FROM word_aliases
    """)

    # 3. 删除旧表
    op.drop_table('word_aliases')
    op.drop_table('word_prototypes')
    # ### 迁移结束 ###


def downgrade() -> None:
    # ### 手动编写的降级脚本 ###
    
    # 1. 重建旧表
    op.create_table('word_prototypes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('query', sa.String(), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False, server_default='de>zh'),
        sa.Column('analysis', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('query')
    )
    
    op.create_table('word_aliases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alias_query', sa.String(), nullable=False),
        sa.Column('prototype_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['prototype_id'], ['word_prototypes.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('alias_query')
    )

    # 2. 将新表数据迁回旧表
    op.execute("""
        INSERT INTO word_prototypes (id, query, analysis, timestamp)
        SELECT id, query_text, analysis_markdown, timestamp FROM knowledge_entries WHERE entry_type = 'WORD'
    """)
    op.execute("""
        INSERT INTO word_aliases (id, alias_query, prototype_id)
        SELECT id, alias_text, entry_id FROM entry_aliases
    """)

    # 3. 删除新表
    op.drop_table('entry_aliases')
    op.drop_table('follow_ups')
    op.drop_table('knowledge_entries')
    # ### 降级结束 ###