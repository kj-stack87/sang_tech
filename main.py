from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from auth import ensure_default_user, router as auth_router
from database import SessionLocal, engine, ensure_app_schema
from models import Base
from routers import cream, dashboard, mileage, santech
from seed import run_seed


Base.metadata.create_all(bind=engine)
ensure_app_schema(engine)

with SessionLocal() as db:
    run_seed(db)
    ensure_default_user(db)

app = FastAPI(title="상테크 & 리셀 실적 관리")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(santech.router)
app.include_router(cream.router)
app.include_router(mileage.router)
app.include_router(auth_router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")
