import React from 'react';
import { Link } from 'react-router-dom';

function TopBar() {
  return (
    <div style={{ width: '100%', background: '#244026', padding: '1rem 0', display: 'flex', justifyContent: 'center', position: 'fixed', top: 0, left: 0, zIndex: 10 }}>
      <nav style={{ display: 'flex', gap: '2rem' }}>
        <Link to="/">Home</Link>
        <Link to="/about">About Us</Link>
        <Link to="/contact">Contact</Link>
      </nav>
    </div>
  );
}

export default TopBar;