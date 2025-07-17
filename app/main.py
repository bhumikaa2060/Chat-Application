from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine

from app.routes import auth, chats, communication, home, profile, search, user_to_user

from database.models import Base
import os

Base.metadata.create_all(bind=engine)

app = FastAPI()
origins = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows these origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)
app.include_router(chats.router)
app.include_router(communication.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(search.router)
app.include_router(user_to_user.router)

app.mount(
    "/profile_images",
    StaticFiles(directory=profile.UPLOAD_PROFILE_DIR),  # app/uploads/profile_pics/
    name="profile_images",
)

app.mount(
    "/uploads/messages",  # URL path where files can be accessed
    StaticFiles(directory=os.path.join("uploads", "messages")),  # Correct path to the 'uploads/messages' directory
    name="message_files"
)

app.mount(
    "/uploads/group-image",  # URL path where files can be accessed
    StaticFiles(directory=os.path.join("uploads", "group-image")),  # Correct path to the 'uploads/messages' directory
    name="group-images"
)

app.include_router(home.router)
app.include_router(user_to_user.router)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
