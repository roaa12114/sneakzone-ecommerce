import React, { useEffect, useState } from "react";
import { collection, getDocs, setDoc, doc, increment } from "firebase/firestore";
import { db, auth } from "../firebase";
import "./products.css";
import { useNavigate, useLocation } from "react-router-dom";

function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  // taking values from the url
  const queryParams = new URLSearchParams(location.search);
  const searchQuery = queryParams.get("search")?.toLowerCase() || "";
  const categoryFromURL = queryParams.get("category") || "all";

  
  const [selectedCategory, setSelectedCategory] = useState(categoryFromURL);

  // category updateL
  useEffect(() => {
    setSelectedCategory(categoryFromURL);
  }, [categoryFromURL]);

  // fetch products from firebase
  useEffect(() => {
    const fetchProducts = async () => {
      setError(null);
      try {
        const querySnapshot = await getDocs(collection(db, "products"));
        const productsData = querySnapshot.docs.map((doc) => ({
          id: doc.id,
          ...doc.data(),
        }));
        setProducts(productsData);
      } catch (e) {
        console.error("Error fetching products: ", e);
        setError("failed");
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

// felteration and search
  const filteredProducts = products.filter((p) => {
    const matchCategory =
      selectedCategory === "all" || p.category?.toLowerCase() === selectedCategory;
    const matchSearch =
      (p.name?.toLowerCase() || "").includes(searchQuery) ||
      (p.description?.toLowerCase() || "").includes(searchQuery);
    return matchCategory && matchSearch;
  });

  // redirect to the product page
  const handleView = (id) => {
    navigate(`/product/${id}`);
  };

  // add to cart
  const handleAddToCart = async (product) => {
  const user = auth.currentUser;
  if (!user) {
    alert("Please login first!");
    return;
  }
  try {
    // Deterministic doc ID: {uid}_{productId}. setDoc with merge
    // means first write creates the doc (quantity=1 via increment),
    // subsequent writes atomically bump quantity. No duplicates.
    const cartDocId = `${user.uid}_${product.id}`;
    await setDoc(doc(db, "cart", cartDocId), {
      uid: user.uid,
      productId: product.id,
      name: product.name,
      price: product.price,
      image: product.image,
      quantity: increment(1),
    }, { merge: true });

    alert(`${product.name} added to cart!`);
  } catch (error) {
    console.error("Error adding to cart: ", error);
  }};


  return (
    <div className="products-page">
      <h2 className="products-title">Explore Our Sneakers 👟</h2>

      {/* filter by click */}
      <div className="category-filter">
        {["all", "men", "women", "kids"].map((cat) => (
          <button
            key={cat}
            className={selectedCategory === cat ? "active" : ""}
            onClick={() => {
              setSelectedCategory(cat);
              navigate(`/products?category=${cat}`);
            }}
          >
            {cat.charAt(0).toUpperCase() + cat.slice(1)}
          </button>
        ))}
      </div>

      {/* display product */}
      {loading ? (
        <p className="text-center">Loading products…</p>
      ) : error ? (
        <div className="text-center">
          <p>Something went wrong loading products.</p>
          <button className="view-btn" onClick={() => window.location.reload()}>Retry</button>
        </div>
      ) : filteredProducts.length === 0 ? (
        <p className="text-center">No products match your search. Try a different filter.</p>
      ) : (
      <div className="products-grid">
        {filteredProducts.map((product) => (
          <div className="product-card" key={product.id}>
            <img src={product.image} alt={product.name} />
            <h3>{product.name}</h3>
            <p className="price">${product.price}</p>
            <div className="buttonsStyle">
            <button className="view-btn" onClick={() => handleView(product.id)}>
              View
            </button>
            <button className="view-btn" onClick={() => handleAddToCart(product)}>
              Add to Cart
            </button>
            </div>
          </div>
          
        ))}
      </div>
      )}
    </div>
  );
}

export default Products;
