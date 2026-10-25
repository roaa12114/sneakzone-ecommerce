import React, { useState } from 'react';
import { signInWithEmailAndPassword, sendPasswordResetEmail } from "firebase/auth";
import { auth } from "../firebase"; 
import { useNavigate, useLocation } from "react-router-dom";
import "./login.css"; // Importing CSS file



function Login() {

  // define state for username & password
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [resetMode, setResetMode] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  
  
  // handle login form submit
  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setInfo("");
    if (resetMode) {
      try {
        await sendPasswordResetEmail(auth, email);
        setInfo("Password reset email sent. Check your inbox.");
        setResetMode(false);
      } catch (err) {
        setError(err.message || "Could not send reset email.");
      }
      return;
    }
    try {
      await signInWithEmailAndPassword(auth, email, password);
      // Redirect back to where the user was trying to go (T11).
      // Falls back to /products if no `from` was passed.
      const from = location.state?.from?.pathname || "/products";
      navigate(from, { replace: true });
    } catch (err) {
      // Surface Firebase's own error text (e.g. "wrong password").
      setError(err.message || "Invalid email or password.");
    }
  };


  return (
    <div className="login-container">
      <h2 className="login-title">Login</h2>
      <form onSubmit={handleLogin}>
        <div className="form-group">
          <label>Email Address</label>
          <input 
            type="email"
            className="form-input"
            placeholder="Enter your email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label>Password</label>
          <input 
            type="password"
            className="form-input"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required={!resetMode}
          />
        </div>
        <button type="submit" className="login-btn">{resetMode ? "Send Reset Email" : "Login"}</button>
        <button
          type="button"
          className="login-btn"
          style={{ marginTop: "8px", background: "transparent", color: "#571414", border: "1px solid #571414" }}
          onClick={() => { setResetMode(!resetMode); setError(""); setInfo(""); }}
        >
          {resetMode ? "Back to Login" : "Forgot Password?"}
        </button>
        {error && <p style={{ color: "red" }}>{error}</p>}
        {info && <p style={{ color: "green" }}>{info}</p>}
      </form>
    </div>
  );
};

export default Login;