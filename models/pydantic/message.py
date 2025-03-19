from typing import Optional
from pydantic import BaseModel
from datetime import date

class MessageCreate(BaseModel):
    version: str
    contenu: str
    type_message: str
    date: date
    history_id: int
    context: str  

class Message(BaseModel):
    id: int
    version: str
    contenu: str
    file_url: Optional[str] = None  
    type_message: str
    date: date
    history_id: int



class DetectContextPayload(BaseModel):
    contenu: str
    type_message: Optional[str] = "USER"  


