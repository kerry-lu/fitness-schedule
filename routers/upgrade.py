import os
import shutil
import tarfile
import hashlib
import urllib.request
import json
import zipfile
import io
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from version import FRONTEND_VERSION, BACKEND_VERSION, UPDATES_DIR, BACKUPS_DIR, GITHUB_REPO, GITHUB_TOKEN

router = APIRouter(prefix="/api/upgrade", tags=["升级"])

# 可升级的文件清单（相对于项目根目录）
UPGRADEABLE_FILES = [
    "main.py",
    "auth.py",
    "authorization.py",
    "database.py",
    "schemas.py",
    "models.py",
    "routers/",
    "static/",
]

# 不允许升级的文件（数据库等）
PROTECTED_FILES = [
    "fitness_schedule.db",
    "*.db",
    ".venv/",
    "migrations/",
    "backups/",
    "updates/",
    ".git/",
]


class VersionInfo(BaseModel):
    frontend: str
    backend: str
    has_update: bool = False
    update_info: Optional[dict] = None


class UpdateFile(BaseModel):
    path: str
    size: int
    modified: str
    hash: Optional[str] = None


class UpdateInfo(BaseModel):
    version: str
    files: List[UpdateFile]
    description: Optional[str] = None


class BackupInfo(BaseModel):
    name: str
    path: str
    size: int
    created: str


def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_protected(path: str) -> bool:
    """检查文件是否受保护，不允许升级"""
    from fnmatch import fnmatch
    for pattern in PROTECTED_FILES:
        if fnmatch(path, pattern) or path.startswith(pattern.rstrip('/')):
            return True
    return False


def calculate_file_hash(filepath: str) -> str:
    """计算文件SHA256哈希"""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def calculate_dir_hash(dirpath: str) -> str:
    """计算目录内容哈希"""
    sha256 = hashlib.sha256()
    for root, dirs, files in os.walk(dirpath):
        dirs.sort()
        files.sort()
        for f in files:
            fp = os.path.join(root, f)
            relpath = os.path.relpath(fp, dirpath)
            sha256.update(relpath.encode())
            with open(fp, 'rb') as file:
                for chunk in iter(lambda: file.read(8192), b''):
                    sha256.update(chunk)
    return sha256.hexdigest()[:16]


@router.get("/versions", response_model=VersionInfo)
def get_versions():
    """获取当前版本信息"""
    root = get_project_root()

    # 检查是否有可用更新
    update_info = None
    has_update = False

    update_path = os.path.join(root, UPDATES_DIR)
    if os.path.exists(update_path):
        version_file = os.path.join(update_path, "VERSION")
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                content = f.read().strip()
            # 支持纯版本号或 BACKEND_VERSION = "x.x.x" 格式
            if '=' in content:
                update_version = content.split('=')[1].strip().strip('"')
            else:
                update_version = content
            if update_version != BACKEND_VERSION:
                has_update = True
                update_info = {
                    "version": update_version,
                    "path": update_path
                }

    return {
        "frontend": FRONTEND_VERSION,
        "backend": BACKEND_VERSION,
        "has_update": has_update,
        "update_info": update_info
    }


@router.get("/update-files")
def get_update_files():
    """获取待升级文件列表"""
    root = get_project_root()
    update_path = os.path.join(root, UPDATES_DIR)

    if not os.path.exists(update_path):
        raise HTTPException(status_code=404, detail="没有找到升级文件")

    files = []
    for item in os.listdir(update_path):
        filepath = os.path.join(update_path, item)
        relpath = os.path.relpath(filepath, root)

        if is_protected(relpath):
            continue

        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            files.append({
                "path": relpath,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        elif os.path.isdir(filepath):
            for sub_root, sub_dirs, sub_files in os.walk(filepath):
                for f in sub_files:
                    fp = os.path.join(sub_root, f)
                    rel = os.path.relpath(fp, root)
                    if is_protected(rel):
                        continue
                    stat = os.stat(fp)
                    files.append({
                        "path": rel,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })

    return files


@router.post("/backup")
def create_backup():
    """创建当前版本的备份"""
    root = get_project_root()
    backup_dir = os.path.join(root, BACKUPS_DIR)

    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{BACKEND_VERSION}_{timestamp}"
    backup_path = os.path.join(backup_dir, backup_name)

    # 创建备份tar.gz
    with tarfile.open(f"{backup_path}.tar.gz", "w:gz") as tar:
        for item in UPGRADEABLE_FILES:
            item_path = os.path.join(root, item)
            if os.path.exists(item_path):
                tar.add(item_path, arcname=os.path.join(backup_name, item))

    stat = os.stat(f"{backup_path}.tar.gz")

    return {
        "name": backup_name,
        "path": f"{backup_path}.tar.gz",
        "size": stat.st_size,
        "created": datetime.now().isoformat()
    }


@router.get("/backups")
def list_backups():
    """列出所有备份"""
    root = get_project_root()
    backup_dir = os.path.join(root, BACKUPS_DIR)

    if not os.path.exists(backup_dir):
        return []

    backups = []
    for f in os.listdir(backup_dir):
        if f.endswith('.tar.gz'):
            filepath = os.path.join(backup_dir, f)
            stat = os.stat(filepath)
            backups.append({
                "name": f,
                "path": filepath,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })

    return sorted(backups, key=lambda x: x["created"], reverse=True)


@router.post("/restore/{backup_name}")
def restore_backup(backup_name: str):
    """从备份恢复"""
    root = get_project_root()
    backup_path = os.path.join(root, BACKUPS_DIR, backup_name)

    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="备份文件不存在")

    # 解压备份
    extract_dir = os.path.join(root, "_restore_temp")
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)

    with tarfile.open(backup_path, "r:gz") as tar:
        tar.extractall(extract_dir)

    # 恢复文件
    for item in UPGRADEABLE_FILES:
        backup_item = os.path.join(extract_dir, backup_name.replace('.tar.gz', ''), item)
        target_item = os.path.join(root, item)

        if os.path.exists(backup_item):
            if os.path.isdir(backup_item):
                if os.path.exists(target_item):
                    shutil.rmtree(target_item)
                shutil.copytree(backup_item, target_item)
            else:
                shutil.copy2(backup_item, target_item)

    # 清理临时目录
    shutil.rmtree(extract_dir)

    return {"message": "恢复成功，请重启服务"}


