import React, { useEffect, useState } from "react";
import { auth, db, onAuthStateChanged } from "../firebase";
import { doc, getDoc, updateDoc } from "firebase/firestore";
import {
  updateProfile,
  updatePassword,
  updateEmail,
  signOut,
  reauthenticateWithCredential,
  EmailAuthProvider,
} from "firebase/auth";
import "./profile.css";

function Profile() {
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        const docRef = doc(db, "users", user.uid);
        const docSnap = await getDoc(docRef);

        if (docSnap.exists()) {
          setNewName(docSnap.data().name);
          setNewEmail(user.email);
        }
      }
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const handleUpdate = async () => {
    const user = auth.currentUser;
    if (!user) return alert("No user logged in!");

    try {
      // لو المستخدم بيغيّر الإيميل أو الباسورد لازم نعمل إعادة مصادقة
      if (currentPassword) {
        const cred = EmailAuthProvider.credential(user.email, currentPassword);
        await reauthenticateWithCredential(user, cred);
      }

      // تحديث الاسم في Firestore
      await updateDoc(doc(db, "users", user.uid), { name: newName });

      // تحديث الإيميل
      if (newEmail && newEmail !== user.email) {
        await updateEmail(user, newEmail);
      }

      // تحديث الباسورد
      if (newPassword) {
        await updatePassword(user, newPassword);
      }

      // تحديث الاسم في Firebase Auth
      await updateProfile(user, { displayName: newName });

      alert("✅ Profile updated successfully!");
    } catch (error) {
      console.error("Error updating profile: ", error);
      alert(`⚠️ ${error.message}`);
    }
  };

  const handleLogout = async () => {
    await signOut(auth);
    window.location.href = "/login";
  };

  if (loading) return <p>Loading profile...</p>;

  return (
    <div className="profile-container">
      <h2>👤 My Profile</h2>
      <div className="profile-form">
        <label>Name</label>
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
        />

        <label>Email</label>
        <input
          type="email"
          value={newEmail}
          onChange={(e) => setNewEmail(e.target.value)}
        />

        <label>Current Password</label>
        <input
          type="password"
          placeholder="Enter current password"
          onChange={(e) => setCurrentPassword(e.target.value)}
        />

        <label>New Password</label>
        <input
          type="password"
          placeholder="Enter new password"
          onChange={(e) => setNewPassword(e.target.value)}
        />

        <button onClick={handleUpdate}>Update Profile</button>
        <button className="logout-btn" onClick={handleLogout}>
          Logout
        </button>
      </div>
    </div>
  );
}

export default Profile;