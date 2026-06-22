from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.responses import ok
from app.models.admin import RechargeOrder
from app.models.user import User
from app.schemas.admin import CreateOrderRequest, PayCallbackRequest
from app.services.admin_service import create_order, list_packages, pay_callback, serialize_order

router = APIRouter()


@router.get("/packages")
def packages(db: Session = Depends(get_db)):
    return ok(list_packages(db))


@router.post("/create-order")
def create_recharge_order(payload: CreateOrderRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(create_order(db, current_user, payload.packageId))


@router.post("/pay-callback")
def callback(payload: PayCallbackRequest, db: Session = Depends(get_db)):
    return ok(pay_callback(db, payload.tradeNo, payload.transactionId, payload.status))


@router.get("/orders")
def orders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(RechargeOrder).where(RechargeOrder.user_id == current_user.id).order_by(RechargeOrder.id.desc())).all()
    return ok([serialize_order(row) for row in rows])


@router.get("/orders/{tradeNo}")
def order_detail(tradeNo: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(RechargeOrder).where(RechargeOrder.trade_no == tradeNo, RechargeOrder.user_id == current_user.id))
    return ok(serialize_order(row) if row else None)
