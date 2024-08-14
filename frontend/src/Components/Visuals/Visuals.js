import React, { useState, useEffect } from 'react';
import Basic from './Basic';
import Ripple from './Ripple';
import Interactive3D from './Interactive3D';
import CherryBlossomVisual from './CherryBlossomVisual';
import Droplets from './Droplets';
import Bubbles from './Bubbles';
import Terrain from './Terrain';

const visualsList = [
  'basic',
  'ripple',
  '3d',
  // 'cherry-blossom',
  'droplets',
  'bubbles',
  'terrain',
];

const Visuals = ({ visual, setSelectedVisual }) => {
  const [currentVisualIndex, setCurrentVisualIndex] = useState(visualsList.indexOf(visual));

  useEffect(() => {
    // Get the visual from local storage if it exists
    const storedVisual = localStorage.getItem('currentVisual');
    if (storedVisual && visualsList.includes(storedVisual)) {
      setCurrentVisualIndex(visualsList.indexOf(storedVisual));
      setSelectedVisual(storedVisual);
    }
  }, [setSelectedVisual]);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentVisualIndex((prevIndex) => (prevIndex + 1) % visualsList.length);
    }, 60000); // 60000 milliseconds = 1 minute

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const currentVisual = visualsList[currentVisualIndex];
    if (currentVisual !== visual) {
      setSelectedVisual(currentVisual);
      localStorage.setItem('currentVisual', currentVisual);
      window.location.reload(); // Reload the browser when the visual changes
    }
  }, [currentVisualIndex, visual, setSelectedVisual]);

  const currentVisual = visualsList[currentVisualIndex];

  return (
    <div className="visuals">
      {currentVisual === 'basic' && <Basic />}
      {currentVisual === 'ripple' && <Ripple />}
      {currentVisual === '3d' && <Interactive3D />}
      {/* {currentVisual === 'cherry-blossom' && <CherryBlossomVisual />} */}
      {currentVisual === 'droplets' && <Droplets />}
      {currentVisual === 'bubbles' && <Bubbles />}
      {currentVisual === 'terrain' && <Terrain />}
    </div>
  );
};

export default Visuals;
