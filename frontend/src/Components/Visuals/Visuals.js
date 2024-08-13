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
  'cherry-blossom',
  'droplets',
  'bubbles',
  'terrain',
];

const Visuals = ({ visual, setSelectedVisual }) => {
  const [currentVisualIndex, setCurrentVisualIndex] = useState(visualsList.indexOf(visual));

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentVisualIndex((prevIndex) => (prevIndex + 1) % visualsList.length);
    }, 60000); // 60000 milliseconds = 1 minute

    // Clear the interval on component unmount
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    setSelectedVisual(visualsList[currentVisualIndex]);
  }, [currentVisualIndex, setSelectedVisual]);

  return (
    <div className="visuals">
      {visual === 'basic' && <Basic />}
      {visual === 'ripple' && <Ripple />}
      {visual === '3d' && <Interactive3D />}
      {visual === 'cherry-blossom' && <CherryBlossomVisual />}
      {visual === 'droplets' && <Droplets />}
      {visual === 'bubbles' && <Bubbles />}
      {visual === 'terrain' && <Terrain />}
    </div>
  );
};

export default Visuals;
