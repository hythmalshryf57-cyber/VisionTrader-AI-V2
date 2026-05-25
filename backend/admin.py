from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models
from auth import get_current_user
import threading

router = APIRouter()

from config import settings
from services.telegram_bot import TelegramBot
from services.crypto_vault import vault as crypto_vault
import secrets
from datetime import datetime, timedelta

telegram = TelegramBot(token=getattr(settings, 'TELEGRAM_BOT_TOKEN', None))

@router.get("/soc-dashboard")
async def soc_dashboard(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # محاولات دخول فاشلة (placeholder)
    failed_attempts = []  # TODO: implement from logs

    # مستخدمين مشبوهين
    suspicious_users = db.query(models.User).filter(models.User.is_frozen == True).all()

    # استهلاك API (placeholder)
    api_usage = {"gemini": 0, "deepseek": 0}  # TODO: implement counters

    # حالة السيرفر
    import psutil
    server_status = {
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent
    }

    # تنبيهات حية (placeholder)
    alerts = []  # TODO: implement real-time alerts

    return {
        "threat_map": failed_attempts,
        "suspicious_users": [
            {"id": u.id, "email": u.email, "reason": "frozen"}
            for u in suspicious_users
        ],
        "api_usage": api_usage,
        "server_status": server_status,
        "live_alerts": alerts
    }


@router.get("/user-dossier/{user_id}")
async def user_dossier(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    devices = db.query(models.UserDevice).filter(models.UserDevice.user_id == user_id).all()
    activities = db.query(models.UserActivityMaster).filter(models.UserActivityMaster.user_id == user_id).order_by(models.UserActivityMaster.timestamp.desc()).limit(200).all()
    trades = db.query(models.ShadowTrade).filter(models.ShadowTrade.user_id == user_id).order_by(models.ShadowTrade.created_at.desc()).limit(200).all()

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "is_frozen": getattr(user, 'is_frozen', False),
            "registered_at": user.registered_at
        },
        "devices": [{"device_id": d.device_id, "device_name": d.device_name, "is_trusted": d.is_trusted, "first_seen": d.first_seen} for d in devices],
        "activities": [{"action": a.action, "ip": a.ip, "device": a.device, "location": a.location, "is_vpn": a.is_vpn, "timestamp": a.timestamp} for a in activities],
        "trades": [{"market": t.market, "entry_price": t.entry_price, "exit_price": t.exit_price, "status": t.status, "pnl": t.pnl, "created_at": t.created_at} for t in trades]
    }

@router.get("/users")
async def list_users(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    users = db.query(models.User).order_by(models.User.registered_at.desc()).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "invite_code": u.invite_code,
            "ip_address": u.ip_address,
            "is_active": u.is_active,
            "is_admin": u.is_admin,
            "registered_at": u.registered_at.isoformat() if u.registered_at else None
        }
        for u in users
    ]


@router.get("/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "email": user.email,
        "invite_code": user.invite_code,
        "ip_address": user.ip_address,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "registered_at": user.registered_at
    }

@router.put("/users/{user_id}/toggle")
async def toggle_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = not user.is_active
    db.commit()
    return {"status": "updated"}

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Keep user record but mark inactive (soft stop)
    user.is_active = False
    db.commit()
    return {"status": "disabled"}


