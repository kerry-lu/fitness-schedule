"""
认证相关测试
"""
import pytest
from auth import verify_password, get_password_hash, create_access_token


class TestPasswordHashing:
    """密码哈希测试"""

    def test_password_hash_is_different_from_plain(self):
        """哈希后的密码与原文不同"""
        password = "mysecretpassword"
        hashed = get_password_hash(password)
        assert hashed != password

    def test_same_password_different_hashes(self):
        """同一密码每次哈希结果不同（因为加盐）"""
        password = "mysecretpassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2

    def test_verify_correct_password(self):
        """验证正确密码"""
        password = "mysecretpassword"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """验证错误密码"""
        password = "mysecretpassword"
        hashed = get_password_hash(password)
        assert verify_password("wrongpassword", hashed) is False


class TestJWTToken:
    """JWT Token 测试"""

    def test_create_access_token(self):
        """创建访问令牌"""
        token = create_access_token(data={"sub": "123"})
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_parts(self):
        """Token 包含三部分（用点分隔）"""
        token = create_access_token(data={"sub": "123"})
        parts = token.split(".")
        assert len(parts) == 3
