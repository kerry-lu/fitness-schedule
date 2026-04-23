"""
数据库迁移管理器
"""
import os
import importlib
import hashlib
from datetime import datetime
from typing import List, Tuple, Optional
from pathlib import Path
from sqlalchemy import text

from migrations.env import get_session, run_sql, table_exists


MIGRATIONS_TABLE = "schema_migrations"
MIGRATIONS_DIR = Path(__file__).parent / "versions"


class MigrationManager:
    def __init__(self):
        self._ensure_migrations_table()

    def _ensure_migrations_table(self):
        """确保 migrations 表存在"""
        if not table_exists(MIGRATIONS_TABLE):
            run_sql(f"""
                CREATE TABLE {MIGRATIONS_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version VARCHAR(255) NOT NULL UNIQUE,
                    name VARCHAR(255),
                    applied_at DATETIME NOT NULL,
                    checksum VARCHAR(64)
                )
            """)

    def get_applied_migrations(self) -> List[str]:
        """获取已应用的迁移版本列表"""
        with get_session() as db:
            result = db.execute(
                text(f"SELECT version FROM {MIGRATIONS_TABLE} ORDER BY version")
            )
            return [row[0] for row in result]

    def get_pending_migrations(self) -> List[Tuple[str, str]]:
        """获取待应用的迁移 (version, name)"""
        applied = set(self.get_applied_migrations())
        pending = []

        if not MIGRATIONS_DIR.exists():
            return pending

        for file in sorted(MIGRATIONS_DIR.glob("*.py")):
            if file.name.startswith("_"):
                continue
            version = file.stem
            if version not in applied:
                name = self._get_migration_name(file)
                pending.append((version, name))

        return pending

    def _get_migration_name(self, file: Path) -> str:
        """从文件内容获取迁移名称"""
        try:
            content = file.read_text()
            if '"""' in content:
                start = content.find('"""') + 3
                end = content.find('"""', start)
                if start > 2 and end > start:
                    first_line = content[start:end].strip().split('\n')[0]
                    return first_line.strip()
        except:
            pass
        return file.stem

    def _compute_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        return hashlib.md5(file_path.read_bytes()).hexdigest()

    def apply_migration(self, version: str) -> bool:
        """应用单个迁移"""
        file_path = MIGRATIONS_DIR / f"{version}.py"
        if not file_path.exists():
            raise FileNotFoundError(f"Migration file not found: {version}.py")

        # 导入迁移模块
        spec = importlib.util.spec_from_file_location(f"migration_{version}", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 执行升级
        if hasattr(module, 'upgrade'):
            module.upgrade()

        # 记录迁移
        checksum = self._compute_checksum(file_path)
        name = self._get_migration_name(file_path)
        applied_at = datetime.now().isoformat()

        with get_session() as db:
            db.execute(
                text(f"INSERT INTO {MIGRATIONS_TABLE} (version, name, applied_at, checksum) VALUES (:v, :n, :a, :c)"),
                {"v": version, "n": name, "a": applied_at, "c": checksum}
            )
            db.commit()

        print(f"  ✓ Applied: {version} - {name}")
        return True

    def migrate(self, target_version: Optional[str] = None):
        """
        执行迁移

        Args:
            target_version: 目标版本，不传则迁移到最新
        """
        pending = self.get_pending_migrations()

        if not pending:
            print("No pending migrations")
            return

        print(f"Found {len(pending)} pending migration(s)\n")

        for version, name in pending:
            if target_version and version > target_version:
                break
            self.apply_migration(version)

        print("\nMigration completed")

    def rollback(self, version: str):
        """回滚到指定版本"""
        applied = self.get_applied_migrations()

        if version not in applied:
            raise ValueError(f"Migration {version} is not applied")

        # 获取需要回滚的迁移
        to_rollback = [v for v in applied if v > version]
        to_rollback.reverse()

        print(f"Rolling back {len(to_rollback)} migration(s)\n")

        for v in to_rollback:
            self._rollback_migration(v)

        print("\nRollback completed")

    def _rollback_migration(self, version: str):
        """回滚单个迁移"""
        file_path = MIGRATIONS_DIR / f"{version}.py"
        if not file_path.exists():
            raise FileNotFoundError(f"Migration file not found: {version}.py")

        spec = importlib.util.spec_from_file_location(f"migration_{version}", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, 'downgrade'):
            module.downgrade()

        with get_session() as db:
            db.execute(
                text(f"DELETE FROM {MIGRATIONS_TABLE} WHERE version = :v"),
                {"v": version}
            )
            db.commit()

        print(f"  ✓ Rolled back: {version}")

    def status(self):
        """显示迁移状态"""
        applied = set(self.get_applied_migrations())
        pending = self.get_pending_migrations()

        print("Migration Status")
        print("=" * 50)

        if not applied and not pending:
            print("No migrations found")
            return

        # 显示已应用的
        if applied:
            print("\nApplied:")
            for v in applied:
                print(f"  [{v}]")
        else:
            print("\nApplied: (none)")

        # 显示待应用的
        if pending:
            print("\nPending:")
            for v, name in pending:
                print(f"  [{v}] {name}")
        else:
            print("\nPending: (none)")

        print()


def current():
    """获取当前数据库版本"""
    if not table_exists(MIGRATIONS_TABLE):
        return None
    with get_session() as db:
        result = db.execute(
            text(f"SELECT version FROM {MIGRATIONS_TABLE} ORDER BY version DESC LIMIT 1")
        )
        row = result.fetchone()
        return row[0] if row else None


# CLI 入口
if __name__ == "__main__":
    import sys

    manager = MigrationManager()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        manager.status()
    elif cmd == "migrate":
        target = sys.argv[2] if len(sys.argv) > 2 else None
        manager.migrate(target)
    elif cmd == "rollback":
        if len(sys.argv) < 3:
            print("Usage: python manager.py rollback <version>")
            sys.exit(1)
        manager.rollback(sys.argv[2])
    elif cmd == "create":
        if len(sys.argv) < 3:
            print("Usage: python manager.py create <migration_name>")
            sys.exit(1)
        from migrations.create import create_migration
        create_migration(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        print("Available: status, migrate, rollback, create")
