"""
数据库备份与恢复
独立于应用升级的数据库安全备份功能
支持自定义数据库路径
"""
import os
import shutil
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine, get_db
from auth import get_current_user, is_head_coach
import models


router = APIRouter(prefix="/api/database", tags=["数据库备份"])


def require_head_coach(current_user: models.User = Depends(get_current_user)):
    """只有主教练才能访问数据库备份功能"""
    if not is_head_coach(current_user):
        raise HTTPException(status_code=403, detail="只有主教练才能执行此操作")
    return current_user


DB_BACKUPS_DIR = "db_backups"
DB_FILE_NAME = "fitness_schedule.db"
CONFIG_FILE = "db_config.json"


def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_config_path():
    """获取配置文件路径"""
    return os.path.join(get_project_root(), CONFIG_FILE)


def load_config() -> dict:
    """加载配置"""
    config_path = get_config_path()
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    """保存配置"""
    config_path = get_config_path()
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def get_db_path() -> str:
    """获取数据库文件路径"""
    # 优先使用环境变量
    env_path = os.environ.get('DATABASE_PATH')
    if env_path:
        return env_path

    # 其次使用配置文件
    config = load_config()
    if config.get('db_path'):
        return config['db_path']

    # 默认值
    return os.path.join(get_project_root(), DB_FILE_NAME)


def get_backups_dir() -> str:
    """获取备份目录路径"""
    root = get_project_root()
    path = os.path.join(root, DB_BACKUPS_DIR)
    if not os.path.exists(path):
        os.makedirs(path)
    return path


class BackupInfo(BaseModel):
    name: str
    path: str
    size: int
    created: str


class DbConfig(BaseModel):
    db_path: str
    backups_dir: str


class DbConfigUpdate(BaseModel):
    db_path: str


class BackupToPathRequest(BaseModel):
    target_path: str


class RestoreFromPathRequest(BaseModel):
    backup_path: str


@router.get("/config", response_model=DbConfig)
def get_config(current_user: models.User = Depends(require_head_coach)):
    """获取数据库配置"""
    return {
        "db_path": get_db_path(),
        "backups_dir": get_backups_dir()
    }


@router.post("/config")
def update_config(config_update: DbConfigUpdate, current_user: models.User = Depends(require_head_coach)):
    """更新数据库路径配置"""
    db_path = config_update.db_path.strip()

    if not db_path:
        raise HTTPException(status_code=400, detail="数据库路径不能为空")

    # 处理相对路径 - 转换为绝对路径
    if not os.path.isabs(db_path):
        db_path = os.path.join(get_project_root(), db_path)

    # 验证父目录是否存在，如果不存在则尝试创建
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except OSError as e:
            raise HTTPException(status_code=400, detail=f"无法创建目录: {e}")

    # 如果数据库文件已存在，验证是否可读可写
    if os.path.exists(db_path):
        if not os.access(db_path, os.R_OK | os.W_OK):
            raise HTTPException(status_code=400, detail="数据库文件权限不足")

    # 保存配置
    config = load_config()
    config['db_path'] = db_path
    try:
        save_config(config)
    except OSError as e:
        raise HTTPException(
            status_code=400,
            detail=f"无法写入配置文件，请通过环境变量 DATABASE_PATH 设置数据库路径。请求的路径: {db_path}"
        )

    return {"message": "配置已更新", "db_path": db_path}


@router.get("/backups", response_model=List[BackupInfo])
def list_backups(current_user: models.User = Depends(require_head_coach)):
    """列出所有数据库备份"""
    backups_dir = get_backups_dir()
    backups = []

    if not os.path.exists(backups_dir):
        return []

    for f in os.listdir(backups_dir):
        if f.endswith('.db'):
            filepath = os.path.join(backups_dir, f)
            stat = os.stat(filepath)
            backups.append({
                "name": f,
                "path": filepath,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })

    return sorted(backups, key=lambda x: x["created"], reverse=True)


@router.post("/backup", response_model=BackupInfo)
def create_backup(current_user: models.User = Depends(require_head_coach)):
    """创建数据库备份"""
    db_path = get_db_path()

    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="数据库文件不存在")

    backups_dir = get_backups_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"db_backup_{timestamp}.db"
    backup_path = os.path.join(backups_dir, backup_name)

    # 复制数据库文件
    shutil.copy2(db_path, backup_path)

    stat = os.stat(backup_path)

    return {
        "name": backup_name,
        "path": backup_path,
        "size": stat.st_size,
        "created": datetime.now().isoformat()
    }


