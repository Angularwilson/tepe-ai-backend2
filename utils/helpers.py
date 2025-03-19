import logging
import os
from datetime import timedelta, datetime, timezone 
from typing import  Union
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
# import openai
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from starlette import status

from database import SessionLocal
from models.sqlalchemy.user import User
import threading
import json
from dotenv import load_dotenv
import google.generativeai as genai
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("La variable d'environnement GOOGLE_API_KEY n'est pas définie.")
genai.configure(api_key=GOOGLE_API_KEY)
# openai.api_key = os.getenv("OPENAI_API_KEY")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440
# ACCESS_TOKEN_EXPIRE_MINUTES = 60
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

BLACKLIST_FILE = "blacklisted_tokens.json"
blacklisted_tokens = set()
blacklist_lock = threading.Lock()


if os.path.exists(BLACKLIST_FILE):
    with open(BLACKLIST_FILE, "r") as f:
        try:
            blacklisted_tokens.update(json.load(f))
        except json.JSONDecodeError:
            print("Erreur lors du chargement du fichier de blacklist. Le fichier est peut-être vide ou corrompu.")
            
            
def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not pwd_context.verify(password, user.password):
        return False
    return user


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email, User.status == 1).first()


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
    
        expire = datetime.now(timezone.utc) + expires_delta  
    else:
      
        expire = datetime.now(datetime.timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def check_token_validity(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
 #-----Mes METHODES ----------------------------------------------------       
async def check_token_validity_with_blacklist(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    with blacklist_lock:
        if token in blacklisted_tokens:
            raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def add_token_to_blacklist(token: str):
    with blacklist_lock:
        blacklisted_tokens.add(token)
        with open(BLACKLIST_FILE, "w") as f:
            json.dump(list(blacklisted_tokens), f)
            


def get_current_user(
    db: Session = Depends(check_token_validity_with_blacklist),
    token: str = Depends(oauth2_scheme)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(db, email)
    if not user:
        raise credentials_exception

    return user

def create_refresh_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)  
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> str | None:

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        return email
    except JWTError:
        return None
    
    
def detect_context(user_message: str) -> str:
    """
    Tente de classer le message utilisateur en 'education', 'politique' ou 'general'.
    Utilise gemini-1.5-flash en posant un prompt explicite.
    En cas d'erreur ou si la réponse n'est pas claire, renvoie 'general'.
    """
    prompt = f"""
    Je veux que tu lises ce message et décides s'il parle principalement d'éducation,
    de politique ou ni l'un ni l'autre (dans ce cas réponds 'general').
    Réponds UNIQUEMENT par 'education', 'politique' ou 'general', en minuscule.

    Message Utilisateur:
    {user_message}
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([prompt])
        raw_text = response.text.strip().lower()

        if raw_text in ["education", "politique", "general"]:
            return raw_text
        else:
            return "general"

    except Exception as e:

        return "general"

    
    
def generative_ai(user_message: Union[str, list], context: str, conversation_history: list[str] = None, generate_image: bool = True) -> dict:
    # Si user_message est une liste, on concatène ses parties pour la détection de contexte
    if context == "auto":
        if isinstance(user_message, list):
            combined = " ".join([part if isinstance(part, str) else "" for part in user_message])
            context = detect_context(combined)
        else:
            context = detect_context(user_message)
    if context == "education":
        system_prompt = (
            "Tu es Tépé AI spécialisé dans l'éducation. "
            "Tu fournis des conseils pédagogiques, des explications claires et "
            "des réponses adaptées aux questions éducatives."
        )
    elif context == "politique":
        system_prompt = (
            "Tu es Tépé AI spécialisé dans la politique. "
            "Tu analyses des situations politiques, fournis des explications et "
            "des avis éclairés sur des questions politiques."
        )
    else:
        system_prompt = (
            "Tu es Tépé AI généralisé. Tu ne parleras pas de Gemini, tu es un bijou de TEPE CORPORATION."
        )

    model_text = genai.GenerativeModel('gemini-1.5-flash')
    prompt_parts = [system_prompt]
    if conversation_history:
        prompt_parts += conversation_history
    # Si user_message est une liste, on ajoute chacune de ses parties, sinon on ajoute directement la chaîne.
    if isinstance(user_message, list):
        prompt_parts.extend(user_message)
    else:
        prompt_parts.append(user_message)

    try:
        response = model_text.generate_content(prompt_parts)
        text_response = response.text
    except Exception as e:
        text_response = f"[ERREUR] Impossible de générer la réponse : {e}"

    result = {
        "text": text_response,
    }

    if generate_image:
        model_image = genai.GenerativeModel('gemini-1.5-flash-vision')
        # Pour la génération d'image, on prend uniquement le texte (on ne peut pas envoyer la base64 ici)
        image_prompt = f"{context.capitalize()} illustration : " + (user_message if isinstance(user_message, str) else "")
        try:
            img_response = model_image.generate_content([image_prompt])
            if img_response.parts:
                for part in img_response.parts:
                    if hasattr(part.data, 'url'):
                        image_url = part.data.url
                        result["image_url"] = image_url
                        break
                else:
                    result["image_url"] = "[ERREUR] Impossible d'obtenir l'URL de l'image."
            else:
                result["image_url"] = "[ERREUR] Aucune partie dans la réponse de l'image."
        except Exception as e:
            result["image_url"] = f"[ERREUR] Impossible de générer l'image : {e}"
    return result


    
def generate_label(context: str, user_message: str) -> str:
 
    if context == "education":
        prompt = f"Génère un titre concis pour une discussion éducative basée sur : {user_message}"
    elif context == "politique":
        prompt = f"Génère un titre concis pour une discussion politique basée sur : {user_message}"
    else:
        prompt = f"Génère un titre pour une discussion générale basée sur : {user_message}"

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')  
        response = model.generate_content([prompt])
        title = response.text.strip() if response and response.text else "Nouvelle discussion"
    except Exception as e:
        title = "Nouvelle discussion"
    
    return title


def detect_context_strict(user_message: str, is_image: bool = False) -> str:
    if is_image:

        prompt = f"""
        Tu dois classer ce message ou cette image en 'education' ou 'politique'.
        Ne réponds que par un seul mot: 'education' ou 'politique'.
        Indice: c'est un message IMAGE, mais essaie de deviner le thème.
        """
    else:
        prompt = f"""
        Tu dois classer strictement ce message utilisateur en 'education' ou 'politique'. 
        Ne réponds que par un seul mot: 'education' ou 'politique'.
        Message:
        {user_message}
        """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([prompt])
        raw_text = response.text.strip().lower()


        if "politique" in raw_text:
            return "politique"
        else:
           
            return "education"
    except Exception as e:
        logging.exception("Erreur dans detect_context_strict: %s", e)
        return "education"
 
    
def extraire_nom_depuis_email(email):
    """
    Extrait un nom d'utilisateur à partir de l'adresse e-mail.
    """
    try:
        partie_locale = email.split('@')[0]
        nom_propre = ''.join(char if char.isalpha() else ' ' for char in partie_locale)
        mots = nom_propre.split()
        mots_capitalises = [mot.capitalize() for mot in mots]

        nom_utilisateur = ' '.join(mots_capitalises)
        return nom_utilisateur
    except Exception as e:
        print(f"Erreur lors de l'extraction du nom depuis l'e-mail : {str(e)}")
        return "Utilisateur Inconnu"
