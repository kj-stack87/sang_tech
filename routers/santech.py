import re
from datetime import datetime
from math import floor
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import MonthlySummary, SantechCard, SantechTransaction, User
from schemas import SantechCardCreate, SantechCreate, SantechRefundUpdate, SantechUpdate


router = APIRouter(prefix="/api", tags=["santech"])
READ_ONLY_CUTOFF = "2026-06"


def _month_from_date(date_value: str) -> str:
    return date_value[:7]


def _validate_month(month: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise HTTPException(status_code=422, detail="month must use YYYY-MM")
    try:
        datetime.strptime(f"{month}-01", "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="month must be a real calendar month") from exc
    return month


def _current_month() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m")


def _serialize_transaction(row: SantechTransaction) -> dict:
    return {
        "id": row.id,
        "date": row.date,
        "year_month": row.year_month,
        "product": row.product,
        "refund_vendor": row.refund_vendor or None,
        "card": row.card,
        "purchase_amount": row.purchase_amount,
        "refund_amount": row.refund_amount,
        "point_amount": row.point_amount,
        "cashback_amount": row.cashback_amount,
        "profit": row.profit,
        "korean_air": row.korean_air,
        "asiana": row.asiana,
        "hana_mile": row.hana_mile,
        "memo": row.memo,
        "created_at": row.created_at,
    }


def _serialize_card(row: SantechCard) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "benefit_type": row.benefit_type,
        "mileage_target": row.mileage_target or "hana_mile",
        "mileage_spend_amount": row.mileage_spend_amount or 0,
        "mileage_earn_amount": row.mileage_earn_amount or 0,
        "reward_rate": row.reward_rate or 0,
        "monthly_cap": row.monthly_cap,
        "is_unlimited": bool(row.is_unlimited),
        "created_at": row.created_at,
    }


def _card_profile(db: Session, user_id: int, name: str) -> SantechCard:
    row = db.query(SantechCard).filter(SantechCard.user_id == user_id, SantechCard.name == name).first()
    if row is None:
        raise HTTPException(status_code=422, detail="등록된 카드가 아닙니다. 카드 관리에서 먼저 추가해주세요.")
    return row


def _card_names(db: Session, user_id: int) -> list[str]:
    rows = db.query(SantechCard.name).filter(SantechCard.user_id == user_id).order_by(SantechCard.id.asc()).all()
    return [row.name for row in rows]


def _card_benefits(db: Session, user_id: int, payload, year_month: str, exclude_id: int | None = None) -> dict:
    purchase = payload.purchase_amount
    benefits = {"point_amount": 0, "cashback_amount": 0, "korean_air": 0, "asiana": 0, "hana_mile": 0}
    profile = _card_profile(db, user_id, payload.card)

    if profile.benefit_type == "mileage":
        target = profile.mileage_target or "hana_mile"
        benefits[target] = floor((purchase / profile.mileage_spend_amount) * profile.mileage_earn_amount)
    elif profile.benefit_type in {"cashback", "discount"}:
        benefit_amount = floor(purchase * ((profile.reward_rate or 0) / 100))
        if profile.is_unlimited:
            benefits["cashback_amount"] = benefit_amount
            return benefits
        query = db.query(func.coalesce(func.sum(SantechTransaction.cashback_amount), 0)).filter(
            SantechTransaction.year_month == year_month,
            SantechTransaction.card == profile.name,
            SantechTransaction.user_id == user_id,
        )
        if exclude_id is not None:
            query = query.filter(SantechTransaction.id != exclude_id)
        used_benefit = query.scalar() or 0
        remaining = max(0, (profile.monthly_cap or 0) - used_benefit)
        benefits["cashback_amount"] = min(benefit_amount, remaining)

    return benefits


def _recent_templates(db: Session, user_id: int) -> list[dict]:
    rows = (
        db.query(SantechTransaction)
        .filter(SantechTransaction.year_month > READ_ONLY_CUTOFF, SantechTransaction.user_id == user_id)
        .order_by(SantechTransaction.date.desc(), SantechTransaction.id.desc())
        .limit(100)
        .all()
    )
    templates = []
    seen = set()
    for row in rows:
        key = (
            row.date,
            row.product,
            row.card,
            row.purchase_amount,
            row.korean_air,
            row.asiana,
            row.memo or "",
        )
        if key in seen:
            continue
        seen.add(key)
        templates.append(_serialize_transaction(row))
        if len(templates) == 10:
            break
    return templates


def _seed_summary(db: Session, month: str) -> dict:
    row = db.query(MonthlySummary).filter(MonthlySummary.year_month == month).first()
    return {
        "purchase": row.st_purchase if row else 0,
        "refund": row.st_refund if row else 0,
        "point": row.st_point if row else 0,
        "cashback": row.st_cashback if row else 0,
        "profit": row.st_profit if row else 0,
        "korean_air": row.st_korean_air if row else 0,
        "asiana": row.st_asiana if row else 0,
        "hana_mile": row.st_hana_mile if row else 0,
    }


def _blank_summary() -> dict:
    return {
        "purchase": 0,
        "refund": 0,
        "point": 0,
        "cashback": 0,
        "profit": 0,
        "korean_air": 0,
        "asiana": 0,
        "hana_mile": 0,
    }


def _live_summary(db: Session, user_id: int, month: str) -> dict:
    row = (
        db.query(
            func.coalesce(func.sum(SantechTransaction.purchase_amount), 0).label("purchase"),
            func.coalesce(func.sum(SantechTransaction.refund_amount), 0).label("refund"),
            func.coalesce(func.sum(SantechTransaction.point_amount), 0).label("point"),
            func.coalesce(func.sum(SantechTransaction.cashback_amount), 0).label("cashback"),
            func.coalesce(func.sum(SantechTransaction.profit), 0).label("profit"),
            func.coalesce(func.sum(SantechTransaction.korean_air), 0).label("korean_air"),
            func.coalesce(func.sum(SantechTransaction.asiana), 0).label("asiana"),
            func.coalesce(func.sum(SantechTransaction.hana_mile), 0).label("hana_mile"),
        )
        .filter(SantechTransaction.year_month == month, SantechTransaction.user_id == user_id)
        .one()
    )
    return {
        "purchase": row.purchase,
        "refund": row.refund,
        "point": row.point,
        "cashback": row.cashback,
        "profit": row.profit,
        "korean_air": row.korean_air,
        "asiana": row.asiana,
        "hana_mile": row.hana_mile,
    }


def _card_usage(db: Session, user_id: int, month: str) -> list[dict]:
    usage = {
        card: {
            "card": card,
            "count": 0,
            "purchase_amount": 0,
            "refund_amount": 0,
            "cashback_amount": 0,
            "point_amount": 0,
            "hana_mile": 0,
            "profit": 0,
        }
        for card in _card_names(db, user_id)
    }
    rows = (
        db.query(
            SantechTransaction.card,
            func.count(SantechTransaction.id).label("count"),
            func.coalesce(func.sum(SantechTransaction.purchase_amount), 0).label("purchase_amount"),
            func.coalesce(func.sum(SantechTransaction.refund_amount), 0).label("refund_amount"),
            func.coalesce(func.sum(SantechTransaction.cashback_amount), 0).label("cashback_amount"),
            func.coalesce(func.sum(SantechTransaction.point_amount), 0).label("point_amount"),
            func.coalesce(func.sum(SantechTransaction.hana_mile), 0).label("hana_mile"),
            func.coalesce(func.sum(SantechTransaction.profit), 0).label("profit"),
        )
        .filter(SantechTransaction.year_month == month, SantechTransaction.user_id == user_id)
        .group_by(SantechTransaction.card)
        .all()
    )
    for row in rows:
        if row.card not in usage:
            usage[row.card] = {
                "card": row.card,
                "count": 0,
                "purchase_amount": 0,
                "refund_amount": 0,
                "cashback_amount": 0,
                "point_amount": 0,
                "hana_mile": 0,
                "profit": 0,
            }
        usage[row.card].update(
            {
                "count": row.count,
                "purchase_amount": row.purchase_amount,
                "refund_amount": row.refund_amount,
                "cashback_amount": row.cashback_amount,
                "point_amount": row.point_amount,
                "hana_mile": row.hana_mile,
                "profit": row.profit,
            }
        )
    return list(usage.values())


@router.get("/santech/cards")
def get_santech_cards(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(SantechCard).filter(SantechCard.user_id == user.id).order_by(SantechCard.id.asc()).all()
    return [_serialize_card(row) for row in rows]


@router.post("/santech/cards")
def create_santech_card(payload: SantechCardCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    exists = db.query(SantechCard).filter(SantechCard.user_id == user.id, SantechCard.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=409, detail="이미 등록된 카드입니다.")
    row = SantechCard(
        user_id=user.id,
        name=payload.name,
        benefit_type=payload.benefit_type,
        mileage_target=payload.mileage_target,
        mileage_spend_amount=payload.mileage_spend_amount,
        mileage_earn_amount=payload.mileage_earn_amount,
        reward_rate=payload.reward_rate,
        monthly_cap=payload.monthly_cap,
        is_unlimited=1 if payload.is_unlimited else 0,
        created_at=datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_card(row)


@router.delete("/santech/cards/{card_id}")
def delete_santech_card(card_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.query(SantechCard).filter(SantechCard.id == card_id, SantechCard.user_id == user.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="카드를 찾을 수 없습니다.")
    used = (
        db.query(SantechTransaction.id)
        .filter(SantechTransaction.user_id == user.id, SantechTransaction.card == row.name)
        .first()
    )
    if used:
        raise HTTPException(status_code=409, detail="이미 거래에 사용된 카드는 삭제할 수 없습니다.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/santech")
def get_santech(month: str = Query(default=None), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    month = _validate_month(month or _current_month())
    read_only = month <= READ_ONLY_CUTOFF

    if read_only:
        return {
            "month": month,
            "read_only": True,
            "summary": _seed_summary(db, month) if user.is_seed_owner else _blank_summary(),
            "transactions": [],
            "recent_templates": _recent_templates(db, user.id),
            "card_usage": [],
        }

    transactions = (
        db.query(SantechTransaction)
        .filter(SantechTransaction.year_month == month, SantechTransaction.user_id == user.id)
        .order_by(SantechTransaction.date.desc(), SantechTransaction.id.desc())
        .all()
    )
    return {
        "month": month,
        "read_only": False,
        "summary": _live_summary(db, user.id, month),
        "transactions": [_serialize_transaction(row) for row in transactions],
        "recent_templates": _recent_templates(db, user.id),
        "card_usage": _card_usage(db, user.id, month),
    }


@router.post("/santech")
def create_santech(payload: SantechCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    year_month = _month_from_date(payload.date)
    if year_month <= READ_ONLY_CUTOFF:
        raise HTTPException(status_code=403, detail="2026-06 이하 시드 데이터는 수정할 수 없습니다.")

    rows = []
    created_at = datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")
    for _ in range(payload.quantity):
        benefits = _card_benefits(db, user.id, payload, year_month)
        profit = benefits["point_amount"] + benefits["cashback_amount"] - payload.purchase_amount
        row = SantechTransaction(
            user_id=user.id,
            date=payload.date,
            year_month=year_month,
            purchase_amount=payload.purchase_amount,
            refund_amount=0,
            point_amount=benefits["point_amount"],
            cashback_amount=benefits["cashback_amount"],
            profit=profit,
            product=payload.product,
            refund_vendor=None,
            card=payload.card,
            korean_air=benefits["korean_air"] or payload.korean_air,
            asiana=benefits["asiana"] or payload.asiana,
            hana_mile=benefits["hana_mile"],
            gift_amount=0,
            memo=payload.memo,
            created_at=created_at,
        )
        db.add(row)
        db.flush()
        rows.append(row)

    db.commit()
    for row in rows:
        db.refresh(row)
    return [_serialize_transaction(row) for row in rows]


@router.patch("/santech/{transaction_id}/refund")
def update_santech_refund(transaction_id: int, payload: SantechRefundUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.query(SantechTransaction).filter(SantechTransaction.id == transaction_id, SantechTransaction.user_id == user.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="거래를 찾을 수 없습니다.")
    if row.year_month <= READ_ONLY_CUTOFF:
        raise HTTPException(status_code=403, detail="2026-06 이하 시드 데이터는 수정할 수 없습니다.")

    row.refund_amount = payload.refund_amount
    row.refund_vendor = payload.refund_vendor
    row.profit = row.refund_amount + row.point_amount + row.cashback_amount - row.purchase_amount
    db.commit()
    db.refresh(row)
    return _serialize_transaction(row)


@router.patch("/santech/{transaction_id}")
def update_santech(transaction_id: int, payload: SantechUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.query(SantechTransaction).filter(SantechTransaction.id == transaction_id, SantechTransaction.user_id == user.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="거래를 찾을 수 없습니다.")
    if row.year_month <= READ_ONLY_CUTOFF:
        raise HTTPException(status_code=403, detail="2026-06 이하 시드 데이터는 수정할 수 없습니다.")

    year_month = _month_from_date(payload.date)
    if year_month <= READ_ONLY_CUTOFF:
        raise HTTPException(status_code=403, detail="2026-06 이하 시드 데이터로 변경할 수 없습니다.")
    if payload.refund_amount > 0 and not payload.refund_vendor:
        raise HTTPException(status_code=422, detail="환급액이 있으면 환급처를 선택해주세요.")

    benefits = _card_benefits(db, user.id, payload, year_month, exclude_id=row.id)
    row.date = payload.date
    row.year_month = year_month
    row.purchase_amount = payload.purchase_amount
    row.refund_amount = payload.refund_amount
    row.refund_vendor = payload.refund_vendor if payload.refund_amount > 0 else None
    row.point_amount = benefits["point_amount"]
    row.cashback_amount = benefits["cashback_amount"]
    row.card = payload.card
    row.product = payload.product
    row.korean_air = benefits["korean_air"] or payload.korean_air
    row.asiana = benefits["asiana"] or payload.asiana
    row.hana_mile = benefits["hana_mile"]
    row.memo = payload.memo
    row.profit = row.refund_amount + row.point_amount + row.cashback_amount - row.purchase_amount
    db.commit()
    db.refresh(row)
    return _serialize_transaction(row)


@router.delete("/santech/{transaction_id}")
def delete_santech(transaction_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.query(SantechTransaction).filter(SantechTransaction.id == transaction_id, SantechTransaction.user_id == user.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="거래를 찾을 수 없습니다.")
    if row.year_month <= READ_ONLY_CUTOFF:
        raise HTTPException(status_code=403, detail="2026-06 이하 시드 데이터는 삭제할 수 없습니다.")
    db.delete(row)
    db.commit()
    return {"ok": True}
