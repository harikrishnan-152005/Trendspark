import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.database import SessionLocal, UserDB
from app.auth.utils import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------
# REGISTER
# -----------------------------
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    
@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):

    existing_user = db.query(UserDB).filter(UserDB.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = UserDB(
        id=str(uuid.uuid4()),
        username=data.username.strip().lower(),  # ✅ FIX
        email=data.email,
        hashed_password=hash_password(data.password)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User created successfully"}


# -----------------------------
# LOGIN
# -----------------------------
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):
    username = form_data.username.strip().lower()

    user = db.query(UserDB).filter(
        UserDB.username == username
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Wrong password")

    token = create_access_token({"sub": user.username})

    return {
        "access_token": token,
        "token_type": "bearer"
    }

# -----------------------------
# GET CURRENT USER
# -----------------------------
def get_current_user(token: str = Depends(oauth2_scheme),
                     db: Session = Depends(get_db)):

    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    username = payload.get("sub")
    user = db.query(UserDB).filter(UserDB.username == username).first()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
