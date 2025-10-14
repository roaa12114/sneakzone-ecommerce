import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "bootstrap/dist/css/bootstrap.min.css"; // ✅ استيراد bootstrap
import "./index.css"; // الستايلات الخاصة بيكي

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
