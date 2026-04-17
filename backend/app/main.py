from fastapi import FastAPI

from app.api.routes import router as api_router


app = FastAPI(title="Minimal FastAPI Backend")
app.include_router(api_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Backend is running"}
