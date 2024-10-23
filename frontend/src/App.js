import Dashboard from "./views/Dashboard";
import { Container, Typography } from "@mui/material";
import * as React from "react";
import { useState } from "react";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";

export default function App() {
    const [coordinate, setCoordinate] = useState(["x", "y", "z"]);

    const handleCoordinate = (event, newCoordinate) => {
        setCoordinate(newCoordinate);
    };

    const [bodyPart, setBodyPart] = useState([
        "shoulder",
        "hip",
        "hand",
        "foot",
        "head",
    ]);

    const handleBodyPart = (event, newBodyPart) => {
        setBodyPart(newBodyPart);
    };

    const [direction, setDirection] = React.useState(["left", "right"]);

    const handleDirection = (event, newDirection) => {
        setDirection(newDirection);
    };
    return (
        <div className="component">
            {/* X, Y, Z Toggles */}
            <ToggleButtonGroup
                className="toggleButtonGroup"
                value={coordinate}
                onChange={handleCoordinate}
                aria-label="coordinates"
            >
                <ToggleButton value="x" aria-label="x">
                    X
                </ToggleButton>
                <ToggleButton value="y" aria-label="y">
                    Y
                </ToggleButton>
                <ToggleButton value="z" aria-label="z">
                    Z
                </ToggleButton>
            </ToggleButtonGroup>

            {/* Body Part Toggles */}
            <ToggleButtonGroup
                className="toggleButtonGroup"
                value={bodyPart}
                onChange={handleBodyPart}
                aria-label="body part"
            >
                <ToggleButton value="shoulder" aria-label="">
                    Shoulder
                </ToggleButton>
                <ToggleButton value="hip" aria-label="">
                    Hip
                </ToggleButton>
                <ToggleButton value="hand" aria-label="">
                    Hand
                </ToggleButton>
                <ToggleButton value="foot" aria-label="">
                    Foot
                </ToggleButton>
                <ToggleButton value="head" aria-label="">
                    Head
                </ToggleButton>
            </ToggleButtonGroup>

            {/* Left, Right Toggles */}
            <ToggleButtonGroup
                className="toggleButtonGroup"
                value={direction}
                onChange={handleDirection}
                aria-label="direction"
            >
                <ToggleButton value="left" aria-label="left aligned">
                    Left
                </ToggleButton>
                <ToggleButton value="right" aria-label="centered">
                    Right
                </ToggleButton>
            </ToggleButtonGroup>
            <Container
                sx={{
                    border: "1px solid black",
                    width: "fit-content",
                    mt: 10,
                    borderRadius: 300,
                }}
            >
                <p>hi</p>
            </Container>
        </div>
    );
}
