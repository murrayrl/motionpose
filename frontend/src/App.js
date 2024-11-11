// Import necessary modules and components
import Dashboard from "./views/Dashboard"; // Custom dashboard component (not used directly in this code)
import { Container, Typography } from "@mui/material"; // MUI components for layout and text styling
import * as React from "react"; // React library
import { useState, useEffect } from "react"; // React hooks for state management and side effects
import ToggleButton from "@mui/material/ToggleButton"; // MUI ToggleButton component
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"; // MUI ToggleButtonGroup for grouping toggle buttons
import Stack from '@mui/material/Stack'; // MUI Stack component


// Main App component
export default function App() {
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
        "right ankle"
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
        sendToWebSocket({ coordinate: newCoordinate, bodyPart}); // Send updated state to server
    };

    // Handler for body part selection changes
    const handleBodyPart = (event, newBodyPart) => {
        setBodyPart(newBodyPart); // Update body part state
        sendToWebSocket({ coordinate, bodyPart: newBodyPart}); // Send updated state to server
    };

    // Helper function to log current selected values to console
    const logCurrentValues = (coord, body, dir) => {
        console.log("Current Values:");
        console.log("Coordinates: ", coord.join(", ")); // Join array to display as comma-separated string
        console.log("Body Part: ", body.join(", "));
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
                <Stack spacing = {2}>
                    <ToggleButton value="nose" aria-label=""> Nose </ToggleButton>
                    <div>
                        <ToggleButton value="left eye" aria-label=""> Left Eye </ToggleButton>
                        <ToggleButton value="right eye" aria-label=""> Right Eye </ToggleButton>
                    </div>
                    <div>
                        <ToggleButton value="left ear" aria-label=""> Left Ear </ToggleButton>
                        <ToggleButton value="right ear" aria-label=""> Right Ear </ToggleButton>
                    </div>
                    <div>
                        <ToggleButton value="left shoulder" aria-label=""> Left Shoulder </ToggleButton>
                        <ToggleButton value="right shoulder" aria-label=""> Right Shoulder </ToggleButton>
                    </div>
                    <div>
                        <ToggleButton value="left elbow" aria-label=""> Left Elbow </ToggleButton>
                        <ToggleButton value="right elbow" aria-label=""> Right Elbow </ToggleButton>
                    </div>
                    <div>
                        <ToggleButton value="left wrist" aria-label=""> Left Wrist </ToggleButton>
                        <ToggleButton value="right wrist" aria-label=""> Right Wrist </ToggleButton>
                    </div>
                    <div>
                        <ToggleButton value="left hip" aria-label=""> Left Hip </ToggleButton>
                        <ToggleButton value="right hip" aria-label=""> Right Hip </ToggleButton>
                    </div>
                    <div>
                        <ToggleButton value="left knee" aria-label=""> Left Knee </ToggleButton>
                        <ToggleButton value="right knee" aria-label=""> Right Knee </ToggleButton>
                    </div>
                    <div>
                        <ToggleButton value="left ankle" aria-label=""> Left Ankle </ToggleButton>
                        <ToggleButton value="right ankle" aria-label=""> Right Ankle </ToggleButton>
                    </div>
                </Stack>
                
            </ToggleButtonGroup>
        </div>
    );
}