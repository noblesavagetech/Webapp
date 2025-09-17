import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './HomePage';
import SignupPage from './SignupPage';
import Dashboard from './Dashboard';
import Portal from './Portal';
import AboutUs from './AboutUs';
import Contact from './Contact';
import './App.css';

function App() {
  return (
    <div className="app-container">
      <Router>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/about" element={<AboutUs />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/dashboard/:customerId" element={<Dashboard />} />
          <Route path="/portal/:customerId" element={<Portal />} />
        </Routes>
      </Router>
    </div>
  );
}

export default App;
