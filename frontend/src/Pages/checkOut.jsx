import React, { useEffect, useState } from "react";
import { Container, Form, Button, Alert, Spinner } from "react-bootstrap";
import { useNavigate } from "react-router-dom";
import { auth, db, onAuthStateChanged } from "../firebase";
import {
  collection,
  query,
  where,
  getDocs,
  doc,
  writeBatch,
  serverTimestamp,
} from "firebase/firestore";

function Checkout() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  // Re-read the user's cart docs (we do NOT trust router state for the total).
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (!user) {
        setItems([]);
        setTotal(0);
        setLoading(false);
        return;
      }
      try {
        const q = query(collection(db, "cart"), where("uid", "==", user.uid));
        const snap = await getDocs(q);
        const docs = snap.docs.map((d) => ({ id: d.id, ...d.data() }));
        setItems(docs);
        const sum = docs.reduce((acc, it) => {
          const price = Number(it.price) || 0;
          const qty = Number(it.quantity) || 1;
          return acc + price * qty;
        }, 0);
        setTotal(sum);
      } catch (e) {
        console.error("Checkout load error:", e);
      } finally {
        setLoading(false);
      }
    });
    return () => unsubscribe();
  }, []);

  const handlePayment = async (e) => {
    e.preventDefault();
    if (items.length === 0) {
      setError("Your cart is empty.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const user = auth.currentUser;
      if (!user) {
        navigate("/login");
        return;
      }
      // One atomic batch: write the order doc, then delete every cart doc.
      // We never store card number or CVV anywhere — payment is a mock.
      const orderId = `${user.uid}_${Date.now()}`;
      const batch = writeBatch(db);
      batch.set(doc(db, "orders", orderId), {
        uid: user.uid,
        items: items.map((it) => {
          const { id: _ignored, ...rest } = it;
          return rest;
        }),
        total,
        status: "paid",
        createdAt: serverTimestamp(),
      });
      items.forEach((it) => {
        batch.delete(doc(db, "cart", it.id));
      });
      await batch.commit();
      setShowSuccess(true);
    } catch (err) {
      console.error("Checkout error:", err);
      setError(err.message || "Payment failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Container className="py-5 text-center">
        <Spinner animation="border" />
      </Container>
    );
  }

  if (showSuccess) {
    return (
      <Container className="py-5">
        <Alert variant="success">
          ✅ Payment successful! Your order has been placed.
        </Alert>
        <Button variant="primary" onClick={() => navigate("/products")}>
          Continue Shopping
        </Button>
      </Container>
    );
  }

  return (
    <Container className="py-5">
      <h2 className="mb-4">Checkout</h2>

      {items.length === 0 ? (
        <Alert variant="info">
          Your cart is empty. <Button variant="link" onClick={() => navigate("/products")}>Browse products</Button>
        </Alert>
      ) : (
        <>
          <Alert variant="info" className="mb-4">
            <strong>Order Total: ${total.toFixed(2)}</strong> ({items.length} item{items.length > 1 ? "s" : ""})
          </Alert>
          <Form onSubmit={handlePayment}>
            <Form.Group className="mb-3">
              <Form.Label>Cardholder Name</Form.Label>
              <Form.Control type="text" placeholder="Enter your name" required />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Card Number</Form.Label>
              <Form.Control type="text" placeholder="1234 5678 9012 3456" required />
              <Form.Text className="text-muted">
                Demo only — no real payment is processed and card details are never stored.
              </Form.Text>
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Expiry Date</Form.Label>
              <Form.Control type="text" placeholder="MM/YY" required />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>CVV</Form.Label>
              <Form.Control type="password" placeholder="***" required />
            </Form.Group>
            <Button variant="success" type="submit" disabled={submitting}>
              {submitting ? <Spinner as="span" animation="border" size="sm" /> : "Pay Now"}
            </Button>
            {error && <Alert variant="danger" className="mt-3">{error}</Alert>}
          </Form>
        </>
      )}
    </Container>
  );
}

export default Checkout;
