from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas
from auth import get_current_user
from authorization import can_modify_template

router = APIRouter(prefix="/api/templates", tags=["课程模板"])


@router.get("", response_model=List[schemas.TemplateResponse])
def list_templates(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=500, description="返回的记录数"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 所有教练都可以查看所有模板
    return db.query(models.CourseTemplate).offset(skip).limit(limit).all()


@router.post("", response_model=schemas.TemplateResponse)
def create_template(template_data: schemas.TemplateCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_template = models.CourseTemplate(
        user_id=current_user.id,
        name=template_data.name,
        content=template_data.content
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.get("/{template_id}", response_model=schemas.TemplateResponse)
def get_template(template_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    template = db.query(models.CourseTemplate).filter(
        models.CourseTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


@router.put("/{template_id}", response_model=schemas.TemplateResponse)
def update_template(template_id: int, template_data: schemas.TemplateCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    template = db.query(models.CourseTemplate).filter(
        models.CourseTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    if not can_modify_template(template, current_user):
        raise HTTPException(status_code=403, detail="无权修改此模板")

    template.name = template_data.name
    template.content = template_data.content
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    template = db.query(models.CourseTemplate).filter(
        models.CourseTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    if not can_modify_template(template, current_user):
        raise HTTPException(status_code=403, detail="无权删除此模板")

    db.delete(template)
    db.commit()
    return {"message": "删除成功"}
