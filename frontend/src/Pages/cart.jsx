import React, { useEffect, useState } from "react";
import { collection, getDocs, deleteDoc, doc } from "firebase/firestore";
import { db } from "../firebase";
import { useNavigate } from "react-router-dom";
import { Container, Row, Col, Card, Button } from "react-bootstrap";

function Cart() {
  const [cartItems, setCartItems] = useState([]);
  const [total, setTotal] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchCart = async () => {
      try {
        const querySnapshot = await getDocs(collection(db, "cart"));
        const items = querySnapshot.docs.map((doc) => ({
          id: doc.id,
          ...doc.data(),
        }));
        setCartItems(items);
        calculateTotal(items);
      } catch (error) {
        console.error("Error fetching cart items: ", error);
      }
    };

    fetchCart();
  }, []);

  const calculateTotal = (items) => {
    const sum = items.reduce((acc, item) => acc + item.price * (item.quantity || 1), 0);
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
                      <strong>Price:</strong> ${item.price} <br />
                      <strong>Quantity:</strong> {item.quantity || 1}
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