@router.post("/backup-to-path", response_model=BackupInfo)
def backup_to_path(request: BackupToPathRequest, current_user: models.User = Depends(require_head_coach)):
    """备份数据库到指定路径"""
    db_path = get_db_path()

    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="数据库文件不存在")

    target_path = request.target_path.strip()

    if not target_path:
        raise HTTPException(status_code=400, detail="目标路径不能为空")

    # 如果是相对路径，转换为绝对路径
    if not os.path.isabs(target_path):
        target_path = os.path.join(get_project_root(), target_path)

    # 验证父目录是否存在，如果不存在则尝试创建
    parent_dir = os.path.dirname(target_path)
    if parent_dir and not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except OSError as e:
            raise HTTPException(status_code=400, detail=f"无法创建目标目录: {e}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 如果目标路径是目录，则在目录下生成带时间戳的备份文件名
    # 如果目标不存在：路径以 / 结尾 或 不以 .db 结尾 且 父目录存在，则视为目录
    if os.path.isdir(target_path):
        target_path = os.path.join(target_path, f"db_backup_{timestamp}.db")
    elif not os.path.exists(target_path):
        parent_dir = os.path.dirname(target_path)
        # 如果父目录存在，且路径不以 .db 结尾，则视为目录
        if parent_dir and os.path.isdir(parent_dir) and not target_path.endswith('.db'):
            # 创建目录
            try:
                os.makedirs(target_path, exist_ok=True)
                target_path = os.path.join(target_path, f"db_backup_{timestamp}.db")
            except OSError as e:
                raise HTTPException(status_code=400, detail=f"无法创建目标目录: {e}")

    # 复制数据库文件
    shutil.copy2(db_path, target_path)

    stat = os.stat(target_path)
    backup_name = os.path.basename(target_path)

    return {
        "name": backup_name,
        "path": target_path,
        "size": stat.st_size,
        "created": datetime.now().isoformat()
    }


@router.post("/restore/{backup_name}")
def restore_backup(backup_name: str, current_user: models.User = Depends(require_head_coach)):
    """从备份恢复数据库"""
    backups_dir = get_backups_dir()
    backup_path = os.path.join(backups_dir, backup_name)

    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="备份文件不存在")

    db_path = get_db_path()

    # 1. 先备份当前数据库（以防万一）
    emergency_backup_name = None
    if os.path.exists(db_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        emergency_backup_name = f"emergency_restore_{timestamp}.db"
        emergency_backup_path = os.path.join(backups_dir, emergency_backup_name)
        shutil.copy2(db_path, emergency_backup_path)

    # 2. 关闭所有现有数据库连接
    engine.dispose()

    # 3. 复制备份文件到数据库位置
    shutil.copy2(backup_path, db_path)

    return {
        "message": "恢复成功",
        "backup_used": backup_name,
        "emergency_backup": emergency_backup_name
    }


@router.post("/restore-from-path")
def restore_from_path(request: RestoreFromPathRequest, current_user: models.User = Depends(require_head_coach)):
    """从指定路径恢复数据库"""
    backup_path = request.backup_path.strip()

    if not backup_path:
        raise HTTPException(status_code=400, detail="备份路径不能为空")

    # 如果是相对路径，转换为绝对路径
    if not os.path.isabs(backup_path):
        backup_path = os.path.join(get_project_root(), backup_path)

    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="备份文件不存在")

    if not os.path.isfile(backup_path):
        raise HTTPException(status_code=400, detail="备份路径不是文件")

    db_path = get_db_path()
    backups_dir = get_backups_dir()

    # 1. 先备份当前数据库（以防万一）
    emergency_backup_name = None
    if os.path.exists(db_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        emergency_backup_name = f"emergency_restore_{timestamp}.db"
        emergency_backup_path = os.path.join(backups_dir, emergency_backup_name)
        shutil.copy2(db_path, emergency_backup_path)

    # 2. 关闭所有现有数据库连接
    engine.dispose()

    # 3. 复制备份文件到数据库位置
    shutil.copy2(backup_path, db_path)

    return {
        "message": "恢复成功",
        "backup_used": backup_path,
        "emergency_backup": emergency_backup_name
    }


@router.delete("/backups/{backup_name}")
def delete_backup(backup_name: str, current_user: models.User = Depends(require_head_coach)):
    """删除数据库备份"""
    backups_dir = get_backups_dir()
    backup_path = os.path.join(backups_dir, backup_name)

    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="备份文件不存在")

    os.remove(backup_path)

    return {"message": "备份已删除"}
