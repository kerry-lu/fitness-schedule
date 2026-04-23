from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import engine, Base
import models
import routers.auth
import routers.students
import routers.courses
import routers.schedules
import routers.templates
import routers.coaches

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

# 静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/login")
def login_page():
    return FileResponse("static/login.html")


@app.get("/management")
def management_page():
    return FileResponse("static/management.html")
