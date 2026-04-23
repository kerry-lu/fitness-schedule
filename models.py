from sqlalchemy import Column, Integer, Float, String, Text, Date, Time, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    name = Column(String)
    role = Column(String, default="coach")  # coach=教练, head_coach=主教练
    created_at = Column(DateTime, default=datetime.utcnow)

    students = relationship("Student", back_populates="user")
    schedules = relationship("Schedule", back_populates="user")
    course_templates = relationship("CourseTemplate", back_populates="user")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, index=True)
    phone = Column(String, nullable=True)
    gender = Column(String, nullable=True)  # 男/女
    age = Column(Integer, nullable=True)  # 年龄
    specialty = Column(String, nullable=True)  # 专项类型（如：增肌、减脂、康复等）
    rehabilitation = Column(Text, nullable=True)  # 康复内容
    note = Column(Text, nullable=True)
    # 课时管理
    total_hours = Column(Integer, default=0)  # 总课时
    remaining_hours = Column(Float, default=0.0)  # 剩余课时
    expiration_date = Column(Date, nullable=True)  # 到期日期
    enable_credits = Column(Integer, default=1)  # 是否启用课时功能 0=关闭 1=开启
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="students")
    schedules = relationship("Schedule", back_populates="student")
    attendance_records = relationship("AttendanceRecord", back_populates="student")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    duration_minutes = Column(Integer)
    description = Column(Text, nullable=True)

    schedules = relationship("Schedule", back_populates="course")


class CourseTemplate(Base):
    __tablename__ = "course_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, index=True)
    content = Column(Text)  # JSON 格式训练内容
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="course_templates")
    schedules = relationship("Schedule", back_populates="template")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    student_id = Column(Integer, ForeignKey("students.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    template_id = Column(Integer, ForeignKey("course_templates.id"), nullable=True)
    date = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)
    note = Column(Text, nullable=True)
    # 独立的训练内容（JSON格式），不从属于模板
    training_content = Column(Text, nullable=True)
    # 重复相关字段
    repeat_type = Column(String, default="none")  # none, daily, weekly, monthly
    repeat_end_date = Column(Date, nullable=True)
    series_id = Column(String, nullable=True)  # 同一系列课程共享此 ID
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="schedules")
    student = relationship("Student", back_populates="schedules")
    course = relationship("Course", back_populates="schedules")
    template = relationship("CourseTemplate", back_populates="schedules", foreign_keys=[template_id])
    attendance_record = relationship("AttendanceRecord", back_populates="schedule", uselist=False)


class AttendanceRecord(Base):
    """上课记录"""
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"))
    student_id = Column(Integer, ForeignKey("students.id"))
    user_id = Column(Integer, ForeignKey("users.id"))  # 上课教练
    date = Column(Date)
    status = Column(String, default="completed")  # completed, absent, cancelled
    student_status = Column(String, nullable=True)  # 学员状态：良好/疲劳/不适
    coach_note = Column(Text, nullable=True)  # 教练备注
    created_at = Column(DateTime, default=datetime.utcnow)

    schedule = relationship("Schedule", back_populates="attendance_record")
    student = relationship("Student", back_populates="attendance_records")
    user = relationship("User")
