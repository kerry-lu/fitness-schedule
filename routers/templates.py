from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas
from auth import get_current_user, is_head_coach

router = APIRouter(prefix="/api/templates", tags=["课程模板"])


def can_modify_template(template: models.CourseTemplate, current_user: models.User) -> bool:
    """检查是否可以修改模板：创建者或主教练"""
    return template.user_id == current_user.id or is_head_coach(current_user)


@router.get("", response_model=List[schemas.TemplateResponse])
def list_templates(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # 所有教练都可以查看所有模板
    return db.query(models.CourseTemplate).all()


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
