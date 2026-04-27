from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from database import engine, Base
import models
import routers.auth
import routers.students
import routers.courses
import routers.schedules
import routers.templates
import routers.coaches
import routers.upgrade
import routers.database_backup

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="体能教练课表系统")

# 挂载路由
app.include_router(routers.auth.router)
app.include_router(routers.students.router)
app.include_router(routers.courses.router)
app.include_router(routers.schedules.router)
app.include_router(routers.templates.router)
app.include_router(routers.coaches.router)
app.include_router(routers.upgrade.router)
app.include_router(routers.database_backup.router)

# 静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误，返回友好的中文错误消息"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        msg = error["msg"]
        errors.append(f"{field}: {msg}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "，".join(errors) if errors else "请求参数验证失败"}
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """处理数据库错误"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "数据库操作失败，请稍后重试"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "服务器内部错误，请稍后重试"}
    )


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/login")
def login_page():
    return FileResponse("static/login.html")


@app.get("/management")
def management_page():
    return FileResponse("static/management.html")


# 迁移 API
@app.get("/api/migrations/status")
def get_migration_status():
    """获取迁移状态"""
    from migrations.manager import MigrationManager
    manager = MigrationManager()
    applied = manager.get_applied_migrations()
    pending = manager.get_pending_migrations()
    return {
        "applied": applied,
        "pending": [{"version": v, "name": n} for v, n in pending],
        "all_applied": len(pending) == 0
    }


@app.post("/api/migrations/migrate")
def run_migrations():
    """执行待应用的迁移"""
    from migrations.manager import MigrationManager
    manager = MigrationManager()
    pending = manager.get_pending_migrations()
    if not pending:
        return {"message": "没有待应用的迁移", "applied": [], "pending": []}

    applied = []
    for version, name in pending:
        manager.apply_migration(version)
        applied.append({"version": version, "name": name})

    return {
        "message": f"已应用 {len(applied)} 个迁移",
        "applied": applied,
        "pending": manager.get_pending_migrations()
    }
