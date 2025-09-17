function Dashboard() {
  const { customerId } = useParams();
  // TODO: Fetch dashboard data from backend
  return (
    <>
      <TopBar />
      <div className="card" style={{ marginTop: '5rem' }}>
        <h2>Dashboard for Customer {customerId}</h2>
        {/* Display dashboard info here */}
      </div>
    </>
  );
}

export default Dashboard;
