var limit = 4; // Turn this up for less lag. A good number for smooth animation is 4
var sizeMult = 0.26; // Fractal size relative to screen. Larger multipliers will increase detail
var brLenRatio = 0.67; // Size of child branch relative to parent
var canvasSize = 600;
var previousCoordinates = { x: canvasSize / 2, y: canvasSize / 2 };
var externalX = canvasSize / 2; // Default external X-coordinate
var externalY = canvasSize / 2; // Default external Y-coordinate

function setup() {
  createCanvas(canvasSize, canvasSize);
  colorMode(HSB, 255);

  try {
    // Establish a connection to the WebSocket server
    const socket = new WebSocket('ws://localhost:5678');
    console.log("Attempting to connect to WebSocket server");
    console.log("socket: ", socket);

    // Connection opened event
    // Set up connection event handlers
    socket.onopen = function(event) {
      console.log('Connected to the WebSocket server');
    };

    // Listen for messages from the WebSocket server
    socket.onmessage = function(event) {
      console.log("Message received:", event.data);
      const data = JSON.parse(event.data);
      externalX = data.x;
      externalY = data.y;
    };

    // Connection closed event
    socket.onclose = function(event) {
      console.log('Disconnected from the WebSocket server :(');
    };

    // Handling any errors with the WebSocket
    socket.onerror = function(event) {
      console.error('WebSocket error observed:', event);
    };
  } catch (error) {
    console.error('WebSocket initialization failed:', error);
  }
}

function draw() {
  background(50);

  // Use the external coordinates to adjust the angle and length
  let angle = map(externalX, 0, width, 0, TWO_PI);
  let length = map(externalY, 0, height, 0, height * sizeMult);

  // Calculate the rate of change of the coordinates
  let rateOfChange = dist(externalX, externalY, previousCoordinates.x, previousCoordinates.y);

  // Adjust the fractal's color based on the rate of change
  let hue = map(rateOfChange, 0, 50, 0, 255);
  stroke(hue, 255, 255);

  translate(width / 2, height);
  branch(length, angle);

  // Update previous coordinates for the next frame
  previousCoordinates = { x: externalX, y: externalY };
}

function branch(length, angle) {
  line(0, 0, 0, -length);
  translate(0, -length);
  length *= brLenRatio;
  
  if (length > limit) {
    push();
    rotate(angle);
    branch(length, angle);
    pop();

    push();
    rotate(-angle);
    branch(length, angle);
    pop();
  }
}
