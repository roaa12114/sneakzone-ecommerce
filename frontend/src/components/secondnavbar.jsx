import React, { useState, useEffect } from "react";
import ReactDOM from "react-dom";
import "./secondnavbar.css";
import { useNavigate } from "react-router-dom";

function SecondNavbar() {
  const [searchQuery, setSearchQuery] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const navigate = useNavigate();

  // ✅ Search handler
  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/products?search=${encodeURIComponent(searchQuery)}`);
      setSearchQuery("");
    }
  };

  // ✅ Navigate to category directly
  const handleCategory = (category) => {
    navigate(`/products?category=${category}`);
    setShowDropdown(false); // Close dropdown after navigating
  };

  // ✅ Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      const dropdown = document.getElementById("categoryDropdown");
      if (dropdown && !dropdown.contains(event.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, []);

  return (
    <nav className="navbar navbar-expand-lg second-navbar shadow-sm">
      <div className="container-fluid">
        {/* Toggler for mobile */}
        <button
          className="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navbarSupportedContent"
          aria-controls="navbarSupportedContent"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span className="navbar-toggler-icon"></span>
        </button>

        {/* Navbar Links */}
        <div className="collapse navbar-collapse" id="navbarSupportedContent">
          <ul className="navbar-nav me-auto mb-2 mb-lg-0">
            <li className="nav-item">
              <a className="nav-link" href="/">Home</a>
            </li>

            <li className="nav-item">
              <a className="nav-link" href="/products">Products</a>
            </li>

            {/* Categories Dropdown */}
            <li className="nav-item dropdown">
              <a
                className="nav-link dropdown-toggle"
                href="#"
                id="categoryDropdown"
                role="button"
                onClick={() => setShowDropdown(!showDropdown)}
              >
                Categories
              </a>

              {/* ✅ Render dropdown via Portal */}
              {showDropdown &&
                ReactDOM.createPortal(
                  <ul
                    className="dropdown-menu show"
                    style={{
                      position: "absolute",
                      top: "60px",
                      left: "150px",
                      zIndex: 999999,
                    }}
                  >
                    <li>
                      <a
                        className="dropdown-item"
                        onClick={() => handleCategory("men")}
                      >
                        Men
                      </a>
                    </li>
                    <li>
                      <a
                        className="dropdown-item"
                        onClick={() => handleCategory("women")}
                      >
                        Women
                      </a>
                    </li>
                    <li>
                      <a
                        className="dropdown-item"
                        onClick={() => handleCategory("kids")}
                      >
                        Kids
                      </a>
                    </li>
                  </ul>,
                  document.getElementById("dropdown-root")
                )}
            </li>
          </ul>

          {/* ✅ Search Form */}
          <form className="d-flex" role="search" onSubmit={handleSearch}>
            <input
              className="form-control me-2"
              type="search"
              placeholder="Search sneakers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search"
            />
            <button className="btn btn-outline-success" type="submit">
              Search
            </button>
          </form>
        </div>
      </div>
    </nav>
  );
}

export default SecondNavbar;
