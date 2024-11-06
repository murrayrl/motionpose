

import React, { useEffect, useRef, useState } from 'react';
import p5 from 'p5';

const FallingSnow = () => {
  const sketchRef = useRef();
  const [people, setPeople] = useState([]);

  useEffect(() => {
    let ws;
    const sketch = (p) => {
      
      let snowflakes = [];
      let color1, color2; // Declare color variables in the p5 instance scope

      class Snowflake {
        constructor(x, y) {
          this.x = x;
          this.y = y;
          this.radius = p.random(2, 5); // Randomize snowflake size
          this.alpha = 255; // Start fully visible
          this.speed = p.random(0.5, 2); // Randomize fall speed
        }

        update() {
          this.y += this.speed; // Snowflake falling speed
          this.alpha -= 1; // Slow fading
          if (this.y > p.height) {
            this.y = 0; // Reset snowflake to the top
          }
        }

        show() {
          p.noStroke();
          p.fill(255, 255, 255, this.alpha);
          p.ellipse(this.x, this.y, this.radius * 2);
        }

        isDead() {
          return this.alpha <= 0;
        }
      }

      function setGradient(x, y, w, h, c1, c2, axis) {
        p.noFill();
        for (let i = y; i <= y + h; i++) {
          let inter = p.map(i, y, y + h, 0, 1);
          let c = p.lerpColor(c1, c2, inter);
          p.stroke(c);
          p.line(x, i, x + w, i);
        }
      }

      p.setup = () => {
        p.createCanvas(p.windowWidth, p.windowHeight);
        color1 = p.color(10, 10, 50); // Darker blue background
        color2 = p.color(100, 150, 255); // Lighter blue transition

        ws = new WebSocket('ws://localhost:8765');
        ws.onopen = () => console.log("WebSocket is open now.");
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data && Array.isArray(data)) {
            data.forEach(person => {
              if (person.keypoints && Array.isArray(person.keypoints)) {
                person.keypoints.forEach(keypoint => {
                  snowflakes.push(new Snowflake(keypoint.x, keypoint.y)); // Snowflakes created from keypoints
                });
              }
            });
          } else {
            console.error("Invalid data format:", data);
          }
        };
        ws.onerror = (error) => console.log("WebSocket Error:", error);
        ws.onclose = () => console.log("WebSocket is closed now.");
      };

      p.draw = () => {
        p.clear();
        setGradient(0, 0, p.width, p.height, color1, color2, p.Y_AXIS); // Gradient background
        snowflakes = snowflakes.filter(flake => !flake.isDead());
        snowflakes.forEach(flake => {
          flake.update();
          flake.show();
        });
      };
    };

    const myP5 = new p5(sketch, sketchRef.current);

    return () => {
      myP5.remove();
      ws && ws.close();
    };
  }, []);  // Empty dependency array to prevent recreating the p5 instance on every render

  return <div ref={sketchRef}></div>;
};

export default FallingSnow;