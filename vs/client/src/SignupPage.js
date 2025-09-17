import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import TopBar from './TopBar';

function SignupPage() {
  const [form, setForm] = useState({ name: '', location: '', estimatedValue: '' });
  const navigate = useNavigate();

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    // TODO: Send signup data to backend
    // Simulate response with customerId
    const customerId = '123';
    navigate(`/dashboard/${customerId}`);
  };

  return (
    <>
      <TopBar />
      <div style={{ marginTop: '5rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '2.5rem', color: '#FFD700', whiteSpace: 'nowrap', textShadow: '0 0 1px #000, 1px 1px 0 #000, -1px -1px 0 #000' }}>Noble Savage Intake Form</h1>
        </div>
        <form style={{
          maxWidth: '700px',
          margin: '0 auto',
          background: 'none',
          boxShadow: 'none',
          padding: '0',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}>
          <h2 style={{ fontSize: '2rem', marginBottom: '1.5rem', textAlign: 'center' }}>Step 1: Your Role and Goals</h2>
          <label style={{ fontWeight: 600, marginBottom: '1rem', display: 'block', textAlign: 'center' }}>
            What best describes you? (Select all that apply)
          </label>
          <div style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', alignItems: 'flex-start', width: '100%', maxWidth: '400px', margin: '0 auto' }}>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="role" value="Everyday American starting a small business" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Everyday American starting a small business</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="role" value="Leader or founder (business, nonprofit, or community)" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Leader or founder (business, nonprofit, or community)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="role" value="Spiritual or cultural guide (educator, elder, or advocate)" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Spiritual or cultural guide (educator, elder, or advocate)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="role" value="Other" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Other:</span>
              <input type="text" name="roleOther" placeholder="Please specify" style={{ width: '250px', marginLeft: '8px' }} />
            </label>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem', textAlign: 'left', flexWrap: 'nowrap' }}>
            <span style={{ fontSize: '1.25rem', fontWeight: 600, marginRight: '1rem', whiteSpace: 'nowrap', color: '#fff', textAlign: 'left', fontFamily: 'inherit' }}>What’s your main goal with Noble Savage?</span>
            <span style={{ fontWeight: 400, fontSize: '1.25rem', color: '#fff', whiteSpace: 'nowrap', textAlign: 'left', fontFamily: 'inherit' }}>(Choose one or write your own)</span>
          </div>
          <div style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', alignItems: 'flex-start', width: '100%', maxWidth: '400px', margin: '0 auto' }}>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="mainGoal" value="Grow business" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Grow business</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="mainGoal" value="Start or streamline a business (automation, setup, etc.)" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Start or streamline a business (automation, setup, etc.)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="mainGoal" value="Explore ancestral or land claims (heritage, status, etc.)" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Explore ancestral or land claims (heritage, status, etc.)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="mainGoal" value="Optimize taxes or finances (personal or business)" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Optimize taxes or finances (personal or business)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="mainGoal" value="Get help with legal or historical documents" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Get help with legal or historical documents</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="mainGoal" value="Other" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Other:</span>
              <input type="text" name="mainGoalOther" placeholder="Please specify" style={{ width: '250px' }} />
            </label>
          </div>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', marginTop: '2rem', textAlign: 'center', color: '#fff', fontWeight: 600 }}>How should we communicate with you?</h2>
          <label style={{ fontWeight: 600, marginBottom: '1rem', display: 'block', textAlign: 'left', marginLeft: '0', width: '100%', maxWidth: '400px', margin: '0 auto' }}>Tone:</label>
          <div style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', alignItems: 'flex-start', width: '100%', maxWidth: '400px', margin: '0 auto' }}>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem', marginLeft: '2rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="tone" value="Empowered & Respectful (Uplifting)" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Empowered & Respectful (Uplifting)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem', marginLeft: '2rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="tone" value="Clear & Professional (straight to the point)" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Clear & Professional (straight to the point)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem', marginLeft: '2rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="tone" value="Friendly & Supportive (warm, conversational)" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Friendly & Supportive (warm, conversational)</span>
            </label>
          </div>
          <label style={{ fontWeight: 600, marginBottom: '1rem', display: 'block', textAlign: 'left', marginLeft: '0', width: '100%', maxWidth: '400px', margin: '0 auto' }}>Format:</label>
          <div style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', alignItems: 'flex-start', width: '100%', maxWidth: '400px', margin: '0 auto' }}>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem', marginLeft: '2rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="format" value="PDF Guide (detailed, printable)" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>PDF Guide (detailed, printable)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem', marginLeft: '2rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="format" value="Task List in Notion (organized, trackable)" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Task List in Notion (organized, trackable)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem', marginLeft: '2rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="format" value="Simple Checklist (quick, actionable)" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Simple Checklist (quick, actionable)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem', marginLeft: '2rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="format" value="Conversational Summary (like a friendly email)" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Conversational Summary (like a friendly email)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', marginBottom: '0.5rem', marginLeft: '2rem' }}>
              <span style={{ display: 'inline-block', width: '32px' }}>
                <input type="checkbox" name="format" value="Other" style={{ width: '22px', height: '22px', borderRadius: '0px', border: '2px solid #2e7d32', accentColor: '#2e7d32' }} />
              </span>
              <span>Other:</span>
              <input type="text" name="formatOther" placeholder="Please specify" style={{ width: '250px' }} />
            </label>
          </div>
        </form>
      </div>
    </>
  );
}

export default SignupPage;
