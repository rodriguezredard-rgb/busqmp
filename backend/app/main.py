from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import DEBUG, FRONTEND_URL
from app.routers.opportunities import router as opportunities_router
from app.routers.sync import router as sync_router
from app.routers.profiles import router as profiles_router
from app.routers.cron import router as cron_router

app = FastAPI(title="Peken v2.0", version="2.0.0", description="Buscador de oportunidades de mercado público y compras ágiles")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

app.include_router(opportunities_router)
app.include_router(sync_router)
app.include_router(profiles_router)
app.include_router(cron_router)


@app.get("/health")
def health():
    return {"status": "ok", "debug": DEBUG}
