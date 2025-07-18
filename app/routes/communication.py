import base64
import json
import os
import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.connection_manager import ConnectionManager
from app.database import SessionLocal, get_db
from app.utils import check_user_inroom, get_current_user, verify_password, verify_token
from database.models import Chatroom, Message, RoomMembers, User


def json_text(

    sender: str, message_id: int, text: str, ts: datetime | None = None
) -> dict:
    return {
        "type": "text",
        "message_id": message_id,
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "sender": sender,
        "text": text,
    }


def json_file(
    sender: str,
    message_id: int,
    url: str,
    caption: str = "",
    ts: datetime | None = None,
) -> dict:
    return {
        "type": "file",
        "message_id": message_id,
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "sender": sender,
        "file_url": url,
        "text": caption,
    }


router = APIRouter()


@router.get("/chatroom/{roomid}")
def get_chatroom_info(
    roomid: int,
    token: str = Header(...),
):
    db = SessionLocal()
    print("checking")
    user = verify_token(token, db)
    room = db.query(Chatroom).filter(Chatroom.id == roomid).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    creator = db.query(User).filter(User.id == room.created_by).first()
    return {
        "user": f"{user.first_name} {user.last_name}",
        "roomname": room.roomname,
        "creator": f"{creator.first_name} {creator.last_name}",
        "created_at": room.created_at.isoformat(),
        "image_url": room.image,
    }


html = """
<!DOCTYPE html>
<html>
    <head><title>Chat</title></head>
    <body>
        <form onsubmit="CreateConnection(event)">
            <input id="roomid" placeholder="Enter room id"/>
            <input id="token" placeholder="Enter token" />
            <input id="roompassword" placeholder="Enter room password (if private)" />
            <button>Connect</button>
        </form>
        <hr>
        <div id="room-info" style="display:none;">
            <p><strong>Logged in User:</strong> <span id="user"></span></p>
            <p><strong>Room:</strong> <span id="roomname"></span></p>
            <p><strong>Creator:</strong> <span id="creator"></span></p>
        </div>
        <form onsubmit="SendMsg(event)">
            <input id="message" placeholder="Enter Message"/>
            <input type="file" id="fileInput" />
            <button>Send Msg</button>
        </form>
        <ul id="messages"></ul>
    </body>
    <script>
        var ws = null;

        function CreateConnection(event){
            event.preventDefault();

            if (ws !== null && ws.readyState === WebSocket.OPEN) {
                alert("Already connected!");
                return;
            }

            const roomid = document.getElementById("roomid").value;
            const token = document.getElementById("token").value;
            const password = document.getElementById("roompassword").value;

            fetch(`http://localhost:8000/chatroom/${roomid}`, {
                headers: {
                    "token": token
                }
            })
            .then(response => {
                console.log("Fetching");
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                document.getElementById("user").innerText = data.user;
                document.getElementById("roomname").innerText = data.roomname;
                document.getElementById("creator").innerText = data.creator;
                document.getElementById("room-info").style.display = "block";
            })
            .catch(error => {
                console.error("Fetch failed:", error);
                alert("Failed to fetch chatroom details.");
            });


            ws = new WebSocket(`ws://localhost:8000/chat/${roomid}?token=${token}&password=${encodeURIComponent(password)}`);

            ws.onmessage = (event) => {
                const message = document.createElement("li");
                const text = event.data;

                if (text.includes("/uploads/")) {
                    const parts = text.split(" ");
                    const fileUrl = parts.find(p => p.includes("/uploads/"));
                    const ext = fileUrl.split('.').pop().toLowerCase();

                    const labelText = text.replace(fileUrl, "").trim();
                    const lines = labelText.split('\\n');
                    lines.forEach((line, index) => {
                        const p = document.createElement("p");
                        if (index === 0 && line.startsWith("Timestamp")) {
                            p.style.fontWeight = "bold";
                        }
                        p.textContent = line;
                        message.appendChild(p);
                    });

                    if (["jpg", "jpeg", "png", "gif", "webp"].includes(ext)) {
                        const img = document.createElement("img");
                        img.src = fileUrl;
                        img.style.maxWidth = "200px";
                        img.style.border = "1px solid #ccc";
                        img.style.marginTop = "5px";
                        message.appendChild(img);
                    } else if (["mp4", "webm"].includes(ext)) {
                        const video = document.createElement("video");
                        video.src = fileUrl;
                        video.controls = true;
                        video.style.maxWidth = "300px";
                        video.style.border = "1px solid #ccc";
                        video.style.marginTop = "5px";
                        message.appendChild(video);
                    } else {
                        const link = document.createElement("a");
                        link.href = encodeURI(fileUrl);
                        link.textContent = "Download file";
                        link.download = "";
                        link.target = "_blank";
                        message.appendChild(link);
                    }

                } else {
                    const lines = text.split('\\n');
                    lines.forEach((line, index) => {
                        const p = document.createElement("p");
                        if (index === 0 && line.startsWith("Timestamp")) {
                            p.style.fontWeight = "bold";
                        }
                        p.textContent = line;
                        message.appendChild(p);
                    });
                }

                document.getElementById('messages').appendChild(message);
            };


            ws.onclose = () => {
                ws = null;
                document.getElementById("messages").innerHTML = "";
                document.getElementById("room-info").style.display = "none";
            };
        }

        function SendMsg(event){
            event.preventDefault();
            const msg = document.getElementById("message").value;
            const fileInput =  document.getElementById("fileInput");
            const file = fileInput.files[0];

            if(file){
                const reader= new FileReader();
                reader.onload = () => {
                    const base64 = reader.result;
                    const payload = {
                        type: "file",
                        filename: file.name,
                        mimetype: file.type,
                        data: base64,
                        text: msg
                    };
                    ws.send(JSON.stringify(payload));
                    document.getElementById("message").value = "";
                    document.getElementById("fileInput").value = "";
                };
                reader.readAsDataURL(file);
            } else{
                ws.send(JSON.stringify({
                    type: "text",
                    text: msg
                }));
                document.getElementById("message").value = "";
                document.getElementById("fileInput").value = "";
            }
        }
    </script>
</html>
"""

