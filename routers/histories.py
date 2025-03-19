from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from zoneinfo import ZoneInfo
from models.pydantic.history import CreateHistory, History
from models.sqlalchemy.history import History as DBHistory
from models.sqlalchemy.user import User
from utils.helpers import check_token_validity, get_current_user
import os
from urllib.parse import urlparse
router = APIRouter()

from datetime import datetime
from zoneinfo import ZoneInfo

@router.post("/create/histories", response_model=History)
def create_history(history: CreateHistory, db: Session = Depends(check_token_validity)):

    now_utc = datetime.now(ZoneInfo("UTC"))

    db_history = DBHistory(
        label=history.label,
        context=history.context,
        user_id=history.user_id,
        date=now_utc  
    )
    db.add(db_history)
    db.commit()
    db.refresh(db_history)

    return db_history



@router.get("/all_user_histories",response_model=List[History])
def list_histories(
    db: Session = Depends(check_token_validity),
    current_user: User = Depends(get_current_user)
):
    histories = (
        db.query(DBHistory)
        .filter(DBHistory.user_id == current_user.id)
        .order_by(desc(DBHistory.date)) 
        .all()
    )
    return histories

@router.get("/user_histories/{history_id}", response_model=History)
def get_history(
    history_id: int,
    db: Session = Depends(check_token_validity),
    current_user: User = Depends(get_current_user)
):
   
    history = db.query(DBHistory).filter(
        DBHistory.id == history_id,
        DBHistory.user_id == current_user.id
    ).first()
    if not history:
        raise HTTPException(status_code=404, detail="Historique non trouvé")
    return history


@router.delete("/delete/{history_id}")
def delete_history(
    history_id: int,
    db: Session = Depends(check_token_validity),
    current_user: User = Depends(get_current_user)
):
  
    history = db.query(DBHistory).filter(
        DBHistory.id == history_id,
        DBHistory.user_id == current_user.id
    ).first()
    if not history:
        raise HTTPException(status_code=404, detail="Historique non trouvé")

    
    for message in history.messages:
        if message.file_url:
            try:
               
                parsed_url = urlparse(message.file_url)
                file_path = parsed_url.path 
               
                if file_path.startswith('/'):
                    file_path = file_path[1:]
                local_file_path = os.path.join(os.getcwd(), file_path)
                if os.path.exists(local_file_path):
                    os.remove(local_file_path)
                    print(f"Fichier supprimé: {local_file_path}")
                else:
                    print(f"Fichier non trouvé: {local_file_path}")
            except Exception as e:
                print(f"Erreur lors de la suppression du fichier {message.file_url}: {e}")

    db.delete(history)
    db.commit()

    return {"message": "Historique et images associées supprimés avec succès."}