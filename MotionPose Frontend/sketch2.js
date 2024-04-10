let flies = []; // fireflies method
let population = 20;

let socket; // WebSocket for receiving coordinates
let previousCoordinates = { x: 0, y: 0, z: 0 }; // Initial coordinates

function setup() {
  createCanvas(windowWidth, windowHeight);
  for (let i = 0; i < population; i++) {
    flies.push(new firefly());
  }

  // Connect to the WebSocket server
  socket = new WebSocket('ws://localhost:5678');

  // Set up WebSocket event listeners
  socket.onmessage = function(event) {
    var message = JSON.parse(event.data);
    previousCoordinates.x = message.x;
    previousCoordinates.y = message.y;
    previousCoordinates.z = message.z;
  };

  socket.onopen = function(event) {
    console.log('Connected to WebSocket server.');
  };

  socket.onerror = function(event) {
    console.error('WebSocket error:', event);
  };
}

function draw() {
  background(0, 5, 15, 255);
  for (let i = 0; i < flies.length; i++) {
    flies[i].update();
  }
}

function firefly() {
    this.x = random(width);
    this.y = random(height);
    this.xoff = random(100);
    this.yoff = random(100);
    this.prevX = this.x;
    this.prevY = this.y;
    this.wave = random(5);
    this.rate = random(0.05, 0.1);
    this.roff = random(2);
    this.risepol = 1;
    this.toff = random(25);
  
    this.update = function() {
      // Map the Y and Z coordinates to control the direction
      let dirX = map(previousCoordinates.y, 0, 1000, -1, 1);
      let dirY = map(previousCoordinates.z, 0, 1000, -1, 1);
  
      // Update noise offsets based on the direction
      this.xoff += dirX * 0.01;
      this.yoff += dirY * 0.01;
  
      // Constrain the fireflies to fly within a small range
      this.x = constrain(this.x + map(noise(this.xoff), 0, 1, -1, 1), this.prevX - 5, this.prevX + 5);
      this.y = constrain(this.y + map(noise(this.yoff), 0, 1, -1, 1), this.prevY - 5, this.prevY + 5);
  
      // Flashing
      this.wave += this.rate;
      let flash = abs(sin(this.wave) * 255);
      let falpha = map(flash, 0, 255, 50, 155);
  
      // Map the distance coordinate to control the color
      let hue = map(previousCoordinates.z, 0, 1000, 0, 359);
  
      // Display the firefly
      push();
      translate(this.x, this.y);
  
      // Wings
      this.roff += 2;
      let r = map(sin(this.roff), -1, 1, -PI * 0.25, PI * 0.25);
      strokeWeight(2);
      let winglen = 12;
      push(); // Right wing
      stroke(255, 200, 0, 125);
      rotate(r);
      line(0, 0, -winglen, 0);
      pop();
  
      push(); // Left wing
      stroke(255, 200, 0, 125);
      rotate(-r);
      line(0, 0, winglen, 0);
      pop();
  
      let size = map(flash, 0, 255, 10, 25);
      strokeWeight(size);
      stroke(hue, 100, 100, falpha);
      point(0, 0); // Halo
  
      strokeWeight(size * 0.25);
      stroke(255, 255, 0, 255);
      point(0, 0); // Light source
      pop();
    };
  }
