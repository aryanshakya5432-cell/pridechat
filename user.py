from sqlalchemy.orm import Session
from models import User

def create_user(username: str, password: str, session: Session):
    user = User(username=username, password=password) # password_hash ki jagah password use kiya
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def authenticate_user(username: str, password: str, session: Session):
    user = session.query(User).filter_by(username=username).first()
    if user and user.password == password: # user.password_hash ki jagah user.password check hoga
        return user
    return None