import React, { useEffect, useRef, useState } from 'react';
import p5 from 'p5';

const Terrain = () => {
  const sketchRef = useRef();
  const [people, setPeople] = useState([]);

  useEffect(() => {
    const sketch = (p) => {
      let ws;
      let terrain = [];
      let baseTerrain = [];
      let cols, rows;
      const scl = 20;
      const w = 1400;
      const h = 1000;
      let spreadFactor = 1;
      let frameCounter = 0;

      p.setup = () => {
        p.createCanvas(p.windowWidth, p.windowHeight, p.WEBGL);
        cols = Math.floor(w / scl);
        rows = Math.floor(h / scl);

        // Initialize terrain
        for (let x = 0; x < cols; x++) {
          terrain[x] = [];
          baseTerrain[x] = [];
          for (let y = 0; y < rows; y++) {
            baseTerrain[x][y] = p.map(p.noise(x * 0.2, y * 0.2), 0, 1, -100, 100);
            terrain[x][y] = baseTerrain[x][y];
          }
        }

        // Connect to the WebSocket
        ws = new WebSocket('ws://localhost:8765');
        ws.onopen = () => {
          console.log("WebSocket is open now.");
        };
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);

          // Check if keypoints property exists and is an array
          if (data && Array.isArray(data)) {
            setPeople(data);
          } else {
            console.error("Invalid data format:", data);
          }
        };
        ws.onerror = (error) => {
          console.log("WebSocket Error:", error);
        };
        ws.onclose = () => {
          console.log("WebSocket is closed now.");
        };
      };

      p.draw = () => {
        // Increment frame counter
        frameCounter++;

        // Refresh every three frames
        if (frameCounter % 3 === 0) {
          p.background(0);

          // Calculate arm spread and update spreadFactor
          if (people.length > 0) {
            const leftHand = people.find(point => point.label === 'left_wrist');
            const rightHand = people.find(point => point.label === 'right_wrist');
            if (leftHand && rightHand) {
              const armSpread = p.dist(leftHand.x, leftHand.y, rightHand.x, rightHand.y);
              spreadFactor = p.map(armSpread, 0, p.windowWidth, 0.5, 2);
            }
          }

          // Update terrain heights based on spreadFactor
          for (let x = 0; x < cols; x++) {
            for (let y = 0; y < rows; y++) {
              terrain[x][y] = baseTerrain[x][y] * spreadFactor;
            }
          }

          p.stroke(255);
          p.noFill();
          p.translate(0, 50);
          p.rotateX(p.PI / 3);
          p.translate(-w / 2, -h / 2);

          for (let y = 0; y < rows - 1; y++) {
            p.beginShape(p.TRIANGLE_STRIP);
            for (let x = 0; x < cols; x++) {
              p.vertex(x * scl, y * scl, terrain[x][y]);
              p.vertex(x * scl, (y + 1) * scl, terrain[x][y + 1]);
            }
            p.endShape();
          }
        }
      };

      p.windowResized = () => {
        p.resizeCanvas(p.windowWidth, p.windowHeight);
      };
    };

    const myP5 = new p5(sketch, sketchRef.current);

    return () => {
      myP5.remove();
    };
  }, [people]);

  return <div ref={sketchRef}></div>;
};

export default Terrain;