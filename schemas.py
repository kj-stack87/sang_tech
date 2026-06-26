import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


SANTECH_PRODUCTS = {"신세계상품권", "북앤라이프", "컬쳐랜드", "틴캐시", "게임온패스"}
SANTECH_REFUND_VENDORS = {"포인트로페이", "페이즈", "마일캐시", "원천", "골드", "팔라고", "GLN"}
CARD_BENEFIT_TYPES = {"mileage", "cashback", "discount"}
MILEAGE_TARGETS = {"korean_air", "asiana", "hana_mile"}

CREAM_PLATFORMS = {"크림", "솔드아웃"}
CREAM_CARD_COMPANIES = {
    "신한 에어1.5",
    "삼성 스마",
    "삼성 항공",
    "기업 마일앤조이",
    "우리 인피니트",
}


def _strip_optional(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _validate_date(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("date must use YYYY-MM-DD")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("date must be a real calendar date") from exc
    return value


def _validate_non_negative(value: int) -> int:
    if value < 0:
        raise ValueError("amount and mileage fields must be 0 or more")
    return value


def _validate_choice(value: str, allowed: set[str], field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} is required")
    value = value.strip()
    if value not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise ValueError(f"{field_name} must be one of: {allowed_text}")
    return value


def _validate_free_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} is required")
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} is required")
    if len(value) > 40:
        raise ValueError(f"{field_name} must be 40 characters or fewer")
    return value


def _validate_card_name(value: str) -> str:
    return _validate_free_text(value, "card")


def _validate_email(value: Optional[str]) -> Optional[str]:
    value = _strip_optional(value)
    if value is None:
        return None
    if len(value) > 120:
        raise ValueError("email must be 120 characters or fewer")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        raise ValueError("email must be a valid email address")
    return value


class SantechCreate(BaseModel):
    date: str
    product: str
    refund_vendor: Optional[str] = None
    card: str
    purchase_amount: int
    refund_amount: int = 0
    point_amount: int = 0
    cashback_amount: int = 0
    korean_air: int = 0
    asiana: int = 0
    hana_mile: int = 0
    quantity: int = 1
    memo: Optional[str] = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        return _validate_date(value)

    @field_validator(
        "purchase_amount",
        "refund_amount",
        "point_amount",
        "cashback_amount",
        "korean_air",
        "asiana",
        "hana_mile",
    )
    @classmethod
    def validate_non_negative(cls, value: int) -> int:
        return _validate_non_negative(value)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: int) -> int:
        if value < 1:
            raise ValueError("quantity must be 1 or more")
        if value > 100:
            raise ValueError("quantity must be 100 or fewer")
        return value

    @field_validator("product")
    @classmethod
    def validate_product(cls, value: str) -> str:
        return _validate_choice(value, SANTECH_PRODUCTS, "product")

    @field_validator("card")
    @classmethod
    def validate_card(cls, value: str) -> str:
        return _validate_card_name(value)

    @field_validator("memo", mode="before")
    @classmethod
    def normalize_memo(cls, value):
        return _strip_optional(value)


