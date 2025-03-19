from datetime import timedelta
import os
import time
import logging
from fastapi import APIRouter, Depends, HTTPException, requests
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from starlette import status
from models.pydantic.refresh_token import RefreshTokenRequest
from database import get_db
from models.pydantic.user import GoogleLoginRequest, UserLogin, UserRegister
from models.sqlalchemy.user import User
from firebase_admin import auth as firebase_auth
from utils.helpers import  authenticate_user, ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, pwd_context,extraire_nom_depuis_email, \
    get_user_by_email, oauth2_scheme,  add_token_to_blacklist, get_current_user,create_refresh_token,decode_token,SECRET_KEY, ALGORITHM 
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

logger = logging.getLogger("auth")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    user_check = authenticate_user(db, email=user.email, password=user.password)
    if not user_check:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    refresh_token_expires = timedelta(days=7)
    refresh_token = create_refresh_token(
        data={"sub": user.email},
        expires_delta=refresh_token_expires
    )
    
    return {"user": user_check,
            "access_token": access_token,"refresh_token": refresh_token ,"token_type": "bearer"}


@router.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    user_check = get_user_by_email(db, user.email)
    if user_check:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is already used",
            headers={"WWW-Authenticate": "Bearer"},
        )
    hashed_password = pwd_context.hash(user.password)
    db_user = User(email=user.email,
                   password=hashed_password,
                   firstname=user.firstname,
                   lastname=user.lastname,
                   status=1)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return login(UserLogin(email=user.email,
                           password=user.password), db)

#---Mes news routes p ----------------------------------------------------
@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(token: str = Depends(oauth2_scheme)):
    add_token_to_blacklist(token)  # mettre token dans la blackli
    return {"message": "Déconnexion réussie"}

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):return current_user



@router.post("/handle_google_login")
def handle_google_login(
    data: GoogleLoginRequest,
    db: Session = Depends(get_db)
):
    
    if not data.id_token:
        print("Erreur: Aucun id_token fourni.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="id_token est requis pour l'authentification Google."
        )

    try:

   
        print("Vérification du token Firebase...")
        time.sleep(4) 
        decoded_token = firebase_auth.verify_id_token(data.id_token)

        print("Token Firebase vérifié avec succès:", decoded_token)

    
        email = decoded_token.get("email")
        firstname = decoded_token.get("given_name")
        lastname = decoded_token.get("family_name")

        if not email:
            print("Erreur: Le token ne contient pas d'email.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Le token ne contient pas d'email."
            )

        if not firstname or not lastname:
            nom_complet = extraire_nom_depuis_email(email)
            noms = nom_complet.split()
            if len(noms) > 1:
                firstname = noms[0]
                lastname = ' '.join(noms[1:])
            else:
                firstname = noms[0]
                lastname = ""

        print(f"Infos récupérées : email={email}, firstname={firstname}, lastname={lastname}")

    except Exception as e:
        print(f"Erreur lors de la vérification du token Firebase : {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token Firebase invalide ou expiré: {str(e)}"
        )


    print(f"Vérification de l'utilisateur dans la base de données pour l'email: {email}")
    try:
        user_in_db = get_user_by_email(db, email)
    except Exception as e:
        print(f"Erreur lors de la recherche de l'utilisateur dans la base : {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la vérification de l'utilisateur : {str(e)}"
        )

    if not user_in_db:
        print("Utilisateur non trouvé en base, création d'un nouvel utilisateur...")
        try:
            user_in_db = User(
                email=email,
                password="",  
                firstname=firstname,
                lastname=lastname,
                status=1
            )
            db.add(user_in_db)
            db.commit()
            db.refresh(user_in_db)
            print(f"Nouvel utilisateur créé : {user_in_db}")
        except Exception as e:
            print(f"Erreur lors de la création de l'utilisateur : {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la création de l'utilisateur : {str(e)}"
            )

    try:
        print("Génération des tokens JWT...")
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_in_db.email},
            expires_delta=access_token_expires
        )
        refresh_token_expires = timedelta(days=7)
        refresh_token = create_refresh_token(
            data={"sub": user_in_db.email},
            expires_delta=refresh_token_expires
        )
        print("Tokens générés avec succès.")
    except Exception as e:
        print(f"Erreur lors de la génération des tokens JWT : {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération des tokens : {str(e)}"
        )

   
    print("Retour de la réponse au client.")
    return {
        "message": "Login Google via Firebase réussi",
        "user": {
            "id": user_in_db.id,
            "firstname": user_in_db.firstname or "Google User",
            "lastname": user_in_db.lastname or "User",
            "email": user_in_db.email,
            "password": "",
            "status": user_in_db.status,
        },
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }



@router.post("/refresh_token")
async def refresh_token_endpoint(token_request: RefreshTokenRequest):
    """
    Vérifie le refresh token, et si valide, génère un nouveau token d'accès et un nouveau refresh token.
    """
    # Décodage et vérification du refresh token
    try:
        payload = jwt.decode(token_request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            logger.error("Payload du refresh token invalide, 'sub' manquant : %s", payload)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Payload du token invalide"
            )
    except JWTError as e:
        logger.error("Erreur lors du décodage du refresh token : %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou expiré"
        )

    # Génération des nouveaux tokens
    try:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(data={"sub": email}, expires_delta=access_token_expires)

        refresh_token_expires = timedelta(days=7)
        new_refresh_token = create_refresh_token(data={"sub": email}, expires_delta=refresh_token_expires)

        logger.info("Nouveaux tokens générés avec succès pour l'email: %s", email)
    except Exception as e:
        logger.exception("Erreur lors de la génération des nouveaux tokens pour l'email %s: %s", email, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la génération des nouveaux tokens"
        )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }