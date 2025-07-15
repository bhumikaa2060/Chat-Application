from datetime import datetime

from fastapi import APIRouter, Depends, Header
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils import verify_token
from database.models import Chatroom, Message, User

router = APIRouter()


@router.get("/home")
def get_all_messages(authorization: str = Header(...), db: Session = Depends(get_db)):
    userinfo = verify_token(authorization, db)

    # 1. PERSONAL MESSAGES
    personal_msgs = (
        db.query(Message, User.first_name, User.last_name, User.username)
        .join(User, Message.receiver_id == User.id)
        .filter(
            and_(
                Message.sender_id == userinfo.id,
                or_(Message.status == "delivered", Message.status == "read"),
            )
        )
        .order_by(Message.receiver_id, Message.sent_at.desc())
        .all()
    )

    personal_grouped = {}
    for message, first_name, last_name, username in personal_msgs:
        rid = message.receiver_id
        if rid not in personal_grouped:
            personal_grouped[rid] = {
                "type": "personal",
                "receiver_id": rid,
                "receiver_full_name": f"{first_name} {last_name}",
                "username": username,
                "delivered_count": 0,
                "last_message": {
                    "message_id": message.id,
                    "content": message.content,
                    "status": message.status,
                    "timestamp": message.sent_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
                    "file_url": message.file_url,
                    "file_type": message.file_type,
                },
            }
        if message.status == "delivered":
            personal_grouped[rid]["delivered_count"] += 1

    # 2. GROUP CHAT MESSAGES
    subq = (
        db.query(Message.room_id, func.max(Message.sent_at).label("latest_sent_at"))
        .filter(Message.sender_id == userinfo.id)
        .group_by(Message.room_id)
        .subquery()
    )

    group_results = (
        db.query(Chatroom.id, Chatroom.roomname, Message.content, Message.sent_at)
        .join(Message, Chatroom.id == Message.room_id)
        .join(
            subq,
            (Message.room_id == subq.c.room_id)
            & (Message.sent_at == subq.c.latest_sent_at),
        )
        .filter(Message.sender_id == userinfo.id)
        .all()
    )

    # 3. Merge and Sort
    combined = []

    # Add personal
    combined.extend(personal_grouped.values())

    # Add group
    for id, roomname, content, sent_at in group_results:
        combined.append(
            {
                "type": "group",
                "room_id": id,
                "roomname": roomname,
                "content": content,
                "timestamp": sent_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
            }
        )

    # Unified sort by latest timestamp
    def get_timestamp(entry):
        if entry["type"] == "personal":
            return datetime.strptime(
                entry["last_message"]["timestamp"], "%Y-%m-%d %H:%M:%S.%f"
            )
        return datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S.%f")

    combined.sort(key=get_timestamp, reverse=True)

    return combined
