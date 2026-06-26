import json
import os
import smtplib
import socket
from datetime import datetime
from email.message import EmailMessage
from urllib import error as urlerror
from urllib import request as urlrequest
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import DailyEmailSetting, User
from routers.dashboard import build_mileage_totals, build_monthly_rows
from schemas import DailyEmailSettingsUpdate


router = APIRouter(prefix="/api", tags=["email-reports"])


def _create_ipv4_connection(host: str, port: int, timeout, source_address=None):
    last_error = None
    for family, socktype, proto, _canonname, sockaddr in socket.getaddrinfo(
        host,
        port,
        socket.AF_INET,
        socket.SOCK_STREAM,
    ):
        sock = None
        try:
            sock = socket.socket(family, socktype, proto)
            if timeout is not None:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sockaddr)
            return sock
        except OSError as exc:
            last_error = exc
            if sock is not None:
                sock.close()
    if last_error is not None:
        raise last_error
    raise OSError(f"{host}:{port}의 IPv4 주소를 찾지 못했습니다.")


class IPv4SMTP(smtplib.SMTP):
    def _get_socket(self, host, port, timeout):
        if self.debuglevel > 0:
            self._print_debug("connect:", (host, port))
        return _create_ipv4_connection(host, port, timeout, self.source_address)


def _today() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")


def _now() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")


def _format_number(value) -> str:
    return f"{int(round(value or 0)):,}"


def _format_won(value) -> str:
    number = int(round(value or 0))
    sign = "-" if number < 0 else ""
    return f"{sign}{abs(number):,}원"


def _format_profit(value) -> str:
    number = int(round(value or 0))
    if number > 0:
        return f"+{_format_won(number)}"
    return _format_won(number)


def _serialize_setting(row: DailyEmailSetting | None) -> dict:
    return {
        "email": row.email if row else None,
        "enabled": bool(row.enabled) if row else False,
        "last_sent_on": row.last_sent_on if row else None,
    }


def _get_or_create_setting(db: Session, user_id: int) -> DailyEmailSetting:
    row = db.query(DailyEmailSetting).filter(DailyEmailSetting.user_id == user_id).first()
    if row is None:
        row = DailyEmailSetting(user_id=user_id, enabled=0, updated_at=_now())
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _smtp_config() -> dict:
    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM") or username
    if not host or not username or not password or not sender:
        raise HTTPException(status_code=500, detail="SMTP 환경변수가 설정되지 않았습니다.")
    return {
        "host": host,
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": username,
        "password": password,
        "sender": sender,
        "starttls": os.getenv("SMTP_STARTTLS", "true").lower() != "false",
        "force_ipv4": os.getenv("SMTP_FORCE_IPV4", "true").lower() != "false",
    }


def _resend_config() -> dict | None:
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        return None
    return {
        "api_key": api_key,
        "sender": os.getenv("RESEND_FROM") or "Santech Report <onboarding@resend.dev>",
    }


def _compose_report(db: Session, user: User) -> tuple[str, str]:
    monthly_rows = build_monthly_rows(db, user)
    current_month = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m")
    current = next((row for row in monthly_rows if row["year_month"] == current_month), None)
    totals = build_mileage_totals(db, user, monthly_rows)
    total_profit = sum(row["total_profit"] for row in monthly_rows)
    total_st_profit = sum(row["st_profit"] for row in monthly_rows)
    total_cr_profit = sum(row["cr_profit"] for row in monthly_rows)

    lines = [
        f"{user.username}님의 상테크 & 리셀 일일 리포트",
        f"기준일: {_today()}",
        "",
        "[누적 요약]",
        f"- 누적 총 수익: {_format_profit(total_profit)}",
        f"- 상테크 수익: {_format_profit(total_st_profit)}",
        f"- 리셀 수익: {_format_profit(total_cr_profit)}",
        f"- 누적 마일리지: {_format_number(totals['total'])} mi",
        f"  대한항공 {_format_number(totals['korean_air'])} / 아시아나 {_format_number(totals['asiana'])} / 하나마일 {_format_number(totals['hana_mile'])}",
        "",
        f"[{current_month} 요약]",
    ]
    if current:
        lines.extend(
            [
                f"- 총 수익: {_format_profit(current['total_profit'])}",
                f"- 상테크 매매: {_format_won(current['st_purchase'])}",
                f"- 상테크 환급: {_format_won(current['st_refund'])}",
                f"- 상테크 수익: {_format_profit(current['st_profit'])}",
                f"- 리셀 수익: {_format_profit(current['cr_profit'])}",
                f"- 마일리지: {_format_number(current['total_miles'])} mi",
            ]
        )
    else:
        lines.append("- 이번 달 데이터가 아직 없습니다.")

    recent_rows = monthly_rows[:6]
    if recent_rows:
        lines.extend(["", "[최근 월별 요약]"])
        for row in recent_rows:
            lines.append(
                f"- {row['year_month']}: 총 {_format_profit(row['total_profit'])}, "
                f"상테크 {_format_profit(row['st_profit'])}, 리셀 {_format_profit(row['cr_profit'])}, "
                f"마일 {_format_number(row['total_miles'])} mi"
            )

    subject = f"[상테크 리포트] {_today()} 일일 요약"
    return subject, "\n".join(lines)


