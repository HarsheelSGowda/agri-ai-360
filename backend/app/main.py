from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, dashboard, farms, history, models_router, predict, risk, weather, yield_router
from app.core.config import settings
from app.database.base import Base
from app.database.session import engine
from app.models import *  # noqa: F401,F403  (registers all ORM models with Base metadata)

app = FastAPI(
    title="AgriAI 360 API",
    description="Explainable AI-Powered Intelligent Crop Recommendation and Farm Decision Support System",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": exc.errors()})


@app.get("/health")
def health():
    return {"status": "ok", "service": "agri-ai-360-backend"}


app.include_router(auth.router, prefix="/api")
app.include_router(farms.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(predict.router, prefix="/api")
app.include_router(models_router.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(risk.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(yield_router.router, prefix="/api")
