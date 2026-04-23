from database import engine, SessionLocal, Base
from sqlalchemy import text
import os

# 获取数据库路径
DB_PATH = "fitness_schedule.db"


def get_connection():
    """获取数据库连接"""
    return engine.connect()


def get_session():
    """获取数据库会话"""
    return SessionLocal()


def get_table_names():
    """获取所有表名"""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        return [row[0] for row in result]


def table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    return table_name in get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    if not table_exists(table_name):
        return False
    with engine.connect() as conn:
        result = conn.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in result]
        return column_name in columns


def run_sql(sql: str):
    """执行 SQL 语句"""
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
