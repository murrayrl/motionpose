// Import necessary modules and components
import Dashboard from "./views/Dashboard"; // Custom dashboard component (not used directly in this code)
import { Container, Typography } from "@mui/material"; // MUI components for layout and text styling
import * as React from "react"; // React library
import { useState, useEffect } from "react"; // React hooks for state management and side effects
import ToggleButton from "@mui/material/ToggleButton"; // MUI ToggleButton component
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"; // MUI ToggleButtonGroup for grouping toggle buttons

// Main App component
export default function App() {
    // Define state variables with default values
    const [coordinate, setCoordinate] = useState(["x", "y", "z"]); // Track selected coordinates (e.g., x, y, z)
    const [bodyPart, setBodyPart] = useState([
        "shoulder",
        "hip",
        "hand",
        "foot",
        "head",
    ]); // Track selected body parts
    const [direction, setDirection] = React.useState(["left", "right"]); // Track selected direction (left or right)
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
        sendToWebSocket({ coordinate: newCoordinate, bodyPart, direction }); // Send updated state to server
    };

    // Handler for body part selection changes
    const handleBodyPart = (event, newBodyPart) => {
        setBodyPart(newBodyPart); // Update body part state
        sendToWebSocket({ coordinate, bodyPart: newBodyPart, direction }); // Send updated state to server
    };

    // Handler for direction selection changes
    const handleDirection = (event, newDirection) => {
        setDirection(newDirection); // Update direction state
        sendToWebSocket({ coordinate, bodyPart, direction: newDirection }); // Send updated state to server
    };

    // Helper function to log current selected values to console
    const logCurrentValues = (coord, body, dir) => {
        console.log("Current Values:");
        console.log("Coordinates: ", coord.join(", ")); // Join array to display as comma-separated string
        console.log("Body Part: ", body.join(", "));
        console.log("Direction: ", dir.join(", "));
    };

    // Component return: JSX layout for the UI
    return (
        <div className="component">
            {/* Coordinate selection toggle buttons */}
            <ToggleButtonGroup
                className="toggleButtonGroup"
                value={coordinate} // Bind to coordinate state
                onChange={handleCoordinate} // Call handler on change
                aria-label="coordinates" // Accessibility label
            >
                <ToggleButton value="x" aria-label="x"> X </ToggleButton>
                <ToggleButton value="y" aria-label="y"> Y </ToggleButton>
                <ToggleButton value="z" aria-label="z"> Z </ToggleButton>
            </ToggleButtonGroup>

            {/* Body part selection toggle buttons */}
            <ToggleButtonGroup
                className="toggleButtonGroup"
                value={bodyPart} // Bind to bodyPart state
                onChange={handleBodyPart} // Call handler on change
                aria-label="body part" // Accessibility label
            >
                <ToggleButton value="shoulder" aria-label=""> Shoulder </ToggleButton>
                <ToggleButton value="hip" aria-label=""> Hip </ToggleButton>
                <ToggleButton value="hand" aria-label=""> Hand </ToggleButton>
                <ToggleButton value="foot" aria-label=""> Foot </ToggleButton>
                <ToggleButton value="head" aria-label=""> Head </ToggleButton>
            </ToggleButtonGroup>

            {/* Direction selection toggle buttons */}
            <ToggleButtonGroup
                className="toggleButtonGroup"
                value={direction} // Bind to direction state
                onChange={handleDirection} // Call handler on change
                aria-label="direction" // Accessibility label
            >
                <ToggleButton value="left" aria-label="left aligned"> Left </ToggleButton>
                <ToggleButton value="right" aria-label="centered"> Right </ToggleButton>
            </ToggleButtonGroup>
        </div>
    );
}