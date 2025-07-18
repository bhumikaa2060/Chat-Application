from fastapi import APIRouter, Depends, Query,Request
from sqlalchemy.orm import Session

from app.database import get_db
from database.models import Chatroom, RoomMembers, User

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/users")
def search_users(query: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    return db.query(User).filter(User.username.ilike(f"{query}%")).limit(10).all()


@router.get("/rooms")
def search_rooms(query: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    return (
        db.query(Chatroom).filter(Chatroom.roomname.ilike(f"{query}%")).limit(10).all()
    )


@router.get("/users-in-room")
def search_users_in_room(
    room_id: int, query: str = Query(..., min_length=1), db: Session = Depends(get_db)
):
    return (
        db.query(User)
        .join(RoomMembers)
        .filter(RoomMembers.room_id == room_id, User.username.ilike(f"{query}%"))
        .limit(10)
        .all()
    )

# @router.get("/users/{user_id}")
# def get_single_user(user_id: int, db: Session = Depends(get_db)):
#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(404, "User not found")

#     return {
#         "id":        user.id,
#         "full_name": f"{user.first_name} {user.last_name}",
#         # "username": user.username,
#         "profile_image": user.profile_image,   # None if you don’t store one
#         "email":     user.email,
#     }


@router.get("/users/{user_id}")
def get_single_user(
    user_id: int,
    db: Session = Depends(get_db),
    request: Request = None
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # If user has a profile image, build full URL
    image_url = (
        request.url_for("uploads", path=f"profile_pics/{user.profile_image}")
        if user.profile_image else None
    )

    return {
        "id": user.id,
        "full_name": f"{user.first_name} {user.last_name}",
        "profile_image": image_url,
        "email": user.email,
    }