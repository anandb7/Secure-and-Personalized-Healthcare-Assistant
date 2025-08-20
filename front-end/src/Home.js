import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { Upload, Bot, User, Moon, Sun, Search } from 'lucide-react';
import './index.css';
import Buttons from './Buttons';

export default function Home() {
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    weight: '',
    height: '',
    refDoc: '',
    hba1c: '',
    creatinine: '',
    fastingGlucose: '',
    haemoglobin: '',
    pcv: '',
    rbcCount: ''
  });

  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [showTestButtons, setShowTestButtons] = useState(false);
  const [showYesNoButtons, setShowYesNoButtons] = useState(false);
  const [selectedTests, setSelectedTests] = useState([]);
  const [prescriptionLink, setPrescriptionLink] = useState('');
  const [labTestResults, setLabTestResults] = useState({});
  const ws = useRef(null);
  const [theme, setTheme] = useState('light');
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const [showProfileEdit, setShowProfileEdit] = useState(false);

  const initialTestNames = ["HBA1C", "Creatinine", "Fasting Glucose", "Haemoglobin", "PCV", "RBC Count"];

  useEffect(() => {
    document.body.className = theme === 'light' ? 'light-mode' : 'dark-mode';
  }, [theme]);

  useEffect(() => {
    ws.current = new WebSocket('ws://localhost:8000/ws');
    ws.current.onmessage = (event) => {
      const newMessage = event.data;
      setMessages((prevMessages) => [...prevMessages, { type: 'response', text: newMessage }]);
    };
    return () => {
      ws.current.close();
    };
  }, []);

  useEffect(() => {
    const welcomeMessageTimeout = setTimeout(() => {
      setMessages((prevMessages) => [...prevMessages, { type: 'response', text: 'HELLO WELCOME !!!' }]);
    }, 5000);
    return () => clearTimeout(welcomeMessageTimeout);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (file) {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await axios.post('http://localhost:8000/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        const data = response.data;

        const extractedData = data.data;
        const labTestResults = extractedData['Lab Test Results'];

        setFormData({
          name: extractedData['Patient Information'].name,
          age: extractedData['Patient Information'].age,
          weight: extractedData['Patient Information'].weight,
          height: extractedData['Patient Information'].height,
          refDoc: extractedData['Patient Information'].refDoc || 'Not found',
          hba1c: labTestResults['HBA1C, GLYCATED HEMOGLOBIN'],
          creatinine: labTestResults['CREATININE , SERUM'],
          fastingGlucose: labTestResults['GLUCOSE, FASTING , NAF PLASMA'],
          haemoglobin: labTestResults['HAEMOGLOBIN'],
          pcv: labTestResults['PCV'],
          rbcCount: labTestResults['RBC COUNT']
        });

        setLabTestResults(labTestResults);
        setSelectedTests(initialTestNames);
        setShowProfileEdit(true);

      } catch (error) {
        console.error('Error uploading file:', error);
      }
    }
  };

  const handleProfileUpdate = async () => {
    try {
      await axios.post('http://localhost:8000/update_profile', formData);
      setShowProfileEdit(false);
      setMessages((prevMessages) => [...prevMessages, { type: 'response', text: 'Do you want additional results to be included in your analysis or is this enough?' }]);
      setShowYesNoButtons(true);
    } catch (error) {
      console.error('Error updating profile:', error);
    }
  };

  const handleSendMessage = () => {
    if (inputValue.toLowerCase() === 'yes') {
      handleYesClick();
    } else if (inputValue.toLowerCase() === 'no') {
      handleNoClick();
    }

    if (inputValue) {
      setMessages((prevMessages) => [...prevMessages, { type: 'user', text: inputValue }]);
      ws.current.send(inputValue);
      setInputValue('');
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter') {
      handleSendMessage();
    }
  };

  const handleButtonClick = async (testName) => {
    if (testName === 'OK') {
      setShowTestButtons(false);
      try {
        const response = await axios.post('http://localhost:8000/update_analysis', selectedTests);
        const updatedAnalysis = response.data.data;
        setMessages((prevMessages) => [...prevMessages, { type: 'response', text: `Prescription based on the selected tests is being generated.` }]);
        generatePrescription(true);

      } catch (error) {
        console.error('Error updating analysis:', error);
      }
    } else if (!selectedTests.includes(testName)) {
      setSelectedTests([...selectedTests, testName]);
      setMessages((prevMessages) => [...prevMessages, { type: 'user', text: `${testName} selected` }]);
    } else {
      setSelectedTests(selectedTests.filter(test => test !== testName));
    }
  };

  const handleYesClick = () => {
    setShowTestButtons(true);
    setShowYesNoButtons(false);
    setMessages((prevMessages) => [...prevMessages, { type: 'user', text: 'Yes' }]);
  };

  const handleNoClick = async () => {
    setShowTestButtons(false);
    setMessages((prevMessages) => [...prevMessages, { type: 'user', text: 'No' }]);
    setMessages((prevMessages) => [...prevMessages, { type: 'response', text: 'Please wait for the prescription.' }]);
    setShowYesNoButtons(false);
    generatePrescription();
  };

  const generatePrescription = async (isUpdated = false) => {
    try {
      const response = await axios.post('http://localhost:8000/generate_prescription', { isUpdate: isUpdated });
      const filePath = response.data.file_path;
      setPrescriptionLink(filePath);
    } catch (error) {
      console.error('Error generating prescription:', error);
    }
  };

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  return (
    <div className={`container-fluid pt-5 ${theme}-mode`}>
      <nav className={`navbar navbar-expand-lg fixed-top ${theme}-mode`}>
        <div className="container-fluid">
          <Link to="/" className="navbar-brand nav-link">Site Name</Link>
          <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav"
            aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
            <span className="navbar-toggler-icon"></span>
          </button>
          <div className="collapse navbar-collapse" id="navbarNav">
            <ul className="navbar-nav ms-auto">
              <li className="nav-item">
                <Link to="/" className="nav-link" aria-current="page">Chat</Link>
              </li>
              <li className="nav-item">
                <Link to="/pricing" className="nav-link">Pricing</Link>
              </li>
              <li className="nav-item">
                <Link to="/about" className="nav-link">About</Link>
              </li>
              <li className="nav-item">
                <Link to="/contact" className="nav-link">Contact Us</Link>
              </li>
              <li className="nav-item">
                <button onClick={toggleTheme} className="btn btn-outline-secondary" style={{ border: 'none' }}>
                  {theme === 'light' ? <Moon size={25} /> : <Sun size={25} />}
                </button>
              </li>
            </ul>
          </div>
        </div>
      </nav>
      <div className="row">
        <div className={`col-md-7 p-3 chat-container ${theme}-mode`}>
          <div className={`chat-window d-flex flex-column ${theme}-mode`} ref={messagesContainerRef}>
            <div className="chat-content flex-grow-1 overflow-auto">
              <div className="messages">
                {messages.map((message, index) => (
                  <div key={index} className={`message ${message.type}`}>
                    {message.type === 'user' ? <User size={40} className="avatar" /> : <Bot size={40} className="avatar" />}
                    <span className="message-text">{message.text}</span>
                  </div>
                ))}
                <div ref={messagesEndRef} />
                {showYesNoButtons && (
                  <div className="yes-no-buttons">
                    <button onClick={handleYesClick} className="btn btn-primary">Yes</button>
                    <button onClick={handleNoClick} className="btn btn-secondary">No</button>
                  </div>
                )}
                {showTestButtons && (
                  <Buttons 
                    testNames={Object.keys(labTestResults).filter(test => !initialTestNames.includes(test.toUpperCase().replace(/ /g, '')))} 
                    handleButtonClick={handleButtonClick} 
                    selectedTests={selectedTests} 
                  />
                )}
                {showProfileEdit && (
                  <div className="profile-edit-container">
                    <h4 style={{ fontSize: '1.2em' }}>Is your profile information correct?</h4>
                    <div className="form-group">
                      <label>Name:</label>
                      <input type="text" className="form-control" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} />
                    </div>
                    <div className="form-group">
                      <label>Age:</label>
                      <input type="text" className="form-control" value={formData.age} onChange={(e) => setFormData({ ...formData, age: e.target.value })} />
                    </div>
                    <div className="form-group">
                      <label>Weight:</label>
                      <input type="text" className="form-control" value={formData.weight} onChange={(e) => setFormData({ ...formData, weight: e.target.value })} />
                    </div>
                    <div className="form-group">
                      <label>Height:</label>
                      <input type="text" className="form-control" value={formData.height} onChange={(e) => setFormData({ ...formData, height: e.target.value })} />
                    </div>
                    <button onClick={handleProfileUpdate} className="btn btn-primary">Continue</button>
                  </div>
                )}
              </div>
            </div>
            <div className="input-group mb-3 search-bar-container">
              <input
                type="text"
                className="form-control search-input"
                placeholder="Type a message..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                aria-label="Message input"
                onKeyPress={handleKeyPress}
              />
              <button className="btn btn-outline-secondary custom-button" type="button" onClick={handleSendMessage}>
                <Search size={20} />
              </button>
              <label className="btn btn-outline-secondary custom-button" htmlFor="fileUpload">
                <Upload size={20} />
              </label>
              <input type="file" className="form-control-file" accept=".pdf" style={{ display: 'none' }} id="fileUpload" onChange={handleFileChange} />
            </div>
          </div>
          {prescriptionLink && (
            <div className="download-prescription">
              <a href={`http://localhost:8000/download?file_path=${prescriptionLink}`} className="btn btn-outline-primary" download>Download Prescription</a>
            </div>
          )}
        </div>

        <div className={`col-md-5 results-section ${theme}-mode`}>
          <div className="medical-info">
            <h4>Information</h4>
            <div className="form-group">
              <label>Name:</label>
              <input type="text" className="form-control" value={formData.name} readOnly />
            </div>
            <div className="form-group">
              <label>Age:</label>
              <input type="text" className="form-control" value={formData.age} readOnly />
            </div>
            <div className="form-group">
              <label>Weight:</label>
              <input type="text" className="form-control" value={formData.weight} readOnly />
            </div>
            <div className="form-group">
              <label>Height:</label>
              <input type="text" className="form-control" value={formData.height} readOnly />
            </div>
            <div className="form-group">
              <label>Ref Doc:</label>
              <input type="text" className="form-control" value={formData.refDoc} readOnly />
            </div>
          </div>
          <div className="lab-results">
            <h4>Lab Test Results:</h4>
            <div className="row">
              {initialTestNames.map(testName => (
                <div className="col-md-6" key={testName}>
                  <div className="form-group">
                    <label>{testName.replace(/([A-Z])/g, ' $1').trim()}:</label>
                    <input type="text" className="form-control" value={formData[testName.toLowerCase().replace(/ /g, '')] || 'Not found'} readOnly />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
