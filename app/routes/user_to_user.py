from fastapi import WebSocket, APIRouter, Depends, WebSocketDisconnect, Header
from app.database import get_db, SessionLocal
from sqlalchemy.orm import Session
from app.utils import verify_token, verify_user
from app.connection_manager import UserConnectionManager
from fastapi.responses import HTMLResponse
from database.models import Message, User
from sqlalchemy import or_, and_
import base64
import uuid
import json
import os
from contextlib import contextmanager

router = APIRouter()

html = """
<!DOCTYPE html>
<html>
    <head><title>User Chat</title></head>
    <body>
        <form onSubmit="CreateConnection(event)">
            <input id="receiver" placeholder="Enter id you want to send msg"/>
            <input id="token" placeholder="Enter token" />
            <button>Connect</button>
        </form>

        <hr>

        <form onSubmit="SendMsg(event)">
            <input id="message" placeholder="Enter the msg"/>
            <input type="file" id="fileInput" />
            <button>Send</button>
        </form>

        <ul id="messages"></ul>

        <script>
            var ws = null;

            function CreateConnection(event){
                event.preventDefault();
                if (ws !== null && ws.readyState === WebSocket.OPEN) {
                    alert("Already connected!");
                    return;
                }

                const receiverid = document.getElementById("receiver").value;
                const token = document.getElementById("token").value;

                ws = new WebSocket(`ws://localhost:8000/userchat/${receiverid}?token=${token}`);

                ws.onmessage = (event) => {
                    const msgList = document.getElementById("messages");
                    const li = document.createElement("li");
                    li.textContent = event.data;
                    msgList.appendChild(li);
                };
            }

            function SendMsg(event){
                event.preventDefault(); 
                const msg = document.getElementById("message").value;
                const fileInput =  document.getElementById("fileInput");
                const file = fileInput.files[0];
                status =  "sending"
                if (ws && ws.readyState === WebSocket.OPEN) {
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
                    }
                    // Optional: show your own sent message in the list
                    const msgList = document.getElementById("messages");
                    const li = document.createElement("li");
                    li.textContent = "Timestamp :"+getCurrentTimestamp() +"You: " + msg + " Status:" + status;
                    msgList.appendChild(li);
                } else {
                    alert("WebSocket not connected.");
                }
            }
            function getCurrentTimestamp() {
                const now = new Date();
                
                const year = now.getFullYear();
                const month = String(now.getMonth() + 1).padStart(2, '0'); // Months are zero-based
                const day = String(now.getDate()).padStart(2, '0');
                
                const hours = String(now.getHours()).padStart(2, '0');
                const minutes = String(now.getMinutes()).padStart(2, '0');
                const seconds = String(now.getSeconds()).padStart(2, '0');
                
                return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
            }
        </script>
    </body>
</html>
"""

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

usermanager = UserConnectionManager()

@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def build_message_dict(msg, sender_name, include_file_url_key=True, msg_type="message_history"):
    base = {
        "type": msg_type,
        "message_id": msg.id,
        "timestamp": msg.sent_at.strftime("%Y-%m-%d %H:%M:%S"),
        "sender": sender_name,
        "content": msg.content if msg.content else None,
        "status": msg.status
    }
    # Use consistent "file_url" key in message dict
    if include_file_url_key:
        base["file_url"] = msg.file_url if msg.file_url else None
    else:
        base["file_url"] = msg.file_url if msg.file_url else None
    return base

async def send_message(websocket: WebSocket, msg_dict: dict):
    await websocket.send_text(json.dumps(msg_dict))

@router.get("/")
def display():
    return HTMLResponse(html)

