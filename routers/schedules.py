from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import date, time as time_cls
import uuid
from database import get_db
import models
import schemas
from auth import get_current_user, is_head_coach
from authorization import can_modify_schedule, can_access_coach_management

router = APIRouter(prefix="/api/schedules", tags=["课表管理"])

# 每节课扣减的课时数
CREDIT_DEDUCTION_PER_SESSION = 1


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
    # 只显示当前教练自己的课程安排
    query = db.query(models.Schedule).options(
        joinedload(models.Schedule.student),
        joinedload(models.Schedule.course),
        joinedload(models.Schedule.template),
        joinedload(models.Schedule.attendance_record),
        joinedload(models.Schedule.user)
    ).filter(models.Schedule.user_id == current_user.id)

    if start_date:
        query = query.filter(models.Schedule.date >= start_date)
    if end_date:
        query = query.filter(models.Schedule.date <= end_date)

    schedules = query.order_by(models.Schedule.date.desc(), models.Schedule.start_time.desc()).offset(skip).limit(limit).all()

    # 转换格式，将 user 映射到 coach
    result = []
    for s in schedules:
        result.append({
            "id": s.id,
            "user_id": s.user_id,
            "coach_id": s.user_id,
            "student_id": s.student_id,
            "course_id": s.course_id,
            "date": s.date,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "note": s.note,
            "template_id": s.template_id,
            "training_content": s.training_content,
            "repeat_type": s.repeat_type,
            "repeat_end_date": s.repeat_end_date,
            "repeat_days": s.repeat_days,
            "series_id": s.series_id,
            "created_at": s.created_at,
            "student": s.student,
            "course": s.course,
            "template": s.template,
            "attendance_record": s.attendance_record,
            "coach": s.user,
        })
    return result


def generate_repeat_dates(start_date: date, repeat_type: str, repeat_end_date: date, repeat_days: list = None) -> list:
    """根据重复类型生成所有重复日期

    Args:
        start_date: 起始日期
        repeat_type: 重复类型 (daily, weekly, monthly)
        repeat_end_date: 重复结束日期
        repeat_days: 每周重复的周几列表，如 [2, 4] 表示周二和周四
    """
    from datetime import timedelta
    dates = [start_date]
    current_date = start_date

    if not repeat_end_date:
        return dates

    while True:
        if repeat_type == "daily":
            current_date = current_date + timedelta(days=1)
        elif repeat_type == "weekly":
            if repeat_days:
                # 按指定周几重复
                current_date = current_date + timedelta(days=1)
                while current_date.weekday() + 1 not in repeat_days and current_date <= repeat_end_date:
                    current_date = current_date + timedelta(days=1)
            else:
                current_date = current_date + timedelta(weeks=1)
        elif repeat_type == "monthly":
            # 每月同一天
            month = current_date.month + 1
            year = current_date.year
            if month > 12:
                month = 1
                year += 1
            # 处理月末情况（如 31 号）
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            day = min(current_date.day, last_day)
            current_date = date(year, month, day)
        else:
            break

        if current_date > repeat_end_date:
            break
        dates.append(current_date)

    return dates


def check_time_conflict(db: Session, student_id: int, schedule_date: date, start_time: time_cls, end_time: time_cls, coach_id: int = None, exclude_id: int = None) -> bool:
    """检查单个日期是否存在时间冲突"""
    query = db.query(models.Schedule).filter(
        models.Schedule.student_id == student_id,
        models.Schedule.date == schedule_date,
        # 时间重叠检测：(existing_start < new_end) AND (existing_end > new_start)
        models.Schedule.start_time < end_time,
        models.Schedule.end_time > start_time
    )

    if coach_id is not None:
        query = query.filter(models.Schedule.user_id == coach_id)

    if exclude_id:
        query = query.filter(models.Schedule.id != exclude_id)

    conflicting = query.first()
    return conflicting is not None


