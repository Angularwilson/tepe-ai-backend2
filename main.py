import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from starlette.middleware.cors import CORSMiddleware

from models.sqlalchemy.base import Base
from routers import auth, messages, users, histories
from contextlib import asynccontextmanager
import firebase_admin
from firebase_admin import credentials

load_dotenv()
origins = os.getenv("ORIGINS")
DB_URL = os.getenv("DB_URL")

if not firebase_admin._apps: 
    cred = credentials.Certificate("tepe-ai-firebase-adminsdk-fbsvc-600c4e1f89.json")
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK initialisé.")
else:
    print("Firebase Admin SDK déjà initialisé.")

@asynccontextmanager
async def lifespan(app :FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()  
app = FastAPI(lifespan=lifespan)
engine = create_engine(DB_URL)

# Middleware for CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the API"}


# Register routers
app.include_router(auth.router, prefix='/api/auth', tags=["auth"])
app.include_router(users.router, prefix='/api/users', tags=["users"])
app.include_router(histories.router, prefix='/api/histories', tags=["histories"])
app.include_router(messages.router, prefix='/api/messages', tags=["messages"])
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# Custom OpenAPI definition to add security schemes
security_schemes = {
    "HTTPBearer": {
        "type": "http",
        "scheme": "bearer"
    }
}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="TEPE AI API",
        version="1.0.0",
        description="API de l'application mobile IA de Tépé",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = security_schemes
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"HTTPBearer": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Start the application
if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        # host="localhost",
        port=8082,
    )


