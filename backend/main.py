from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

from routes.users import router as users_router
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
