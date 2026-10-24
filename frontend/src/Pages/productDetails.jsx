import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { db, auth } from "../firebase";
import { doc, getDoc, collection, addDoc, query, where, getDocs, serverTimestamp } from "firebase/firestore";
import "./productDetails.css";

function ProductDetails() {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [comment, setComment] = useState("");
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [myFeedback, setMyFeedback] = useState(null);

  useEffect(() => {
    const fetchProduct = async () => {
      const docRef = doc(db, "products", id);
      const docSnap = await getDoc(docRef);
      if (docSnap.exists()) {
        setProduct(docSnap.data());
      }
    };
    fetchProduct();
  }, [id]);

  // ✅ جلب الفيدباك الخاص بالمستخدم فقط
  useEffect(() => {
    const fetchMyFeedback = async () => {
      const user = auth.currentUser;
      if (!user) return;

      const q = query(
        collection(db, "feedback"),
        where("productId", "==", id),
        where("userEmail", "==", user.email)
      );

      const querySnapshot = await getDocs(q);
      if (!querySnapshot.empty) {
        setMyFeedback(querySnapshot.docs[0].data());
      }
    };

    fetchMyFeedback();
  }, [id]);

  // ✅ إرسال الفيدباك
  const handleFeedbackSubmit = async () => {
    if (!comment || rating === 0) {
      alert("Please add both a comment and a rating!");
      return;
    }

    const user = auth.currentUser;
    if (!user) {
      alert("Please login first!");
      return;
    }

    try {
      await addDoc(collection(db, "feedback"), {
        productId: id,
        userEmail: user.email,
        comment,
        rating,
        createdAt: serverTimestamp(),
      });

      alert("Feedback submitted successfully!");
      setMyFeedback({ comment, rating });
      setComment("");
      setRating(0);
    } catch (error) {
      console.error("Error adding feedback: ", error);
    }
  };

  // add to cart (per-user; matches products.jsx logic + uid from task 3)
  const handleAddToCart = async () => {
    const user = auth.currentUser;
    if (!user) {
      alert("Please login first!");
      return;
    }
    try {
      await addDoc(collection(db, "cart"), {
        name: product.name,
        price: product.price,
        image: product.image,
        quantity: 1,
        uid: user.uid,
      });
      let currentCount = parseInt(localStorage.getItem("cartCount")) || 0;
      localStorage.setItem("cartCount", currentCount + 1);
      window.dispatchEvent(new Event("storage"));
      alert(`${product.name} added to cart!`);
    } catch (error) {
      console.error("Error adding to cart: ", error);
    }
  };

  if (!product) {
    return <p className="loading">Loading product details...</p>;
  }

  return (
    <div className="product-details-page">
      <div className="product-details-container">
        <div className="image-section">
          <img
            src={product.image}
            alt={product.name}
            className="details-image"
          />
        </div>

        <div className="info-section">
          <h1 className="product-name">{product.name}</h1>
          <p className="product-price">${product.price}</p>
          <p className="product-description">{product.description}</p>
          <button className="add-to-cart" onClick={handleAddToCart}>Add to Cart</button>

          {/* 📝 Feedback Form */}
          <div className="feedback-section">
            <h3>Leave Feedback:</h3>

            {/* 🌟 Rating Stars */}
            <div className="star-rating">
              {[...Array(5)].map((star, index) => {
                const currentRating = index + 1;
                return (
                  <span
                    key={index}
                    className={`star ${currentRating <= (hover || rating) ? "filled" : ""}`}
                    onClick={() => setRating(currentRating)}
                    onMouseEnter={() => setHover(currentRating)}
                    onMouseLeave={() => setHover(rating)}
                  >
                    ★
                  </span>
                );
              })}
            </div>

            <textarea
              placeholder="Write your feedback..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />

            <button className="submit-feedback" onClick={handleFeedbackSubmit}>
              Submit
            </button>

            {/* ✅ عرض فيدباك المستخدم فقط */}
            {myFeedback && (
              <div className="my-feedback">
                <h4>Your Feedback:</h4>
                <p>⭐ {myFeedback.rating}/5</p>
                <p>{myFeedback.comment}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProductDetails;
