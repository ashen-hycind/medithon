import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIzaSyC2uYAsKZw9_7XSiU26Gx_0Ue7VrNyuGo0",
  authDomain: "v-medithon.firebaseapp.com",
  projectId: "v-medithon",
  storageBucket: "v-medithon.firebasestorage.app",
  messagingSenderId: "632360377954",
  appId: "1:632360377954:web:41257cc981d0ef2d4cfb3b"
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
