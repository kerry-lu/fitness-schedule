"""
Initial Schema Migration
"""

from migrations.env import run_sql, column_exists, table_exists


def upgrade():
    """
    升级数据库 - 添加示例字段
    此迁移仅作为示例，不会执行任何操作
    """
    pass


def downgrade():
    """
    回滚数据库 - 移除示例字段
    此迁移仅作为示例，不会执行任何操作
    """
    pass
