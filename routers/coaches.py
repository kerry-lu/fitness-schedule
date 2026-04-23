from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas
from auth import get_current_user, is_head_coach

router = APIRouter(prefix="/api/coaches", tags=["教练管理"])


class CoachUpdateRole(BaseModel):
    role: str


@router.get("", response_model=List[schemas.UserResponse])
def list_coaches(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """获取所有教练列表，只有主教练可访问"""
    if not is_head_coach(current_user):
        raise HTTPException(status_code=403, detail="只有主教练可访问此功能")
    return db.query(models.User).all()


@router.get("/{coach_id}", response_model=schemas.UserResponse)
def get_coach(coach_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """获取指定教练信息，只有主教练可访问"""
    if not is_head_coach(current_user):
        raise HTTPException(status_code=403, detail="只有主教练可访问此功能")
    coach = db.query(models.User).filter(models.User.id == coach_id).first()
    if not coach:
        raise HTTPException(status_code=404, detail="教练不存在")
    return coach


@router.put("/{coach_id}/role", response_model=schemas.UserResponse)
def update_coach_role(coach_id: int, update_data: CoachUpdateRole, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """更新教练角色，只有主教练可访问"""
    if not is_head_coach(current_user):
        raise HTTPException(status_code=403, detail="只有主教练可访问此功能")

    coach = db.query(models.User).filter(models.User.id == coach_id).first()
    if not coach:
        raise HTTPException(status_code=404, detail="教练不存在")

    if update_data.role not in ["coach", "head_coach"]:
        raise HTTPException(status_code=400, detail="角色必须是 coach 或 head_coach")

    # 不能修改自己的角色
    if coach_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")

    coach.role = update_data.role
    db.commit()
    db.refresh(coach)
    return coach
