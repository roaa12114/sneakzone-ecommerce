import { initializeApp } from "firebase/app";
import { getAuth, onAuthStateChanged } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyAxORvQ1MLg0MVWoRxvk9ei1Z5IXk-4T0o",
  authDomain: "sneakzone-c56f7.firebaseapp.com",
  projectId: "sneakzone-c56f7",
  storageBucket: "sneakzone-c56f7.appspot.com",
  messagingSenderId: "719265074871",
  appId: "1:719265074871:web:949fbbc21c2fea44104732",
  measurementId: "G-2R7779GDFF"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export { onAuthStateChanged }; // 👈 عشان نستخدمها في Navbar
