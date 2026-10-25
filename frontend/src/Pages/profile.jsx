import React, { useEffect, useState } from "react";
import { auth, db, onAuthStateChanged } from "../firebase";
import { doc, getDoc, updateDoc } from "firebase/firestore";
import {
  updateProfile,
  updatePassword,
  verifyBeforeUpdateEmail,
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

    const wantsEmailChange = newEmail && newEmail !== user.email;
    const wantsPasswordChange = !!newPassword;
    // Email and password changes are sensitive: require reauth.
    if ((wantsEmailChange || wantsPasswordChange) && !currentPassword) {
      alert("Please enter your current password to change email or password.");
      return;
    }

    try {
      // 1) Reauth FIRST if any sensitive change requested.
      if (currentPassword) {
        const cred = EmailAuthProvider.credential(user.email, currentPassword);
        await reauthenticateWithCredential(user, cred);
      }

      // 2) Auth writes first (cheap; no email change yet).
      if (newName) {
        await updateProfile(user, { displayName: newName });
      }
      if (wantsPasswordChange) {
        await updatePassword(user, newPassword);
      }
      if (wantsEmailChange) {
        // verifyBeforeUpdateEmail sends a verification link to the NEW
        // address. The actual email change happens when the user clicks
        // it. This replaces the deprecated updateEmail.
        await verifyBeforeUpdateEmail(user, newEmail);
      }

      // 3) Firestore LAST — only if all Auth writes succeeded.
      await updateDoc(doc(db, "users", user.uid), { name: newName });

      alert(
        wantsEmailChange
          ? "✅ Profile updated. Check your NEW email inbox to confirm the email change."
          : "✅ Profile updated successfully!"
      );
      setCurrentPassword("");
      setNewPassword("");
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