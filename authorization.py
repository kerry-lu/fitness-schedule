"""
权限验证工具函数
"""
import models
from auth import is_head_coach


def can_modify_student(student: models.Student, current_user: models.User) -> bool:
    """检查是否可以修改学员：创建者或主教练"""
    return student.user_id == current_user.id or is_head_coach(current_user)


def can_modify_schedule(schedule: models.Schedule, current_user: models.User) -> bool:
    """检查是否可以修改课程安排：创建者或主教练"""
    return schedule.user_id == current_user.id or is_head_coach(current_user)


def can_modify_template(template: models.CourseTemplate, current_user: models.User) -> bool:
    """检查是否可以修改模板：创建者或主教练"""
    return template.user_id == current_user.id or is_head_coach(current_user)


def can_access_coach_management(current_user: models.User) -> bool:
    """检查是否可以访问教练管理功能"""
    return is_head_coach(current_user)