def check_conflicts_for_dates(db: Session, student_id: int, dates: list, start_time: time_cls, end_time: time_cls, coach_id: int, exclude_id: int = None) -> list:
    """批量检查多个日期的冲突，一次查询完成"""
    if not dates:
        return []

    # 查询所有在日期范围内且时间重叠的课程
    query = db.query(models.Schedule).filter(
        models.Schedule.student_id == student_id,
        models.Schedule.date.in_(dates),
        models.Schedule.start_time < end_time,
        models.Schedule.end_time > start_time
    )

    if coach_id is not None:
        query = query.filter(models.Schedule.user_id == coach_id)

    if exclude_id:
        query = query.filter(models.Schedule.id != exclude_id)

    conflicting = query.all()
    # 返回冲突的日期列表
    return [str(s.date) for s in conflicting]


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

    # 处理训练内容：如果选择了模板，复制模板内容
    training_content = schedule_data.training_content
    if not training_content and schedule_data.template_id:
        template = db.query(models.CourseTemplate).filter(models.CourseTemplate.id == schedule_data.template_id).first()
        if template:
            training_content = template.content

    # 处理重复课程
    repeat_type = schedule_data.repeat_type or "none"
    # 解析 repeat_days JSON 字符串为列表
    import json
    repeat_days_list = None
    if schedule_data.repeat_days:
        try:
            repeat_days_list = json.loads(schedule_data.repeat_days)
        except json.JSONDecodeError:
            repeat_days_list = None

    if repeat_type == "none" or not schedule_data.repeat_end_date:
        # 不重复，只创建一条课程，先检查冲突
        # 使用当前用户ID检查冲突，避免其他教练的课程影响本教练的预约时段
        if check_time_conflict(db, schedule_data.student_id, schedule_data.date, schedule_data.start_time, end_time, coach_id=current_user.id):
            raise HTTPException(status_code=400, detail="该时间段与已有课程冲突")

        series_id = None
        # 如果指定了 coach_id 则使用，否则使用当前用户
        coach_id = schedule_data.coach_id if schedule_data.coach_id else current_user.id
        db_schedule = models.Schedule(
            user_id=coach_id,
            student_id=schedule_data.student_id,
            course_id=schedule_data.course_id,
            template_id=schedule_data.template_id,
            date=schedule_data.date,
            start_time=schedule_data.start_time,
            end_time=end_time,
            note=schedule_data.note,
            training_content=training_content,
            repeat_type=repeat_type,
            repeat_end_date=None,
            repeat_days=schedule_data.repeat_days,
            series_id=None
        )
        db.add(db_schedule)
        db.commit()
        db.refresh(db_schedule)
    else:
        # 重复课程，生成 series_id 并创建所有重复实例
        # 如果指定了 coach_id 则使用，否则使用当前用户
        coach_id = schedule_data.coach_id if schedule_data.coach_id else current_user.id

        series_id = str(uuid.uuid4())
        repeat_dates = generate_repeat_dates(
            schedule_data.date,
            repeat_type,
            schedule_data.repeat_end_date,
            repeat_days_list
        )

        # 批量检查所有日期冲突（一次查询完成）
        conflict_dates = check_conflicts_for_dates(
            db, schedule_data.student_id, repeat_dates,
            schedule_data.start_time, end_time, coach_id
        )

        if conflict_dates:
            raise HTTPException(status_code=400, detail=f"以下日期存在时间冲突: {', '.join(conflict_dates)}")

        first_schedule = None
        for idx, repeat_date in enumerate(repeat_dates):
            db_schedule = models.Schedule(
                user_id=coach_id,
                student_id=schedule_data.student_id,
                course_id=schedule_data.course_id,
                template_id=schedule_data.template_id,
                date=repeat_date,
                start_time=schedule_data.start_time,
                end_time=end_time,
                note=schedule_data.note,
                training_content=training_content,
                repeat_type=repeat_type,
                repeat_end_date=schedule_data.repeat_end_date,
                repeat_days=schedule_data.repeat_days,
                series_id=series_id
            )
            db.add(db_schedule)
            if idx == 0:
                first_schedule = db_schedule

        db.commit()
        db.refresh(first_schedule)
        db_schedule = first_schedule

    return db_schedule


