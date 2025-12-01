import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import Home from "./pages/Home";
import Builder from "./pages/Builder";
import "./index.css";

const qc = new QueryClient();

// Create router with v7 future flags to suppress warnings
const router = createBrowserRouter(
  [
    { path: "/", element: <Home /> },
    { path: "/builder", element: <Builder /> },
  ],
  {
    future: {
      v7_startTransition: true,
      v7_relativeSplatPath: true,
    },
  }
);

createRoot(document.getElementById("root")).render(
  <QueryClientProvider client={qc}>
    <RouterProvider router={router} />
  </QueryClientProvider>
);
