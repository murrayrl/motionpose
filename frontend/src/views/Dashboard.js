import { Box, Stack, ToggleButton, ToggleButtonGroup } from "@mui/material";
import { useEffect, useState } from "react";

export default function Dashboard() {
  // Define state variables with default values
  const [coordinate, setCoordinate] = useState(["x", "y", "z"]); // Track selected coordinates (e.g., x, y, z)
  const [bodyPart, setBodyPart] = useState([
    "nose",
    "left eye",
    "right eye",
    "left ear",
    "right ear",
    "left shoulder",
    "right shoulder",
    "left elbow",
    "right elbow",
    "left wrist",
    "right wrist",
    "left hip",
    "right hip",
    "left knee",
    "right knee",
    "left ankle",
    "right ankle",
  ]); // Track selected body parts
  const [ws, setWs] = useState(null); // WebSocket instance

  // Establish WebSocket connection when component mounts
  useEffect(() => {
    const websocket = new WebSocket("ws://localhost:6789"); // Connect to WebSocket server on localhost

    // Log connection status to console
    websocket.onopen = () => {
      console.log("Connected to WebSocket server");
    };

    websocket.onclose = () => {
      console.log("Disconnected from WebSocket server");
    };

    websocket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    setWs(websocket); // Save WebSocket instance in state

    // Clean up WebSocket connection when component unmounts
    return () => {
      websocket.close();
    };
  }, []);

  // Function to send data to WebSocket server
  const sendToWebSocket = (data) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data)); // Convert data to JSON and send through WebSocket
    }
  };

  // Handler for coordinate selection changes
  const handleCoordinate = (event, newCoordinate) => {
    setCoordinate(newCoordinate); // Update coordinate state
    sendToWebSocket({ coordinate: newCoordinate, bodyPart }); // Send updated state to server
  };

  // Handler for body part selection changes
  const handleBodyPart = (event, newBodyPart) => {
    setBodyPart(newBodyPart); // Update body part state
    sendToWebSocket({ coordinate, bodyPart: newBodyPart }); // Send updated state to server
  };

  // Helper function to log current selected values to console
  // const logCurrentValues = (coord, body, dir) => {
  //   console.log("Current Values:");
  //   console.log("Coordinates: ", coord.join(", ")); // Join array to display as comma-separated string
  //   console.log("Body Part: ", body.join(", "));
  // };

  // Component return: JSX layout for the UI
  return (
    <Box
      sx={{ width: "100%", display: "flex", justifyContent: "center", pt: 6 }}
    >
      {/* Body part selection toggle buttons */}
      <ToggleButtonGroup
        className="toggleButtonGroup"
        value={bodyPart} // Bind to bodyPart state
        onChange={handleBodyPart} // Call handler on change
        aria-label="body part" // Accessibility label
      >
        <Stack
          spacing={2}
          sx={{ width: "30vw", display: "flex", alignItems: "center" }}
        >
          <Box
            sx={{ width: "100%", display: "flex", justifyContent: "center" }}
          >
            <ToggleButton
              value="nose"
              aria-label=""
              sx={{ width: "fit-content" }}
            >
              {" "}
              Nose{" "}
            </ToggleButton>
          </Box>
          <Box sx={{ display: "flex", gap: 2 }}>
            <ToggleButton value="left eye" aria-label="">
              {" "}
              Left Eye{" "}
            </ToggleButton>
            <ToggleButton value="right eye" aria-label="">
              {" "}
              Right Eye{" "}
            </ToggleButton>
          </Box>
          <Box sx={{ display: "flex", gap: 2 }}>
            <ToggleButton value="left ear" aria-label="">
              {" "}
              Left Ear{" "}
            </ToggleButton>
            <ToggleButton value="right ear" aria-label="">
              {" "}
              Right Ear{" "}
            </ToggleButton>
          </Box>
          <Box sx={{ display: "flex", gap: 2 }}>
            <ToggleButton value="left shoulder" aria-label="">
              {" "}
              Left Shoulder{" "}
            </ToggleButton>
            <ToggleButton value="right shoulder" aria-label="">
              {" "}
              Right Shoulder{" "}
            </ToggleButton>
          </Box>
          <Box sx={{ display: "flex", gap: 2 }}>
            <ToggleButton value="left elbow" aria-label="">
              {" "}
              Left Elbow{" "}
            </ToggleButton>
            <ToggleButton value="right elbow" aria-label="">
              {" "}
              Right Elbow{" "}
            </ToggleButton>
          </Box>
          <Box sx={{ display: "flex", gap: 2 }}>
            <ToggleButton value="left wrist" aria-label="">
              {" "}
              Left Wrist{" "}
            </ToggleButton>
            <ToggleButton value="right wrist" aria-label="">
              {" "}
              Right Wrist{" "}
            </ToggleButton>
          </Box>
          <Box sx={{ display: "flex", gap: 2 }}>
            <ToggleButton value="left hip" aria-label="">
              {" "}
              Left Hip{" "}
            </ToggleButton>
            <ToggleButton value="right hip" aria-label="">
              {" "}
              Right Hip{" "}
            </ToggleButton>
          </Box>
          <Box sx={{ display: "flex", gap: 2 }}>
            <ToggleButton value="left knee" aria-label="">
              {" "}
              Left Knee{" "}
            </ToggleButton>
            <ToggleButton value="right knee" aria-label="">
              {" "}
              Right Knee{" "}
            </ToggleButton>
          </Box>
          <Box sx={{ display: "flex", gap: 2 }}>
            <ToggleButton value="left ankle" aria-label="">
              {" "}
              Left Ankle{" "}
            </ToggleButton>
            <ToggleButton value="right ankle" aria-label="">
              {" "}
              Right Ankle{" "}
            </ToggleButton>
          </Box>
          {/* Coordinate selection toggle buttons */}
          <ToggleButtonGroup
            className="toggleButtonGroup"
            value={coordinate} // Bind to coordinate state
            onChange={handleCoordinate} // Call handler on change
            aria-label="coordinates" // Accessibility label
          >
            <ToggleButton value="x" aria-label="x">
              {" "}
              X{" "}
            </ToggleButton>
            <ToggleButton value="y" aria-label="y">
              {" "}
              Y{" "}
            </ToggleButton>
            <ToggleButton value="z" aria-label="z">
              {" "}
              Z{" "}
            </ToggleButton>
          </ToggleButtonGroup>
        </Stack>
      </ToggleButtonGroup>
    </Box>
  );
}
