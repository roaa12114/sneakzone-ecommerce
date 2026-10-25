import React, { useState } from "react";
import "./secondnavbar.css";
import { useNavigate, Link } from "react-router-dom";

function SecondNavbar() {
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();

  // ✅ Search handler
  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/products?search=${encodeURIComponent(searchQuery)}`);
      setSearchQuery("");
    }
  };

  // ✅ Navigate to category directly (Bootstrap closes the dropdown
  //    for us, so we don't need showDropdown state or click-outside logic.)
  const handleCategory = (category) => {
    navigate(`/products?category=${category}`);
  };

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
              <Link className="nav-link" to="/">Home</Link>
            </li>

            <li className="nav-item">
              <Link className="nav-link" to="/products">Products</Link>
            </li>

            {/* Categories Dropdown — native Bootstrap, no portal */}
            <li className="nav-item dropdown">
              <a
                className="nav-link dropdown-toggle"
                href="#"
                role="button"
                data-bs-toggle="dropdown"
                aria-expanded="false"
              >
                Categories
              </a>
              <ul className="dropdown-menu">
                <li>
                  <button
                    type="button"
                    className="dropdown-item"
                    onClick={() => handleCategory("men")}
                  >
                    Men
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    className="dropdown-item"
                    onClick={() => handleCategory("women")}
                  >
                    Women
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    className="dropdown-item"
                    onClick={() => handleCategory("kids")}
                  >
                    Kids
                  </button>
                </li>
              </ul>
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
