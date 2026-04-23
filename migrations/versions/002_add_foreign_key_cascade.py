"""
Add Foreign Key Cascade Delete
Created: 2026-04-24
"""

from migrations.env import run_sql, column_exists, table_exists


def upgrade():
    """
    升级数据库 - 启用外键级联删除
    注意: SQLite 外键级联需要在连接时启用 PRAGMA foreign_keys=ON
    此迁移确保数据库连接正确配置
    """
    # SQLite 的 ALTER TABLE 不支持添加外键约束
    # 外键约束已在 SQLAlchemy 模型中定义
    # 运行时通过 database.py 中的 event listener 启用 PRAGMA foreign_keys=ON
    pass


def downgrade():
    """
    回滚数据库
    """
    pass
