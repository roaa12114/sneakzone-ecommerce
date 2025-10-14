import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import NavigationBar from "./components/navBar.jsx";
import Home from "./Pages/home";
import Login from "./Pages/login.jsx";
import Signup from "./Pages/signUp.jsx";
import Profile from "./Pages/profile";
import Products from "./Pages/products.jsx";
import ProductDetails from "./Pages/productDetails.jsx";
import "bootstrap/dist/css/bootstrap.min.css";
import Cart from "./Pages/cart.jsx";
import Checkout from "./Pages/checkOut.jsx";

function App() {
  return (
    <Router>
      <NavigationBar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/products" element={<Products/>} />
        <Route path="/product/:id" element={<ProductDetails />} />
        <Route path="/cart" element={<Cart />} />
        <Route path="/payment" element={<Checkout />} />
      </Routes>
    </Router>
  );
}

export default App;
