import { Navbar, Nav, Container, Button } from "react-bootstrap";
import { Link, useNavigate } from "react-router-dom";
import React, { useEffect, useState } from "react";
import { auth, onAuthStateChanged } from "../firebase";
import { signOut } from "firebase/auth";
import { FaShoppingCart } from "react-icons/fa";
import "./navbar.css"; 

function NavigationBar() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [cartCount, setCartCount] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    // listen for user login/logout changes
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (user) {
        setIsLoggedIn(true);
      } else {
        setIsLoggedIn(false);
      }
    });
return () => unsubscribe();
  }, []);
  
  useEffect(() => {
    // لما الصفحة تفتح أو تتحدث، يجيب العدد من localStorage
    const count = parseInt(localStorage.getItem("cartCount")) || 0;
    setCartCount(count);

    // نعمل listener لو العدد اتغير (مثلاً لما نضيف من صفحة تانية)
    window.addEventListener("storage", () => {
      const updatedCount = parseInt(localStorage.getItem("cartCount")) || 0;
      setCartCount(updatedCount);
    });
  }, []);

  const handleLogout = async () => {
    await signOut(auth);
    navigate("/login");
  };

  return (
    <Navbar expand="lg" className="first-navbar shadow-sm">
      <Container>
        <Navbar.Brand as={Link} to="/" className="fw-bold fs-4 site-logo">
          SneakZone 👟
        </Navbar.Brand>

        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="ms-auto">
            {isLoggedIn ? (
              <>
                <Nav.Link as={Link} to="/profile" className="me-3 nav-link-custom">
                  Profile
                </Nav.Link>
                <Button
                  variant="outline-danger"
                  size="sm"
                  onClick={handleLogout}
                >
                  Logout
                </Button>
              </>
            ) : (
              <>
                <Nav.Link as={Link} to="/login" className="me-3 nav-link-custom">
                  Login
                </Nav.Link>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => navigate("/signup")}
                >
                  Sign Up
                </Button>
              </>
            )}
          </Nav>
          <Nav.Link as={Link} to="/cart" className="me-3 nav-link-custom">
  <FaShoppingCart size={20} style={{ marginRight: "5px" }} />
  Cart
  {cartCount > 0 && (
    <span
      style={{
        position: "absolute",
        top: "5px",
        right: "50px",
        backgroundColor: "#571414",
        color: "white",
        borderRadius: "50%",
        fontSize: "12px",
        width: "20px",
        height: "20px",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {cartCount}
    </span>
  )}
</Nav.Link>

        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
}

export default NavigationBar;
