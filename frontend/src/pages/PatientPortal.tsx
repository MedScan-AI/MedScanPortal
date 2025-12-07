import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { patientService } from '../services/api';
import ChatInterface from '../components/ChatInterface';

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

interface PatientProfile {
  user_id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  date_of_birth?: string;
  patient_id?: string;
  age_years?: number;
  weight_kg?: number;
  height_cm?: number;
  gender?: string;
  blood_type?: string;
  allergies?: string[];
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  medical_history?: string;
}

const PatientPortal = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('profile');
  const [scans, setScans] = useState<Scan[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [profile, setProfile] = useState<PatientProfile | null>(null);
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
      } else if (activeTab === 'profile') {
        const response = await patientService.getProfile();
        setProfile(response.data);
      }
      // Chat tab doesn't need to fetch data
    } catch (err) {
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab !== 'chat') {
      fetchData();
    } else {
      setLoading(false);
    }
  }, [activeTab]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const calculateBMI = (weight?: number, height?: number) => {
    if (!weight || !height) return 'N/A';
    const heightInMeters = height / 100;
    const bmi = weight / (heightInMeters * heightInMeters);
    return bmi.toFixed(1);
  };

  return (
    <div>
      <nav className="navbar navbar-expand-lg navbar-light bg-white border-bottom shadow-sm">
        <div className="container-fluid">
          <span className="navbar-brand fw-bold text-primary">Patient Portal</span>
          <span className="navbar-text me-3">
            Welcome, {user?.first_name} {user?.last_name}
          </span>
          <button className="btn btn-outline-danger btn-sm" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>

      <div className="container-fluid mt-4">
        <ul className="nav nav-tabs mb-4">
          <li className="nav-item">
            <button 
              className={`nav-link ${activeTab === 'profile' ? 'active' : ''}`}
              onClick={() => setActiveTab('profile')}
            >
              📋 Profile
            </button>
          </li>
          <li className="nav-item">
            <button 
              className={`nav-link ${activeTab === 'scans' ? 'active' : ''}`}
              onClick={() => setActiveTab('scans')}
            >
              🔬 My Scans
            </button>
          </li>
          <li className="nav-item">
            <button 
              className={`nav-link ${activeTab === 'reports' ? 'active' : ''}`}
              onClick={() => setActiveTab('reports')}
            >
              📄 Reports
            </button>
          </li>
          <li className="nav-item">
            <button 
              className={`nav-link ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              💬 Ask Questions
            </button>
          </li>
        </ul>

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div className="row">
            <div className="col-lg-8">
              {loading ? (
                <div className="text-center p-5">
                  <div className="spinner-border" />
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
                          <label className="form-label text-muted small">Patient ID</label>
                          <p className="fw-bold">{profile?.patient_id || 'N/A'}</p>
                        </div>
                        <div className="col-md-6 mb-3">
                          <label className="form-label text-muted small">Full Name</label>
                          <p className="fw-bold">{profile?.first_name} {profile?.last_name}</p>
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

                  {/* Physical Measurements */}
                  <div className="card mb-4">
                    <div className="card-header bg-info text-white">
                      <h5 className="mb-0">Physical Measurements</h5>
                    </div>
                    <div className="card-body">
                      <div className="row">
                        <div className="col-md-4 mb-3">
                          <label className="form-label text-muted small">Height</label>
                          <p className="fw-bold">{profile?.height_cm ? `${profile.height_cm} cm` : 'N/A'}</p>
                        </div>
                        <div className="col-md-4 mb-3">
                          <label className="form-label text-muted small">Weight</label>
                          <p className="fw-bold">{profile?.weight_kg ? `${profile.weight_kg} kg` : 'N/A'}</p>
                        </div>
                        <div className="col-md-4 mb-3">
                          <label className="form-label text-muted small">BMI</label>
                          <p className="fw-bold">{calculateBMI(profile?.weight_kg, profile?.height_cm)}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Medical Information */}
                  <div className="card mb-4">
                    <div className="card-header bg-warning text-dark">
                      <h5 className="mb-0">Medical Information</h5>
                    </div>
                    <div className="card-body">
                      <div className="mb-3">
                        <label className="form-label text-muted small">Allergies</label>
                        {profile?.allergies && profile.allergies.length > 0 ? (
                          <div>
                            {profile.allergies.map((allergy, index) => (
                              <span key={index} className="badge bg-danger me-2 mb-2">{allergy}</span>
                            ))}
                          </div>
                        ) : (
                          <p>No known allergies</p>
                        )}
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* Scans Tab */}
        {activeTab === 'scans' && (
          <div>
            <h4>My Scan History</h4>
            {loading ? (
              <div className="text-center p-5">
                <div className="spinner-border" />
              </div>
            ) : scans.length === 0 ? (
              <div className="alert alert-info">No scans available</div>
            ) : (
              <div className="row">
                {scans.map((scan) => (
                  <div key={scan.id} className="col-md-4 mb-3">
                    <div className="card">
                      <div className="card-header d-flex justify-content-between">
                        <span className="badge bg-info">{scan.urgency_level}</span>
                        <span className="badge bg-secondary">{scan.status}</span>
                      </div>
                      <div className="card-body">
                        <h5 className="card-title">{scan.examination_type}</h5>
                        <p className="card-text">
                          <strong>Scan #:</strong> {scan.scan_number}<br />
                          <strong>Region:</strong> {scan.body_region}<br />
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

        {/* Reports Tab */}
        {activeTab === 'reports' && (
          <div>
            <h4>Published Reports</h4>
            {loading ? (
              <div className="text-center p-5">
                <div className="spinner-border" />
              </div>
            ) : reports.length === 0 ? (
              <div className="alert alert-info">No reports available</div>
            ) : (
              <div className="list-group">
                {reports.map((report) => (
                  <div key={report.id} className="list-group-item">
                    <h5>{report.report_title}</h5>
                    <p className="mb-1">{report.impression}</p>
                    <small className="text-muted">
                      Published: {new Date(report.published_at).toLocaleDateString()}
                    </small>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Chat Tab - NEW */}
        {activeTab === 'chat' && (
          <div className="row justify-content-center">
            <div className="col-lg-8">
              <ChatInterface />
              
              {/* Suggested Questions */}
              <div className="card mt-3">
                <div className="card-body">
                  <h6 className="card-title">💡 Suggested Questions:</h6>
                  <div className="d-flex flex-wrap gap-2">
                    {[
                      "What are the symptoms of tuberculosis?",
                      "How is lung cancer treated?",
                      "What is a chest X-ray used for?",
                      "What should I know about TB medication?",
                      "What are the side effects of chemotherapy?"
                    ].map((question, idx) => (
                      <button
                        key={idx}
                        className="btn btn-sm btn-outline-primary"
                        onClick={() => {
                          // You can auto-fill the input or send directly
                          // For now, just show the question as an example
                        }}
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Disclaimer */}
              <div className="alert alert-warning mt-3">
                <small>
                  <strong>⚠️ Medical Disclaimer:</strong> This AI assistant provides general information only. 
                  Always consult your healthcare provider for medical advice. In case of emergency, call 911.
                </small>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PatientPortal;