import React, { useState } from 'react';
import './Sidebar.css';

const Sidebar = ({ setSelectedVisual, selectedVisual }) => {
  const [isOpen, setIsOpen] = useState(true);

  const toggleSidebar = () => {
    setIsOpen(!isOpen);
  };

  const visualsList = [
    { name: 'Basic', value: 'basic' },
    { name: 'Ripple', value: 'ripple' },
    { name: '3D', value: '3d' },
    // { name: 'Cherry Blossom', value: 'cherry-blossom' },
    { name: 'Droplets', value: 'droplets' },
    { name: 'Bubbles', value: 'bubbles' },
    { name: 'Terrain', value: 'terrain' },
  ];

  return (
    <div className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      <button onClick={toggleSidebar}>
        {isOpen ? 'Collapse' : 'Expand'}
      </button>
      <ul>
        {visualsList.map((visual) => (
          <li
            key={visual.value}
            onClick={() => setSelectedVisual(visual.value)}
            className={selectedVisual === visual.value ? 'active' : ''}
          >
            {visual.name}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Sidebar;
