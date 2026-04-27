from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import json

# 获取项目根目录
def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 读取数据库路径配置
def get_database_url():
    # 1. 优先使用环境变量
    env_path = os.environ.get('DATABASE_PATH')
    if env_path:
        return f"sqlite:///{env_path}"

    # 2. 其次使用配置文件
    config_path = os.path.join(get_project_root(), 'db_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            if config.get('db_path'):
                return f"sqlite:///{config['db_path']}"

    # 3. 默认值
    db_path = os.path.join(get_project_root(), 'fitness_schedule.db')
    return f"sqlite:///{db_path}"


SQLALCHEMY_DATABASE_URL = get_database_url()

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)


# 启用 SQLite 外键级联删除
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
