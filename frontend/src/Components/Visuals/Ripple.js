import React, { useEffect, useRef, useState } from 'react';
import p5 from 'p5';

const Ripple = () => {
  const sketchRef = useRef();
  const [people, setPeople] = useState([]);

  useEffect(() => {
    let ws;
    const sketch = (p) => {
      
      let rings = [];
      let color1, color2; // Declare color variables in the p5 instance scope

      class Ring {
        constructor(x, y) {
          this.x = x;
          this.y = y;
          this.radius = 0;
          this.alpha = 255; // Start fully visible
        }

        update() {
          this.radius += 2; // Control the speed of the radius expansion
          this.alpha -= 5; // Slower fade
        }

        show() {
          p.noFill();
          p.stroke(255, 255, 255, this.alpha);
          p.strokeWeight(2);
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
        color1 = p.color(0, 50, 100); // Initialize colors in setup
        color2 = p.color(0, 100, 200);

        ws = new WebSocket('ws://localhost:8765');
        ws.onopen = () => console.log("WebSocket is open now.");
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data && Array.isArray(data)) {
            data.forEach(person => {
              if (person.keypoints && Array.isArray(person.keypoints)) {
                person.keypoints.forEach(keypoint => {
                  rings.push(new Ring(keypoint.x, keypoint.y));
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
        setGradient(0, 0, p.width, p.height, color1, color2, p.Y_AXIS); // Use the color variables
        rings = rings.filter(ring => !ring.isDead());
        rings.forEach(ring => {
          ring.update();
          ring.show();
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

export default Ripple;
