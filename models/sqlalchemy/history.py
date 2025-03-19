import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from models.sqlalchemy.base import Base
import uuid


class History(Base):
    __tablename__ = "histories"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String)
    context = Column(String)
    date = Column(DateTime, default=datetime.datetime.now())

    user_id = Column(String, ForeignKey("users.id"))

    messages = relationship("Message", back_populates="history", cascade="all, delete-orphan")
    
    user = relationship("User", back_populates="histories")