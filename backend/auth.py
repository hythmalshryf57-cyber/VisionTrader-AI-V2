from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
import models
from config import settings
from pydantic import BaseModel

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: str
    password: str
    invite_code: Optional[str] = None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

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
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        # Log security event
        log = models.SecurityLog(event_type="session_expired", description="JWT validation failed or expired")
        db.add(log)
        db.commit()
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=Token)
def register(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check invite code
    if user.invite_code:
        invite = db.query(models.InviteCode).filter(models.InviteCode.code == user.invite_code).first()
        if not invite:
            raise HTTPException(status_code=400, detail="Invalid invite code")
        
        client_ip = request.client.host
        if invite.used_ip and invite.used_ip != client_ip:
            raise HTTPException(status_code=400, detail="This invite code has been used on another device")
        
        if not invite.used_ip:
            invite.used_ip = client_ip
            db.commit()
    
    hashed_password = get_password_hash(user.password)
    trial_start = datetime.utcnow()
    trial_end = trial_start + timedelta(days=7)
    new_user = models.User(
        email=user.email, 
        hashed_password=hashed_password, 
        invite_code=user.invite_code,
        ip_address=request.client.host,
        is_admin=(user.email == "admin@visiontrader.ai"),  # Assuming admin email
        trial_start=trial_start,
        trial_end=trial_end,
        has_used_trial=True
    )
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
    
    access_token = create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email})
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
        "daily_limit": 10,
        "has_used_trial": current_user.has_used_trial
    }
