from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Table
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Association table for Group Members
group_members = Table(
    'group_members',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('group_id', Integer, ForeignKey('chats.id'))
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    bio = Column(String, default="Hey there! I am using PrideChat.")
    avatar = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)  # Room name or username or group name
    is_group = Column(Boolean, default=False)
    admin_username = Column(String, nullable=True)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    sender = Column(String)
    content = Column(String)