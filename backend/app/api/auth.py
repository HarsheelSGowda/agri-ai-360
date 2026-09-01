from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.database.session import get_db
from app.models.user import Farmer, User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_user_out(user: User, farmer: Farmer) -> UserOut:
    return UserOut(id=user.id, name=farmer.name, email=user.email, location=farmer.location, preferred_language=farmer.preferred_language)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()

    farmer = Farmer(
        user_id=user.id,
        name=payload.name,
        location=payload.location,
        preferred_language=payload.preferred_language,
    )
    db.add(farmer)
    db.commit()
    db.refresh(user)
    db.refresh(farmer)

    token = create_access_token(subject=user.email)
    return AuthResponse(access_token=token, user=_to_user_out(user, farmer))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")

    farmer = db.query(Farmer).filter(Farmer.user_id == user.id).first()
    if not farmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer profile missing for this account.")

    token = create_access_token(subject=user.email)
    return AuthResponse(access_token=token, user=_to_user_out(user, farmer))
