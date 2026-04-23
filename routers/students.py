from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas
from auth import get_current_user
from authorization import can_modify_student

router = APIRouter(prefix="/api/students", tags=["学员管理"])


class CreditAdjustRequest(BaseModel):
    hours: int  # 正数增加，负数减少


@router.get("", response_model=List[schemas.StudentResponse])
def list_students(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=500, description="返回的记录数"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 所有教练都可以查看所有学员
    return db.query(models.Student).offset(skip).limit(limit).all()


@router.post("", response_model=schemas.StudentResponse)
def create_student(student_data: schemas.StudentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_student = models.Student(**student_data.model_dump(), user_id=current_user.id)
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


@router.get("/{student_id}", response_model=schemas.StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学员不存在")
    return student


@router.put("/{student_id}", response_model=schemas.StudentResponse)
def update_student(student_id: int, student_data: schemas.StudentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学员不存在")

    if not can_modify_student(student, current_user):
        raise HTTPException(status_code=403, detail="无权修改此学员")

    for key, value in student_data.model_dump().items():
        setattr(student, key, value)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学员不存在")

    if not can_modify_student(student, current_user):
        raise HTTPException(status_code=403, detail="无权删除此学员")

    db.delete(student)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{student_id}/adjust-credits", response_model=schemas.StudentResponse)
def adjust_credits(student_id: int, adjust_data: CreditAdjustRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """手动调整课时"""
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学员不存在")

    if not can_modify_student(student, current_user):
        raise HTTPException(status_code=403, detail="无权调整此学员课时")

    new_remaining = student.remaining_hours + adjust_data.hours
    # 允许负数课时
    student.remaining_hours = new_remaining
    if adjust_data.hours > 0:
        student.total_hours = student.total_hours + adjust_data.hours

    db.commit()
    db.refresh(student)
    return student
