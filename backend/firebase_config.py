import os
import firebase_admin
from firebase_admin import credentials, firestore, auth

firebase_app = None
db = None

def init_firebase():
    global firebase_app, db
    if firebase_app is not None:
        return db

    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
    
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_app = firebase_admin.initialize_app(cred)
        print(f"Firebase Admin initialized using service account: {cred_path}")
    else:
        # Fallback to default credentials or application default
        try:
            firebase_app = firebase_admin.initialize_app()
            print("Firebase Admin initialized with default credentials.")
        except Exception as e:
            print(f"Warning: Firebase credentials not found. Set FIREBASE_CREDENTIALS_PATH or GOOGLE_APPLICATION_CREDENTIALS: {e}")

    try:
        db = firestore.client()
    except Exception as e:
        print(f"Warning: Firestore client could not be initialized: {e}")
        db = None
        
    return db

def get_firestore_db():
    global db
    if db is None:
        return init_firebase()
    return db
