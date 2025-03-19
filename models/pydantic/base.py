from pydantic import BaseModel


class BaseModelConfig(BaseModel):
    class Config:
        orm_mode = True


