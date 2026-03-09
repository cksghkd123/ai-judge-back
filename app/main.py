from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.judge import router as judge_router
from app.api.me import router as me_router

app = FastAPI(title="AI Judge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(me_router)
app.include_router(judge_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello, FastAPI!"}
