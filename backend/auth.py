from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
import models
from config import settings
from services.telegram_service import telegram_service
from pydantic import BaseModel

router = APIRouter()
FREE_ANALYSIS_LIMIT = 3

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: str
    password: str
    invite_code: Optional[str] = None

def verify_password(plain_password, hashed_password):
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except UnknownHashError:
        return False

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session expired or invalid. Please login again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
    except JWTError:
        # Log security event
        log = models.SecurityLog(event_type="session_expired", description="JWT validation failed or expired")
        db.add(log)
        db.commit()
        raise credentials_exception

    user = None
    if isinstance(sub, int):
        user = db.query(models.User).filter(models.User.id == sub).first()
    elif isinstance(sub, str) and sub.isdigit():
        user = db.query(models.User).filter(models.User.id == int(sub)).first()
    elif isinstance(sub, str):
        user = db.query(models.User).filter(models.User.email == sub).first()

    if user is None:
        raise credentials_exception
    return user


def _validate_invite_code(code: str, db: Session, client_ip: Optional[str] = None):
    if not code:
        raise HTTPException(status_code=400, detail="رمز الدعوة مطلوب.")

    invite = db.query(models.InviteCode).filter(models.InviteCode.code == code).first()
    if not invite:
        raise HTTPException(status_code=400, detail="رمز دعوة غير صالح")

    if invite.expiry_date and invite.expiry_date < datetime.utcnow():
        raise HTTPException(status_code=400, detail="انتهت صلاحية رمز الدعوة")

    if invite.max_uses and invite.uses_count >= invite.max_uses:
        raise HTTPException(status_code=400, detail="تم استخدام رمز الدعوة بالكامل")

    if client_ip and invite.used_ip and invite.used_ip != client_ip:
        raise HTTPException(status_code=400, detail="تم استخدام رمز الدعوة على جهاز آخر")

    if client_ip and not invite.used_ip:
        invite.used_ip = client_ip

    return invite


def _apply_invite_code_to_user(user: models.User, code: str, db: Session, client_ip: Optional[str] = None):
    invite = _validate_invite_code(code, db, client_ip=client_ip)
    if user.invite_code != code:
        user.invite_code = code
        invite.uses_count = (invite.uses_count or 0) + 1
    db.add(user)
    db.add(invite)
    db.commit()
    return invite


@router.post("/register", response_model=Token)
def register(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    trial_start = datetime.utcnow()
    trial_end = trial_start + timedelta(days=7)
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        invite_code=user.invite_code,
        ip_address=request.client.host,
        is_admin=(user.email.lower() == settings.ADMIN_EMAIL.lower() and settings.ADMIN_EMAIL),
        trial_start=trial_start,
        trial_end=trial_end,
        has_used_trial=False,
        daily_analyses_count=0
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if user.invite_code:
        _apply_invite_code_to_user(new_user, user.invite_code, db=db, client_ip=request.client.host)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    default_prefs = models.UserPreferences(
        user_id=new_user.id,
        theme='dark',
        language='ar',
        demo_mode=False,
        demo_balance=1000000.0,
        trading_mode='day',
        capital=10000.0,
        account_balance=10000.0,
        risk_percentage=1.0,
        favorite_strategies='[]',
        watchlist='[]'
    )
    db.add(default_prefs)
    db.commit()
    
    access_token = create_access_token(data={"sub": str(new_user.id), "user_id": new_user.id, "email": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post('/request-invite')
def request_invite(payload: dict, request: Request, db: Session = Depends(get_db)):
    email = (payload.get('email') or '').strip() or 'مستخدم غير مسجل'
    message = (
        f"طلب رمز دعوة جديد من: {email}\n"
        f"IP: {request.client.host}\n"
        f"الرجاء إرسال رمز الدعوة إلى هذا الدردشة الخاصة.")
    telegram_service.send_message("6380833552", message)
    return {"status": "ok", "message": "تم إرسال طلب رمز الدعوة إلى تيليجرام."}


@router.post('/validate-invite')
def validate_invite(payload: dict, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    code = (payload.get('invite_code') or '').strip()
    _apply_invite_code_to_user(current_user, code, db=db, client_ip=request.client.host)
    return {"status": "ok", "message": "تم تفعيل رمز الدعوة بنجاح. يمكنك الاستمرار في التحليل."}


class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    # If the stored hash uses an older/other scheme, re-hash with the preferred scheme
    try:
        current_scheme = pwd_context.identify(user.hashed_password)
    except Exception:
        current_scheme = None
    if current_scheme != "pbkdf2_sha256":
        try:
            user.hashed_password = get_password_hash(payload.password)
            db.add(user)
            db.commit()
        except Exception:
            db.rollback()

    if user.email.lower() == settings.ADMIN_EMAIL.lower() and settings.ADMIN_EMAIL:
        if not user.is_admin:
            user.is_admin = True
            db.add(user)
            db.commit()

    access_token = create_access_token(data={"sub": str(user.id), "user_id": user.id, "email": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.get("/trial-status")
async def get_trial_status(current_user: models.User = Depends(get_current_user)):
    now = datetime.utcnow()
    trial_active = False
    days_left = 0
    if current_user.trial_start and current_user.trial_end:
        if now < current_user.trial_end:
            trial_active = True
            days_left = (current_user.trial_end - now).days

    return {
        "trial_active": trial_active,
        "days_left": days_left,
        "daily_analyses_used": current_user.daily_analyses_count,
        "daily_limit": FREE_ANALYSIS_LIMIT,
        "has_used_trial": current_user.has_used_trial
    }
