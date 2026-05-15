from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import auth

router = APIRouter()


@router.get('/history/analyses')
async def list_analyses(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.is_admin:
        records = db.query(models.Analysis).order_by(models.Analysis.created_at.desc()).all()
    else:
        records = db.query(models.Analysis).filter(models.Analysis.user_id == current_user.id, models.Analysis.is_deleted == False).order_by(models.Analysis.created_at.desc()).all()
    return [
        {
            'id': r.id,
            'market': r.market,
            'description': r.description,
            'is_deleted': bool(getattr(r, 'is_deleted', False)),
            'created_at': r.created_at
        }
        for r in records
    ]


@router.get('/history/activities/{user_id}')
async def get_activities(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Admin can view others; users can view their own
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(status_code=403, detail='Access denied')
    acts = db.query(models.UserActivityMaster).filter(models.UserActivityMaster.user_id == user_id).order_by(models.UserActivityMaster.timestamp.desc()).limit(500).all()
    return [{
        'action': a.action,
        'ip': a.ip,
        'device': a.device,
        'location': a.location,
        'is_vpn': a.is_vpn,
        'timestamp': a.timestamp
    } for a in acts]
