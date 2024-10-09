import React, { useEffect, useRef } from 'react';
import p5 from 'p5';

const Interactive3D = () => {
  const sketchRef = useRef();
  const previousPosition = useRef({ x: 0, y: 0 });
  const velocity = useRef({ x: 0, y: 0 });
  const ws = useRef(null);

  useEffect(() => {
    const sketch = new p5((p) => {
      let globe;
      let angleX = 0;
      let angleY = 0;
      const friction = 0.97;  // Friction to dampen rotation
      const sensitivity = 0.001;  // Adjust sensitivity for movement detection

      p.preload = () => {
        globe = p.loadImage('https://cdn.jsdelivr.net/npm/three-globe/example/img/earth-night.jpg');
      };

      p.setup = () => {
        p.createCanvas(p.windowWidth, p.windowHeight, p.WEBGL);
        p.background(0);
        p.noStroke();

        // Setup WebSocket connection
        ws.current = new WebSocket('ws://localhost:8765');
        ws.current.onopen = () => console.log("WebSocket is open now.");
        ws.current.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data && Array.isArray(data)) {
            data.forEach(person => {
              person.keypoints.forEach(keypoint => {
                if (keypoint.label === "right_wrist") {
                  const currentX = keypoint.x;
                  const currentY = keypoint.y;
                  const deltaX = currentX - previousPosition.current.x;
                  const deltaY = currentY - previousPosition.current.y;

                  // Invert the spin for both x and y-coordinate changes
                  velocity.current.x = deltaY * sensitivity;  // Correctly invert y-axis to x rotation
                  velocity.current.y = -deltaX * sensitivity;  // Invert x-axis to y rotation

                  previousPosition.current.x = currentX;
                  previousPosition.current.y = currentY;
                }
              });
            });
          }
        };
        ws.current.onerror = (error) => console.log("WebSocket Error:", error);
        ws.current.onclose = () => console.log("WebSocket is closed now.");
      };

      p.draw = () => {
        p.background(0);

        // Use a single directional light
        p.ambientLight(500); // Add ambient light to evenly illuminate the globe
        // p.pointLight(255, 255, 255, 0, 0, 1000);

        p.specularMaterial(50); // Specular material to give the globe a natural shine

        p.translate(0, 0, 0);

        // Update angles based on velocity
        angleX += velocity.current.x;  // Apply x rotation based on y movement
        angleY += velocity.current.y;  // Apply y rotation based on x movement
        // Apply friction
        velocity.current.x *= friction;
        velocity.current.y *= friction;

        // Apply rotation
        p.rotateX(-angleX); // Invert direction for intuitive control
        p.rotateY(angleY);

        if (globe) {
          p.texture(globe);
        }
        p.sphere(200); // Draw the globe
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

export default Interactive3D;
