from collections import defaultdict

from models import CreamTransaction, MileageCarry, MonthlySummary, SantechCard, SantechTransaction


SANTECH_SEED = [
    {
        "year_month": "2026-02",
        "st_korean_air": 17451,
        "st_asiana": 1514,
        "st_hana_mile": 4956,
        "st_purchase": 56293300,
        "st_refund": 55688335,
        "st_profit": -193037,
        "st_point": 0,
        "st_cashback": 411928,
    },
    {
        "year_month": "2026-03",
        "st_korean_air": 3561,
        "st_asiana": 23187,
        "st_hana_mile": 53060,
        "st_purchase": 116644900,
        "st_refund": 115534003,
        "st_profit": -214693,
        "st_point": 0,
        "st_cashback": 896204,
    },
    {
        "year_month": "2026-04",
        "st_korean_air": 1669,
        "st_asiana": 1823,
        "st_hana_mile": 13014,
        "st_purchase": 39521000,
        "st_refund": 39176445,
        "st_profit": 76610,
        "st_point": 0,
        "st_cashback": 421165,
    },
    {
        "year_month": "2026-05",
        "st_korean_air": 4238,
        "st_asiana": 18708,
        "st_hana_mile": 16606,
        "st_purchase": 34184200,
        "st_refund": 33842739,
        "st_profit": -23641,
        "st_point": 27440,
        "st_cashback": 290380,
    },
    {
        "year_month": "2026-06",
        "st_korean_air": 3667,
        "st_asiana": 17385,
        "st_hana_mile": 49600,
        "st_purchase": 80055150,
        "st_refund": 79253349,
        "st_profit": -227841,
        "st_point": 377198,
        "st_cashback": 196762,
    },
]

CREAM_SEED = [
    {
        "year_month": "2026-01",
        "cr_hilton": 6330,
        "cr_korean_air": 0,
        "cr_asiana": 229,
        "cr_profit": -20763,
        "cr_buy_total": 5119600,
    },
    {
        "year_month": "2026-02",
        "cr_hilton": 6292,
        "cr_korean_air": 0,
        "cr_asiana": 0,
        "cr_profit": -19314,
        "cr_buy_total": 4742700,
    },
    {
        "year_month": "2026-03",
        "cr_hilton": 0,
        "cr_korean_air": 3561,
        "cr_asiana": 23187,
        "cr_profit": -595,
        "cr_buy_total": 19117532,
    },
    {
        "year_month": "2026-04",
        "cr_hilton": 0,
        "cr_korean_air": 1669,
        "cr_asiana": 1823,
        "cr_profit": 10690,
        "cr_buy_total": 2933000,
    },
    {
        "year_month": "2026-05",
        "cr_hilton": 0,
        "cr_korean_air": 4238,
        "cr_asiana": 18708,
        "cr_profit": 32906,
        "cr_buy_total": 16777300,
    },
    {
        "year_month": "2026-06",
        "cr_hilton": 0,
        "cr_korean_air": 3667,
        "cr_asiana": 17385,
        "cr_profit": -25494,
        "cr_buy_total": 15407900,
    },
]

MILEAGE_CARRY_SEED = []

SANTECH_CARD_SEED = [
    {
        "name": "MG",
        "benefit_type": "discount",
        "reward_rate": 10,
        "monthly_cap": 60000,
        "is_unlimited": 0,
    },
    {
        "name": "하나마일",
        "benefit_type": "mileage",
        "mileage_target": "hana_mile",
        "mileage_spend_amount": 1500,
        "mileage_earn_amount": 1.6,
        "is_unlimited": 1,
    },
    {
        "name": "any",
        "benefit_type": "discount",
        "reward_rate": 1.7,
        "monthly_cap": 100000,
        "is_unlimited": 0,
    },
    {
        "name": "원더",
        "benefit_type": "discount",
        "reward_rate": 1.2,
        "is_unlimited": 1,
    },
    {
        "name": "행복",
        "benefit_type": "cashback",
        "reward_rate": 1.5,
        "is_unlimited": 1,
    },
]

MONTHLY_FIELDS = [
    "st_korean_air",
    "st_asiana",
    "st_hana_mile",
    "st_purchase",
    "st_refund",
    "st_profit",
    "st_point",
    "st_cashback",
    "cr_hilton",
    "cr_korean_air",
    "cr_asiana",
    "cr_profit",
    "cr_buy_total",
]


def _empty_month(year_month: str) -> dict:
    data = {field: 0 for field in MONTHLY_FIELDS}
    data["year_month"] = year_month
    data["is_seed"] = 1
    return data


def seed_monthly_summary(db):
    merged = defaultdict(lambda: None)

    for item in SANTECH_SEED + CREAM_SEED:
        year_month = item["year_month"]
        if merged[year_month] is None:
            merged[year_month] = _empty_month(year_month)
        for key, value in item.items():
            if key != "year_month":
                merged[year_month][key] = value

    for year_month in sorted(merged):
        exists = db.query(MonthlySummary).filter(MonthlySummary.year_month == year_month).first()
        if exists:
            continue
        db.add(MonthlySummary(**merged[year_month]))

    db.commit()


def seed_mileage_carry(db):
    for item in MILEAGE_CARRY_SEED:
        exists = db.query(MileageCarry).filter(MileageCarry.year == item["year"]).first()
        if exists:
            continue
        db.add(MileageCarry(**item))
    db.commit()


def seed_santech_cards_for_user(db, user_id: int):
    for item in SANTECH_CARD_SEED:
        exists = db.query(SantechCard).filter(SantechCard.user_id == user_id, SantechCard.name == item["name"]).first()
        if exists:
            continue
        db.add(
            SantechCard(
                user_id=user_id,
                name=item["name"],
                benefit_type=item["benefit_type"],
                mileage_target=item.get("mileage_target", "hana_mile"),
                mileage_spend_amount=item.get("mileage_spend_amount", 0),
                mileage_earn_amount=item.get("mileage_earn_amount", 0),
                reward_rate=item.get("reward_rate", 0),
                monthly_cap=item.get("monthly_cap"),
                is_unlimited=item.get("is_unlimited", 1),
                created_at="seed",
            )
        )
    db.commit()


def purge_pre_2026_data(db):
    db.query(MonthlySummary).filter(MonthlySummary.year_month < "2026-01").delete(synchronize_session=False)
    db.query(SantechTransaction).filter(SantechTransaction.year_month < "2026-01").delete(synchronize_session=False)
    db.query(CreamTransaction).filter(CreamTransaction.year_month < "2026-01").delete(synchronize_session=False)
    db.query(MileageCarry).filter(MileageCarry.year < 2026).delete(synchronize_session=False)
    db.commit()


def run_seed(db):
    purge_pre_2026_data(db)
    seed_monthly_summary(db)
    seed_mileage_carry(db)
