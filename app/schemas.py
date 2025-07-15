from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, StringConstraints

# class UserCreate(BaseModel):
#     username: str
#     first_name: str
#     middle_name: str | None = None
#     last_name: str
#     email: EmailStr
#     password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr

    class Config:
        orm_mode = True


class UserOut(BaseModel):
    id: int
    username: str
    first_name: str
    middle_name: str | None
    last_name: str
    email: EmailStr
    created_at: datetime
    profile_image: str | None

    class Config:
        orm_mode = True


# class UserUpdate(BaseModel):
#     first_name: str | None = None
#     middle_name: str | None = None
#     last_name: str | None = None
#     email: EmailStr | None = None


class ChangePassword(BaseModel):
    old_password: Annotated[str, StringConstraints(min_length=6)]
    new_password: Annotated[str, StringConstraints(min_length=6)]


# class CreateTable(BaseModel):
#     room_name: str
#     password: str | None = None


class JoinRoom(BaseModel):
    room_id: int
    password: str | None = None


class LastMessageResponse(BaseModel):
    roomname: str
    content: str
    timestamp: str

    class Config:
        orm_mode = True
