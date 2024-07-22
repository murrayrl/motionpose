import React from 'react';
import Basic from './Basic';

const Visuals = ({ visual }) => {
  return (
    <div className="visuals">
      {visual === 'basic' && <Basic />}
    </div>
  );
};

export default Visuals;
