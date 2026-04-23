"""
Schema 验证测试
"""
import pytest
from pydantic import ValidationError
from schemas import UserCreate, StudentCreate, CourseCreate


class TestUserSchema:
    """用户 Schema 测试"""

    def test_valid_user_create(self):
        """创建有效用户"""
        user = UserCreate(username="testuser", password="password123", name="测试用户")
        assert user.username == "testuser"
        assert user.password == "password123"

    def test_password_too_short(self):
        """密码太短应抛出验证错误"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="testuser", password="12345", name="测试用户")
        assert "密码长度至少6位" in str(exc_info.value)

    def test_username_with_special_chars(self):
        """用户名包含特殊字符应抛出验证错误"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="test@user", password="password123", name="测试用户")
        assert "用户名只能包含字母、数字和下划线" in str(exc_info.value)

    def test_username_with_space(self):
        """用户名包含空格应抛出验证错误"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="test user", password="password123", name="测试用户")
        assert "用户名只能包含字母、数字和下划线" in str(exc_info.value)

    def test_username_underscore_ok(self):
        """下划线用户名应该有效"""
        user = UserCreate(username="test_user", password="password123", name="测试用户")
        assert user.username == "test_user"


class TestStudentSchema:
    """学员 Schema 测试"""

    def test_valid_student_create(self):
        """创建有效学员"""
        student = StudentCreate(name="张三", phone="13800138000", age=25)
        assert student.name == "张三"
        assert student.age == 25

    def test_invalid_phone_format(self):
        """无效手机号格式"""
        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(name="张三", phone="12345")
        assert "手机号格式不正确" in str(exc_info.value)

    def test_valid_china_mobile_phone(self):
        """有效中国手机号"""
        student = StudentCreate(name="张三", phone="13800138000")
        assert student.phone == "13800138000"

    def test_age_too_young(self):
        """年龄太小"""
        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(name="张三", age=0)
        assert "年龄必须在1-150之间" in str(exc_info.value)

    def test_age_too_old(self):
        """年龄太大"""
        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(name="张三", age=200)
        assert "年龄必须在1-150之间" in str(exc_info.value)

    def test_valid_age_boundary(self):
        """边界年龄值应该有效"""
        student1 = StudentCreate(name="张三", age=1)
        assert student1.age == 1
        student2 = StudentCreate(name="李四", age=150)
        assert student2.age == 150


class TestCourseSchema:
    """课程 Schema 测试"""

    def test_valid_course_create(self):
        """创建有效课程"""
        course = CourseCreate(name="体能训练", duration_minutes=60)
        assert course.name == "体能训练"
        assert course.duration_minutes == 60

    def test_zero_duration(self):
        """零时长应抛出验证错误"""
        with pytest.raises(ValidationError) as exc_info:
            CourseCreate(name="无效课程", duration_minutes=0)
        assert "课程时长必须大于0" in str(exc_info.value)

    def test_negative_duration(self):
        """负时长应抛出验证错误"""
        with pytest.raises(ValidationError) as exc_info:
            CourseCreate(name="无效课程", duration_minutes=-30)
        assert "课程时长必须大于0" in str(exc_info.value)
