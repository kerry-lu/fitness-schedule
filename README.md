# 跃界-课表管理系统

健身教练课程安排与学员课时管理系统，支持多教练、多学员、课程模板、日历视图等功能。

## 功能特性

- **日历视图** - FullCalendar 实现，支持月/周/日视图切换
- **课程管理** - 快速添加、编辑、删除课程安排
- **学员管理** - 学员信息管理、课时统计
- **模板系统** - 训练内容模板复用，支持多阶段多动作
- **教练管理** - 支持主教练/教练角色权限
- **重复课程** - 支持每天/每周/每月重复
- **快速添加** - 点击日历日期快速创建课程
- **响应式设计** - 支持桌面端和移动端

## 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite
- **前端**: 原生 JavaScript + FullCalendar 6.1.10
- **认证**: JWT Token
- **容器化**: Docker / Docker Compose

## 快速启动

### Docker 方式（推荐）

```bash
# 克隆项目
git clone https://github.com/kerry-lu/fitness-schedule.git
cd fitness-schedule

# 启动服务（使用默认密钥，仅用于开发）
./start.sh

# 停止服务
./stop.sh
```

访问 http://localhost:8000

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 设置密钥环境变量
export SECRET_KEY=your-secret-key-here

# 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

访问 http://localhost:8000

## 重要配置

### SECRET_KEY 环境变量

**必须设置！** 系统强制要求 `SECRET_KEY` 环境变量用于 JWT token 签名。

```bash
# Linux/macOS
export SECRET_KEY=your-very-long-random-secret-key

# Windows (CMD)
set SECRET_KEY=your-very-long-random-secret-key

# Docker 运行时
docker run -e SECRET_KEY=your-secret-key kerrylu/fitness-schedule:latest
```

建议使用 32+ 字符的随机字符串作为密钥。

## 数据库迁移

系统支持数据库迁移，便于版本升级。

```bash
# 查看迁移状态
python migrations/manager.py status

# 执行待应用迁移
python migrations/manager.py migrate

# 回滚到指定版本
python migrations/manager.py rollback 001

# 创建新迁移
python migrations/create.py add_new_field
```

## 软路由 Docker 部署

### 方式一：使用 GitHub 自动构建（推荐）

1. **配置 Docker Hub 密钥**
   - 在 GitHub 仓库 Settings → Secrets 中添加：
     - `DOCKERHUB_USERNAME`：你的 Docker Hub 用户名
     - `DOCKERHUB_TOKEN`：你的 Docker Hub Access Token

2. **推送代码自动构建**
   - 每次推送代码到 main 分支，GitHub Actions 会自动构建并推送镜像到 Docker Hub

3. **在软路由上拉取并运行**
   ```bash
   # 拉取镜像
   docker pull kerrylu/fitness-schedule:latest

   # 创建数据目录
   mkdir -p /mnt/storage/fitness-schedule/data

   # 运行容器（注意设置 SECRET_KEY）
   docker run -d \
     --name fitness-schedule \
     --restart unless-stopped \
     -p 8000:8000 \
     -e SECRET_KEY=your-production-secret-key \
     -v /mnt/storage/fitness-schedule/data:/app/data \
     kerrylu/fitness-schedule:latest
   ```

### 方式二：本地构建镜像

在有 Docker 的电脑上：

```bash
# 克隆项目
git clone https://github.com/kerry-lu/fitness-schedule.git
cd fitness-schedule

# 构建镜像
docker build -t kerrylu/fitness-schedule:latest .

# 导出镜像（可选）
docker save kerrylu/fitness-schedule:latest -o fitness-schedule.tar

# 上传到软路由（使用 scp 或 U 盘）
scp fitness-schedule.tar root@192.168.1.1:/tmp/

# 在软路由上加载镜像
docker load -i /tmp/fitness-schedule.tar

# 运行容器
docker run -d \
  --name fitness-schedule \
  --restart unless-stopped \
  -p 8000:8000 \
  -e SECRET_KEY=your-secret-key \
  -v /mnt/storage/fitness-schedule/data:/app/data \
  kerrylu/fitness-schedule:latest
```

### 软路由解析cli命令示例

```bash
# 拉取镜像
docker pull kerrylu/fitness-schedule:latest

# 创建容器
解析cli run -d --name fitness-schedule --restart unless-stopped -p 8000:8000 -e SECRET_KEY=your-secret-key -v /mnt/storage/fitness-schedule/data:/app/data kerrylu/fitness-schedule:latest
```

**注意事项：**
- 确保软路由已安装 Docker
- 数据目录 `/mnt/storage/fitness-schedule/data` 请根据实际存储路径修改
- 首次使用需要登录注册账号
- **必须设置 `SECRET_KEY` 环境变量**

## 初始账号

首次启动需要注册账号，第一个注册的账号自动成为主教练。

## 页面说明

### 首页 - 日历视图

- 显示所有课程安排
- 支持拖拽调整课程时间
- 点击日期可快速添加课程
- 右侧面板显示课程详情

### 管理页面

- **学员管理** - 添加/编辑/删除学员，设置课时
- **课程管理** - 添加/编辑/删除课程类型，设置时长
- **模板管理** - 添加/编辑/删除训练内容模板

## 课程时间设置

- 可预约时间：10:00 - 20:00
- 每节课时长：30/60/90/120 分钟

## 安全特性

- JWT Token 认证（强制要求 SECRET_KEY）
- 统一的登录错误消息（防止用户枚举）
- 输入验证（密码长度、手机号格式、年龄范围等）
- HTML 转义防 XSS
- 外键级联删除
- 数据库索引优化

## 测试

```bash
# 安装测试依赖
pip install pytest

# 运行测试
SECRET_KEY=test-secret pytest tests/ -v
```

## 变更日志

### v2.0 (2026-04-24)

**安全更新：**
- JWT 密钥强制使用环境变量
- 统一登录错误消息防止用户枚举
- 前端 HTML 转义防 XSS 攻击
- 添加外键级联删除

**功能更新：**
- 数据库迁移框架
- API 分页支持
- 输入验证增强（密码、手机号、年龄、课程时长）
- Toast 通知系统
- 全局异常处理

**性能优化：**
- 数据库外键列添加索引
- 扣减课时常量定义

## 许可证

MIT License
