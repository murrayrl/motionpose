var limit = 4; //Turn this up for less lag. A good number for smooth animation is 4
var sizeMult = 0.26; //Fractal size relative to screen. Larger multipliers will increase detail
var brLenRatio = 0.67; //Size of child branch relative to parent
var canvasSize = 600;
var previousCoordinates = { x: 0, y: 0 };

function setup() {
  createCanvas(canvasSize, canvasSize);
  colorMode(HSB, 255);
}

function draw() {
  background(50);

  // Use the mouse coordinates to adjust the angle and length
  let angle = map(mouseX, 0, width, 0, TWO_PI);
  let length = map(mouseY, 0, height, 0, height * sizeMult);

  // Calculate the rate of change of the coordinates
  let rateOfChange = dist(mouseX, mouseY, previousCoordinates.x, previousCoordinates.y);

  // Adjust the fractal's color based on the rate of change
  let hue = map(rateOfChange, 0, 50, 0, 255);
  stroke(hue, 255, 255);

  translate(width / 2, height);
  branch(length, angle);

  // Update previous coordinates for the next frame
  previousCoordinates = { x: mouseX, y: mouseY };
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