UPLOAD_DIR = os.path.join("uploads", "messages")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/group")
def display_home():
    return HTMLResponse(html)


manager = ConnectionManager()


@router.websocket("/chat/{roomid}")
async def websocket_endpoint(
    websocket: WebSocket, roomid: str, db: Session = Depends(get_db)
):
    token = websocket.query_params.get("token")
    password = websocket.query_params.get("password", "")
    userinfo = verify_token(token, db)
    userid = int(userinfo.id)
    roomid = int(roomid)

    room = db.query(Chatroom).filter(Chatroom.id == roomid).first()
    if not room:
        await websocket.close(code=1008)
        return

    is_member = check_user_inroom(userid, roomid, db)
    if not is_member:
        await websocket.close(code=1008)
        return

    if room.is_private:
        if not password or not verify_password(password, room.password):
            await websocket.close(code=1008)
            return

    await manager.connect(websocket, roomid)
    await send_past_messages_to_user(websocket, roomid)
    await manager.brodcast(
        f"{userinfo.first_name} {userinfo.last_name} is online.", roomid
    )

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)

                if data["type"] == "text":
                    stored_msg = store_and_return_message(userid, roomid, data["text"])
                    await manager.brodcast(
                        f"Timestamp: {stored_msg['sent_at']}\n{stored_msg['sender']}: {stored_msg['content']}",
                        roomid,
                    )

                elif data["type"] == "file":
                    header, base64_data = data["data"].split(",", 1)
                    file_data = base64.b64decode(base64_data)
                    filename = f"{uuid.uuid4()}_{data['filename'].replace(' ', '_')}"
                    filepath = os.path.join(UPLOAD_DIR, filename)

                    with open(filepath, "wb") as f:
                        f.write(file_data)

                    file_url = f"/{UPLOAD_DIR}/{filename}"

                    stored_msg = store_and_return_message(
                        userid,
                        roomid,
                        content=data.get("text"),
                        file_url=file_url,
                        file_type=data["mimetype"],
                    )

                    await manager.brodcast(
                        json_file(
                            stored_msg["sender"],
                            stored_msg["message_id"],
                            file_url,
                            stored_msg["content"],
                            stored_msg["sent_at"],
                        ),
                        roomid,
                    )
            except json.JSONDecodeError:
                await websocket.send_text("Invalid JSON format.")
                continue  # Don't exit the loop
    except WebSocketDisconnect:
        manager.disconnect(websocket, roomid)
        # await manager.brodcast(f"{userinfo.first_name} {userinfo.last_name} is offline", roomid)


async def send_past_messages_to_user(websocket: WebSocket, roomid: int):
    db = SessionLocal()
    try:
        results = (
            db.query(
                Message.content,
                Message.id,
                Message.file_url,
                Message.file_type,
                User.first_name,
                User.last_name,
                Message.sent_at,
            )
            .join(User, Message.sender_id == User.id)
            .filter(Message.room_id == roomid)
            .order_by(Message.sent_at)
            .all()
        )

        for content, id, file_url, file_type, first_name, last_name, sent_at in results:
            payload = json_file(f"{first_name} {last_name}", id, file_url, content or "", sent_at)
            # if file_url:
            #     if content:
            #         message_text = f"Timestamp: {time}\n{first_name} {last_name} sent a file: {content} {file_url}"
            #     else:
            #         message_text = f"Timestamp: {time}\n{first_name} {last_name} sent a file: {file_url}"
            # else:
            #     message_text = f"Timestamp: {time}\n{first_name} {last_name}: {content}"
            print(payload)
            await websocket.send_text(json.dumps(payload))
    finally:
        db.close()


def store_and_return_message(
    userid: int, room_id: int, content: str, file_url: str = None, file_type: str = None
) -> dict:
    db = SessionLocal()
    try:
        print("working")
        new_message = Message(
            content=content,
            sender_id=userid,
            room_id=room_id,
            file_url=file_url,
            file_type=file_type,
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        print("data sent")

        user = db.query(User).filter(User.id == userid).first()

        return {
            "message_id": new_message.id,
            "sender": f"{user.first_name}  {user.last_name}",
            "content": new_message.content or "",
            "file_url": new_message.file_url,
            "sent_at": new_message.sent_at,
        }
    finally:
        db.close()


@router.get("/leftchat/{roomid}")
async def left_chat(
    roomid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    userid = user.id
    userinfo = db.query(User.first_name, User.last_name).filter_by(id=userid).first()

    if not userinfo:
        return {"error": "User not found"}

    membership = check_user_inroom(userid, roomid, db)
    if membership:
        full_name = f"{userinfo.first_name} {userinfo.last_name}"

        db.query(RoomMembers).filter_by(user_id=userid, room_id=roomid).delete()
        db.commit()

        await manager.brodcast(json_text(full_name, "has left the chat"), roomid)

        return {"message": "Leave message stored and broadcasted"}
    else:
        return {"message": "No user in this room"}
