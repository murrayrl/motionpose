import React, { useEffect, useRef, useState } from 'react';
import p5 from 'p5';

const Stick = () => {
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
                const newPerson = {};
                person.keypoints.forEach(keypoint => {
                  newPerson[keypoint.label] = {
                    x: keypoint.x,
                    y: keypoint.y,
                  };
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

      console.log(people);

      p.draw = () => {
        p.background(255); // Clear the background
        p.noStroke();

        let max_upper = 0;
        let max_lower = 0;
        
        for (let person of people) {
            // draw the head
            if (('left_eye' in person) &&
                ('right_eye' in person) &&
                ('nose' in person)) {
                const face_width = 1.5 * (Math.abs(person['left_eye'].x - person['right_eye'].x)); 
                // Save the current state (translation/rotation/etc)
                p.push();
                // Translate to the origin of the shape
                p.translate(person['nose'].x, person['nose'].y);
                // Rotate around the origin
                const eye_dist = Math.sqrt(Math.pow(person['left_eye'].x - person['right_eye'].x, 2) + Math.pow(person['left_eye'].y - person['right_eye'].y, 2))
                const angle_degrees = Math.sin((person['left_eye'].y - person['right_eye'].y) / eye_dist); 
                p.fill(0, 0, 0); // Eye
                
                p.rotate(angle_degrees);
                p.ellipse(0, 0, face_width * 4 / 3, face_width);  
                p.pop();

                p.fill(0, 0, 0); // Eye
                p.arc(person['nose'].x, person['nose'].y + (face_width * .65), (face_width * 4 / 3)/2, face_width / 4, 0, 3.14);

                p.fill(129, 105, 130); // Purple eye markings
                
                p.ellipse(person['nose'].x, person['nose'].y + 200, 50, 200);
                p.ellipse(person['nose'].x, person['nose'].y - 200, 50, 100);
              // p.ellipse(person['nose'].x, person['nose'].y, face_width, face_width * 4 / 3);
            }
        }

        
        if (people[0] && people[1]) {
          const h_center = Math.abs((people[0]['nose'].x + people[1]['nose'].x))/2;
          const v_center =  Math.abs((people[0]['nose'].y + people[1]['nose'].y)) / 2;
          
          p.fill(0, 0, 0); // Black for mouth
          // Drawing the mouth
          p.arc(h_center, v_center + 400, Math.abs(people[0]['nose'].x - people[1]['nose'].x), 50,  0, 3.14);
          p.arc(h_center, v_center + 440, 70, 20,  0, 3.14);

          // p.fill(201, 196, 193); // face
          // p.rect(h_center, v_center, 100, 55);
        }


        // for (let keypoint of people) {
        //   p.ellipse(keypoint.x, keypoint.y, 10, 10); // Draw the circle
        // }
      };
    };

    const myP5 = new p5(sketch, sketchRef.current);

    return () => {
      myP5.remove();
    };
  }, [people]);

  return <div ref={sketchRef}></div>;
};

export default Stick;
