import TopBar from './TopBar';

function AboutUs() {
  return (
    <>
      <TopBar />
      <div style={{
        marginTop: '5rem',
        background: 'linear-gradient(135deg, #355E3B 60%, #6EC6FF 100%)',
        borderRadius: '32px',
        boxShadow: '0 12px 48px rgba(0,0,0,0.25)',
        padding: '5rem',
        width: '98vw',
        maxWidth: '1200px',
        color: '#fff',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}>
        <h2 style={{ fontSize: '4rem', marginBottom: '2.5rem', fontWeight: 800 }}>About us</h2>
        <p style={{ fontSize: '2rem', marginBottom: '2rem', textAlign: 'center' }}>Helping everyday Americans achieve their goals with clarity and ease.</p>
        <p style={{ fontSize: '1.7rem', marginBottom: '1.7rem', textAlign: 'center' }}>The Noble Savage ecosystem is designed to create systematic sovereignty for entrepreneurs who value freedom, community, and generational wealth building.</p>
        <p style={{ fontSize: '1.7rem', marginBottom: '1.7rem', textAlign: 'center' }}>You're not working with amateurs. You have access to an enterprise-level system that treats your success as systematically as a Fortune 500 company manages their operations. Most funding companies keep their clients in the dark about their processes. We believe you deserve to understand exactly how we're engineering your success. When you understand the systematic approach behind your journey, you can move forward with certainty that every step is designed for your benefit. You're not just a client - you're a strategic partner in your own success. The more you understand our system, the better you can leverage it.</p>
        <p style={{ fontSize: '1.7rem', marginBottom: '1.7rem', textAlign: 'center' }}>You're not just getting funded - you're joining a movement.</p>
      </div>
    </>
  );
}

export default AboutUs;
