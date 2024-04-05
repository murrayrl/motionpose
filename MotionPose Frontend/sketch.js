var limit = 4; //Turn this up for less lag. A good number for smooth animation is 4
var sizeMult = 0.26; //Fractal size relative to screen. Larger multipliers will increase detail
var brLenRatio = 0.67; //Size of child branch relative to parent
var canvasSize = 600;
var previousCoordinates = { x: canvasSize / 2, y: canvasSize / 2 }; // Start at the center

var socket;

function setup() {
  createCanvas(canvasSize, canvasSize);
  colorMode(HSB, 255);

  // Connect to the WebSocket server
  socket = new WebSocket('ws://localhost:5678');

  // Set up WebSocket event listeners
  socket.onmessage = function(event) {
    var message = JSON.parse(event.data);
    previousCoordinates.x = message.x;
    previousCoordinates.y = message.y;
  };

  socket.onopen = function(event) {
    console.log('Connected to WebSocket server.');
  };

  socket.onerror = function(event) {
    console.error('WebSocket error:', event);
  };
}

function draw() {
  background(50);

  // Use the received coordinates to adjust the angle and length
  let angle = map(previousCoordinates.x, 0, width, 0, TWO_PI);
  let length = map(previousCoordinates.y, 0, height, 0, height * sizeMult);

  // Calculate the rate of change of the coordinates
  let rateOfChange = dist(previousCoordinates.x, previousCoordinates.y, previousCoordinates.x, previousCoordinates.y);

  // Adjust the fractal's color based on the rate of change
  let hue = map(rateOfChange, 0, 50, 0, 255);
  stroke(hue, 255, 255);

  translate(width / 2, height);
  branch(length, angle);
}

function branch(length, angle) {
  line(0, 0, 0, -length);
  translate(0, -length);

  push();
  rotate(angle);
  if (length > limit) {
    branch(length * brLenRatio, angle);
  }
  pop();

  push();
  rotate(-angle);
  if (length > limit) {
    branch(length * brLenRatio, angle);
  }
  pop();
}
