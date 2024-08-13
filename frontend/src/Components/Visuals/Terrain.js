import React, { useEffect, useRef } from 'react';
import p5 from 'p5';

const Terrain = () => {
  const sketchRef = useRef();
  const ws = useRef(null);
  const wristDistance = useRef(100); // Initial distance

  useEffect(() => {
    const sketch = new p5((p) => {
      let cols, rows;
      let scl = 20; // Scale of the terrain
      let w = 1400; // Width of the terrain
      let h = 1000; // Height of the terrain
      let terrain = [];

      p.setup = () => {
        p.createCanvas(p.windowWidth, p.windowHeight, p.WEBGL);
        cols = w / scl;
        rows = h / scl;

        // Initialize terrain array
        for (let x = 0; x < cols; x++) {
          terrain[x] = [];
          for (let y = 0; y < rows; y++) {
            terrain[x][y] = 0; // Default height
          }
        }

        // Setup WebSocket connection
        ws.current = new WebSocket('ws://localhost:8765');
        ws.current.onopen = () => console.log("WebSocket is open now.");
        ws.current.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data && Array.isArray(data)) {
            data.forEach(person => {
              const rightWrist = person.keypoints.find(k => k.label === "right_wrist");
              const leftWrist = person.keypoints.find(k => k.label === "left_wrist");

              if (rightWrist && leftWrist) {
                const dist = p.dist(rightWrist.x, rightWrist.y, leftWrist.x, leftWrist.y);
                wristDistance.current = p.map(dist, 0, p.windowWidth * 0.5, 500, 0); // Inverted range for the effect
              }
            });
          }
        };
        ws.current.onerror = (error) => console.log("WebSocket Error:", error);
        ws.current.onclose = () => console.log("WebSocket is closed now.");
      };

      p.draw = () => {
        p.background(0);
        p.rotateX(p.PI / 3);
        p.translate(-w / 2, -h / 2);
        
        let yoff = 0;
        for (let y = 0; y < rows; y++) {
          let xoff = 0;
          for (let x = 0; x < cols; x++) {
            terrain[x][y] = p.map(p.noise(xoff, yoff), 0, 1, -wristDistance.current, wristDistance.current);
            xoff += 0.05; // Adjust for more pronounced changes in the terrain
          }
          yoff += 0.05;
        }

        // Draw the terrain
        for (let y = 0; y < rows - 1; y++) {
          p.beginShape(p.TRIANGLE_STRIP);
          for (let x = 0; x < cols; x++) {
            p.fill(200, 200, 200, 150);
            p.vertex(x * scl, y * scl, terrain[x][y]);
            p.vertex(x * scl, (y + 1) * scl, terrain[x][y + 1]);
          }
          p.endShape();
        }
      };
    }, sketchRef.current);

    return () => {
      sketch.remove();
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []); // Empty dependency array ensures setup runs only once

  return <div ref={sketchRef}></div>;
};

export default Terrain;