class SantechUpdate(BaseModel):
    date: str
    product: str
    card: str
    purchase_amount: int
    refund_amount: int = 0
    refund_vendor: Optional[str] = None
    korean_air: int = 0
    asiana: int = 0
    memo: Optional[str] = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        return _validate_date(value)

    @field_validator("purchase_amount", "refund_amount", "korean_air", "asiana")
    @classmethod
    def validate_non_negative(cls, value: int) -> int:
        return _validate_non_negative(value)

    @field_validator("product")
    @classmethod
    def validate_product(cls, value: str) -> str:
        return _validate_choice(value, SANTECH_PRODUCTS, "product")

    @field_validator("card")
    @classmethod
    def validate_card(cls, value: str) -> str:
        return _validate_card_name(value)

    @field_validator("refund_vendor", mode="before")
    @classmethod
    def normalize_refund_vendor(cls, value):
        return _strip_optional(value)

    @field_validator("refund_vendor")
    @classmethod
    def validate_refund_vendor(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _validate_choice(value, SANTECH_REFUND_VENDORS, "refund_vendor")

    @field_validator("memo", mode="before")
    @classmethod
    def normalize_memo(cls, value):
        return _strip_optional(value)


class SantechResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: str
    year_month: str
    product: Optional[str]
    refund_vendor: Optional[str]
    card: Optional[str]
    purchase_amount: int
    refund_amount: int
    point_amount: int
    cashback_amount: int
    profit: int
    korean_air: int
    asiana: int
    hana_mile: int
    memo: Optional[str]
    created_at: Optional[str]


class SantechRefundUpdate(BaseModel):
    refund_amount: int
    refund_vendor: str

    @field_validator("refund_amount")
    @classmethod
    def validate_non_negative(cls, value: int) -> int:
        return _validate_non_negative(value)

    @field_validator("refund_vendor")
    @classmethod
    def validate_refund_vendor(cls, value: str) -> str:
        return _validate_choice(value, SANTECH_REFUND_VENDORS, "refund_vendor")


class SantechCardCreate(BaseModel):
    name: str
    benefit_type: str
    mileage_target: str = "hana_mile"
    mileage_spend_amount: int = 0
    mileage_earn_amount: float = 0
    reward_rate: float = 0
    monthly_cap: Optional[int] = None
    is_unlimited: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_card_name(value)

    @field_validator("benefit_type")
    @classmethod
    def validate_benefit_type(cls, value: str) -> str:
        return _validate_choice(value, CARD_BENEFIT_TYPES, "benefit_type")

    @field_validator("mileage_target")
    @classmethod
    def validate_mileage_target(cls, value: str) -> str:
        return _validate_choice(value, MILEAGE_TARGETS, "mileage_target")

    @field_validator("mileage_spend_amount")
    @classmethod
    def validate_mileage_spend_amount(cls, value: int) -> int:
        return _validate_non_negative(value)

    @field_validator("mileage_earn_amount", "reward_rate")
    @classmethod
    def validate_non_negative_float(cls, value: float) -> float:
        if value < 0:
            raise ValueError("benefit values must be 0 or more")
        return value

    @field_validator("monthly_cap")
    @classmethod
    def validate_monthly_cap(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        return _validate_non_negative(value)

    @model_validator(mode="after")
    def validate_benefit_fields(self):
        if self.benefit_type == "mileage":
            if self.mileage_spend_amount <= 0 or self.mileage_earn_amount <= 0:
                raise ValueError("mileage cards require spend amount and earned mileage")
            self.reward_rate = 0
            self.monthly_cap = None
            self.is_unlimited = True
            return self

        if self.reward_rate <= 0:
            raise ValueError("cashback and discount cards require a positive reward rate")
        self.mileage_spend_amount = 0
        self.mileage_earn_amount = 0
        self.mileage_target = "hana_mile"
        if self.is_unlimited:
            self.monthly_cap = None
        elif self.monthly_cap is None or self.monthly_cap <= 0:
            raise ValueError("limited cashback and discount cards require a positive monthly cap")
        return self


class SantechCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    benefit_type: str
    mileage_target: str
    mileage_spend_amount: int
    mileage_earn_amount: float
    reward_rate: float
    monthly_cap: Optional[int]
    is_unlimited: bool
    created_at: Optional[str]


class AuthRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = _validate_free_text(value, "username")
        if len(value) < 3:
            raise ValueError("username must be at least 3 characters")
        if len(value) > 40:
            raise ValueError("username must be 40 characters or fewer")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not isinstance(value, str) or len(value) < 4:
            raise ValueError("password must be at least 4 characters")
        if len(value) > 120:
            raise ValueError("password must be 120 characters or fewer")
        return value


class DailyEmailSettingsUpdate(BaseModel):
    email: Optional[str] = None
    enabled: bool = False

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, value):
        return _validate_email(value)

    @model_validator(mode="after")
    def validate_enabled_email(self):
        if self.enabled and not self.email:
            raise ValueError("email is required when daily email is enabled")
        return self


class CreamCreate(BaseModel):
    date: str
    platform: str
    card_company: str
    buy_amount: int
    sell_amount: int
    payback_amount: int = 0
    korean_air: int = 0
    asiana: int = 0
    condition: Optional[str] = None
    memo: Optional[str] = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        return _validate_date(value)

    @field_validator(
        "buy_amount",
        "sell_amount",
        "payback_amount",
        "korean_air",
        "asiana",
    )
    @classmethod
    def validate_non_negative(cls, value: int) -> int:
        return _validate_non_negative(value)

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: str) -> str:
        return _validate_choice(value, CREAM_PLATFORMS, "platform")

    @field_validator("card_company")
    @classmethod
    def validate_card_company(cls, value: str) -> str:
        return _validate_choice(value, CREAM_CARD_COMPANIES, "card_company")

    @field_validator("condition", "memo", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _strip_optional(value)


class CreamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: str
    year_month: str
    platform: str
    card_company: Optional[str]
    buy_amount: int
    sell_amount: int
    payback_amount: int
    profit: int
    korean_air: int
    asiana: int
    condition: Optional[str]
    memo: Optional[str]
    created_at: Optional[str]
