import React, { useEffect, useRef, useState } from 'react';
import p5 from 'p5';

const People = () => {
  const sketchRef = useRef();
  const [people, setPeople] = useState([]);

  useEffect(() => {
    const sketch = (p) => {
      let ws;

      p.setup = () => {
        p.createCanvas(p.windowWidth, p.windowHeight);
        p.background(255);

        // Connect to the WebSocket
        ws = new WebSocket('ws://localhost:8765');
        ws.onopen = () => {
          console.log("WebSocket is open now.");
        };
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);

          // Check if keypoints property exists and is an array
          if (data && Array.isArray(data)) {
            // Update people data
            const newPeople = [];
            data.forEach(person => {
              if (person.keypoints && Array.isArray(person.keypoints)) {
                const newPerson = [];
                person.keypoints.forEach(keypoint => {
                  newPerson.push({
                    x: keypoint.x,
                    y: keypoint.y,})
                });
                newPeople.push(newPerson);
              }
            });
            setPeople(newPeople);
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

      let colorInd = 0;
      const colors = [[255, 0, 0], [255, 127, 0], [255, 255, 0], [0, 255, 0], [0, 255, 255], [0, 0, 255], [127, 0, 255], [255, 0, 255]];
      p.draw = () => {
        p.background(255); // Clear the background

        for (let person of people) {
            p.fill(colors[colorInd][0], colors[colorInd][1], colors[colorInd][2]); // Color for the circles
            p.noStroke();

            for (let keypoint of person) {
                p.ellipse(keypoint.x, keypoint.y, 10, 10); // Draw the circle
            }
            colorInd++;
        }

        colorInd = 0;
      };
    };

    const myP5 = new p5(sketch, sketchRef.current);

    return () => {
      myP5.remove();
    };
  }, [people]);

  return <div ref={sketchRef}></div>;
};

export default People;
