from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import init_db
from models import User, Chat, Message
from chat import manager
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SessionLocal = init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class LoginSchema(BaseModel):
    username: str
    password: str

class ProfileSchema(BaseModel):
    username: str
    bio: str = None
    avatar: str = None

class AdminAddUserSchema(BaseModel):
    admin_username: str
    new_username: str
    new_password: str

class AdminChangePasswordSchema(BaseModel):
    admin_username: str
    target_username: str
    new_password: str

class CreateGroupSchema(BaseModel):
    admin_username: str
    group_name: str
    members: List[str]

@app.post("/login")
def login(data: LoginSchema, db: Session = Depends(get_db)):
    admin_user = db.query(User).filter_by(username="admin").first()
    if not admin_user:
        admin = User(username="admin", password="admin123", is_admin=True, bio="PrideChat Administrator")
        db.add(admin)
        db.commit()

    user = db.query(User).filter_by(username=data.username, password=data.password).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    
    return {
        "status": "success", 
        "username": user.username, 
        "bio": getattr(user, 'bio', "Hey there! I am using PrideChat."),
        "avatar": getattr(user, 'avatar', None),
        "is_admin": getattr(user, 'is_admin', False)
    }

@app.post("/admin/add-user")
def admin_add_user(data: AdminAddUserSchema, db: Session = Depends(get_db)):
    admin = db.query(User).filter_by(username=data.admin_username, is_admin=True).first()
    if not admin:
        raise HTTPException(status_code=403, detail="Unauthorized: Only admin can add users.")
    
    existing = db.query(User).filter_by(username=data.new_username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists!")
    
    new_user = User(username=data.new_username, password=data.new_password, is_admin=False, bio="Hey there! I am using PrideChat.")
    db.add(new_user)
    db.commit()
    return {"status": "success", "message": f"User {data.new_username} created successfully!"}

@app.post("/admin/change-password")
def admin_change_password(data: AdminChangePasswordSchema, db: Session = Depends(get_db)):
    admin = db.query(User).filter_by(username=data.admin_username, is_admin=True).first()
    if not admin:
        raise HTTPException(status_code=403, detail="Unauthorized: Only admin can change passwords.")
    
    target_user = db.query(User).filter_by(username=data.target_username).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found!")
    
    target_user.password = data.new_password
    db.commit()
    return {"status": "success", "message": f"Password for @{data.target_username} updated successfully!"}

@app.post("/chats/get-or-create")
def get_or_create_chat(data: dict, db: Session = Depends(get_db)):
    user1 = data.get("user1")
    user2 = data.get("user2")
    room_name = f"chat_{'_'.join(sorted([user1, user2]))}"
    
    chat = db.query(Chat).filter_by(name=room_name).first()
    if not chat:
        chat = Chat(name=room_name, is_group=False)
        db.add(chat)
        db.commit()
        db.refresh(chat)
    return {"chat_id": chat.id, "room_name": room_name}

@app.post("/chats/create-group")
def create_group(data: CreateGroupSchema, db: Session = Depends(get_db)):
    existing = db.query(Chat).filter_by(name=data.group_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Group name already exists!")
    
    group = Chat(name=data.group_name, is_group=True, admin_username=data.admin_username)
    db.add(group)
    db.commit()
    db.refresh(group)
    return {"status": "success", "chat_id": group.id, "group_name": group.name}

@app.get("/chats/groups")
def get_groups(db: Session = Depends(get_db)):
    groups = db.query(Chat).filter_by(is_group=True).all()
    return [{"id": g.id, "name": g.name, "admin": g.admin_username} for g in groups]

@app.get("/admin/all-messages")
def get_all_messages_for_admin(admin_username: str, db: Session = Depends(get_db)):
    admin = db.query(User).filter_by(username=admin_username, is_admin=True).first()
    if not admin:
        raise HTTPException(status_code=403, detail="Unauthorized")
    messages = db.query(Message).all()
    return [{"chat_id": m.chat_id, "sender": m.sender, "content": m.content} for m in messages]

@app.post("/user/profile")
def update_profile(data: ProfileSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=data.username).first()
    if user:
        if data.bio is not None:
            user.bio = data.bio
        if data.avatar is not None:
            user.avatar = data.avatar
        db.commit()
        return {"status": "success", "bio": user.bio, "avatar": user.avatar}
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/users")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{
        "id": u.id, 
        "username": u.username, 
        "bio": getattr(u, 'bio', "Hey there! I am using PrideChat."),
        "avatar": getattr(u, 'avatar', None)
    } for u in users]

@app.get("/messages/{chat_id}")
def get_messages(chat_id: int, db: Session = Depends(get_db)):
    messages = db.query(Message).filter_by(chat_id=chat_id).all()
    return [{"sender": m.sender, "content": m.content} for m in messages]

@app.websocket("/chat/{chat_id}")
async def chat_websocket(websocket: WebSocket, chat_id: int):
    await manager.connect(chat_id, websocket)
    db = SessionLocal()
    try:
        while True:
            data = await websocket.receive_text()
            if ":CALL_SIGNAL:" not in data and ":TYPING:" not in data and ":SEEN:" not in data:
                parts = data.split(":")
                sender = parts[0]
                content = data.replace(f"{sender}:", "", 1)
                db_msg = Message(chat_id=chat_id, sender=sender, content=content)
                db.add(db_msg)
                db.commit()
            await manager.broadcast(chat_id, data)
    except WebSocketDisconnect:
        manager.disconnect(chat_id, websocket)
    finally:
        db.close()