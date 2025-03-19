
import base64
from datetime import date
from typing import List, Optional, Union

from fastapi import APIRouter, Depends,File, Form, UploadFile
from sqlalchemy import asc
from sqlalchemy.orm import Session

from models.pydantic.message import DetectContextPayload, MessageCreate, Message
from models.sqlalchemy.message import Message as DBMessage
from models.sqlalchemy.user import User
from utils.helpers import check_token_validity, detect_context_strict, generative_ai, get_current_user,generate_label,detect_context
from models.sqlalchemy.history import History as DBHistory
import shutil
import os
from PyPDF2 import PdfReader
BASE_URL = os.getenv("BASE_URL", "http://192.168.1.69:8082/")


router = APIRouter()


@router.post("/send_message")
def send_message(
    version: str = Form("1.0"),
    contenu: str = Form(""),  
    context: str = Form("auto"),
    history_id: int = Form(0),
    file: UploadFile = File(None), 
    db: Session = Depends(check_token_validity),
    current_user: User = Depends(get_current_user)
):
    """
    Envoie un message contenant du texte ET/OU un fichier (image, PDF, etc.).
    Pour un PDF, aucun extrait de texte n'est réalisé : seul le texte saisi par l'utilisateur est utilisé,
    et éventuellement l'URL du fichier est ajoutée.
    """
    file_url: Optional[str] = None
    file_extension = ""
    user_message_to_send: Union[str, List[Union[str, dict]]] = contenu

    if file:
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_url = f"{BASE_URL}{upload_dir}/{file.filename}"
        file_extension = file.filename.lower()

        if file_extension.endswith(".pdf"):
            user_message_to_send = contenu
        else:
            file_size = os.stat(file_path).st_size
            max_size = 20 * 1024 * 1024  
            if file_size <= max_size:
                try:
                    with open(file_path, "rb") as f:
                        encoded_image = base64.b64encode(f.read()).decode("utf-8")
                    mime_type = "image/jpeg" if file_extension.endswith(".jpg") or file_extension.endswith(".jpeg") else "image/png"
                    image_part = {"mime_type": mime_type, "data": encoded_image}
                    user_message_to_send = [contenu, image_part]
                except Exception as e:
                    user_message_to_send = contenu + "\nL'URL du fichier est : " + file_url
            else:
                user_message_to_send = contenu + "\nL'URL du fichier est : " + file_url

        type_message = "FILE"
    else:
        type_message = "USER"

    
    if context == "auto":
        if file:
            context = detect_context_strict(contenu if contenu else "fichier", is_image=not file_extension.endswith(".pdf"))
        else:
            context = detect_context(contenu)


    merged_message = contenu
    if file_url and file_extension.endswith(".pdf"):
        pass

  
    if history_id <= 0:
        label = generate_label(context, merged_message)
        db_history = DBHistory(
            label=label,
            context=context,
            user_id=current_user.id
        )
        db.add(db_history)
        db.commit()
        db.refresh(db_history)
        history_id = db_history.id
    else:
        db_history = db.query(DBHistory).filter(DBHistory.id == history_id).first()
        if not db_history:
            return {"error": "Historique introuvable"}

    db_msg = DBMessage(
        version=version,
        contenu=merged_message,
        file_url=file_url,
        type_message=type_message,
        date=date.today(),
        history_id=history_id
    )
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)

    final_context = db_history.context
    previous_msgs = db.query(DBMessage).filter(DBMessage.history_id == history_id).order_by(DBMessage.date).all()
    conversation_history = [f"{m.type_message}: {m.contenu}" for m in previous_msgs]

    wants_image = ("photo" in contenu.lower() or "image" in contenu.lower())

    ai_result = generative_ai(
        user_message=user_message_to_send,
        context=final_context,
        conversation_history=conversation_history,
        generate_image=wants_image
    )
    db_ai_msg = DBMessage(
        version="1.0",
        contenu=ai_result["text"],
        file_url=None,
        type_message="AI_RESPONSE",
        date=date.today(),
        history_id=history_id
    )
    db.add(db_ai_msg)
    db.commit()
    db.refresh(db_ai_msg)

    return {
        "user_message": db_msg,
        "ai_message": db_ai_msg,
        "file_url": file_url,
        "history_id": history_id,
        "ai_image_url": ai_result.get("image_url")
    }

@router.get("/get_messages", response_model=List[Message])
def get_messages(history_id: int, db: Session = Depends(check_token_validity)):
    db_msgs = (
        db.query(DBMessage)
        .filter(DBMessage.history_id == history_id)
        .order_by(asc(DBMessage.date))  
        .all()
    )
    return db_msgs


@router.post("/detect_context_strict")
def detect_context_strict_route(
    payload: DetectContextPayload,
    db = Depends(check_token_validity),
):
    user_message = payload.contenu
    is_image = (payload.type_message == "IMAGE")
    final_context = detect_context_strict(user_message, is_image=is_image)
    return {"context": final_context}


@router.get("/featured_discussion")
def get_featured_discussion(
    db: Session = Depends(check_token_validity),
    current_user: User = Depends(get_current_user)
):
    """
    Retourne le dernier historique de l'utilisateur (contexte 'education' ou 'politique'),
    ainsi que les deux derniers messages :
      - Le dernier message de l'utilisateur (USER/FILE)
      - Le dernier message de l'IA (AI_RESPONSE)
    + une liste d'images extraites de la discussion.
    """
    
    all_histories = (
        db.query(DBHistory)
        .filter(DBHistory.user_id == current_user.id)
        .order_by(DBHistory.id.asc())
        .all()
    )
    if not all_histories:
        return {
            "success": True,
            "featured": {
                "lines": None, 
                "images": [],
                "history_id": None,
                "context": None
            }
        }

 
    filtered = [h for h in all_histories if h.context.lower() in ("education", "politique")]
    if not filtered:
        return {
            "success": True,
            "featured": {
                "lines": None,
                "images": [],
                "history_id": None,
                "context": None
            }
        }

  
    last_history = filtered[-1]
    history_id = last_history.id
    discussion_context = last_history.context.lower()

    
    db_msgs = (
        db.query(DBMessage)
        .filter(DBMessage.history_id == history_id)
        .order_by(DBMessage.id.asc())
        .all()
    )
    if not db_msgs:
        return {
            "success": True,
            "featured": {
                "lines": None,
                "images": [],
                "history_id": history_id,
                "context": discussion_context
            }
        }

  
    reversed_msgs = list(reversed(db_msgs))

    def is_user(m: DBMessage) -> bool:
        return m.type_message.upper() in ("USER", "FILE")

    def is_ai(m: DBMessage) -> bool:
        return m.type_message.upper() == "AI_RESPONSE"

    def trim_text(txt: str, max_len: int = 110) -> str:
        return txt if len(txt) <= max_len else txt[:max_len] + "..."

    last_user = None
    last_ai = None
    for m in reversed_msgs:
        if last_user is None and is_user(m):
            last_user = m
        elif last_ai is None and is_ai(m):
            last_ai = m
        if last_user and last_ai:
            break

    lines = []
    if last_user:
        lines.append({
            "type": last_user.type_message,
            "contenu": trim_text(last_user.contenu, 100)
        })
    if last_ai:
        lines.append({
            "type": last_ai.type_message,
            "contenu": trim_text(last_ai.contenu, 100)
        })

    images = [m.file_url for m in db_msgs if m.file_url is not None]
    if len(images) > 2:
        images = images[:2]

    return {
        "success": True,
        "featured": {
            "lines": lines,       
            "images": images,      
            "history_id": history_id,
            "context": discussion_context
        }
    }