@router.get("/{schedule_id}", response_model=schemas.ScheduleResponse)
def get_schedule(schedule_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    schedule = db.query(models.Schedule).options(
        joinedload(models.Schedule.student),
        joinedload(models.Schedule.course),
        joinedload(models.Schedule.template),
        joinedload(models.Schedule.attendance_record),
        joinedload(models.Schedule.user)
    ).filter(models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="课程安排不存在")

    # 手动构建响应数据，将 user 映射到 coach
    from schemas import ScheduleResponse
    response_data = {
        "id": schedule.id,
        "user_id": schedule.user_id,
        "coach_id": schedule.user_id,
        "student_id": schedule.student_id,
        "course_id": schedule.course_id,
        "date": schedule.date,
        "start_time": schedule.start_time,
        "end_time": schedule.end_time,
        "note": schedule.note,
        "template_id": schedule.template_id,
        "training_content": schedule.training_content,
        "repeat_type": schedule.repeat_type,
        "repeat_end_date": schedule.repeat_end_date,
        "repeat_days": schedule.repeat_days,
        "series_id": schedule.series_id,
        "created_at": schedule.created_at,
        "student": schedule.student,
        "course": schedule.course,
        "template": schedule.template,
        "attendance_record": schedule.attendance_record,
        "coach": schedule.user,  # user 关系映射到 coach 字段
    }
    return response_data


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

    # 检查冲突 - 如果更新了 date, start_time 或 course_id
    new_date = update_data.get("date", schedule.date)
    new_start_time = update_data.get("start_time", schedule.start_time)
    new_course_id = update_data.get("course_id", schedule.course_id)

    if "date" in update_data or "start_time" in update_data or "course_id" in update_data:
        # 获取课程时长
        if new_course_id != schedule.course_id:
            course = db.query(models.Course).filter(models.Course.id == new_course_id).first()
        else:
            course = db.query(models.Course).filter(models.Course.id == schedule.course_id).first()

        if course:
            # 计算新的结束时间
            if isinstance(new_start_time, str):
                start_time_str = new_start_time
            else:
                start_time_str = new_start_time.strftime("%H:%M")
            end_time_str = calculate_end_time(start_time_str, course.duration_minutes)
            parts = end_time_str.split(":")
            new_end_time = time_cls(int(parts[0]), int(parts[1]))

            if check_time_conflict(db, schedule.student_id, new_date, new_start_time, new_end_time, coach_id=schedule.user_id, exclude_id=schedule_id):
                raise HTTPException(status_code=400, detail="该时间段与已有课程冲突")

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
    schedule.repeat_days = None

    db.commit()
    db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}/series")
def delete_schedule_series(schedule_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """删除整个重复系列的所有课程"""
    schedule = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="课程安排不存在")

    if not can_modify_schedule(schedule, current_user):
        raise HTTPException(status_code=403, detail="无权删除此课程安排")

    if not schedule.series_id:
        raise HTTPException(status_code=400, detail="该课程不是重复系列")

    # 删除整个系列的所有课程
    deleted_count = db.query(models.Schedule).filter(
        models.Schedule.series_id == schedule.series_id
    ).delete()
    db.commit()

    return {"message": f"已删除系列中 {deleted_count} 节课程"}


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

    # 如果启用课时功能且需要扣减，使用行锁防止竞态条件
    if deduct_credits and schedule.student.enable_credits:
        # 使用 with_for_update() 锁定学生行，防止并发扣减
        student = db.query(models.Student).filter(
            models.Student.id == schedule.student_id
        ).with_for_update().first()

        if student and student.remaining_hours > 0:
            # 按课程时长扣减课时：30分钟=0.5课时，60分钟=1课时，以此类推
            credits_to_deduct = schedule.course.duration_minutes / 60.0
            student.remaining_hours = max(0, student.remaining_hours - credits_to_deduct)

    db.commit()
    return {"message": "课程已完成", "remaining_hours": int(schedule.student.remaining_hours) if schedule.student else 0}


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
