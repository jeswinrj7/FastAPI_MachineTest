from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
from sqlalchemy import create_engine, Column, Integer, String, LargeBinary, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import io

DATABASE_URL = "postgresql://user_registration_user:helloworld@localhost:5432/user_registration_db"
SQLALCHEMY_DATABASE_URL = DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users_1"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    phone = Column(String, index=True)

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    profile_picture = Column(LargeBinary)
    user_id = Column(Integer, ForeignKey('users_1.id'))

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserRegistration(BaseModel):
    full_name: str
    email: str
    password: str
    phone: str

class UserProfile(BaseModel):
    full_name: str
    email: str
    phone: str
    profile_picture: bytes  # Profile picture will be returned as bytes

@app.post("/register/")
async def register_user(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(...),
    profile_picture: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Check if email or phone already exists
    if db.query(User).filter((User.email == email) | (User.phone == phone)).first():
        raise HTTPException(status_code=400, detail="Email or phone already registered")

    new_user = User(full_name=full_name, email=email, password=password, phone=phone)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Save profile picture to the database
    new_profile = Profile(profile_picture=profile_picture.file.read(), user_id=new_user.id)
    db.add(new_profile)
    db.commit()

    return {"message": "User registered successfully"}

@app.get("/user/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/profile-picture/{user_id}")
def get_profile_picture(user_id: int, db: Session = Depends(get_db)):
    profiles = db.query(Profile).filter(Profile.user_id == user_id).first()
    if profiles is None:
        raise HTTPException(status_code=404, detail="Profile picture not found")    
    return StreamingResponse(io.BytesIO(profiles.profile_picture), media_type="image/jpeg")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)