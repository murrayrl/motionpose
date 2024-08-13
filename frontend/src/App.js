import React, { useState } from 'react';
import Sidebar from './Components/Sidebar/Sidebar';
import Visuals from './Components/Visuals/Visuals';
import './App.css';

function App() {
  const [selectedVisual, setSelectedVisual] = useState('basic');

  return (
    <div className="App">
      <Sidebar setSelectedVisual={setSelectedVisual} />
      <div className="main-view">
        <Visuals visual={selectedVisual} setSelectedVisual={setSelectedVisual} />
      </div>
    </div>
  );
}

export default App;
