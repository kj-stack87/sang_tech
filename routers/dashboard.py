from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import CreamTransaction, MileageCarry, MonthlySummary, SantechTransaction, User


router = APIRouter(prefix="/api", tags=["dashboard"])

MONTHLY_FIELDS = [
    "st_korean_air",
    "st_asiana",
    "st_hana_mile",
    "st_purchase",
    "st_refund",
    "st_profit",
    "st_point",
    "st_cashback",
    "cr_korean_air",
    "cr_asiana",
    "cr_profit",
    "cr_buy_total",
]


def _blank_month(year_month: str) -> dict:
    row = {field: 0 for field in MONTHLY_FIELDS}
    row["year_month"] = year_month
    row["is_seed"] = False
    return row


def _finalize_month(row: dict) -> dict:
    row["korean_air"] = row["st_korean_air"] + row["cr_korean_air"]
    row["asiana"] = row["st_asiana"] + row["cr_asiana"]
    row["hana_mile"] = row["st_hana_mile"]
    row["total_miles"] = row["korean_air"] + row["asiana"] + row["hana_mile"]
    row["total_profit"] = row["st_profit"] + row["cr_profit"]
    row["mile_unit_price"] = abs(row["st_profit"]) / row["total_miles"] if row["total_miles"] else 0
    row["is_seed"] = bool(row["is_seed"])
    return row


def build_monthly_rows(db: Session, user: User) -> list[dict]:
    rows: dict[str, dict] = {}

    if user.is_seed_owner:
        for summary in db.query(MonthlySummary).all():
            row = rows.setdefault(summary.year_month, _blank_month(summary.year_month))
            for field in MONTHLY_FIELDS:
                row[field] += getattr(summary, field) or 0
            row["is_seed"] = bool(summary.is_seed)

    santech_groups = (
        db.query(
            SantechTransaction.year_month,
            func.coalesce(func.sum(SantechTransaction.korean_air), 0).label("st_korean_air"),
            func.coalesce(func.sum(SantechTransaction.asiana), 0).label("st_asiana"),
            func.coalesce(func.sum(SantechTransaction.hana_mile), 0).label("st_hana_mile"),
            func.coalesce(func.sum(SantechTransaction.purchase_amount), 0).label("st_purchase"),
            func.coalesce(func.sum(SantechTransaction.refund_amount), 0).label("st_refund"),
            func.coalesce(func.sum(SantechTransaction.profit), 0).label("st_profit"),
            func.coalesce(func.sum(SantechTransaction.point_amount), 0).label("st_point"),
            func.coalesce(func.sum(SantechTransaction.cashback_amount), 0).label("st_cashback"),
        )
        .filter(SantechTransaction.user_id == user.id)
        .group_by(SantechTransaction.year_month)
        .all()
    )
    for item in santech_groups:
        row = rows.setdefault(item.year_month, _blank_month(item.year_month))
        for field in [
            "st_korean_air",
            "st_asiana",
            "st_hana_mile",
            "st_purchase",
            "st_refund",
            "st_profit",
            "st_point",
            "st_cashback",
        ]:
            row[field] += getattr(item, field) or 0

    cream_groups = (
        db.query(
            CreamTransaction.year_month,
            func.coalesce(func.sum(CreamTransaction.korean_air), 0).label("cr_korean_air"),
            func.coalesce(func.sum(CreamTransaction.asiana), 0).label("cr_asiana"),
            func.coalesce(func.sum(CreamTransaction.profit), 0).label("cr_profit"),
            func.coalesce(func.sum(CreamTransaction.buy_amount), 0).label("cr_buy_total"),
        )
        .filter(CreamTransaction.user_id == user.id)
        .group_by(CreamTransaction.year_month)
        .all()
    )
    for item in cream_groups:
        row = rows.setdefault(item.year_month, _blank_month(item.year_month))
        for field in ["cr_korean_air", "cr_asiana", "cr_profit", "cr_buy_total"]:
            row[field] += getattr(item, field) or 0

    return sorted((_finalize_month(row) for row in rows.values()), key=lambda item: item["year_month"], reverse=True)


def build_mileage_totals(db: Session, user: User, monthly_rows: list[dict] | None = None) -> dict:
    if monthly_rows is None:
        monthly_rows = build_monthly_rows(db, user)

    totals = {"korean_air": 0, "asiana": 0, "hana_mile": 0}

    for carry in db.query(MileageCarry).filter(MileageCarry.user_id == user.id).all():
        totals["korean_air"] += carry.korean_air or 0
        totals["asiana"] += carry.asiana or 0
        totals["hana_mile"] += carry.hana_mile or 0

    for row in monthly_rows:
        totals["korean_air"] += row["korean_air"]
        totals["asiana"] += row["asiana"]
        totals["hana_mile"] += row["hana_mile"]

    totals["total"] = totals["korean_air"] + totals["asiana"] + totals["hana_mile"]
    return totals


def _current_month() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m")


@router.get("/dashboard")
def get_dashboard(include_current_month: bool = Query(default=True), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    monthly_rows = build_monthly_rows(db, user)
    current_month = _current_month()
    current_row = next((row for row in monthly_rows if row["year_month"] == current_month), None)
    stats_rows = monthly_rows if include_current_month else [row for row in monthly_rows if row["year_month"] < current_month]

    total_st_profit = sum(row["st_profit"] for row in stats_rows)
    total_cr_profit = sum(row["cr_profit"] for row in stats_rows)
    miles = build_mileage_totals(db, user, stats_rows)

    return {
        "current_month": current_month,
        "include_current_month": include_current_month,
        "total_profit": total_st_profit + total_cr_profit,
        "current_month_profit": current_row["total_profit"] if current_row else 0,
        "total_st_profit": total_st_profit,
        "total_cr_profit": total_cr_profit,
        "miles": miles,
        "avg_mile_price": abs(total_st_profit) / miles["total"] if miles["total"] else 0,
    }


@router.get("/monthly")
def get_monthly(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return build_monthly_rows(db, user)
