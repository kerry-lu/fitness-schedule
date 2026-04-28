from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas
from auth import get_current_user, is_head_coach
from authorization import can_access_coach_management

router = APIRouter(prefix="/api/courses", tags=["课程管理"])


@router.get("", response_model=List[schemas.CourseResponse])
def list_courses(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=500, description="返回的记录数"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 课程是共享资源，所有教练都能看到
    return db.query(models.Course).offset(skip).limit(limit).all()


@router.post("", response_model=schemas.CourseResponse)
def create_course(course_data: schemas.CourseCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_course = models.Course(**course_data.model_dump())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course


@router.get("/{course_id}", response_model=schemas.CourseResponse)
def get_course(course_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return course


@router.put("/{course_id}", response_model=schemas.CourseResponse)
def update_course(course_id: int, course_data: schemas.CourseCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    for key, value in course_data.model_dump().items():
        setattr(course, key, value)
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """删除课程，只有主教练才能删除"""
    if not is_head_coach(current_user):
        raise HTTPException(status_code=403, detail="只有主教练才能删除课程")

    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    db.delete(course)
    db.commit()
    return {"message": "删除成功"}