@router.post("/apply")
def apply_update():
    """应用升级（仅升级代码，不影响数据库）"""
    root = get_project_root()
    update_path = os.path.join(root, UPDATES_DIR)

    if not os.path.exists(update_path):
        raise HTTPException(status_code=404, detail="没有找到升级文件")

    # 1. 先创建备份
    backup_result = create_backup()

    # 2. 复制文件
    copied = []
    for item in os.listdir(update_path):
        filepath = os.path.join(update_path, item)
        relpath = os.path.relpath(filepath, root)

        if is_protected(relpath):
            continue

        target = os.path.join(root, relpath)

        try:
            if os.path.isdir(filepath):
                if os.path.exists(target):
                    shutil.rmtree(target)
                shutil.copytree(filepath, target)
            else:
                shutil.copy2(filepath, target)
            copied.append(relpath)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"升级失败：{str(e)}")

    # 3. 更新版本文件
    version_file = os.path.join(update_path, "VERSION")
    if os.path.exists(version_file):
        with open(os.path.join(root, "version.py"), 'r') as f:
            content = f.read()
        with open(version_file, 'r') as f:
            new_version = f.read().strip().split('\n')[0].split('=')[1].strip().strip('"')

        # 简单替换版本号
        import re
        new_content = re.sub(
            r'BACKEND_VERSION = "[^"]*"',
            f'BACKEND_VERSION = "{new_version}"',
            content
        )
        with open(os.path.join(root, "version.py"), 'w') as f:
            f.write(new_content)

    return {
        "message": "升级成功",
        "backup": backup_result["name"],
        "copied_files": len(copied)
    }


@router.delete("/backups/{backup_name}")
def delete_backup(backup_name: str):
    """删除备份"""
    root = get_project_root()
    backup_path = os.path.join(root, BACKUPS_DIR, backup_name)

    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="备份文件不存在")

    os.remove(backup_path)
    return {"message": "备份已删除"}


# ==================== GitHub 升级 ====================

class GitHubRelease(BaseModel):
    tag_name: str
    name: str
    body: Optional[str] = None
    published_at: str
    html_url: str
    assets: List[dict] = []


class GitHubConfig(BaseModel):
    repo: str
    has_token: bool = False


@router.get("/github/config", response_model=GitHubConfig)
def get_github_config():
    """获取GitHub配置"""
    return {
        "repo": GITHUB_REPO,
        "has_token": bool(GITHUB_TOKEN)
    }


@router.post("/github/config")
def set_github_config(config: GitHubConfig):
    """设置GitHub仓库配置"""
    if config.repo and "/" not in config.repo:
        raise HTTPException(status_code=400, detail="仓库格式应为 owner/repo")

    root = get_project_root()
    version_file = os.path.join(root, "version.py")

    with open(version_file, 'r') as f:
        content = f.read()

    # 更新 GITHUB_REPO
    import re
    if 'GITHUB_REPO' in content:
        content = re.sub(
            r'GITHUB_REPO = "[^"]*"',
            f'GITHUB_REPO = "{config.repo}"',
            content
        )
    else:
        content = content + f'\nGITHUB_REPO = "{config.repo}"'

    with open(version_file, 'w') as f:
        f.write(content)

    # 更新 GITHUB_TOKEN（如果提供）
    if config.has_token and not GITHUB_TOKEN:
        raise HTTPException(status_code=400, detail="请在服务器环境变量中设置 GITHUB_TOKEN")

    return {"message": "配置已保存，需要重启服务生效"}


