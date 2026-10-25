import React from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import NavigationBar from "./components/navBar.jsx";
import Home from "./Pages/home";
import Login from "./Pages/login.jsx";
import Signup from "./Pages/signUp.jsx";
import Profile from "./Pages/profile";
import Products from "./Pages/products.jsx";
import ProductDetails from "./Pages/productDetails.jsx";
import Cart from "./Pages/cart.jsx";
import Checkout from "./Pages/checkOut.jsx";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "./firebase";
import { Spinner } from "react-bootstrap";
import { Navigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";

// Route guard: shows a loading state until onAuthStateChanged fires,
// then either renders the children or redirects to /login. Without
// the loading state, logged-in users would briefly appear logged-out
// on refresh and get bounced.
function ProtectedRoute({ children }) {
  const [state, setState] = useState("loading");
  const location = useLocation();
  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (user) => {
      setState(user ? "authed" : "anon");
    });
    return () => unsub();
  }, []);
  if (state === "loading") {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ minHeight: "60vh" }}>
        <Spinner animation="border" />
      </div>
    );
  }
  if (state === "anon") {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return children;
}

// Simple 404 page with a link home.
function NotFound() {
  return (
    <div className="d-flex flex-column align-items-center justify-content-center" style={{ minHeight: "60vh" }}>
      <h1 className="display-1 fw-bold">404</h1>
      <p className="lead">Page not found.</p>
      <Link to="/" className="btn btn-primary mt-3">Go home</Link>
    </div>
  );
}

function App() {
  return (
    <Router>
      <NavigationBar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/products" element={<Products/>} />
        <Route path="/product/:id" element={<ProductDetails />} />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          }
        />
        <Route
          path="/cart"
          element={
            <ProtectedRoute>
              <Cart />
            </ProtectedRoute>
          }
        />
        <Route
          path="/payment"
          element={
            <ProtectedRoute>
              <Checkout />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}

export default App;
