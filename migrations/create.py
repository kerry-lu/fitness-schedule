#!/usr/bin/env python3
"""
创建新的数据库迁移文件

用法:
    python migrations/create.py <migration_name>
    python migrations/create.py add_student_level

示例迁移文件:
    migrations/versions/001_add_student_level.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime

MIGRATIONS_DIR = Path(__file__).parent / "versions"


def create_migration(name: str):
    """创建新的迁移文件"""
    # 获取下一个版本号
    existing = list(MIGRATIONS_DIR.glob("*.py"))
    if existing:
        versions = []
        for f in existing:
            try:
                versions.append(int(f.stem.split("_")[0]))
            except:
                pass
        next_version = max(versions) + 1 if versions else 1
    else:
        next_version = 1

    version_str = f"{next_version:03d}"
    filename = MIGRATIONS_DIR / f"{version_str}_{name}.py"

    if filename.exists():
        print(f"Error: Migration already exists: {filename.name}")
        sys.exit(1)

    content = f'''"""
{name.replace('_', ' ').title()}
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

from migrations.env import run_sql, column_exists, table_exists


def upgrade():
    """
    升级数据库
    """
    # 示例: 添加新字段
    # if table_exists("students") and not column_exists("students", "level"):
    #     run_sql("ALTER TABLE students ADD COLUMN level VARCHAR(50)")
    pass


def downgrade():
    """
    回滚数据库
    """
    # 示例: 回滚操作
    # if column_exists("students", "level"):
    #     run_sql("ALTER TABLE students DROP COLUMN level")
    pass
'''

    filename.write_text(content)
    print(f"Created: {filename.name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    name = sys.argv[1].lower().strip()
    if not name.replace("_", "").isalnum():
        print("Error: Migration name must be alphanumeric with underscores only")
        sys.exit(1)

    create_migration(name)
