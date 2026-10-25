import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { db, auth, onAuthStateChanged } from "../firebase";
import { doc, getDoc, collection, setDoc, query, where, getDocs, serverTimestamp, increment, deleteDoc } from "firebase/firestore";
import "./productDetails.css";

function ProductDetails() {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [comment, setComment] = useState("");
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [myFeedback, setMyFeedback] = useState(null);
  const [allFeedback, setAllFeedback] = useState([]);
  const [currentUid, setCurrentUid] = useState(null);
  const [currentUserName, setCurrentUserName] = useState("");
  const [productError, setProductError] = useState(null);

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

  // ✅ Track current user (fixes auth.currentUser-null-on-refresh race)
  //    Also cache their display name from users/{uid} so we can
  //    attribute feedback without exposing email.
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setCurrentUid(user ? user.uid : null);
      if (!user) {
        setMyFeedback(null);
        setCurrentUserName("");
        return;
      }
      // Prefer the name from users/{uid}; fall back to Auth displayName.
      try {
        const snap = await getDoc(doc(db, "users", user.uid));
        setCurrentUserName(snap.exists() ? (snap.data().name || user.displayName || "") : (user.displayName || ""));
      } catch {
        setCurrentUserName(user.displayName || "");
      }
    });
    return () => unsubscribe();
  }, []);

  // ✅ Fetch ALL public feedback for this product (no auth gate).
  //    Drop orderBy — sort client-side by updatedAt so legacy
  //    docs without the field still render (sorted last).
  //    No composite index needed.
  useEffect(() => {
    const fetchFeedback = async () => {
      try {
        const q = query(
          collection(db, "feedback"),
          where("productId", "==", id)
        );
        const snap = await getDocs(q);
        const list = snap.docs
          .map((d) => ({ id: d.id, ...d.data() }))
          .sort((a, b) => {
            const ta = a.updatedAt?.toMillis?.() || 0;
            const tb = b.updatedAt?.toMillis?.() || 0;
            return tb - ta;
          });
        setAllFeedback(list);
      } catch (e) {
        console.error("Error fetching feedback:", e);
      }
    };
    fetchFeedback();
  }, [id]);

  // ✅ Derive "my feedback" from allFeedback + currentUid. This
  //    replaces the old `auth.currentUser` read that was null on
  //    first paint after refresh (R2). Whenever the public list
  //    or the current uid changes, re-derive mine + pre-fill form.
  useEffect(() => {
    if (!currentUid) {
      setMyFeedback(null);
      return;
    }
    const mine = allFeedback.find((f) => f.uid === currentUid);
    setMyFeedback(mine || null);
    if (mine) {
      setComment(mine.comment);
      setRating(mine.rating);
    }
  }, [allFeedback, currentUid]);

  // ✅ Submit or update feedback (deterministic doc ID = `{productId}_{uid}`)
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
      const feedbackId = `${id}_${user.uid}`;
      await setDoc(doc(db, "feedback", feedbackId), {
        productId: id,
        uid: user.uid,
        userName: currentUserName || "Anonymous",
        comment,
        rating,
        updatedAt: serverTimestamp(),
      }, { merge: true });

      setMyFeedback({ comment, rating, userName: currentUserName || "Anonymous" });
      // Refresh the public list (no orderBy — sorted client-side).
      const q = query(
        collection(db, "feedback"),
        where("productId", "==", id)
      );
      const snap = await getDocs(q);
      const list = snap.docs
        .map((d) => ({ id: d.id, ...d.data() }))
        .sort((a, b) => {
          const ta = a.updatedAt?.toMillis?.() || 0;
          const tb = b.updatedAt?.toMillis?.() || 0;
          return tb - ta;
        });
      setAllFeedback(list);
    } catch (error) {
      console.error("Error saving feedback: ", error);
      alert(`⚠️ ${error.message}`);
    }
  };

  const handleDeleteFeedback = async () => {
    const user = auth.currentUser;
    if (!user) return;
    if (!confirm("Delete your feedback?")) return;
    try {
      const feedbackId = `${id}_${user.uid}`;
      await deleteDoc(doc(db, "feedback", feedbackId));
      setMyFeedback(null);
      setComment("");
      setRating(0);
      setAllFeedback((prev) => prev.filter((f) => f.id !== feedbackId));
    } catch (error) {
      console.error("Error deleting feedback:", error);
      alert(`⚠️ ${error.message}`);
    }
  };

  // add to cart — deterministic doc ID {uid}_{productId} so duplicates
  // are impossible and increment(1) bumps quantity atomically.
  const handleAddToCart = async () => {
    const user = auth.currentUser;
    if (!user) {
      alert("Please login first!");
      return;
    }
    try {
      const cartDocId = `${user.uid}_${id}`;
      await setDoc(doc(db, "cart", cartDocId), {
        uid: user.uid,
        productId: id,
        name: product.name,
        price: product.price,
        image: product.image,
        quantity: increment(1),
      }, { merge: true });
      alert(`${product.name} added to cart!`);
    } catch (error) {
      console.error("Error adding to cart: ", error);
    }
  };

  if (productError === "not-found") {
    return (
      <div className="product-details-page">
        <p>Product not found.</p>
        <a href="/products" className="btn btn-primary mt-3">Browse products</a>
      </div>
    );
  }
  if (productError === "error") {
    return (
      <div className="product-details-page">
        <p>Something went wrong loading this product. Please try again.</p>
        <a href="/products" className="btn btn-primary mt-3">Browse products</a>
      </div>
    );
  }
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

          {/* 📝 Feedback Section — public reads, author edits */}
          <div className="feedback-section">
            <h3>{myFeedback ? "Your Feedback" : "Leave Feedback"}</h3>

            {/* Show the form to logged-in users. If they already have a
                review, the form pre-fills and the button reads "Update". */}
            {currentUid ? (
              <>
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
                  {myFeedback ? "Update" : "Submit"}
                </button>
                {myFeedback && (
                  <button
                    className="submit-feedback"
                    style={{ marginLeft: "8px" }}
                    onClick={handleDeleteFeedback}
                  >
                    Delete
                  </button>
                )}
              </>
            ) : (
              <p>Please log in to leave feedback.</p>
            )}

            {/* ✅ Public list of all reviews for this product */}
            <h4 style={{ marginTop: "1.5rem" }}>All Reviews ({allFeedback.length})</h4>
            {allFeedback.length === 0 ? (
              <p>No reviews yet. Be the first!</p>
            ) : (
              <ul style={{ listStyle: "none", padding: 0 }}>
                {allFeedback.map((f) => (
                  <li
                    key={f.id}
                    style={{
                      borderBottom: "1px solid #eee",
                      padding: "0.5rem 0",
                    }}
                  >
                    <div>⭐ {f.rating}/5</div>
                    <div>{f.comment}</div>
                    <small style={{ color: "#888" }}>
                      by {f.userName || "Anonymous"}
                      {f.uid === currentUid ? " (you)" : ""}
                    </small>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProductDetails;
