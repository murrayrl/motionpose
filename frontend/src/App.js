// Import necessary modules and components from 'react-router-dom' for routing
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout"; // Layout component used for wrapping the route content
import Home from "./views/Home"; // Home page component
import Dashboard from "./views/Dashboard"; // Dashboard page component
import NoPage from "./views/NoPage"; // Component shown for unknown routes

// Main App component
export default function App() {
  return (
    // BrowserRouter is the top-level component to enable routing within the application
    <BrowserRouter>
      {/* Routes component contains all the route definitions */}
      <Routes>
        {/* Define a route for the root ("/") path, which renders the Layout component */}
        <Route path="/" element={<Layout />}>
          {/* The index route is the default route under the Layout component and will render the Home component */}
          <Route index element={<Home />} />

          {/* Define a route for "/dashboard" path to render the Dashboard component */}
          <Route path="dashboard" element={<Dashboard />} />

          {/* The "*" path acts as a wildcard for undefined routes, and renders the NoPage component */}
          <Route path="*" element={<NoPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
