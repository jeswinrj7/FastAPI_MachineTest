from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pymongo import MongoClient
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from bson import Binary
import io

DATABASE_URL = "postgresql://user_registration_user:helloworld@localhost:5432/user_registration_db"
SQLALCHEMY_DATABASE_URL = DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

MONGO_CONNECTION_STRING = "mongodb://localhost:27017/"
mongo_client = MongoClient(MONGO_CONNECTION_STRING)
mongo_db = mongo_client["profile_pictures"]

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    phone = Column(String, index=True)

class ProfilePicture(BaseModel):
    id: int
    profile_picture: bytes

    class Config:
        arbitrary_types_allowed = True

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserRegistration(BaseModel):
    full_name: str
    email: str
    password: str
    phone: str
    profile_picture: UploadFile = File(...)

@app.post("/register/")
def register_user(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(...),
    profile_picture: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(full_name=full_name, email=email, password=password, phone=phone)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    picture_data = profile_picture.file.read()
    profile_picture_id = mongo_db.profile_pictures.insert_one({
        "id" : new_user.id,
        "profile_picture": Binary(picture_data)
    }).inserted_id

    db.commit()

    return new_user

@app.get("/user/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/profile-picture/{user_id}")
def get_profile_picture(user_id: int):
    picture_data = mongo_db.profile_pictures.find_one({"id": user_id})
    if picture_data is None:
        raise HTTPException(status_code=404, detail="Profile picture not found")
    
    return StreamingResponse(io.BytesIO(picture_data["profile_picture"]), media_type="image/jpeg")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)