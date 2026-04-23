"""
Add Input Validation
Created: 2026-04-24
"""

from migrations.env import run_sql, column_exists, table_exists


def upgrade():
    """
    升级数据库 - 输入验证增强
    此迁移主要添加 Pydantic 层验证，无需数据库变更
    """
    pass


def downgrade():
    """
    回滚数据库
    """
    pass
