import React from 'react';
import Basic from './Basic';
import Ripple from './Ripple';
import Interactive3D from './Interactive3D';
import Bubbles from './Bubbles';
import Terrain from './Terrain';

const Visuals = ({ visual }) => {
  return (
    <div className="visuals">
      {visual === 'basic' && <Basic />}
      {visual === 'ripple' && <Ripple />}
      {visual === '3d' && <Interactive3D />}
      {visual === 'bubbles' && <Bubbles />}
      {visual === 'terrain' && <Terrain/>}
    </div>
  );
};

export default Visuals;
