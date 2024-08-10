import React, { Component } from 'react';
import p5 from 'p5';

class Terrain extends Component {
  constructor(props) {
    super(props);
    this.myRef = React.createRef();
    this.state = {
      people: []
    };
  }

  componentDidMount() {
    this.myP5 = new p5(this.sketch, this.myRef.current);

    // Initialize WebSocket
    this.ws = new WebSocket('ws://localhost:8765');
    this.ws.onopen = () => console.log("WebSocket is open now.");
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data && Array.isArray(data)) {
        this.setState({ people: data });
      } else {
        console.error("Invalid data format:", data);
      }
    };
    this.ws.onerror = (error) => console.log("WebSocket Error:", error);
    this.ws.onclose = () => console.log("WebSocket is closed now.");
  }

  componentWillUnmount() {
    this.myP5.remove();  // Clean up the p5 instance on unmount
    this.ws.close();     // Close WebSocket connection
  }

  sketch = (p) => {
    let terrain = [];
    let baseTerrain = [];
    let cols, rows;
    const scl = 20;
    const w = 1400;
    const h = 1000;
    let spreadFactor = 1;

    p.setup = () => {
      p.createCanvas(p.windowWidth, p.windowHeight, p.WEBGL);
      cols = Math.floor(w / scl);
      rows = Math.floor(h / scl);

      // Initialize terrain
      for (let x = 0; x < cols; x++) {
        terrain[x] = [];
        baseTerrain[x] = [];
        for (let y = 0; y < rows; y++) {
          baseTerrain[x][y] = p.map(p.noise(x * 0.2, y * 0.2), 0, 1, -100, 100);
          terrain[x][y] = baseTerrain[x][y];
        }
      }
    };

    p.draw = () => {
      p.background(0);  // Clear the background

      // Calculate arm spread and update spreadFactor
      if (this.state.people.length > 0) {
        const leftHand = this.state.people.find(point => point.label === 'left_wrist');
        const rightHand = this.state.people.find(point => point.label === 'right_wrist');
        if (leftHand && rightHand) {
          const armSpread = p.dist(leftHand.x, leftHand.y, rightHand.x, rightHand.y);
          spreadFactor = p.map(armSpread, 0, p.windowWidth, 0.5, 2);
        }
      }

      // Update terrain heights based on spreadFactor
      for (let x = 0; x < cols; x++) {
        for (let y = 0; y < rows; y++) {
          terrain[x][y] = baseTerrain[x][y] * spreadFactor;
        }
      }

      p.stroke(255);
      p.noFill();
      p.translate(0, 50);
      p.rotateX(p.PI / 3);
      p.translate(-w / 2, -h / 2);

      for (let y = 0; y < rows - 1; y++) {
        p.beginShape(p.TRIANGLE_STRIP);
        for (let x = 0; x < cols; x++) {
          p.vertex(x * scl, y * scl, terrain[x][y]);
          p.vertex(x * scl, (y + 1) * scl, terrain[x][y + 1]);
        }
        p.endShape();
      }
    };

    p.windowResized = () => {
      p.resizeCanvas(p.windowWidth, p.windowHeight);
    };
  }

  render() {
    return <div ref={this.myRef}></div>;
  }
}

export default Terrain;
