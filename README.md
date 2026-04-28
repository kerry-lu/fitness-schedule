# 跃界-课表管理系统

健身教练课程安排与学员课时管理系统，支持多教练、多学员、课程模板、日历视图、在线升级等功能。

## 功能特性

- **日历视图** - FullCalendar 实现，支持月/周/日视图切换
- **课程管理** - 快速添加、编辑、删除课程安排
- **学员管理** - 学员信息管理、课时统计、课时调整
- **模板系统** - 训练内容模板复用，支持多阶段多动作
- **教练管理** - 支持主教练/教练角色权限
- **重复课程** - 支持每天/每周/每月重复，可选特定日期
- **上课记录** - 完成上课、标记缺席、教练备注
- **数据库备份** - 支持备份、恢复（仅主教练可操作）
- **在线升级** - 支持从 GitHub 下载并应用更新
- **响应式设计** - 支持桌面端和移动端

## 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite
- **前端**: 原生 JavaScript + FullCalendar 6.1.10
- **认证**: JWT Token（7天过期）
- **容器化**: Docker / Docker Compose

## 环境要求

- Docker 20.10+
- Docker Compose 2.0+

## Docker 安装（推荐）

### 方式一：使用 docker-compose

```bash
# 1. 创建项目目录
mkdir -p fitness-schedule && cd fitness-schedule

# 2. 下载 docker-compose.yml
curl -O https://raw.githubusercontent.com/kerry-lu/fitness-schedule/main/docker-compose.yml

# 3. 创建数据目录
mkdir -p data

# 4. 启动服务
SECRET_KEY=$(openssl rand -hex 32) docker-compose up -d
```

### 方式二：手动部署

```bash
# 1. 克隆项目
git clone https://github.com/kerry-lu/fitness-schedule.git
cd fitness-schedule

# 2. 创建数据目录
mkdir -p data

# 3. 构建镜像
docker build -t fitness-schedule .

# 4. 启动容器
docker run -d \
  --name fitness-schedule \
  --restart unless-stopped \
  -p 8000:8000 \
  -e SECRET_KEY=your-secure-random-key \
  -e DATABASE_PATH=/app/data/fitness_schedule.db \
  -v $(pwd)/data:/app/data \
  fitness-schedule
```

### 方式三：使用预构建镜像

```bash
# 1. 创建数据目录
mkdir -p data

# 2. 启动容器
docker run -d \
  --name fitness-schedule \
  --restart unless-stopped \
  -p 8000:8000 \
  -e SECRET_KEY=your-secure-random-key \
  -e DATABASE_PATH=/app/data/fitness_schedule.db \
  -v $(pwd)/data:/app/data \
  kerrylu/fitness-schedule:latest
```

### 访问系统

启动后访问 http://localhost:8000

首次使用需注册账号，第一个注册的账号自动成为**主教练**。

## Docker Compose 配置说明

```yaml
version: '3.8'

services:
  fitness_schedule:
    build: .
    container_name: fitness_schedule
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data          # 数据持久化
    environment:
      - TZ=Asia/Shanghai          # 时区
      - SECRET_KEY=<你的密钥>     # 必须设置！
      - DATABASE_PATH=/app/data/fitness_schedule.db
```

### 环境变量说明

| 变量 | 必须 | 说明 |
|------|------|------|
| `SECRET_KEY` | 是 | JWT 签名密钥，建议 32+ 字符随机字符串 |
| `DATABASE_PATH` | 否 | 数据库路径，默认 `/app/data/fitness_schedule.db` |
| `TZ` | 否 | 时区，默认 `Asia/Shanghai` |
| `GITHUB_TOKEN` | 否 | GitHub API 令牌，提高升级时的 API 限制 |

### 生成密钥

```bash
# Linux/Mac
openssl rand -hex 32

# 或使用 Python
python -c "import secrets; print(secrets.token_hex(32))"
```

## 数据管理

### 备份数据库

```bash
# 备份 data 目录
tar -czf backup_$(date +%Y%m%d).tar.gz data/

# 或使用容器内备份
docker exec fitness-schedule curl -X POST http://localhost:8000/api/database/backup
```

### 恢复数据库

```bash
# 1. 停止容器
docker-compose down  # 或 docker stop fitness-schedule

# 2. 恢复数据目录
rm -rf data/*
tar -xzf backup_xxxx.tar.gz

# 3. 重启容器
docker-compose up -d  # 或 docker start fitness-schedule
```

### 更新系统

```bash
# 1. 拉取最新代码
git pull

# 2. 重建镜像
docker-compose build

# 3. 重启服务
docker-compose up -d

# 数据目录不会被影响
```

## 在线升级

系统支持从 GitHub 在线升级，升级过程不影响数据库。

### 升级步骤

1. 以主教练账号登录
2. 访问 **管理页面 → 系统**
3. 查看当前版本，如有更新点击"下载"
4. 点击"应用升级"
5. 系统自动创建备份，升级完成后刷新页面

### 配置 GitHub Token（可选）

如遇 GitHub API 限制，可设置环境变量：

```bash
# docker-compose.yml 添加
environment:
  - GITHUB_TOKEN=ghp_your_token_here
```

## 权限说明

| 角色 | 权限 |
|------|------|
| 主教练 | 所有功能：学员/课程/模板管理、数据库备份、在线升级 |
| 教练 | 课表管理、查看学员信息、上课记录 |

## 常见问题

### Q: 忘记主教练密码怎么办？

数据库备份目录 `db_backups/` 找到备份文件，恢复即可。

### Q: 如何查看日志？

```bash
docker logs fitness-schedule
```

### Q: 如何进入容器？

```bash
docker exec -it fitness-schedule /bin/bash
```

### Q: 端口被占用？

修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "8080:8000"  # 改为 8080:8000
```

## 本地开发

```bash
# 克隆项目
git clone https://github.com/kerry-lu/fitness-schedule.git
cd fitness-schedule

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export SECRET_KEY=dev-secret-key

# 启动服务
uvicorn main:app --reload
```

## 安全说明

- JWT Token 7 天过期
- 数据库备份/升级功能仅主教练可操作
- SECRET_KEY 必须设置，建议使用随机字符串
- GitHub Token 建议使用环境变量而非硬编码

## 许可证

MIT License
