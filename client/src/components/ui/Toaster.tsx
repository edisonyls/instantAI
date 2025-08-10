import React from "react";

export const Toaster: React.FC = () => {
  return (
    <div
      id="toast-container"
      className="fixed top-4 right-4 z-50 space-y-2"
    ></div>
  );
};

export function showToast(
  message: string,
  type: "success" | "error" = "success"
) {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const el = document.createElement("div");
  el.className = `rounded shadow px-3 py-2 text-sm ${
    type === "success" ? "bg-green-600 text-white" : "bg-red-600 text-white"
  }`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => {
    el.classList.add("opacity-0", "transition", "duration-300");
    setTimeout(() => container.removeChild(el), 300);
  }, 2500);
}
