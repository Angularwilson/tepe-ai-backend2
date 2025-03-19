from pydantic import BaseModel, Field
from datetime import datetime


class CreateHistory(BaseModel):
    label: str
    context: str
    user_id: str


class History(BaseModel):
    id: int
    label: str
    context: str
    date: datetime
    user_id: str
