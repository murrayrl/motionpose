import React from 'react';
import Basic from './Basic';
import Ripple from './Ripple';
import Interactive3D from './Interactive3D';
<<<<<<< HEAD
import Bubbles from './Bubbles';
import Terrain from './Terrain';
=======
import CherryBlossomVisual from './CherryBlossomVisual';
import Droplets from './Droplets';
>>>>>>> b17f81bec6329ba229c90d4b49925d861ac3c282

const Visuals = ({ visual }) => {
  return (
    <div className="visuals">
      {visual === 'basic' && <Basic />}
      {visual === 'ripple' && <Ripple />}
      {visual === '3d' && <Interactive3D />}
<<<<<<< HEAD
      {visual === 'bubbles' && <Bubbles />}
      {visual === 'terrain' && <Terrain/>}
=======
      {visual === 'cherry-blossom' && <CherryBlossomVisual/>}
      {visual === 'droplets' && <Droplets/>}



>>>>>>> b17f81bec6329ba229c90d4b49925d861ac3c282
    </div>
  );
};

export default Visuals;
