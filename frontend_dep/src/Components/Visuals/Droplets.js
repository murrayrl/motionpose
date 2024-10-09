import React, { useEffect, useRef } from 'react';
import p5 from 'p5';

const Wave = () => {
  const sketchRef = useRef();
  const ws = useRef(null);
  const joints = ['left_wrist', 'right_wrist', 'left_ankle', 'right_ankle'];

  useEffect(() => {
    const sketch = new p5((p) => {
      let waves = [];
      let colors = [];
      let jointsData = {};

      p.setup = () => {
        p.createCanvas(p.windowWidth, p.windowHeight);
        p.noStroke();

        // Initialize colors
        for (let i = 0; i < 100; i++) {
          colors.push(p.color(p.random(255), p.random(255), p.random(255), 150));
        }

        // Setup WebSocket connection
        ws.current = new WebSocket('ws://localhost:8765');
        ws.current.onopen = () => console.log("WebSocket is open now.");
        ws.current.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data && Array.isArray(data)) {
            data.forEach(person => {
              if (person.keypoints && Array.isArray(person.keypoints)) {
                person.keypoints.forEach(keypoint => {
                  if (joints.includes(keypoint.label)) {
                    jointsData[keypoint.label] = {
                      x: p.width - keypoint.x, // Invert the x-coordinate
                      y: keypoint.y // Use the original y-coordinate
                    };
                  }
                });
              }
            });
          }
        };
        ws.current.onerror = (error) => console.log("WebSocket Error:", error);
        ws.current.onclose = () => console.log("WebSocket is closed now.");
      };

      p.draw = () => {
        p.background(0);

        // Update waves based on joint data
        Object.keys(jointsData).forEach((joint, index) => {
          let x = jointsData[joint].x;
          let y = jointsData[joint].y;
          waves.push({ x, y, color: colors[index % colors.length] });
        });

        // Draw waves
        for (let i = waves.length - 1; i >= 0; i--) {
          let wave = waves[i];
          p.fill(wave.color);
          p.ellipse(wave.x, wave.y, 10);
          wave.y += 2; // Move wave down
          if (wave.y > p.height) {
            waves.splice(i, 1); // Remove wave if out of canvas
          }
        }
      };

      p.windowResized = () => {
        p.resizeCanvas(p.windowWidth, p.windowHeight);
      };
    }, sketchRef.current);

    return () => {
      sketch.remove();
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [joints]); // Add 'joints' to the dependency array

  return <div ref={sketchRef} style={{ width: '100%', height: '100%' }}></div>;
};

export default Wave;