@router.websocket("/userchat/{receiverid}")
async def user_websocket_endpoint(websocket: WebSocket, receiverid: str, db: Session = Depends(get_db)):
    token = websocket.query_params.get("token")
    userinfo = verify_token(token, db)
    if not userinfo:
        await websocket.close(code=1008)
        return

    sender_id = int(userinfo.id)
    receiver_id = int(receiverid)

    receiver_exist = verify_user(receiver_id, db)
    if not receiver_exist:
        await websocket.close(code=1008)
        return
    
    await usermanager.connect(sender_id, receiver_id, websocket)
    await send_past_message(websocket, sender_id, receiver_id)

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)

                if data["type"] == "text":
                    stored_msg = store_and_return_msg(data["text"], sender_id, receiver_id)
                    # Notify both parties
                    await usermanager.send_msg(sender_id, receiver_id, {
                        **stored_msg,
                        "type": "status_update",
                        "status": "sent"
                    })

                    update_status("delivered", stored_msg["message_id"])

                    await websocket.send_text(json.dumps({
                        **stored_msg,
                        "type": "status_update",
                        "status": "delivered"
                    }))

                elif data["type"] == "file":
                    header, base64_data = data["data"].split(",", 1)
                    file_data = base64.b64decode(base64_data)
                    filename = f"{uuid.uuid4()}_{data['filename'].replace(' ', '_')}"
                    filepath = os.path.join(UPLOAD_DIR, filename)

                    with open(filepath, "wb") as f:
                        f.write(file_data)

                    file_url = f"/{UPLOAD_DIR}/{filename}"

                    stored_msg = store_and_return_msg(
                        content=data.get("text"),
                        sender_id=sender_id,
                        receiver_id=receiver_id,
                        file_url=file_url,
                        file_type=data["mimetype"]
                    )

                    await usermanager.send_msg(sender_id, receiver_id, {
                        **stored_msg,
                        "type": "status_update",
                        "status": "sent"
                    })

                    update_status("delivered", stored_msg["message_id"])

                    await websocket.send_text(json.dumps({
                        **stored_msg,
                        "type": "status_update",
                        "status": "delivered"
                    }))

                elif data["type"] == "read":
                    message_id = data["message_id"]
                    with get_db_session() as db:
                        msg = db.query(Message).filter(Message.id == message_id).first()
                        if msg and msg.receiver_id == sender_id:
                            update_status("read", message_id)
                            sender = db.query(User).filter(User.id == msg.sender_id).first()
                            status_msg = build_message_dict(msg, f"{sender.first_name} {sender.last_name}", include_file_url_key=True, msg_type="status_update")
                            status_msg["status"] = "read"
                            await websocket.send_text(json.dumps(status_msg))
                            # Notify sender if connected
                            await usermanager.send_msg(msg.sender_id, msg.receiver_id, status_msg)

            except json.JSONDecodeError:
                await websocket.send_text("Invalid JSON format.")
                continue
    except WebSocketDisconnect:
        await usermanager.disconnect(sender_id, receiver_id, websocket)
        print(userinfo.first_name, "disconnected")

async def send_past_message(websocket: WebSocket, sender_id: int, receiver_id: int):
    with get_db_session() as db:
        chat_history = (
            db.query(Message, User.first_name, User.last_name)
            .join(User, Message.sender_id == User.id)
            .filter(
                or_(
                    and_(Message.sender_id == sender_id, Message.receiver_id == receiver_id),
                    and_(Message.sender_id == receiver_id, Message.receiver_id == sender_id)
                )
            )
            .order_by(Message.sent_at)
            .all()
        )
        for msg, first_name, last_name in chat_history:
            sender_name = f"{first_name} {last_name}"
            msg_dict = build_message_dict(msg, sender_name)
            await send_message(websocket, msg_dict)

def store_and_return_msg(content: str, sender_id: int, receiver_id: int, file_url: str = None, file_type: str = None) -> dict:
    with get_db_session() as db:
        new_message = Message(
            content=content,
            sender_id=sender_id,
            file_url=file_url,
            file_type=file_type,
            receiver_id=receiver_id,
            status="sent"
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)

        user = db.query(User).filter(User.id == sender_id).first()
        sender_name = f"{user.first_name} {user.last_name}"
        return build_message_dict(new_message, sender_name, include_file_url_key=False)

def update_status(status: str, message_id: int):
    with get_db_session() as db:
        msg = db.query(Message).filter(Message.id == message_id).first()
        if msg:
            msg.status = status
            db.commit()
            return True
    return False

# frontend-url = `ws://localhost:8000/readstatus?messageid=${messageId}&receivertoken=${receiverToken}`;
# receivertoken mean logged in user ko token
@router.websocket("/readstatus")
async def readstatus(websocket: WebSocket, messageid: int, receivertoken: str, db: Session = Depends(get_db)):
    await websocket.accept()

    try:
        userinfo = verify_token(receivertoken, db)
        if not userinfo:
            await websocket.send_text(json.dumps({"error": "Invalid token"}))
            await websocket.close()
            return

        msg = db.query(Message).filter(Message.id == messageid).first()
        if not msg:
            await websocket.send_text(json.dumps({"error": "Message not found"}))
            await websocket.close()
            return

        if userinfo.id != msg.receiver_id:
            await websocket.send_text(json.dumps({"error": "Unauthorized"}))
            await websocket.close()
            return

        # Update status
        update_status("read", messageid)

        sender = db.query(User).filter(User.id == msg.sender_id).first()
        timestamp = msg.sent_at.strftime("%Y-%m-%d %H:%M:%S")

        await websocket.send_text(json.dumps({
            "type": "status_update",
            "message_id": messageid,
            "timestamp": timestamp,
            "sender": f"{sender.first_name} {sender.last_name}",
            "content": msg.content,
            "file_url": msg.file_url,
            "status": "read"
        }))

    except WebSocketDisconnect:
        print("WebSocket disconnected")

    except Exception as e:
        await websocket.send_text(json.dumps({"error": str(e)}))
        await websocket.close()