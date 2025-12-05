import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { patientService } from '../services/api';

interface Scan {
  id: string;
  scan_number: string;
  examination_type: string;
  body_region: string;
  urgency_level: string;
  status: string;
  scan_date: string;
}

interface Report {
  id: string;
  report_number: string;
  report_title: string;
  impression: string;
  published_at: string;
}

const PatientPortal = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('scans');
  const [scans, setScans] = useState<Scan[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'scans') {
        const response = await patientService.getScans();
        setScans(response.data);
      } else if (activeTab === 'reports') {
        const response = await patientService.getReports();
        setReports(response.data);
      }
    } catch (err) {
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div>
      <nav className="navbar navbar-expand-lg navbar-light bg-white border-bottom">
        <div className="container-fluid">
          <span className="navbar-brand">Patient Portal</span>
          <span className="navbar-text me-3">
            Welcome, {user?.first_name} {user?.last_name}
          </span>
          <button className="btn btn-outline-danger btn-sm" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>

      <div className="container-fluid mt-3">
        <ul className="nav nav-tabs mb-3">
          <li className="nav-item">
            <button 
              className={`nav-link ${activeTab === 'profile' ? 'active' : ''}`}
              onClick={() => setActiveTab('profile')}
            >
              Profile
            </button>
          </li>
          <li className="nav-item">
            <button 
              className={`nav-link ${activeTab === 'scans' ? 'active' : ''}`}
              onClick={() => setActiveTab('scans')}
            >
              My Scans
            </button>
          </li>
          <li className="nav-item">
            <button 
              className={`nav-link ${activeTab === 'reports' ? 'active' : ''}`}
              onClick={() => setActiveTab('reports')}
            >
              Reports
            </button>
          </li>
        </ul>

        {activeTab === 'profile' && (
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">My Profile</h5>
              <table className="table">
                <tbody>
                  <tr>
                    <th>Name:</th>
                    <td>{user?.first_name} {user?.last_name}</td>
                  </tr>
                  <tr>
                    <th>Email:</th>
                    <td>{user?.email}</td>
                  </tr>
                  <tr>
                    <th>Phone:</th>
                    <td>{user?.phone || 'N/A'}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'scans' && (
          <div>
            <h4>My Scans</h4>
            {loading ? (
              <div className="text-center p-5">
                <div className="spinner-border" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
              </div>
            ) : scans.length === 0 ? (
              <div className="alert alert-info">No scans available</div>
            ) : (
              <div className="row">
                {scans.map((scan) => (
                  <div key={scan.id} className="col-md-4 mb-3">
                    <div className="card">
                      <div className="card-body">
                        <h5 className="card-title">{scan.examination_type}</h5>
                        <p className="card-text">
                          <strong>Region:</strong> {scan.body_region}<br />
                          <strong>Status:</strong> <span className="badge bg-info">{scan.status}</span><br />
                          <strong>Date:</strong> {new Date(scan.scan_date).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'reports' && (
          <div>
            <h4>Published Reports</h4>
            {loading ? (
              <div className="text-center p-5">
                <div className="spinner-border" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
              </div>
            ) : reports.length === 0 ? (
              <div className="alert alert-info">No reports available</div>
            ) : (
              <div className="list-group">
                {reports.map((report) => (
                  <div key={report.id} className="list-group-item">
                    <h5>{report.report_title}</h5>
                    <p className="mb-1">{report.impression}</p>
                    <small>Published: {new Date(report.published_at).toLocaleDateString()}</small>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PatientPortal;