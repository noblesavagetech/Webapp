import TopBar from './TopBar';

function Contact() {
  return (
    <>
      <TopBar />
      <div className="card" style={{ marginTop: '5rem' }}>
        <h2>Contact</h2>
        <p>Email: support@webapp.com</p>
        <p>Phone: (555) 123-4567</p>
      </div>
    </>
  );
}

export default Contact;
