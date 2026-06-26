from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import CreamTransaction, MileageCarry, MonthlySummary, SantechTransaction, User


router = APIRouter(prefix="/api", tags=["mileage"])


def _current_month() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m")


def _blank_year() -> dict:
    return {"korean_air": 0, "asiana": 0, "hana_mile": 0}


def _add(target: dict, korean_air=0, asiana=0, hana_mile=0):
    target["korean_air"] += korean_air or 0
    target["asiana"] += asiana or 0
    target["hana_mile"] += hana_mile or 0


def _build_by_year(db: Session, user: User, include_current_month: bool = True) -> list[dict]:
    by_year = defaultdict(_blank_year)
    current_month = _current_month()

    for carry in db.query(MileageCarry).filter(MileageCarry.user_id == user.id).all():
        _add(
            by_year[carry.year],
            korean_air=carry.korean_air,
            asiana=carry.asiana,
            hana_mile=carry.hana_mile,
        )

    if user.is_seed_owner:
        monthly_query = db.query(MonthlySummary)
        if not include_current_month:
            monthly_query = monthly_query.filter(MonthlySummary.year_month < current_month)
        for row in monthly_query.all():
            year = int(row.year_month[:4])
            _add(
                by_year[year],
                korean_air=(row.st_korean_air or 0) + (row.cr_korean_air or 0),
                asiana=(row.st_asiana or 0) + (row.cr_asiana or 0),
                hana_mile=row.st_hana_mile,
            )

    santech_query = db.query(SantechTransaction).filter(SantechTransaction.user_id == user.id)
    if not include_current_month:
        santech_query = santech_query.filter(SantechTransaction.year_month < current_month)
    for row in santech_query.all():
        _add(
            by_year[int(row.year_month[:4])],
            korean_air=row.korean_air,
            asiana=row.asiana,
            hana_mile=row.hana_mile,
        )

    cream_query = db.query(CreamTransaction).filter(CreamTransaction.user_id == user.id)
    if not include_current_month:
        cream_query = cream_query.filter(CreamTransaction.year_month < current_month)
    for row in cream_query.all():
        _add(
            by_year[int(row.year_month[:4])],
            korean_air=row.korean_air,
            asiana=row.asiana,
        )

    rows = []
    for year in sorted(by_year.keys(), reverse=True):
        item = {"year": year, **by_year[year]}
        item["total"] = item["korean_air"] + item["asiana"] + item["hana_mile"]
        rows.append(item)
    return rows


@router.get("/mileage")
def get_mileage(include_current_month: bool = Query(default=True), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    by_year = _build_by_year(db, user, include_current_month=include_current_month)
    totals = {"korean_air": 0, "asiana": 0, "hana_mile": 0}

    for row in by_year:
        totals["korean_air"] += row["korean_air"]
        totals["asiana"] += row["asiana"]
        totals["hana_mile"] += row["hana_mile"]

    totals["total"] = totals["korean_air"] + totals["asiana"] + totals["hana_mile"]
    return {
        "totals": totals,
        "by_year": by_year,
        "default_unit_price": 5,
        "include_current_month": include_current_month,
    }
