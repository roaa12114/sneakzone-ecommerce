import React, { useState } from "react";
import { Container, Form, Button, Alert } from "react-bootstrap";

function Checkout() {
  const [showSuccess, setShowSuccess] = useState(false);

  const handlePayment = (e) => {
    e.preventDefault();
    setShowSuccess(true);
    localStorage.removeItem("cart"); 
  };

  return (
    <Container className="py-5">
      <h2 className="mb-4">Checkout</h2>
      <Form onSubmit={handlePayment}>
        <Form.Group className="mb-3">
          <Form.Label>Cardholder Name</Form.Label>
          <Form.Control type="text" placeholder="Enter your name" required />
        </Form.Group>
        <Form.Group className="mb-3">
          <Form.Label>Card Number</Form.Label>
          <Form.Control type="text" placeholder="1234 5678 9012 3456" required />
        </Form.Group>
        <Form.Group className="mb-3">
          <Form.Label>Expiry Date</Form.Label>
          <Form.Control type="text" placeholder="MM/YY" required />
        </Form.Group>
        <Form.Group className="mb-3">
          <Form.Label>CVV</Form.Label>
          <Form.Control type="password" placeholder="***" required />
        </Form.Group>
        <Button variant="success" type="submit">
          Pay Now
        </Button>
      </Form>

      {showSuccess && (
        <Alert variant="success" className="mt-4">
          ✅ Payment successful! Thank you for your purchase.
        </Alert>
      )}
    </Container>
  );
}

export default Checkout;
