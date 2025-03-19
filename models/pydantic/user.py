from pydantic import BaseModel, Field


class UserLogin(BaseModel):
    email: str
    password: str


class UserRegister(BaseModel):
    firstname: str
    lastname: str
    email: str
    password: str


class User(BaseModel):
    id: str
    firstname: str
    lastname: str
    email: str
    password: str
    status: int
    

class GoogleLoginRequest(BaseModel):
    id_token: str


