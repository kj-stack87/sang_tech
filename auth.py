import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import CreamTransaction, SantechTransaction, User, UserSession
from schemas import AuthRequest
from seed import seed_santech_cards_for_user


SESSION_COOKIE = "santech_session"
SESSION_DAYS = 30

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return f"pbkdf2_sha256${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        method, salt_text, digest_text = stored.split("$", 2)
    except ValueError:
        return False
    if method != "pbkdf2_sha256":
        return False
    salt = base64.b64decode(salt_text.encode())
    expected = base64.b64decode(digest_text.encode())
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return secrets.compare_digest(actual, expected)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "is_seed_owner": bool(user.is_seed_owner),
    }


def _first_seed_owner_missing(db: Session) -> bool:
    return (db.query(func.count(User.id)).filter(User.is_seed_owner == 1).scalar() or 0) == 0


def _create_user(db: Session, username: str, password: str, is_seed_owner: bool) -> User:
    user = User(
        username=username,
        password_hash=_hash_password(password),
        is_seed_owner=1 if is_seed_owner else 0,
        created_at=_now().isoformat(timespec="seconds"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    seed_santech_cards_for_user(db, user.id)
    if user.is_seed_owner:
        _assign_legacy_rows(db, user.id)
    return user


def ensure_default_user(db: Session):
    username = os.getenv("SANTECH_DEFAULT_USERNAME", "sago87").strip()
    password = os.getenv("SANTECH_DEFAULT_PASSWORD")
    if not username or not password:
        return
    user = db.query(User).filter(User.username == username).first()
    if user:
        user.password_hash = _hash_password(password)
        if _first_seed_owner_missing(db):
            user.is_seed_owner = 1
        db.commit()
        db.refresh(user)
        seed_santech_cards_for_user(db, user.id)
        if user.is_seed_owner:
            _assign_legacy_rows(db, user.id)
        return
    _create_user(db, username, password, is_seed_owner=_first_seed_owner_missing(db))


def _matches_default_credentials(username: str, password: str) -> bool:
    default_username = os.getenv("SANTECH_DEFAULT_USERNAME", "sago87").strip()
    default_password = os.getenv("SANTECH_DEFAULT_PASSWORD")
    return bool(default_username and default_password and username == default_username and password == default_password)


def _set_session_cookie(response: Response, token: str):
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_DAYS * 24 * 60 * 60,
    )


def _clear_session_cookie(response: Response):
    response.delete_cookie(SESSION_COOKIE)


def _create_session(db: Session, response: Response, user: User):
    token = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(days=SESSION_DAYS)
    db.add(
        UserSession(
            token_hash=_hash_token(token),
            user_id=user.id,
            created_at=_now().isoformat(timespec="seconds"),
            expires_at=expires_at.isoformat(timespec="seconds"),
        )
    )
    db.commit()
    _set_session_cookie(response, token)


def _assign_legacy_rows(db: Session, user_id: int):
    db.query(SantechTransaction).filter(SantechTransaction.user_id.is_(None)).update(
        {"user_id": user_id},
        synchronize_session=False,
    )
    db.query(CreamTransaction).filter(CreamTransaction.user_id.is_(None)).update(
        {"user_id": user_id},
        synchronize_session=False,
    )
    db.commit()


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> User:
    if not session_token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    session = db.query(UserSession).filter(UserSession.token_hash == _hash_token(session_token)).first()
    if session is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    if session.expires_at and datetime.fromisoformat(session.expires_at) < _now():
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다.")
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return user


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return _serialize_user(user)


@router.post("/register")
def register(payload: AuthRequest, response: Response, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username == payload.username).first()
    if exists:
        raise HTTPException(status_code=409, detail="이미 사용 중인 ID입니다.")

    user = _create_user(db, payload.username, payload.password, is_seed_owner=_first_seed_owner_missing(db))

    _create_session(db, response, user)
    return _serialize_user(user)


@router.post("/login")
def login(payload: AuthRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None and _matches_default_credentials(payload.username, payload.password):
        user = _create_user(db, payload.username, payload.password, is_seed_owner=_first_seed_owner_missing(db))

    password_ok = bool(user and _verify_password(payload.password, user.password_hash))
    if user and not password_ok and _matches_default_credentials(payload.username, payload.password):
        user.password_hash = _hash_password(payload.password)
        if _first_seed_owner_missing(db):
            user.is_seed_owner = 1
        db.commit()
        db.refresh(user)
        password_ok = True

    if user is None or not password_ok:
        raise HTTPException(status_code=401, detail="ID 또는 비밀번호가 올바르지 않습니다.")

    seed_santech_cards_for_user(db, user.id)
    if user.is_seed_owner:
        _assign_legacy_rows(db, user.id)

    _create_session(db, response, user)
    return _serialize_user(user)


@router.post("/logout")
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
):
    if session_token:
        session = db.query(UserSession).filter(UserSession.token_hash == _hash_token(session_token)).first()
        if session:
            db.delete(session)
            db.commit()
    _clear_session_cookie(response)
    return {"ok": True}
