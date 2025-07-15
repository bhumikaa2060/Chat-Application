import os
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.utils import get_current_user, hash_password, verify_password
from database import models

UPLOAD_PROFILE_DIR = os.path.join("uploads", "profile_pics")
os.makedirs(UPLOAD_PROFILE_DIR, exist_ok=True)

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/", response_model=schemas.UserOut)
def get_profile(
    request: Request, current_user: models.User = Depends(get_current_user)
):
    if current_user.profile_image:
        current_user.profile_image = (
            str(request.base_url) + "profile_images/" + current_user.profile_image
        )
    return current_user


@router.put("/update", response_model=schemas.UserOut)
async def update_profile(
    request: Request,
    first_name: str = Form(None),
    middle_name: str = Form(None),
    last_name: str = Form(None),
    email: str = Form(None),
    profile_image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if first_name is not None:
        current_user.first_name = first_name
    if middle_name is not None:
        current_user.middle_name = middle_name
    if last_name is not None:
        current_user.last_name = last_name
    if email is not None:
        current_user.email = email

    if profile_image:
        if current_user.profile_image:
            old_path = os.path.join("uploads", current_user.profile_image)
            if os.path.exists(old_path):
                os.remove(old_path)

        ext = profile_image.filename.split(".")[-1]
        new_filename = f"profile_{uuid.uuid4()}.{ext}"
        file_path = os.path.join(UPLOAD_PROFILE_DIR, new_filename)
        with open(file_path, "wb") as f:
            f.write(await profile_image.read())

        current_user.profile_image = new_filename
    db.commit()
    db.refresh(current_user)
    if current_user.profile_image:
        current_user.profile_image = (
            str(request.base_url) + "profile_images/" + current_user.profile_image
        )

    return current_user


@router.put("/change-password")
def change_password(
    payload: schemas.ChangePassword,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not verify_password(payload.old_password, current_user.password):
        raise HTTPException(status_code=400, detail="old password is incorrect")
    current_user.password = hash_password(payload.new_password)
    db.commit()
    return {"detail": "Password updated successfully"}


@router.delete("/image", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile_image(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    if not current_user.profile_image:
        raise HTTPException(status_code=404, detail="No profile image found")

    file_path = os.path.join("uploads", current_user.profile_image)
    if os.path.exists(file_path):
        os.remove(file_path)

    current_user.profile_image = None
    db.commit()
    return {"detail": "Profile image deleted"}
