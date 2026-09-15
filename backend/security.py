from fastapi import Header, HTTPException, status, Depends
import os
from firebase_admin import auth
from firebase_config import init_firebase

init_firebase()

async def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Expected 'Bearer <firebase_token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ")[1]

    # Support development bypass token if explicitly configured for local offline testing
    if os.getenv("DEV_MODE", "false").lower() == "true" and token.startswith("dev-token-"):
        dev_uid = token.replace("dev-token-", "")
        return {"uid": dev_uid, "email": f"{dev_uid}@example.com"}

    try:
        decoded_token = auth.verify_id_token(token)
        return {
            "uid": decoded_token["uid"],
            "email": decoded_token.get("email", "")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired Firebase token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
