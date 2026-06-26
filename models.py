from sqlalchemy import Column, Float, Integer, Text

from database import Base


class MonthlySummary(Base):
    __tablename__ = "monthly_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year_month = Column(Text, nullable=False, unique=True, index=True)
    st_korean_air = Column("st_대한항공", Integer, default=0)
    st_asiana = Column("st_아시아나", Integer, default=0)
    st_hana_mile = Column("st_하나마일", Integer, default=0)
    st_purchase = Column("st_매매", Integer, default=0)
    st_refund = Column("st_환급", Integer, default=0)
    st_profit = Column("st_수익", Integer, default=0)
    st_point = Column("st_적립", Integer, default=0)
    st_cashback = Column("st_청구할인", Integer, default=0)
    cr_hilton = Column("cr_힐튼", Integer, default=0)
    cr_korean_air = Column("cr_대한항공", Integer, default=0)
    cr_asiana = Column("cr_아시아나", Integer, default=0)
    cr_profit = Column("cr_수익", Integer, default=0)
    cr_buy_total = Column("cr_구매합계", Integer, default=0)
    is_seed = Column(Integer, default=0)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(Text, nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    is_seed_owner = Column(Integer, default=0)
    created_at = Column(Text)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_hash = Column(Text, nullable=False, unique=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    created_at = Column(Text)
    expires_at = Column(Text)


class SantechTransaction(Base):
    __tablename__ = "santech_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Text, nullable=False, index=True)
    year_month = Column(Text, nullable=False, index=True)
    purchase_amount = Column("매매", Integer, nullable=False)
    refund_amount = Column("환급", Integer, nullable=False)
    point_amount = Column("포인트", Integer, default=0)
    cashback_amount = Column("캐시백", Integer, default=0)
    profit = Column("수익", Integer, nullable=False)
    product = Column("구매상품", Text)
    refund_vendor = Column("환급처", Text)
    card = Column("카드", Text)
    korean_air = Column("대한항공", Integer, default=0)
    asiana = Column("아시아나", Integer, default=0)
    hana_mile = Column("하나마일", Integer, default=0)
    gift_amount = Column("상품권", Integer, default=0)
    memo = Column("메모", Text)
    created_at = Column(Text)
    user_id = Column(Integer, index=True)


class SantechCard(Base):
    __tablename__ = "santech_card_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(Text, nullable=False, index=True)
    benefit_type = Column(Text, nullable=False)
    mileage_target = Column(Text, default="hana_mile")
    mileage_spend_amount = Column(Integer, default=0)
    mileage_earn_amount = Column(Float, default=0)
    reward_rate = Column(Float, default=0)
    monthly_cap = Column(Integer, nullable=True)
    is_unlimited = Column(Integer, default=1)
    created_at = Column(Text)


class CreamTransaction(Base):
    __tablename__ = "cream_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Text, nullable=False, index=True)
    year_month = Column(Text, nullable=False, index=True)
    platform = Column("플랫폼", Text, nullable=False)
    buy_amount = Column("구매", Integer, nullable=False)
    sell_amount = Column("판매", Integer, nullable=False)
    payback_amount = Column("페이백", Integer, default=0)
    profit = Column("수익", Integer, nullable=False)
    condition = Column("조건", Text)
    card_company = Column("카드사", Text)
    hilton = Column("힐튼", Integer, default=0)
    korean_air = Column("대한항공", Integer, default=0)
    asiana = Column("아시아나", Integer, default=0)
    memo = Column("메모", Text)
    created_at = Column(Text)
    user_id = Column(Integer, index=True)


class MileageCarry(Base):
    __tablename__ = "mileage_carry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, unique=True, index=True)
    korean_air = Column("대한항공", Integer, default=0)
    asiana = Column("아시아나", Integer, default=0)
    hana_mile = Column("하나마일", Integer, default=0)
    hilton = Column("힐튼", Integer, default=0)
    user_id = Column(Integer, index=True)
