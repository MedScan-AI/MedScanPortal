import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { radiologistService } from '../services/api';

interface Scan {
  id: string;
  scan_number: string;
  patient_name: string;
  patient_id: string;
  examination_type: string;
  body_region: string;
  urgency_level: string;
  status: string;
  scan_date: string;
}

const RadiologistPortal = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeView, setActiveView] = useState('pending');
  const [pendingScans, setPendingScans] = useState<Scan[]>([]);
  const [completedScans, setCompletedScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchScans = async () => {
    setLoading(true);
    try {
      if (activeView === 'pending') {
        const response = await radiologistService.getPendingScans();
        setPendingScans(response.data);
      } else {
        const response = await radiologistService.getCompletedScans();
        setCompletedScans(response.data);
      }
    } catch (err) {
      console.error('Error fetching scans:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScans();
  }, [activeView]);

  const handleStartAnalysis = async (scanId: string) => {
    try {
      await radiologistService.startAIAnalysis(scanId);
      alert('AI analysis started');
    } catch (err) {
      alert('Failed to start analysis');
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const scans = activeView === 'pending' ? pendingScans : completedScans;

  return (
    <div>
      <nav className="navbar navbar-expand-lg navbar-light bg-white border-bottom">
        <div className="container-fluid">
          <span className="navbar-brand">Radiologist Portal</span>
          <span className="navbar-text me-3">
            Dr. {user?.first_name} {user?.last_name}
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
              className={`nav-link ${activeView === 'pending' ? 'active' : ''}`}
              onClick={() => setActiveView('pending')}
            >
              Pending Scans {pendingScans.length > 0 && <span className="badge bg-danger">{pendingScans.length}</span>}
            </button>
          </li>
          <li className="nav-item">
            <button 
              className={`nav-link ${activeView === 'completed' ? 'active' : ''}`}
              onClick={() => setActiveView('completed')}
            >
              Completed
            </button>
          </li>
        </ul>

        <div className="d-flex justify-content-between align-items-center mb-3">
          <h4>{activeView === 'pending' ? 'Scan Queue' : 'Completed Cases'}</h4>
          <button className="btn btn-primary btn-sm" onClick={fetchScans}>
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="text-center p-5">
            <div className="spinner-border" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        ) : scans.length === 0 ? (
          <div className="alert alert-info">
            {activeView === 'pending' ? 'No pending scans' : 'No completed cases'}
          </div>
        ) : (
          <div className="row">
            {scans.map((scan) => (
              <div key={scan.id} className="col-md-6 mb-3">
                <div className="card">
                  <div className="card-header d-flex justify-content-between">
                    <span className="badge bg-warning">{scan.urgency_level}</span>
                    <span className="badge bg-secondary">{scan.status}</span>
                  </div>
                  <div className="card-body">
                    <h5 className="card-title">{scan.patient_name}</h5>
                    <p className="card-text">
                      <strong>ID:</strong> {scan.patient_id}<br />
                      <strong>Exam:</strong> {scan.examination_type}<br />
                      <strong>Region:</strong> {scan.body_region}<br />
                      <strong>Date:</strong> {new Date(scan.scan_date).toLocaleDateString()}
                    </p>
                    {activeView === 'pending' && (
                      <button 
                        className="btn btn-primary btn-sm w-100"
                        onClick={() => handleStartAnalysis(scan.id)}
                      >
                        Start AI Analysis
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default RadiologistPortal;