from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import CreamTransaction, MonthlySummary, User
from schemas import CreamCreate


router = APIRouter(prefix="/api", tags=["cream"])
READ_ONLY_CUTOFF = "2026-06"


def _month_from_date(date_value: str) -> str:
    return date_value[:7]


def _serialize_transaction(row: CreamTransaction) -> dict:
    return {
        "id": row.id,
        "date": row.date,
        "year_month": row.year_month,
        "platform": row.platform,
        "card_company": row.card_company,
        "buy_amount": row.buy_amount,
        "sell_amount": row.sell_amount,
        "payback_amount": row.payback_amount,
        "profit": row.profit,
        "korean_air": row.korean_air,
        "asiana": row.asiana,
        "condition": row.condition,
        "memo": row.memo,
        "created_at": row.created_at,
    }


def _serialize_seed(row: MonthlySummary) -> dict:
    return {
        "year_month": row.year_month,
        "cr_korean_air": row.cr_korean_air,
        "cr_asiana": row.cr_asiana,
        "cr_profit": row.cr_profit,
        "cr_buy_total": row.cr_buy_total,
    }


def _has_cream_data(row: MonthlySummary) -> bool:
    return any(
        [
            row.cr_korean_air,
            row.cr_asiana,
            row.cr_profit,
            row.cr_buy_total,
        ]
    )


@router.get("/cream")
def get_cream(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    seed_rows = []
    if user.is_seed_owner:
        seed_rows = (
            db.query(MonthlySummary)
            .filter(MonthlySummary.year_month <= READ_ONLY_CUTOFF)
            .order_by(MonthlySummary.year_month.desc())
            .all()
        )
    transactions = (
        db.query(CreamTransaction)
        .filter(CreamTransaction.year_month > READ_ONLY_CUTOFF, CreamTransaction.user_id == user.id)
        .order_by(CreamTransaction.date.desc(), CreamTransaction.id.desc())
        .all()
    )
    return {
        "seed_summaries": [_serialize_seed(row) for row in seed_rows if _has_cream_data(row)],
        "transactions": [_serialize_transaction(row) for row in transactions],
    }


@router.post("/cream")
def create_cream(payload: CreamCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    year_month = _month_from_date(payload.date)
    if year_month <= READ_ONLY_CUTOFF:
        raise HTTPException(status_code=403, detail="2026-06 이하 시드 데이터는 수정할 수 없습니다.")

    profit = payload.sell_amount - payload.buy_amount + payload.payback_amount
    row = CreamTransaction(
        user_id=user.id,
        date=payload.date,
        year_month=year_month,
        platform=payload.platform,
        card_company=payload.card_company,
        buy_amount=payload.buy_amount,
        sell_amount=payload.sell_amount,
        payback_amount=payload.payback_amount,
        profit=profit,
        korean_air=payload.korean_air,
        asiana=payload.asiana,
        condition=payload.condition,
        memo=payload.memo,
        created_at=datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_transaction(row)


@router.delete("/cream/{transaction_id}")
def delete_cream(transaction_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.query(CreamTransaction).filter(CreamTransaction.id == transaction_id, CreamTransaction.user_id == user.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="거래를 찾을 수 없습니다.")
    if row.year_month <= READ_ONLY_CUTOFF:
        raise HTTPException(status_code=403, detail="2026-06 이하 시드 데이터는 삭제할 수 없습니다.")
    db.delete(row)
    db.commit()
    return {"ok": True}
