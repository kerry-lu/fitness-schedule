# 跃界-课表管理系统

健身教练课程安排与学员课时管理系统，支持多教练、多学员、课程模板、日历视图、在线升级等功能。

## 功能特性

- **日历视图** - FullCalendar 实现，支持月/周/日视图切换
- **课程管理** - 快速添加、编辑、删除课程安排
- **学员管理** - 学员信息管理、课时统计、课时调整
- **模板系统** - 训练内容模板复用，支持多阶段多动作
- **教练管理** - 支持主教练/教练角色权限
- **重复课程** - 支持每天/每周/每月重复，可选特定日期（如每周二、四）
- **快速添加** - 点击日历日期快速创建课程
- **教练筛选** - 按教练过滤日历显示
- **上课记录** - 完成上课、标记缺席、教练备注
- **在线升级** - 支持从 GitHub 下载并应用更新，数据库完全不受影响
- **响应式设计** - 支持桌面端和移动端

## 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite
- **前端**: 原生 JavaScript + FullCalendar 6.1.10 (本地化)
- **认证**: JWT Token
- **容器化**: Docker / Docker Compose

## 快速启动

### Docker 方式（推荐）

```bash
# 克隆项目
git clone https://github.com/kerry-lu/fitness-schedule.git
cd fitness-schedule

# 启动服务
./start.sh

# 停止服务
./stop.sh
```

访问 http://localhost:8000

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 设置密钥环境变量（必须）
export SECRET_KEY=your-secret-key-here

# 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 重要配置

### SECRET_KEY 环境变量

**必须设置！** 系统强制要求 `SECRET_KEY` 环境变量用于 JWT token 签名。

```bash
# 建议使用 32+ 字符的随机字符串
export SECRET_KEY=your-very-long-random-secret-key
```

## 初始账号

首次启动访问 http://localhost:8000/login 注册账号，第一个注册的账号自动成为主教练。

## 页面说明

### 首页 - 日历视图

- 显示所有课程安排，按教练颜色区分
- 支持拖拽调整课程时间
- 点击日期可快速添加课程
- 筛选器支持按教练/学员/课程过滤
- 已完成的课程显示为灰色

**颜色区分（按教练）：**
- 教练1: 蓝色
- 教练2: 绿色
- 教练3: 橙色
- 教练4: 红色
- 更多教练以此类推

### 管理页面

访问 http://localhost:8000/management

- **学员管理** - 添加/编辑/删除学员，设置课时、到期日期
- **课程管理** - 添加/编辑/删除课程类型，设置时长
- **模板管理** - 添加/编辑/删除训练内容模板
- **系统** - 版本信息、在线升级、备份恢复、数据库迁移

## 课程时间设置

- 可预约时间：10:00 - 20:00
- 每节课时长：30/60/90/120 分钟
- 支持课程时间冲突检测

## 在线升级

系统支持从 GitHub 在线升级，升级过程完全不影响数据库。

### 升级步骤

1. 访问管理页面 → 系统
2. 查看当前版本
3. 如有可用更新，点击"下载"获取新版本
4. 点击"应用升级"
5. 系统自动创建备份，升级完成后刷新页面即可

### 配置 GitHub 仓库

系统已预配置 `kerry-lu/fitness-schedule`，如需更改为其他仓库：

编辑 `version.py`：
```python
GITHUB_REPO = "your-username/your-repo"
```

如需提高 GitHub API 限制，可设置环境变量：
```bash
export GITHUB_TOKEN=ghp_your_token_here
```

### 手动升级（不拉取 git）

```bash
# 1. 备份数据库
cp fitness_schedule.db fitness_schedule.db.backup

# 2. 下载升级包并解压
wget https://github.com/kerry-lu/fitness-schedule/releases/download/v1.0.1/fitness_schedule_v1.0.1.zip
unzip -o fitness_schedule_v1.0.1.zip

# 3. 重启服务
```

**升级安全特性：**
- 自动创建代码备份
- 数据库文件完全不受影响
- 支持从备份恢复
- 受保护文件（数据库、虚拟环境、git等）不会被覆盖

## 数据库迁移

系统支持数据库迁移，便于版本升级。

```bash
# 查看迁移状态
python migrations/manager.py status

# 执行待应用迁移
python migrations/manager.py migrate
```

## 软路由 Docker 部署

### 在 OpenWrt 软路由上安装 Docker

```bash
# 安装 Docker
opkg update
opkg install docker docker-compose luci-app-docker

# 启动 Docker
/etc/init.d/docker start
/etc/init.d/docker enable

# 配置存储路径（重要！软路由空间有限）
# 假设使用 U 盘挂载到 /mnt/sda1
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << EOF
{
  "data-root": "/mnt/sda1/docker"
}
EOF
/etc/init.d/docker restart
```

### 部署服务

```bash
# 拉取镜像
docker pull kerrylu/fitness-schedule:latest

# 创建数据目录
mkdir -p /mnt/sda1/fitness-schedule

# 运行容器
docker run -d \
  --name fitness-schedule \
  --restart unless-stopped \
  -p 8000:8000 \
  -e SECRET_KEY=your-production-secret-key \
  -v /mnt/sda1/fitness-schedule/fitness_schedule.db:/app/fitness_schedule.db \
  kerrylu/fitness-schedule:latest
```

**注意：**
- 存储路径 `/mnt/sda1` 根据实际挂载情况调整
- 务必设置 `SECRET_KEY` 环境变量
- 数据库文件映射到容器内 `/app/fitness_schedule.db`

### 更新服务（不丢失数据）

```bash
# 1. 进入目录
cd /opt/fitness-schedule  # 或你的实际路径

# 2. 备份数据库
cp fitness_schedule.db fitness_schedule.db.backup

# 3. 停止容器
docker stop fitness-schedule

# 4. 拉取新代码
git pull

# 5. 重新构建镜像
docker build -t fitness-schedule:latest .

# 6. 重启容器
docker start fitness-schedule
```

## 安全特性

- JWT Token 认证（强制要求 SECRET_KEY）
- 统一的登录错误消息（防止用户枚举）
- 输入验证（密码长度、手机号格式、年龄范围等）
- HTML 转义防 XSS
- 外键级联删除
- 数据库索引优化
- 升级时数据库完全隔离

## 测试

```bash
# 运行测试
SECRET_KEY=test-secret pytest tests/ -v
```

## 变更日志

### v1.0.1 (2026-04-27)

**新增功能：**
- GitHub 在线升级功能
- 完成上课后课程在日历中变灰显示
- 课时扣减显示整数
- 课时调整功能（可增加/减少课时）
- 修复日历变灰问题
- FullCalendar 本地化（避免 CDN 超时）

**技术改进：**
- 新增 routers/upgrade.py 提供升级 API
- 新增 version.py 管理版本信息
- 课程状态样式区分（已完成/缺席/取消）

### v1.0.0 (2026-04-24)

**安全更新：**
- JWT 密钥强制使用环境变量
- 统一登录错误消息防止用户枚举
- 前端 HTML 转义防 XSS 攻击
- 添加外键级联删除

**功能更新：**
- 数据库迁移框架
- API 分页支持
- 输入验证增强
- Toast 通知系统
- 全局异常处理

**性能优化：**
- 数据库外键列添加索引

## 许可证

MIT License
