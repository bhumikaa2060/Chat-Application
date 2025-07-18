import os
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import JoinRoom
from app.utils import (
    check_user_inroom,
    get_current_user,
    hash_password,
    verify_password,
)
from database.models import Chatroom, RoomMembers, User

router = APIRouter()

UPLOAD_FOLDER = os.path.join("uploads", "group-image")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.post("/creategroup")
async def create_table(
    room_name: str = Form(...),
    password: str = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    is_private = bool(password)

    hashed_password = hash_password(password) if is_private else None

    filename = None
    if image:
        ext = os.path.splitext(image.filename)[1]
        filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(file_path, "wb") as f:
            f.write(await image.read())

    # Step 1: Create chatroom
    new_room = Chatroom(

        roomname=room_name,
        is_private=is_private,
        created_by=user.id,
        password=hashed_password,
        image=filename,

    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    # Step 2: Add creator as member
    room_member = RoomMembers(user_id=user.id, room_id=new_room.id, is_admin=True)
    db.add(room_member)
    db.commit()

    return {"message": "Chatroom created successfully", "room_id": new_room.id}


@router.get("/getgroups")
def get_room(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    chat_rooms = db.query(Chatroom).all()
    
    room_list = [{
        "id": room.id,
        "name": room.roomname,
        "image_url": room.image
    } for room in chat_rooms]

    return {"rooms": room_list}



@router.post("/joingroup")
def join_room(
    members: JoinRoom,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    room = db.query(Chatroom).filter(Chatroom.id == members.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chatroom not found")
    user_exist = check_user_inroom(user.id, members.room_id, db)
    if user_exist:
        return {"message": "Already in chat"}

    if room.is_private:
        if not members.password:
            raise HTTPException(
                status_code=401, detail="Password required to join this room"
            )
        if not verify_password(members.password, room.password):
            raise HTTPException(status_code=403, detail="Incorrect password")

    new_member = RoomMembers(user_id=user.id, room_id=members.room_id, is_admin=False)
    db.add(new_member)
    db.commit()
    return {"message": f"Joined chat room '{room.roomname}' successfully"}


@router.put("/group/{room_id}/edit-info")
async def update_group_info(
    room_id: int,
    room_name: str = Form(None),
    password: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    chatroom = db.query(Chatroom).filter(Chatroom.id == room_id).first()
    if not chatroom:
        raise HTTPException(status_code=404, detail="Chatroom not found")

    # Check admin rights
    member = (
        db.query(RoomMembers)
        .filter(RoomMembers.room_id == room_id, RoomMembers.user_id == user.id)
        .first()
    )
    if not member or not member.is_admin:
        raise HTTPException(
            status_code=403, detail="Only admins can update the chatroom"
        )

    updated = False
    if room_name:
        chatroom.roomname = room_name
        updated = True

    if password is not None:
        chatroom.is_private = bool(password)
        chatroom.password = hash_password(password) if password else None
        updated = True

    if updated:
        db.commit()
        return {"message": "Room updated successfully"}
    else:
        return {"message": "No changes made"}


@router.put("/group/{room_id}/edit-image")
async def update_group_image(
    room_id: int,
    remove_image: bool = Form(False),
    new_image: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    chatroom = db.query(Chatroom).filter(Chatroom.id == room_id).first()
    if not chatroom:
        raise HTTPException(status_code=404, detail="Chatroom not found")

    # Check admin rights
    member = (
        db.query(RoomMembers)
        .filter(RoomMembers.room_id == room_id, RoomMembers.user_id == user.id)
        .first()
    )
    if not member or not member.is_admin:
        raise HTTPException(
            status_code=403, detail="Only admins can update the chatroom"
        )

    # Remove old image if requested
    if remove_image and chatroom.image:
        old_path = os.path.join(UPLOAD_FOLDER, chatroom.image)
        if os.path.exists(old_path):
            os.remove(old_path)
        chatroom.image = None

    # Upload new image
    if new_image:
        print("Uploading new image:", new_image.filename)
        ext = os.path.splitext(new_image.filename)[1]
        filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            with open(file_path, "wb") as f:
                f.write(await new_image.read())
        except Exception as e:
            print("Failed to write file:", e)
            raise HTTPException(status_code=500, detail="Image upload failed")
        # Delete previous image if any
        if chatroom.image:
            old_path = os.path.join(UPLOAD_FOLDER, chatroom.image)
            if os.path.exists(old_path):
                os.remove(old_path)

        chatroom.image = filename

    db.commit()
    return {"message": "Group image updated successfully"}

    
@router.post("/leftchat/{room_id}")
def leave_group(
    room_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    member = (
        db.query(RoomMembers)
        .filter(RoomMembers.room_id == room_id, RoomMembers.user_id == user.id)
        .first()
    )

    if not member:
        raise HTTPException(status_code=404, detail="You are not a member of this room")

    db.delete(member)
    db.commit()

    return {"message": f"Left chat room {room_id} successfully"}