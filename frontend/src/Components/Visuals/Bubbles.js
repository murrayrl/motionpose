import React, { useEffect, useRef } from 'react';
import p5 from 'p5';

const Bubbles = () => {
  const sketchRef = useRef();
  const previousPosition = useRef({ x: 0, y: 0 });
  const ws = useRef(null);
  const sensitivity = 10; // Increase this value to make collision detection more sensitive

  useEffect(() => {
    const sketch = new p5((p) => {
      let numBalls = 13;
      let spring = 0.05;
      let gravity = 0.03;
      let friction = -0.9;
      let balls = [];

      class Ball {
        constructor(xin, yin, din, idin, oin, sensitivity) {
          this.x = xin;
          this.y = yin;
          this.vx = 0;
          this.vy = 0;
          this.diameter = din;
          this.id = idin;
          this.others = oin;
          this.sensitivity = sensitivity;
        }

        collide() {
          for (let i = this.id + 1; i < numBalls; i++) {
            let dx = this.others[i].x - this.x;
            let dy = this.others[i].y - this.y;
            let distance = p.sqrt(dx * dx + dy * dy);
            let minDist = this.others[i].diameter / 2 + this.diameter / 2;
            if (distance < minDist) {
              let angle = p.atan2(dy, dx);
              let targetX = this.x + p.cos(angle) * minDist;
              let targetY = this.y + p.sin(angle) * minDist;
              let ax = (targetX - this.others[i].x) * spring;
              let ay = (targetY - this.others[i].y) * spring;
              this.vx -= ax;
              this.vy -= ay;
              this.others[i].vx += ax;
              this.others[i].vy += ay;
            }
          }
        }

        move() {
          this.vy += gravity;
          this.x += this.vx;
          this.y += this.vy;
          if (this.x + this.diameter / 2 > p.width) {
            this.x = p.width - this.diameter / 2;
            this.vx *= friction;
          } else if (this.x - this.diameter / 2 < 0) {
            this.x = this.diameter / 2;
            this.vx *= friction;
          }
          if (this.y + this.diameter / 2 > p.height) {
            this.y = p.height - this.diameter / 2;
            this.vy *= friction;
          } else if (this.y - this.diameter / 2 < 0) {
            this.y = this.diameter / 2;
            this.vy *= friction;
          }
        }

        display() {
          p.ellipse(this.x, this.y, this.diameter, this.diameter);
        }

        isColliding(x, y) {
          let distance = p.dist(this.x, this.y, x, y);
          return distance < (this.diameter / 2 + this.sensitivity);
        }
      }

      p.setup = () => {
        p.createCanvas(p.windowWidth, p.windowHeight);
        for (let i = 0; i < numBalls; i++) {
          balls[i] = new Ball(
            p.random(p.width),
            p.random(p.height),
            p.random(30, 70),
            i,
            balls,
            sensitivity
          );
        }
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

        // Check for collisions with the right wrist keypoint and remove colliding bubbles
        balls = balls.filter(ball => !ball.isColliding(previousPosition.current.x, previousPosition.current.y));

        // Draw bubbles
        p.fill(255, 204);  // Reset fill color to white for the bubbles
        balls.forEach(ball => {
          ball.collide();
          ball.move();
          ball.display();
        });

        // Draw right wrist keypoint as a red dot
        p.fill(255, 0, 0);  // Set fill color to red for the right wrist keypoint
        p.ellipse(previousPosition.current.x, previousPosition.current.y, 10, 10);
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

export default Bubbles;