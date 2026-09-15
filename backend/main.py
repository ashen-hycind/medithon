from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from pathlib import Path
backend_env = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=backend_env, override=True)
load_dotenv(override=True)

from routes.users import router as users_router
from routes.measurements import router as measurements_router
from routes.analysis import router as analysis_router
from firebase_config import init_firebase

app = FastAPI(
    title="Personal Health Monitor API",
    description="Device-agnostic personal health monitoring and analytics platform",
    version="1.0.0"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firebase on startup
@app.on_event("startup")
async def startup_event():
    init_firebase()

@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "service": "Personal Health Monitor API"}

app.include_router(users_router)
app.include_router(measurements_router)
app.include_router(analysis_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
