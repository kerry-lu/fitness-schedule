"""
API 端点测试
"""
import pytest


class TestAuthAPI:
    """认证 API 测试"""

    def test_register_success(self, client):
        """成功注册用户"""
        response = client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "password123", "name": "新用户"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["name"] == "新用户"
        assert "id" in data

    def test_register_duplicate_username(self, client, test_user):
        """重复用户名应失败"""
        response = client.post(
            "/api/auth/register",
            json={"username": "testuser", "password": "password123", "name": "另一个用户"}
        )
        assert response.status_code == 400
        assert "用户名已存在" in response.json()["detail"]

    def test_register_password_too_short(self, client):
        """密码太短应失败"""
        response = client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "12345", "name": "新用户"}
        )
        assert response.status_code == 422

    def test_login_success(self, client, test_user):
        """成功登录"""
        response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """错误密码应失败"""
        response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """不存在的用户应失败"""
        response = client.post(
            "/api/auth/login",
            data={"username": "nonexistent", "password": "password123"}
        )
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]

    def test_get_me_success(self, client, test_user):
        """获取当前用户信息"""
        # 先登录获取 token
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        token = login_response.json()["access_token"]

        # 获取用户信息
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["username"] == "testuser"

    def test_get_me_without_token(self, client):
        """无 token 应失败"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401


class TestStudentAPI:
    """学员管理 API 测试"""

    def test_create_student(self, client, test_user):
        """创建学员"""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        token = login_response.json()["access_token"]

        response = client.post(
            "/api/students",
            json={"name": "学员张三", "phone": "13800138000", "age": 25},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "学员张三"
        assert data["phone"] == "13800138000"

    def test_list_students(self, client, test_user):
        """列出学员"""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        token = login_response.json()["access_token"]

        # 创建学员
        client.post(
            "/api/students",
            json={"name": "学员一"},
            headers={"Authorization": f"Bearer {token}"}
        )

        # 列出学员
        response = client.get(
            "/api/students",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_students_pagination(self, client, test_user):
        """学员列表分页"""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/students?skip=0&limit=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200


class TestCourseAPI:
    """课程管理 API 测试"""

    def test_create_course(self, client, test_user):
        """创建课程"""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        token = login_response.json()["access_token"]

        response = client.post(
            "/api/courses",
            json={"name": "体能训练", "duration_minutes": 60},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "体能训练"

    def test_list_courses(self, client, test_user):
        """列出课程"""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/courses",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
