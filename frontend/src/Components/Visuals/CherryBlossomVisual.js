import React, { useEffect, useRef } from 'react';
import p5 from 'p5';

const CherryBlossomVisual = () => {
  const sketchRef = useRef();
  const ws = useRef(null);

  useEffect(() => {
    const sketch = new p5((p) => {
      let blossoms = [];
      let img;
      let windX = 0;
      let windY = 0;

      class Blossom {
        constructor(x, y) {
          this.x = x;
          this.y = y;
          this.size = p.random(10, 20);
          this.speed = p.createVector(p.random(-1, 1), p.random(2, 5)); // Increase falling speed
          this.alpha = 255; // Start fully visible
        }

        update() {
          this.x += this.speed.x + windX;
          this.y += this.speed.y + windY;
          this.alpha -= 1; // Fade out slowly
          if (this.y > p.height) {
            this.y = -10;
            this.x = p.random(p.width);
          }
          if (this.y < -10) {
            this.y = p.height + 10;
            this.x = p.random(p.width);
          }
          if (this.x > p.width) {
            this.x = -10;
            this.y = p.random(p.height);
          }
          if (this.x < -10) {
            this.x = p.width + 10;
            this.y = p.random(p.height);
          }
        }

        show() {
          p.tint(255, this.alpha);
          p.image(img, this.x, this.y, this.size, this.size);
        }

        isDead() {
          return this.alpha <= 0;
        }
      }

      p.preload = () => {
        img = p.loadImage('/Images/cherry-blossom.png', () => {
          console.log("Image loaded successfully");
        }, (err) => {
          console.error("Error loading image", err);
        });
      };

      p.setup = () => {
        p.createCanvas(p.windowWidth, p.windowHeight);
        for (let i = 0; i < 200; i++) { // Increase the number of initial petals
          blossoms.push(new Blossom(p.random(p.width), p.random(-p.height, p.height)));
        }

        ws.current = new WebSocket('ws://localhost:8765');
        ws.current.onopen = () => console.log("WebSocket is open now.");
        ws.current.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data && Array.isArray(data)) {
            data.forEach(person => {
              if (person.keypoints && Array.isArray(person.keypoints)) {
                person.keypoints.forEach(keypoint => {
                  if (keypoint.label === "right_wrist") {
                    if (keypoint.x < 300) {
                      windX = 5; // Move petals to the right
                    } else if (keypoint.x > 300) {
                      windX = -5; // Move petals to the left
                    } else {
                      windX = 0; // No movement
                    }
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
        p.clear();
        blossoms = blossoms.filter(blossom => !blossom.isDead());
        blossoms.forEach(blossom => {
          blossom.update();
          blossom.show();
        });

        // Generate new blossoms periodically
        if (p.frameCount % 5 === 0) { // Increase the frequency of new petals
          blossoms.push(new Blossom(p.random(p.width), -10));
        }
      };
    }, sketchRef.current);

    return () => {
      sketch.remove();
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []); // Empty dependency array to prevent recreating the p5 instance on every render

  return <div ref={sketchRef} style={{ width: '100%', height: '100%' }}></div>;
};

export default CherryBlossomVisual;
