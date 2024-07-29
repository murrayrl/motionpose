import React from 'react';
import Basic from './Basic';
import Ripple from './Ripple';

const Visuals = ({ visual }) => {
  return (
    <div className="visuals">
      {visual === 'basic' && <Basic />}
      {visual === 'ripple' && <Ripple />}
    </div>
  );
};

export default Visuals;
