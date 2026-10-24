import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from app.api import router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.services import seed_database, sync_official_details


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_database(db)
        sync_official_details(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API phân tích chiến thuật Liên Quân với điểm số có thể giải thích.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

requests_by_ip: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path == "/api/health":
        return await call_next(request)
    now = time.monotonic()
    ip = request.client.host if request.client else "unknown"
    bucket = requests_by_ip[ip]
    while bucket and bucket[0] < now - 60:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_per_minute:
        return JSONResponse(status_code=429, content={"error": {"code": "rate_limited", "message": "Bạn thao tác quá nhanh, vui lòng thử lại sau."}})
    bucket.append(now)
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "Dữ liệu gửi lên không hợp lệ", "details": jsonable_encoder(exc.errors())}})


@app.exception_handler(Exception)
async def unexpected_error(_: Request, exc: Exception):
    if settings.app_env == "development":
        detail = str(exc)
    else:
        detail = "Lỗi máy chủ nội bộ"
    return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": detail}})


app.include_router(router)


@app.get("/")
def root():
    return {"name": settings.app_name, "docs": "/docs", "health": "/api/health"}

