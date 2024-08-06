import React, { useState } from 'react';
import './Sidebar.css';

const Sidebar = ({ setSelectedVisual }) => {
  const [isOpen, setIsOpen] = useState(true);

  const toggleSidebar = () => {
    setIsOpen(!isOpen);
  };

  return (
    <div className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      <button onClick={toggleSidebar}>
        {isOpen ? 'Collapse' : 'Expand'}
      </button>
        <ul>
            <li onClick={() => setSelectedVisual('basic')}>Basic</li>
            <li onClick={() => setSelectedVisual('ripple')}>Ripple</li>
            <li onClick={() => setSelectedVisual('3d')}>3D</li>
            <li onClick={() => setSelectedVisual('cherry-blossom')}>Cherry Blossom</li>
            <li onClick={() => setSelectedVisual('droplets')}>Droplets</li>


        </ul>
    </div>
  );
};

export default Sidebar;
