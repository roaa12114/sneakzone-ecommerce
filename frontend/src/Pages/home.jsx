import { Container, Button } from "react-bootstrap";
import { useNavigate } from "react-router-dom";
import SecondNavbar from "../components/secondnavbar";
import "./home.css";

function Home() {
  const navigate = useNavigate();

  return (
    <div className="firstpage home-section bg-light">
      <SecondNavbar />
      <Container className="container text-center py-5">
        <h1 className="title fw-bold mb-3 ">Welcome to SneakZone</h1>
        <p className="lead ">
          Explore the latest sneakers, add your favorites, and share your
          reviews.
        </p>
        <Button
          variant="primary"
          size="lg"
          className="mt-3"
          onClick={() => navigate("/login")}
        >
          Get Started
        </Button>
      </Container>
    </div>
  );
}

export default Home;
