from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.judge import router as judge_router
from app.api.me import router as me_router

app = FastAPI(title="AI Judge API")

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(me_router)
app.include_router(judge_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello, FastAPI!"}
