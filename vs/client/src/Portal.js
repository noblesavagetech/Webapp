function Portal() {
  const { customerId } = useParams();
  // TODO: Fetch portal/profile data from backend
  return (
    <>
      <TopBar />
      <div className="card" style={{ marginTop: '5rem' }}>
        <h2>Portal for Customer {customerId}</h2>
        {/* Display profile info here */}
      </div>
    </>
  );
}

export default Portal;
