#!/bin/bash

# 构建并启动容器
docker-compose up -d --build

echo "服务已启动: http://localhost:8000"
echo "登录页: http://localhost:8000/login"
