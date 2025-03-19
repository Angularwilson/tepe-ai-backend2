from sqlalchemy import Column, Integer, String, Date, ForeignKey
from models.sqlalchemy.base import Base
from sqlalchemy.orm import relationship


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String)
    contenu = Column(String)
    file_url = Column(String) 
    type_message = Column(String)
    date = Column(Date)
    history_id = Column(Integer, ForeignKey('histories.id'))
    history = relationship("History")
