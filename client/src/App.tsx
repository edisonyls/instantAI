import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Header } from "./components/Layout/Header";
import { Dashboard } from "./pages/Dashboard";
import { PublicChat } from "./pages/PublicChat";
import { Settings } from "./pages/Settings";
import { Toaster } from "./components/ui/Toaster";
import "./App.css";

function App() {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        {/* Public chat route without header */}
        <Route path="/chat" element={<PublicChat />} />

        {/* Admin routes with header */}
        <Route
          path="/*"
          element={
            <div className="min-h-screen bg-gray-50">
              <Header />
              <main className="container mx-auto px-4 py-8">
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </main>
            </div>
          }
        />
      </Routes>
      <Toaster />
    </Router>
  );
}

export default App;
