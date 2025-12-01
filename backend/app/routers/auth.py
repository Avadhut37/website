"""Authentication endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, select

from ..core.config import settings
from ..core.security import create_access_token, hash_password, verify_password
from ..core.logging import logger
from ..core.rate_limit import limiter, RATE_LIMITS
from ..db import get_session
from ..models import User
from ..schemas import Token, UserLogin, UserRegister, UserResponse

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMITS["auth"])
def register(request: Request, payload: UserRegister, session: Session = Depends(get_session)):
    """Register a new user."""
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    hashed = hash_password(payload.password)
    user = User(email=payload.email, hashed_password=hashed)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    logger.info(f"New user registered: {user.email}")
    
    token = create_access_token(user.id)
    return Token(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/login", response_model=Token)
@limiter.limit(RATE_LIMITS["auth"])
def login(request: Request, payload: UserLogin, session: Session = Depends(get_session)):
    """Authenticate and get access token."""
    user = session.exec(select(User).where(User.email == payload.email)).first()
    
    if not user or not verify_password(payload.password, user.hashed_password):
        logger.warning(f"Failed login attempt for: {payload.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    logger.info(f"User logged in: {user.email}")
    
    token = create_access_token(user.id)
    return Token(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
