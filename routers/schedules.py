from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import date, time as time_cls
import uuid
from database import get_db
import models
import schemas
from auth import get_current_user
from authorization import can_modify_schedule, can_access_coach_management

router = APIRouter(prefix="/api/schedules", tags=["课表管理"])


def calculate_end_time(start_time: str, duration_minutes: int) -> str:
    from datetime import datetime, timedelta
    fmt = "%H:%M:%S"
    if len(start_time.split(":")) == 2:
        fmt = "%H:%M"
    t = datetime.strptime(start_time, fmt)
    end = t + timedelta(minutes=duration_minutes)
    return end.strftime(fmt)


@router.get("", response_model=List[schemas.ScheduleResponse])
def list_schedules(
    start_date: date = None,
    end_date: date = None,
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(500, ge=1, le=1000, description="返回的记录数"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 所有教练都可以查看所有课程安排
    query = db.query(models.Schedule).options(
        joinedload(models.Schedule.student),
        joinedload(models.Schedule.course),
        joinedload(models.Schedule.template),
        joinedload(models.Schedule.attendance_record)
    )

    if start_date:
        query = query.filter(models.Schedule.date >= start_date)
    if end_date:
        query = query.filter(models.Schedule.date <= end_date)

    return query.order_by(models.Schedule.date.desc(), models.Schedule.start_time.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=schemas.ScheduleResponse)
def create_schedule(schedule_data: schemas.ScheduleCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # 验证学员存在
    student = db.query(models.Student).filter(models.Student.id == schedule_data.student_id).first()
    if not student:
        raise HTTPException(status_code=400, detail="学员不存在")

    # 获取课程时长
    course = db.query(models.Course).filter(models.Course.id == schedule_data.course_id).first()
    if not course:
        raise HTTPException(status_code=400, detail="课程不存在")

    # 计算结束时间
    start_time_str = schedule_data.start_time.strftime("%H:%M")
    end_time_str = calculate_end_time(start_time_str, course.duration_minutes)

    parts = end_time_str.split(":")
    if len(parts) == 3:
        end_time = time_cls(int(parts[0]), int(parts[1]), int(parts[2]))
    else:
        end_time = time_cls(int(parts[0]), int(parts[1]))

    # 生成 series_id 如果设置了重复
    series_id = None
    if schedule_data.repeat_type and schedule_data.repeat_type != "none":
        series_id = str(uuid.uuid4())

    # 处理训练内容：如果选择了模板，复制模板内容
    training_content = schedule_data.training_content
    if not training_content and schedule_data.template_id:
        template = db.query(models.CourseTemplate).filter(models.CourseTemplate.id == schedule_data.template_id).first()
        if template:
            training_content = template.content

    db_schedule = models.Schedule(
        user_id=current_user.id,
        student_id=schedule_data.student_id,
        course_id=schedule_data.course_id,
        template_id=schedule_data.template_id,
        date=schedule_data.date,
        start_time=schedule_data.start_time,
        end_time=end_time,
        note=schedule_data.note,
        training_content=training_content,
        repeat_type=schedule_data.repeat_type or "none",
        repeat_end_date=schedule_data.repeat_end_date,
        series_id=series_id
    )
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)

    # 加载关联数据
    db_schedule = db.query(models.Schedule).options(
        joinedload(models.Schedule.student),
        joinedload(models.Schedule.course),
        joinedload(models.Schedule.template),
        joinedload(models.Schedule.attendance_record)
    ).filter(models.Schedule.id == db_schedule.id).first()

    return db_schedule


@router.get("/{schedule_id}", response_model=schemas.ScheduleResponse)
def get_schedule(schedule_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    schedule = db.query(models.Schedule).options(
        joinedload(models.Schedule.student),
        joinedload(models.Schedule.course),
        joinedload(models.Schedule.template),
        joinedload(models.Schedule.attendance_record)
    ).filter(models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="课程安排不存在")
    return schedule


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    schedule = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="课程安排不存在")

    if not can_modify_schedule(schedule, current_user):
        raise HTTPException(status_code=403, detail="无权删除此课程安排")

    db.delete(schedule)
    db.commit()
    return {"message": "删除成功"}


@router.put("/{schedule_id}", response_model=schemas.ScheduleResponse)
def update_schedule(
    schedule_id: int,
    schedule_data: schemas.ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    schedule = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="课程安排不存在")

    if not can_modify_schedule(schedule, current_user):
        raise HTTPException(status_code=403, detail="无权修改此课程安排")

    # 更新字段
    update_data = schedule_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "start_time" and value:
            # 处理字符串或 time 对象
            if isinstance(value, str):
                start_time_str = value
            else:
                start_time_str = value.strftime("%H:%M")
            # 重新计算结束时间
            course = db.query(models.Course).filter(models.Course.id == schedule.course_id).first()
            if course:
                end_time_str = calculate_end_time(start_time_str, course.duration_minutes)
                parts = end_time_str.split(":")
                setattr(schedule, "end_time", time_cls(int(parts[0]), int(parts[1])))
            # 将 start_time 转换为 time 对象
            time_parts = start_time_str.split(":")
            setattr(schedule, "start_time", time_cls(int(time_parts[0]), int(time_parts[1])))
        elif key == "template_id" and value:
            # 选择模板时，复制模板内容到 training_content
            template = db.query(models.CourseTemplate).filter(models.CourseTemplate.id == value).first()
            if template:
                setattr(schedule, "template_id", value)
                setattr(schedule, "training_content", template.content)
                continue
        elif key == "date" and value:
            # 处理字符串或 date 对象
            if isinstance(value, str):
                from datetime import datetime
                date_obj = datetime.strptime(value, "%Y-%m-%d").date()
                setattr(schedule, "date", date_obj)
            else:
                setattr(schedule, "date", value)
        elif key == "repeat_end_date" and value:
            if isinstance(value, str):
                from datetime import datetime
                date_obj = datetime.strptime(value, "%Y-%m-%d").date()
                setattr(schedule, "repeat_end_date", date_obj)
            else:
                setattr(schedule, "repeat_end_date", value)
        else:
            setattr(schedule, key, value)

    db.commit()

    # 重新加载关联数据
    schedule = db.query(models.Schedule).options(
        joinedload(models.Schedule.student),
        joinedload(models.Schedule.course),
        joinedload(models.Schedule.template),
        joinedload(models.Schedule.attendance_record)
    ).filter(models.Schedule.id == schedule_id).first()

    return schedule


@router.post("/{schedule_id}/split", response_model=schemas.ScheduleResponse)
def split_schedule(schedule_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """将课程从重复系列中分离，变为独立课程"""
    schedule = db.query(models.Schedule).options(
        joinedload(models.Schedule.student),
        joinedload(models.Schedule.course),
        joinedload(models.Schedule.template),
        joinedload(models.Schedule.attendance_record)
    ).filter(models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="课程安排不存在")

    if not can_modify_schedule(schedule, current_user):
        raise HTTPException(status_code=403, detail="无权修改此课程安排")

    # 清除 series_id 和 repeat_type，使其成为独立课程
    schedule.series_id = None
    schedule.repeat_type = "none"
    schedule.repeat_end_date = None

    db.commit()
    db.refresh(schedule)
    return schedule


@router.get("/{schedule_id}/series", response_model=List[schemas.ScheduleResponse])
def get_schedule_series(schedule_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """获取同一系列的所有课程"""
    schedule = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="课程安排不存在")

    if not schedule.series_id:
        return [schedule]

    series = db.query(models.Schedule).options(
        joinedload(models.Schedule.student),
        joinedload(models.Schedule.course),
        joinedload(models.Schedule.template),
        joinedload(models.Schedule.attendance_record)
    ).filter(
        models.Schedule.series_id == schedule.series_id
    ).order_by(models.Schedule.date, models.Schedule.start_time).all()

    return series


class ScheduleMoveRequest(BaseModel):
    date: date
    start_time: str


@router.put("/{schedule_id}/move")
def move_schedule(
    schedule_id: int,
    move_data: ScheduleMoveRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    schedule = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="课程安排不存在")

    if not can_modify_schedule(schedule, current_user):
        raise HTTPException(status_code=403, detail="无权修改此课程安排")

    # 获取课程时长重新计算结束时间
    course = db.query(models.Course).filter(models.Course.id == schedule.course_id).first()
    if not course:
        raise HTTPException(status_code=400, detail="课程不存在")

    # 计算新的结束时间
    end_time_str = calculate_end_time(move_data.start_time, course.duration_minutes)
    parts = end_time_str.split(":")
    end_time = time_cls(int(parts[0]), int(parts[1]))

    # 解析时间
    time_parts = move_data.start_time.split(":")
    start_time = time_cls(int(time_parts[0]), int(time_parts[1]))

    schedule.date = move_data.date
    schedule.start_time = start_time
    schedule.end_time = end_time

    db.commit()
    return {"message": "移动成功"}


@router.post("/{schedule_id}/complete")
def complete_schedule(
    schedule_id: int,
    deduct_credits: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """完成课程，如果学员启用了课时功能则扣减课时"""
    schedule = db.query(models.Schedule).options(
        joinedload(models.Schedule.student),
        joinedload(models.Schedule.course),
        joinedload(models.Schedule.attendance_record)
    ).filter(models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="课程安排不存在")

    if not can_modify_schedule(schedule, current_user):
        raise HTTPException(status_code=403, detail="无权操作此课程安排")

    # 如果启用课时功能且需要扣减
    if deduct_credits and schedule.student.enable_credits:
        if schedule.student.remaining_hours > 0:
            # 一节课扣减1课时，不关时长
            schedule.student.remaining_hours = schedule.student.remaining_hours - 1

    db.commit()
    return {"message": "课程已完成", "remaining_hours": schedule.student.remaining_hours if schedule.student else 0}


# 上课记录相关
@router.get("/attendance", response_model=List[schemas.AttendanceResponse])
def list_attendance(
    student_id: int = None,
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取上课记录列表"""
    query = db.query(models.AttendanceRecord)

    if student_id:
        query = query.filter(models.AttendanceRecord.student_id == student_id)
    if start_date:
        query = query.filter(models.AttendanceRecord.date >= start_date)
    if end_date:
        query = query.filter(models.AttendanceRecord.date <= end_date)

    return query.order_by(models.AttendanceRecord.date.desc()).all()


@router.post("/attendance", response_model=schemas.AttendanceResponse)
def create_attendance(
    attendance_data: schemas.AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """创建上课记录"""
    # 验证学员存在
    student = db.query(models.Student).filter(models.Student.id == attendance_data.student_id).first()
    if not student:
        raise HTTPException(status_code=400, detail="学员不存在")

    db_attendance = models.AttendanceRecord(
        user_id=current_user.id,
        schedule_id=attendance_data.schedule_id,
        student_id=attendance_data.student_id,
        date=attendance_data.date,
        status=attendance_data.status or "completed",
        student_status=attendance_data.student_status,
        coach_note=attendance_data.coach_note
    )
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    return db_attendance


@router.put("/attendance/{attendance_id}", response_model=schemas.AttendanceResponse)
def update_attendance(
    attendance_id: int,
    attendance_data: schemas.AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """更新上课记录"""
    attendance = db.query(models.AttendanceRecord).filter(models.AttendanceRecord.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="上课记录不存在")

    # 只有记录创建者或主教练可以修改
    if attendance.user_id != current_user.id and not is_head_coach(current_user):
        raise HTTPException(status_code=403, detail="无权修改此上课记录")

    update_data = attendance_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(attendance, key, value)

    db.commit()
    db.refresh(attendance)
    return attendance


@router.get("/attendance/{attendance_id}", response_model=schemas.AttendanceResponse)
def get_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取单条上课记录"""
    attendance = db.query(models.AttendanceRecord).filter(models.AttendanceRecord.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="上课记录不存在")
    return attendance
