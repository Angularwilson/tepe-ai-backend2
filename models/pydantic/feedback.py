from pydantic import BaseModel
from datetime import date

class FeedbackCreate(BaseModel):
    contenu: str
    date: date

class Feedback(BaseModel):
    id: int
    contenu: str
    date: date
    user_id: str  
