import React, { useState } from 'react';
import { signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "../firebase"; 
import { useNavigate } from "react-router-dom";
import "./login.css"; // Importing CSS file



function Login() {

  // define state for username & password
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  
  
  // handle login form submit
  const handleLogin = async (e) => {
    e.preventDefault();
    try {
        await signInWithEmailAndPassword(auth, email, password);
        alert("Logged in successfully");
        navigate("/products");
      } catch(err){
        setError("Invalid email or password. Please try again");
        console.error(err.message);
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
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <button type="submit" className="login-btn">Login</button>
        {error && <p style={{ color: "red" }}>{error}</p>}
      </form>
    </div>
  );
};

export default Login;