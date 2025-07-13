import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export const Home: React.FC = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect to dashboard
    navigate("/dashboard");
  }, [navigate]);

  return null;
};