@router.get("/github/releases", response_model=List[GitHubRelease])
def get_github_releases():
    """获取GitHub releases列表"""
    if not GITHUB_REPO:
        raise HTTPException(status_code=400, detail="请先配置GitHub仓库")

    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "FitnessSchedule-Updater"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            releases = json.loads(response.read().decode())

            # 只返回有附件的releases（排除源码包）
            result = []
            for r in releases:
                if r.get("assets"):  # 有附件的才显示
                    result.append({
                        "tag_name": r["tag_name"],
                        "name": r["name"] or r["tag_name"],
                        "body": r.get("body", ""),
                        "published_at": r["published_at"],
                        "html_url": r["html_url"],
                        "assets": [{"name": a["name"], "size": a["size"], "download_count": a.get("download_count", 0)} for a in r.get("assets", [])]
                    })

            return result
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise HTTPException(status_code=404, detail="仓库不存在或不可访问")
        elif e.code == 403:
            raise HTTPException(status_code=403, detail="API访问受限，请设置GitHub Token")
        raise HTTPException(status_code=500, detail=f"获取失败: {e.code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"网络错误: {str(e)}")


@router.get("/github/latest")
def get_latest_release():
    """获取最新版本信息"""
    if not GITHUB_REPO:
        raise HTTPException(status_code=400, detail="请先配置GitHub仓库")

    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "FitnessSchedule-Updater"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            r = json.loads(response.read().decode())

            # 比较版本
            latest_version = r["tag_name"].lstrip('v')
            current = BACKEND_VERSION.lstrip('v')

            # 简单版本比较
            def parse_version(v):
                return [int(x) for x in v.split('.')]

            latest_parts = parse_version(latest_version)
            current_parts = parse_version(current)

            is_newer = latest_parts > current_parts

            return {
                "tag_name": r["tag_name"],
                "name": r["name"] or r["tag_name"],
                "body": r.get("body", ""),
                "published_at": r["published_at"],
                "html_url": r["html_url"],
                "is_newer": is_newer,
                "current_version": BACKEND_VERSION,
                "assets": [{"name": a["name"], "size": a["size"], "download_count": a.get("download_count", 0)} for a in r.get("assets", [])]
            }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise HTTPException(status_code=404, detail="暂无发布版本")
        raise HTTPException(status_code=500, detail=f"获取失败: {e.code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"网络错误: {str(e)}")


@router.post("/github/download/{tag_name}")
def download_github_release(tag_name: str):
    """从GitHub下载并解压指定版本的升级包"""
    if not GITHUB_REPO:
        raise HTTPException(status_code=400, detail="请先配置GitHub仓库")

    root = get_project_root()
    update_path = os.path.join(root, UPDATES_DIR)

    # 清理旧升级目录
    if os.path.exists(update_path):
        shutil.rmtree(update_path)
    os.makedirs(update_path)

    # 获取release信息
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{tag_name}"

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "FitnessSchedule-Updater"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            r = json.loads(response.read().decode())

            # 查找zipball或tarball资产
            zip_url = None
            for asset in r.get("assets", []):
                if asset["name"].endswith(".zip"):
                    zip_url = asset["browser_download_url"]
                    break

            if not zip_url:
                raise HTTPException(status_code=404, detail="未找到升级包（需要提供.zip格式的发布资产）")

            # 下载zip文件
            req = urllib.request.Request(zip_url, headers=headers)
            with urllib.request.urlopen(req, timeout=300) as response:
                zip_data = io.BytesIO(response.read())

            # 解压到updates目录
            with zipfile.ZipFile(zip_data, 'r') as zip_ref:
                # 获取顶层目录名
                names = zip_ref.namelist()
                top_dir = names[0].split('/')[0] if names else ''

                for name in names:
                    if name.startswith(top_dir):
                        # 去掉顶层目录
                        target_name = name[len(top_dir):].lstrip('/')
                        if not target_name:
                            continue

                        target_path = os.path.join(update_path, target_name)

                        if name.endswith('/'):
                            # 目录
                            os.makedirs(target_path, exist_ok=True)
                        else:
                            # 文件
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)
                            with zip_ref.open(name) as source:
                                with open(target_path, 'wb') as target:
                                    target.write(source.read())

            # 写入VERSION文件
            with open(os.path.join(update_path, "VERSION"), 'w') as f:
                f.write(f'BACKEND_VERSION = "{tag_name.lstrip("v")}"\n')

            return {
                "message": "下载成功",
                "version": tag_name,
                "files": len(names)
            }

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="下载的文件不是有效的ZIP格式")
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=e.code, detail=f"下载失败: {e.code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")
