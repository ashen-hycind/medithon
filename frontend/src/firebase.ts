import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyC2uYAsKZw9_7XSiU26Gx_0Ue7VrNyuGo0",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "v-medithon.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "v-medithon",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "v-medithon.firebasestorage.app",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "632360377954",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:632360377954:web:41257cc981d0ef2d4cfb3b"
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
