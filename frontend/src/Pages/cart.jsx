import React, { useEffect, useState } from "react";
import { collection, getDocs, deleteDoc, doc, query, where, updateDoc, increment } from "firebase/firestore";
import { db, auth, onAuthStateChanged } from "../firebase";
import { useNavigate } from "react-router-dom";
import { Container, Row, Col, Card, Button } from "react-bootstrap";

function Cart() {
  const [cartItems, setCartItems] = useState([]);
  const [total, setTotal] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (!user) {
        setCartItems([]);
        calculateTotal([]);
        return;
      }
      try {
        const q = query(collection(db, "cart"), where("uid", "==", user.uid));
        const querySnapshot = await getDocs(q);
        const items = querySnapshot.docs.map((doc) => ({
          id: doc.id,
          ...doc.data(),
        }));
        setCartItems(items);
        calculateTotal(items);
      } catch (error) {
        console.error("Error fetching cart items: ", error);
      }
    });

    return () => unsubscribe();
  }, []);

  const calculateTotal = (items) => {
    const sum = items.reduce((acc, item) => {
      const price = Number(item.price) || 0;
      const qty = Number(item.quantity) || 1;
      return acc + price * qty;
    }, 0);
    setTotal(sum);
  };

  const handleRemove = async (id) => {
    try {
      await deleteDoc(doc(db, "cart", id));
      const updatedItems = cartItems.filter((item) => item.id !== id);
      setCartItems(updatedItems);
      calculateTotal(updatedItems);
    } catch (error) {
      console.error("Error removing item: ", error);
    }
  };

  const handleUpdateQuantity = async (id, delta) => {
    try {
      const itemRef = doc(db, "cart", id);
      await updateDoc(itemRef, { quantity: increment(delta) });
      setCartItems((prev) =>
        prev.map((it) =>
          it.id === id
            ? { ...it, quantity: Math.max(1, (Number(it.quantity) || 1) + delta) }
            : it
        )
      );
      // Recompute total from the updated local state.
      setCartItems((prev) => {
        calculateTotal(prev);
        return prev;
      });
    } catch (error) {
      console.error("Error updating quantity: ", error);
    }
  };

  const handleProceed = () => {
    navigate("/payment", { state: { total } });
  };

  return (
    <Container className="py-5">
      <h2 className="text-center mb-4">Your Cart 🛒</h2>

      {cartItems.length === 0 ? (
        <p className="text-center">Your cart is empty.</p>
      ) : (
        <>
          <Row>
            {cartItems.map((item) => (
              <Col md={4} sm={6} xs={12} key={item.id} className="mb-4">
                <Card className="h-100 shadow-sm">
                  <Card.Img
                    variant="top"
                    src={item.image}
                    alt={item.name}
                    style={{ height: "250px", objectFit: "cover" }}
                  />
                  <Card.Body>
                    <Card.Title>{item.name}</Card.Title>
                    <Card.Text>
                      <strong>Price:</strong> ${Number(item.price).toFixed(2)} <br />
                      <strong>Quantity:</strong>{" "}
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleUpdateQuantity(item.id, -1)}
                        disabled={(Number(item.quantity) || 1) <= 1}
                      >
                        −
                      </Button>
                      {" "}{Number(item.quantity) || 1}{" "}
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleUpdateQuantity(item.id, +1)}
                      >
                        +
                      </Button>
                    </Card.Text>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => handleRemove(item.id)}
                    >
                      Remove
                    </Button>
                  </Card.Body>
                </Card>
              </Col>
            ))}
          </Row>

          <div className="text-center mt-4">
            <h4>Total: ${total.toFixed(2)}</h4>
            <Button variant="success" className="mt-3" onClick={handleProceed}>
              Proceed to Payment 💳
            </Button>
          </div>
        </>
      )}
    </Container>
  );
}

export default Cart;
