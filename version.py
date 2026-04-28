import os

# 版本信息
FRONTEND_VERSION = "1.0.1"
BACKEND_VERSION = "1.0.1"

# 升级目录
UPDATES_DIR = "updates"
BACKUPS_DIR = "backups"

# GitHub 仓库配置（留空则不启用GitHub升级）
GITHUB_REPO = "kerry-lu/fitness-schedule"  # 格式: owner/repo 例如: "username/fitness_schedule"
# GitHub Token 从环境变量获取，不要硬编码在代码中
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
