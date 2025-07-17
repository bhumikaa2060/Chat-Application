from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from database.models import Chatroom, RoomMembers, User

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/users")
def search_users(query: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    # Create full name expression
    full_name = func.concat_ws(" ", User.first_name, User.middle_name, User.last_name)

    return db.query(User).filter(full_name.ilike(f"%{query}%")).limit(10).all()


@router.get("/rooms")
def search_rooms(query: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    return (
        db.query(Chatroom).filter(Chatroom.roomname.ilike(f"{query}%")).limit(10).all()
    )


@router.get("/users-in-room")
def search_users_in_room(
    room_id: int, query: str = Query(..., min_length=1), db: Session = Depends(get_db)
):
    full_name = func.concat_ws(" ", User.first_name, User.middle_name, User.last_name)

    return (
        db.query(User)
        .join(RoomMembers)
        .filter(RoomMembers.room_id == room_id)
        .filter(full_name.ilike(f"%{query}%"))
        .limit(10)
        .all()
    )
