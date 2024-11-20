// Import necessary components from Material UI and React Router
import { Box, AppBar, Toolbar, Typography, Button } from "@mui/material";
import { useNavigate } from "react-router-dom"; // Import the hook to navigate between pages

export default function Navbar() {
  // Initialize the navigate function from React Router to programmatically navigate
  const navigate = useNavigate();

  return (
    // The Box component acts as a wrapper and uses flexGrow to allow the AppBar to expand
    <Box sx={{ flexGrow: 1 }}>
      {/* The AppBar component is used to create a top navigation bar */}
      <AppBar position="static">
        {/* The Toolbar component provides padding and alignment for the contents inside the AppBar */}
        <Toolbar>
          {/* Typography is used to display the website's title */}
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Machine Learning in Motion
          </Typography>

          {/* Button for navigating to the Home page */}
          <Button onClick={() => navigate("/")} color="inherit">
            Home
          </Button>

          {/* Button for navigating to the Dashboard page */}
          <Button onClick={() => navigate("/dashboard")} color="inherit">
            Dashboard
          </Button>
        </Toolbar>
      </AppBar>
    </Box>
  );
}
