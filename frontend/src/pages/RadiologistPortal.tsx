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

interface RadiologistProfile {
  user_id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  license_number?: string;
  specialization?: string;
  years_of_experience?: number;
  institution?: string;
}

const RadiologistPortal = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeView, setActiveView] = useState('pending');
  const [pendingScans, setPendingScans] = useState<Scan[]>([]);
  const [completedScans, setCompletedScans] = useState<Scan[]>([]);
  const [profile, setProfile] = useState<RadiologistProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchScans = async () => {
    setLoading(true);
    try {
      if (activeView === 'pending') {
        const response = await radiologistService.getPendingScans();
        setPendingScans(response.data);
      } else if (activeView === 'completed') {
        const response = await radiologistService.getCompletedScans();
        setCompletedScans(response.data);
      } else if (activeView === 'profile') {
        const response = await radiologistService.getProfile();
        setProfile(response.data);
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
      <nav className="navbar navbar-expand-lg navbar-dark bg-primary shadow-sm">
        <div className="container-fluid">
          <span className="navbar-brand fw-bold">Radiologist Portal</span>
          <span className="navbar-text text-white me-3">
            Dr. {user?.first_name} {user?.last_name}
          </span>
          <button className="btn btn-outline-light btn-sm" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>

      <div className="container-fluid mt-4">
        <ul className="nav nav-tabs mb-4">
          <li className="nav-item">
            <button 
              className={`nav-link ${activeView === 'pending' ? 'active' : ''}`}
              onClick={() => setActiveView('pending')}
            >
              Pending Scans {pendingScans.length > 0 && <span className="badge bg-danger ms-2">{pendingScans.length}</span>}
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
          <li className="nav-item">
            <button 
              className={`nav-link ${activeView === 'profile' ? 'active' : ''}`}
              onClick={() => setActiveView('profile')}
            >
              My Profile
            </button>
          </li>
        </ul>

        {/* Profile View */}
        {activeView === 'profile' && (
          <div className="row">
            <div className="col-lg-8">
              {loading ? (
                <div className="text-center p-5">
                  <div className="spinner-border" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                </div>
              ) : (
                <>
                  {/* Personal Information */}
                  <div className="card mb-4">
                    <div className="card-header bg-primary text-white">
                      <h5 className="mb-0">Personal Information</h5>
                    </div>
                    <div className="card-body">
                      <div className="row">
                        <div className="col-md-6 mb-3">
                          <label className="form-label text-muted small">Full Name</label>
                          <p className="fw-bold">Dr. {profile?.first_name} {profile?.last_name}</p>
                        </div>
                        <div className="col-md-6 mb-3">
                          <label className="form-label text-muted small">Email</label>
                          <p>{profile?.email}</p>
                        </div>
                        <div className="col-md-6 mb-3">
                          <label className="form-label text-muted small">Phone</label>
                          <p>{profile?.phone || 'N/A'}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Professional Information */}
                  <div className="card mb-4">
                    <div className="card-header bg-success text-white">
                      <h5 className="mb-0">Professional Information</h5>
                    </div>
                    <div className="card-body">
                      <div className="row">
                        <div className="col-md-6 mb-3">
                          <label className="form-label text-muted small">License Number</label>
                          <p className="fw-bold">{profile?.license_number || 'N/A'}</p>
                        </div>
                        <div className="col-md-6 mb-3">
                          <label className="form-label text-muted small">Specialization</label>
                          <p>{profile?.specialization || 'N/A'}</p>
                        </div>
                        <div className="col-md-6 mb-3">
                          <label className="form-label text-muted small">Years of Experience</label>
                          <p>{profile?.years_of_experience ? `${profile.years_of_experience} years` : 'N/A'}</p>
                        </div>
                        <div className="col-md-6 mb-3">
                          <label className="form-label text-muted small">Institution</label>
                          <p>{profile?.institution || 'N/A'}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Statistics (Future) */}
                  <div className="card mb-4">
                    <div className="card-header bg-secondary text-white">
                      <h5 className="mb-0">Statistics</h5>
                    </div>
                    <div className="card-body">
                      <div className="row text-center">
                        <div className="col-md-4 mb-3">
                          <h3 className="text-primary">{completedScans.length}</h3>
                          <p className="text-muted small">Completed Cases</p>
                        </div>
                        <div className="col-md-4 mb-3">
                          <h3 className="text-warning">{pendingScans.length}</h3>
                          <p className="text-muted small">Pending Cases</p>
                        </div>
                        <div className="col-md-4 mb-3">
                          <h3 className="text-success">-</h3>
                          <p className="text-muted small">This Month</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* Scans View */}
        {(activeView === 'pending' || activeView === 'completed') && (
          <>
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
                {activeView === 'pending' ? 'No pending scans in the queue' : 'No completed cases'}
              </div>
            ) : (
              <div className="row">
                {scans.map((scan) => (
                  <div key={scan.id} className="col-md-6 mb-3">
                    <div className="card">
                      <div className="card-header d-flex justify-content-between align-items-center">
                        <span className={`badge ${scan.urgency_level === 'Emergent' ? 'bg-danger' : scan.urgency_level === 'Urgent' ? 'bg-warning' : 'bg-success'}`}>
                          {scan.urgency_level}
                        </span>
                        <span className="badge bg-secondary">{scan.status}</span>
                      </div>
                      <div className="card-body">
                        <h5 className="card-title">{scan.patient_name}</h5>
                        <p className="card-text">
                          <strong>Patient ID:</strong> {scan.patient_id}<br />
                          <strong>Scan #:</strong> {scan.scan_number}<br />
                          <strong>Exam:</strong> {scan.examination_type}<br />
                          <strong>Region:</strong> {scan.body_region}<br />
                          <strong>Date:</strong> {new Date(scan.scan_date).toLocaleDateString()}
                        </p>
                        {activeView === 'pending' && (
                          <button 
                            className="btn btn-primary btn-sm w-100"
                            onClick={() => handleStartAnalysis(scan.id)}
                          >
                            Start AI-Assisted Analysis
                          </button>
                        )}
                        {activeView === 'completed' && (
                          <button className="btn btn-outline-secondary btn-sm w-100">
                            View Report
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default RadiologistPortal;