from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.database.session import get_db
from app.models.farm import Farm
from app.models.notification import Notification
from app.models.user import Farmer
from app.schemas.notification_schema import NotificationGenerateResponse, NotificationOut
from app.services.notification_service import generate_for_farm

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _to_out(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=n.id,
        farm_id=n.farm_id,
        category=n.category,
        priority=n.priority,
        title=n.title,
        message=n.message,
        is_read=n.is_read,
        created_at=n.created_at.isoformat(),
    )


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    farm_id: int | None = None,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
):
    query = db.query(Notification).filter(Notification.farmer_id == farmer.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    if farm_id is not None:
        query = query.filter(Notification.farm_id == farm_id)
    items = query.order_by(Notification.created_at.desc()).limit(100).all()
    return [_to_out(n) for n in items]


@router.post("/generate", response_model=NotificationGenerateResponse)
def generate_notifications(farm_id: int, db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == farmer.id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    created = generate_for_farm(db, farm, farmer)
    return NotificationGenerateResponse(created=len(created), notifications=[_to_out(n) for n in created])


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    note = db.query(Notification).filter(Notification.id == notification_id, Notification.farmer_id == farmer.id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    note.is_read = True
    db.commit()
    db.refresh(note)
    return _to_out(note)


@router.patch("/read-all", response_model=dict)
def mark_all_read(db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    updated = (
        db.query(Notification)
        .filter(Notification.farmer_id == farmer.id, Notification.is_read.is_(False))
        .update({"is_read": True})
    )
    db.commit()
    return {"updated": updated}
