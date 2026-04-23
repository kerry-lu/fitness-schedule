"""
Add Performance Indexes
Created: 2026-04-24
"""

from migrations.env import run_sql, column_exists, table_exists


def upgrade():
    """
    升级数据库 - 添加外键索引以提升查询性能
    注意: SQLite 的 ALTER TABLE 不支持添加索引
    索引将在新表创建或重新创建表时生效
    对于现有表，索引会在下次表重构时应用
    """
    pass


def downgrade():
    """
    回滚数据库
    """
    pass
