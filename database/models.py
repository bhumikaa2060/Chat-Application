import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func, Enum,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class MessageStatus(str, enum.Enum):
    sent = "sent"
    delivered = "delivered"
    read = "read"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    middle_name = Column(String)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    profile_image = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    file_url = Column(String, nullable=True)
    file_type = Column(String, nullable=True)

    # One-to-many: User can create many chatrooms
    chatrooms = relationship("Chatroom", back_populates="creator")
    # Many-to-many: User is member of many chatrooms
    member_of = relationship("RoomMembers", back_populates="user")
    # One-to-many: User sends many messages
    messages_sent = relationship(
        "Message", back_populates="sender", foreign_keys="Message.sender_id"
    )
    # One-to-many: User receives direct messages
    messages_received = relationship(
        "Message", back_populates="receiver", foreign_keys="Message.receiver_id"
    )


class Chatroom(Base):
    __tablename__ = "chatroom"

    id = Column(Integer, primary_key=True, autoincrement=True)
    roomname = Column(String, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_private = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=func.now())
    password = Column(String, nullable=True)
    image = Column(String, nullable=True)

    # Creator of the room
    creator = relationship("User", back_populates="chatrooms")
    # Members of the room
    members = relationship("RoomMembers", back_populates="chatroom")
    # Messages in the room
    messages = relationship("Message", back_populates="room")


class RoomMembers(Base):
    __tablename__ = "room_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("chatroom.id"), nullable=False)
    is_admin = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="member_of")
    chatroom = relationship("Chatroom", back_populates="members")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("chatroom.id"), nullable=True)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    sent_at = Column(DateTime, default=func.now())
    status = Column(Enum(MessageStatus), default=MessageStatus.sent)
    file_url = Column(String, nullable=True)
    file_type = Column(String, nullable=True)

    # Relationships
    sender = relationship(
        "User", back_populates="messages_sent", foreign_keys=[sender_id]
    )
    receiver = relationship(
        "User", back_populates="messages_received", foreign_keys=[receiver_id]
    )
    room = relationship("Chatroom", back_populates="messages")
