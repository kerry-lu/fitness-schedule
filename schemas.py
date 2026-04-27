from __future__ import annotations
from pydantic import BaseModel, field_validator
from datetime import date, time, datetime
from typing import Optional, Union
import re


class UserBase(BaseModel):
    username: str
    name: str


class UserCreate(UserBase):
    password: str
    role: Optional[str] = "coach"

    @field_validator('password')
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        return v

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v


class StudentBase(BaseModel):
    name: str
    phone: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    specialty: Optional[str] = None
    rehabilitation: Optional[str] = None
    note: Optional[str] = None

    @field_validator('age')
    @classmethod
    def age_range(cls, v):
        if v is not None and (v < 1 or v > 150):
            raise ValueError('年龄必须在1-150之间')
        return v

    @field_validator('phone')
    @classmethod
    def phone_format(cls, v):
        if v and not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('手机号格式不正确')
        return v


class UserResponse(UserBase):
    id: int
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class StudentCreate(StudentBase):
    total_hours: Optional[int] = 0
    remaining_hours: Optional[float] = 0.0
    expiration_date: Optional[date] = None
    enable_credits: Optional[int] = 1


class StudentResponse(StudentBase):
    id: int
    user_id: int
    total_hours: int
    remaining_hours: float
    expiration_date: Optional[date] = None
    enable_credits: int
    created_at: datetime

    class Config:
        from_attributes = True


class CourseBase(BaseModel):
    name: str
    duration_minutes: int
    description: Optional[str] = None

    @field_validator('duration_minutes')
    @classmethod
    def duration_positive(cls, v):
        if v <= 0:
            raise ValueError('课程时长必须大于0')
        return v


class CourseCreate(CourseBase):
    pass


class CourseResponse(CourseBase):
    id: int

    class Config:
        from_attributes = True


class TemplateBase(BaseModel):
    name: str
    content: str  # JSON 格式


class TemplateCreate(TemplateBase):
    pass


class TemplateResponse(TemplateBase):
    id: int

    class Config:
        from_attributes = True


class ScheduleBase(BaseModel):
    student_id: int
    course_id: int
    coach_id: Optional[int] = None  # 教练 ID
    date: date
    start_time: time
    note: Optional[str] = None
    template_id: Optional[int] = None
    training_content: Optional[str] = None
    repeat_type: Optional[str] = "none"
    repeat_end_date: Optional[date] = None
    repeat_days: Optional[str] = None  # JSON格式，如 "[1,3,5]"


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    student_id: Union[int, None] = None
    course_id: Union[int, None] = None
    coach_id: Union[int, None] = None
    date: Union[date, str, None] = None
    start_time: Union[time, str, None] = None
    note: Union[str, None] = None
    template_id: Union[int, None] = None
    training_content: Union[str, None] = None
    repeat_type: Union[str, None] = None
    repeat_end_date: Union[date, str, None] = None
    repeat_days: Union[str, None] = None


class AttendanceBase(BaseModel):
    schedule_id: int
    student_id: int
    date: date
    status: Optional[str] = "completed"
    student_status: Optional[str] = None
    coach_note: Optional[str] = None


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(BaseModel):
    status: Optional[str] = None
    student_status: Optional[str] = None
    coach_note: Optional[str] = None


class AttendanceResponse(AttendanceBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ScheduleResponse(ScheduleBase):
    id: int
    user_id: int
    end_time: time
    created_at: datetime
    series_id: Optional[str] = None
    student: Optional[StudentResponse] = None
    course: Optional[CourseResponse] = None
    template: Optional[TemplateResponse] = None
    attendance_record: Optional[AttendanceResponse] = None
    coach: Optional[UserResponse] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
