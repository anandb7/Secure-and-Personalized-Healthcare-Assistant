import React from 'react';
import './buttons.css';

export default function Buttons({ testNames, handleButtonClick, selectedTests }) {
  return (
    <div className="buttons-container">
      {testNames.map((testName) => (
        <button
          key={testName}
          className={`test-button ${selectedTests.includes(testName) ? 'selected' : ''}`}
          onClick={() => handleButtonClick(testName)}
        >
          {testName}
        </button>
      ))}
      <button className="ok-button" onClick={() => handleButtonClick('OK')}>OK</button>
    </div>
  );
}
