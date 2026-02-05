from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.health import router as health_router

app = FastAPI(title="AI Judge API")

app.include_router(health_router)
app.include_router(auth_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello, FastAPI!"}