@router.post("/users/{user_id}/force-logout")
async def force_logout(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.force_logout_at = datetime.utcnow()
    slog = models.SecurityLog(user_id=user_id, event_type='force_logout', ip_address=None, description='Admin forced logout')
    db.add(slog)
    db.commit()
    # notify
    try:
        telegram.alert_vpn_attempt(user_id, 'N/A', 'admin_action', 'force_logout')
    except Exception:
        pass
    return {"status": "force_logout_set"}


@router.post("/users/{user_id}/freeze")
async def freeze_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_frozen = True
    slog = models.SecurityLog(user_id=user_id, event_type='freeze_account', ip_address=None, description='Account frozen by admin')
    db.add(slog)
    db.commit()
    return {"status": "frozen"}


@router.post("/users/{user_id}/device-lock")
async def device_lock(user_id: int, payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    device_id = payload.get('device_id')
    if not device_id:
        raise HTTPException(status_code=400, detail='device_id required')
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    dev = db.query(models.UserDevice).filter(models.UserDevice.user_id == user_id, models.UserDevice.device_id == device_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found for user")
    user.locked_device_id = dev.id
    db.commit()
    return {"status": "device_locked", "device_id": device_id}


@router.post("/users/{user_id}/kill-switch")
async def kill_switch(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    user.force_logout_at = datetime.utcnow()
    slog = models.SecurityLog(user_id=user_id, event_type='kill_switch', ip_address=None, description='Admin kill switch triggered')
    db.add(slog)
    db.commit()
    try:
        threading.Thread(target=telegram.alert_risk_limit, args=(user_id, 'Kill switch activated by admin'), daemon=True).start()
    except Exception:
        pass
    return {"status": "killed"}


@router.post("/users/{user_id}/shadow-monitor")
async def shadow_monitor(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Start a shadow-monitor session token for the user (admin only).

    Note: Actual streaming endpoint is out of scope; this creates a token and logs the action.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    token = secrets.token_urlsafe(16)
    slog = models.SecurityLog(user_id=user_id, event_type='shadow_monitor_start', ip_address=None, description=f'Admin {current_user.id} started shadow monitor token:{token}')
    db.add(slog)
    db.commit()
    return {"status": "started", "stream_token": token, "note": "Use token to initiate stream; stream implementation is separate."}


def _generate_smart_invite_code(db: Session) -> str:
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    while True:
        code = '-'.join(''.join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3))
        if not db.query(models.InviteCode).filter(models.InviteCode.code == code).first():
            return code


@router.get("/invite-codes")
async def list_invite_codes(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    invites = db.query(models.InviteCode).order_by(models.InviteCode.created_at.desc()).all()
    return [
        {
            "code": invite.code,
            "created_at": invite.created_at.isoformat() if invite.created_at else None,
            "expires_at": invite.expiry_date.isoformat() if invite.expiry_date else None,
            "max_uses": invite.max_uses,
            "uses_count": invite.uses_count,
            "used_ip": invite.used_ip or 'N/A',
        }
        for invite in invites
    ]


@router.post("/generate-code-smart")
async def generate_code_smart(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    expiry_days = int(payload.get('expiry_days', 30))
    max_uses = int(payload.get('max_uses', 1))
    code = _generate_smart_invite_code(db)
    expiry = datetime.utcnow() + timedelta(days=expiry_days)
    invite = models.InviteCode(code=code, created_by_admin=True, expiry_date=expiry, max_uses=max_uses)
    db.add(invite)
    db.commit()
    return {
        "code": code,
        "created_at": invite.created_at.isoformat() if invite.created_at else None,
        "expires_at": expiry.isoformat(),
        "max_uses": max_uses,
        "uses_count": invite.uses_count,
    }


@router.post("/decrypt-user-field")
async def decrypt_user_field(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    user_id = payload.get('user_id')
    field = payload.get('field')
    if not user_id or not field:
        raise HTTPException(status_code=400, detail='user_id and field required')
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    value = getattr(user, field, None)
    if not value:
        return {"value": None}
    # Try fernet vault first if value looks encrypted
    try:
        dec = crypto_vault.decrypt_admin(value, current_user)
        return {"value": dec}
    except Exception:
        # fallback: return raw
        return {"value": value}

@router.get("/stats")
async def get_stats(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    total_users = db.query(models.User).count()
    active_users = db.query(models.User).filter(models.User.is_active == True).count()
    inactive_users = total_users - active_users
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users
    }

@router.get("/security-logs")
async def get_security_logs(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    logs = db.query(models.SecurityLog).order_by(models.SecurityLog.timestamp.desc()).limit(100).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "event_type": log.event_type,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp
        }
        for log in logs
    ]