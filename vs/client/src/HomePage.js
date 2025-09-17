import React from 'react';
import { Link } from 'react-router-dom';
import TopBar from './TopBar';

function HomePage() {
  return (
    <>
      <TopBar />
      <div className="card" style={{ marginTop: '5rem' }}>
  <h1>Welcome to Noble Savage</h1>
        <Link to="/signup">
          <button style={{ marginTop: '1.5rem' }}>Sign Up</button>
        </Link>
      </div>
    </>
  );
}

export default HomePage;