def _send_resend_email(to_email: str, subject: str, body: str, config: dict):
    payload = json.dumps(
        {
            "from": config["sender"],
            "to": [to_email],
            "subject": subject,
            "text": body,
        }
    ).encode("utf-8")
    request = urlrequest.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
            "User-Agent": "santech-manager/1.0",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(request, timeout=30) as response:
            if response.status < 200 or response.status >= 300:
                detail = response.read().decode("utf-8", errors="replace")
                raise HTTPException(status_code=502, detail=f"Resend 메일 발송 실패: {detail}")
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"Resend 메일 발송 실패: {detail}") from exc
    except urlerror.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Resend 연결에 실패했습니다: {exc.reason}") from exc


def _send_email(to_email: str, subject: str, body: str):
    resend_config = _resend_config()
    if resend_config is not None:
        _send_resend_email(to_email, subject, body, resend_config)
        return

    config = _smtp_config()
    message = EmailMessage()
    message["From"] = config["sender"]
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    smtp_class = IPv4SMTP if config["force_ipv4"] else smtplib.SMTP
    try:
        with smtp_class(config["host"], config["port"], timeout=30) as smtp:
            if config["starttls"]:
                smtp.starttls()
            smtp.login(config["username"], config["password"])
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise HTTPException(status_code=502, detail=f"메일 서버 연결에 실패했습니다: {exc}") from exc


def _send_report_for_user(db: Session, user: User, setting: DailyEmailSetting, force: bool = False) -> str:
    if not setting.enabled or not setting.email:
        return "disabled"
    today = _today()
    if not force and setting.last_sent_on == today:
        return "skipped"
    subject, body = _compose_report(db, user)
    _send_email(setting.email, subject, body)
    setting.last_sent_on = today
    setting.updated_at = _now()
    db.commit()
    return "sent"


@router.get("/email-settings")
def get_email_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _serialize_setting(_get_or_create_setting(db, user.id))


@router.patch("/email-settings")
def update_email_settings(payload: DailyEmailSettingsUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = _get_or_create_setting(db, user.id)
    row.email = payload.email
    row.enabled = 1 if payload.enabled else 0
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return _serialize_setting(row)


@router.post("/email-settings/test")
def send_test_email(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = _get_or_create_setting(db, user.id)
    if not row.email:
        raise HTTPException(status_code=422, detail="메일 주소를 먼저 저장해주세요.")
    subject, body = _compose_report(db, user)
    _send_email(row.email, f"[테스트] {subject}", body)
    return {"ok": True}


@router.post("/tasks/daily-email")
def send_daily_email_task(x_cron_secret: str | None = Header(default=None), db: Session = Depends(get_db)):
    secret = os.getenv("SANTECH_CRON_SECRET")
    if not secret or x_cron_secret != secret:
        raise HTTPException(status_code=401, detail="인증되지 않은 작업 요청입니다.")

    rows = db.query(DailyEmailSetting).filter(DailyEmailSetting.enabled == 1).all()
    result = {"sent": 0, "skipped": 0, "disabled": 0, "failed": 0}
    errors = []
    for setting in rows:
        user = db.get(User, setting.user_id)
        if user is None:
            result["disabled"] += 1
            continue
        try:
            status = _send_report_for_user(db, user, setting)
            result[status] += 1
        except Exception as exc:
            result["failed"] += 1
            errors.append({"user_id": user.id, "error": str(exc)})
    return {"ok": result["failed"] == 0, "result": result, "errors": errors}
