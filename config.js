import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyBz7KOdIxRMiAUSp4qcIGVU7TkgiPO7h1Q",
  authDomain: "daily-reflection-91e09.firebaseapp.com",
  projectId: "daily-reflection-91e09",
  storageBucket: "daily-reflection-91e09.firebasestorage.app",
  messagingSenderId: "170328982893",
  appId: "1:170328982893:web:2a769175ebd34e071c0664",
  measurementId: "G-VDR81SR617"
};

const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
export default app;
export const auth = getAuth(app);
