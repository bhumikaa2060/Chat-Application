import os
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session

from app.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from app.database import get_db
from app.schemas import UserLogin, UserResponse
from app.utils import hash_password, verify_password
from database.models import User

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

UPLOAD_DIR = os.path.join("uploads", "profile_pics")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/register", response_model=UserResponse)
async def register(
    username: str = Form(...),
    first_name: str = Form(...),
    middle_name: str = Form(None),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    profile_image: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(User)
        .filter((User.username == username) | (User.email == email))
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=400, detail="Username or email already registered"
        )

    profile_image_filename = None
    if profile_image:
        ext = profile_image.filename.split(".")[-1]
        profile_image_filename = f"profile_{uuid.uuid4()}.{ext}"
        file_path = os.path.join(UPLOAD_DIR, profile_image_filename)
        with open(file_path, "wb") as f:
            f.write(await profile_image.read())
    hashed_pw = hash_password(password)
    db_user = User(
        username=username,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        email=email,
        password=hashed_pw,
        profile_image=profile_image_filename,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(db_user.id), "exp": expire}
    access_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return {"access token": f"bearer {access_token}"}

    # return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users", response_model=list[UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users
