import React from 'react';
import Basic from './Basic';
import Ripple from './Ripple';
import Interactive3D from './Interactive3D';
import CherryBlossomVisual from './CherryBlossomVisual';
import Droplets from './Droplets';

const Visuals = ({ visual }) => {
  return (
    <div className="visuals">
      {visual === 'basic' && <Basic />}
      {visual === 'ripple' && <Ripple />}
      {visual === '3d' && <Interactive3D />}
      {visual === 'cherry-blossom' && <CherryBlossomVisual/>}
      {visual === 'droplets' && <Droplets/>}



    </div>
  );
};

export default Visuals;
