from sqlalchemy import Column, String, Integer
from models.sqlalchemy.base import Base
import uuid
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    firstname = Column(String)
    lastname = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    status = Column(Integer, default=1)
    feedbacks = relationship("Feedback", back_populates="user")
    histories = relationship("History", back_populates="user", cascade="all, delete-orphan")