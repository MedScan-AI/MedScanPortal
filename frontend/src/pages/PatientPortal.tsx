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
        console.log('Profile data:', response.data);
        setProfile(response.data);
      }
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

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: '#ffc107',
      in_progress: '#17a2b8',
      ai_analyzed: '#28a745',
      completed: '#0f4c81'
    };
    return colors[status] || '#6c757d';
  };

  return (
    <div style={{ minHeight: '100vh', background: '#f5f7fa' }}>
      {/* Professional Header */}
      <nav className="navbar navbar-expand-lg navbar-light bg-white shadow-sm" style={{ borderBottom: '3px solid #0f4c81' }}>
        <div className="container-fluid px-4">
          <div className="d-flex align-items-center">
            <span style={{ fontSize: '1.75rem', marginRight: '0.75rem' }}>⛨</span>
            <div>
              <h5 className="mb-0 fw-bold" style={{ color: '#0f4c81', fontSize: '1.25rem' }}>
                Patient Portal
              </h5>
              <small style={{ color: '#6c757d', fontSize: '0.85rem' }}>
                Welcome back, {user?.first_name} {user?.last_name}
              </small>
            </div>
          </div>
          <button 
            className="btn btn-outline-danger btn-sm"
            onClick={handleLogout}
            style={{ borderRadius: '6px', padding: '0.5rem 1.25rem' }}
          >
            Sign Out
          </button>
        </div>
      </nav>

      <div className="container-fluid px-4 py-4">
        {/* Professional Tabs */}
        <ul className="nav nav-pills mb-4" style={{ gap: '0.5rem' }}>
          {[
            { key: 'profile', icon: '👤', label: 'Profile' },
            { key: 'scans', icon: '🔬', label: 'My Scans' },
            { key: 'reports', icon: '📋', label: 'Reports' },
            { key: 'chat', icon: '💬', label: 'Ask Questions' }
          ].map(tab => (
            <li className="nav-item" key={tab.key}>
              <button
                className={`nav-link ${activeTab === tab.key ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.key)}
                style={{
                  borderRadius: '8px',
                  padding: '0.65rem 1.5rem',
                  fontWeight: 500,
                  border: 'none',
                  background: activeTab === tab.key ? '#0f4c81' : 'white',
                  color: activeTab === tab.key ? 'white' : '#495057',
                  transition: 'all 0.2s',
                  boxShadow: activeTab === tab.key ? '0 4px 12px rgba(15, 76, 129, 0.2)' : 'none'
                }}
              >
                <span style={{ marginRight: '0.5rem' }}>{tab.icon}</span>
                {tab.label}
              </button>
            </li>
          ))}
        </ul>

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div className="row">
            <div className="col-lg-10">
              {loading ? (
                <div className="text-center py-5">
                  <div className="spinner-border text-primary" />
                </div>
              ) : (
                <div className="row g-4">
                  {/* Personal Information */}
                  <div className="col-md-6">
                    <div className="card border-0 shadow-sm h-100" style={{ borderRadius: '12px' }}>
                      <div className="card-body p-4">
                        <h5 className="mb-4 fw-bold" style={{ color: '#0f4c81' }}>
                          Personal Information
                        </h5>
                        <div className="mb-3">
                          <label className="text-muted small fw-semibold mb-1">Patient ID</label>
                          <p className="mb-0 fw-semibold" style={{ fontSize: '1.05rem' }}>
                            {profile?.patient_id || 'N/A'}
                          </p>
                        </div>
                        <div className="mb-3">
                          <label className="text-muted small fw-semibold mb-1">Full Name</label>
                          <p className="mb-0 fw-semibold" style={{ fontSize: '1.05rem' }}>
                            {profile?.first_name} {profile?.last_name}
                          </p>
                        </div>
                        <div className="mb-3">
                          <label className="text-muted small fw-semibold mb-1">Email</label>
                          <p className="mb-0">{profile?.email}</p>
                        </div>
                        <div className="mb-3">
                          <label className="text-muted small fw-semibold mb-1">Phone</label>
                          <p className="mb-0">{profile?.phone || 'Not provided'}</p>
                        </div>
                        <div className="mb-3">
                          <label className="text-muted small fw-semibold mb-1">Date of Birth</label>
                          <p className="mb-0">
                            {profile?.date_of_birth ? new Date(profile.date_of_birth).toLocaleDateString() : 'Not provided'}
                          </p>
                        </div>
                        <div className="row">
                          <div className="col-6">
                            <label className="text-muted small fw-semibold mb-1">Age</label>
                            <p className="mb-0">{profile?.age_years ? `${profile.age_years} years` : 'N/A'}</p>
                          </div>
                          <div className="col-6">
                            <label className="text-muted small fw-semibold mb-1">Gender</label>
                            <p className="mb-0">{profile?.gender || 'Not specified'}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Medical Information */}
                  <div className="col-md-6">
                    <div className="card border-0 shadow-sm h-100" style={{ borderRadius: '12px' }}>
                      <div className="card-body p-4">
                        <h5 className="mb-4 fw-bold" style={{ color: '#0f4c81' }}>
                          Medical Information
                        </h5>
                        <div className="row mb-3">
                          <div className="col-4">
                            <label className="text-muted small fw-semibold mb-1">Height</label>
                            <p className="mb-0 fw-semibold">{profile?.height_cm ? `${profile.height_cm} cm` : 'N/A'}</p>
                          </div>
                          <div className="col-4">
                            <label className="text-muted small fw-semibold mb-1">Weight</label>
                            <p className="mb-0 fw-semibold">{profile?.weight_kg ? `${profile.weight_kg} kg` : 'N/A'}</p>
                          </div>
                          <div className="col-4">
                            <label className="text-muted small fw-semibold mb-1">BMI</label>
                            <p className="mb-0 fw-semibold">{calculateBMI(profile?.weight_kg, profile?.height_cm)}</p>
                          </div>
                        </div>
                        <div className="mb-3">
                          <label className="text-muted small fw-semibold mb-1">Blood Type</label>
                          <p className="mb-0">{profile?.blood_type || 'Not recorded'}</p>
                        </div>
                        <div className="mb-3">
                          <label className="text-muted small fw-semibold mb-2">Allergies</label>
                          {profile?.allergies && profile.allergies.length > 0 ? (
                            <div className="d-flex flex-wrap gap-2">
                              {profile.allergies.map((allergy, index) => (
                                <span key={index} className="badge bg-danger" style={{ 
                                  padding: '0.5rem 0.75rem',
                                  fontSize: '0.85rem',
                                  fontWeight: 500
                                }}>
                                  {allergy}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <p className="mb-0 text-muted">No known allergies</p>
                          )}
                        </div>
                        <div className="mb-3">
                          <label className="text-muted small fw-semibold mb-1">Medical History</label>
                          <p className="mb-0" style={{ fontSize: '0.95rem', lineHeight: 1.6 }}>
                            {profile?.medical_history || 'No medical history recorded'}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Emergency Contact */}
                  <div className="col-md-6">
                    <div className="card border-0 shadow-sm" style={{ 
                      borderRadius: '12px',
                      background: 'linear-gradient(135deg, #fff5f5 0%, #ffe5e5 100%)',
                      borderLeft: '4px solid #dc3545'
                    }}>
                      <div className="card-body p-4">
                        <h5 className="mb-3 fw-bold" style={{ color: '#dc3545' }}>
                          🚨 Emergency Contact
                        </h5>
                        <div className="mb-2">
                          <label className="text-muted small fw-semibold mb-1">Contact Name</label>
                          <p className="mb-0 fw-semibold">{profile?.emergency_contact_name || 'Not provided'}</p>
                        </div>
                        <div>
                          <label className="text-muted small fw-semibold mb-1">Contact Phone</label>
                          <p className="mb-0 fw-semibold">{profile?.emergency_contact_phone || 'Not provided'}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Scans Tab */}
        {activeTab === 'scans' && (
          <div>
            <div className="d-flex justify-content-between align-items-center mb-4">
              <h4 className="mb-0 fw-bold" style={{ color: '#2c3e50' }}>My Scan History</h4>
            </div>
            {loading ? (
              <div className="text-center py-5">
                <div className="spinner-border text-primary" />
              </div>
            ) : scans.length === 0 ? (
              <div className="card border-0 shadow-sm" style={{ borderRadius: '12px' }}>
                <div className="card-body text-center py-5">
                  <div style={{ fontSize: '3rem', opacity: 0.3 }}>🔬</div>
                  <p className="text-muted mb-0">No scans available</p>
                </div>
              </div>
            ) : (
              <div className="row g-4">
                {scans.map((scan) => (
                  <div key={scan.id} className="col-md-6 col-lg-4">
                    <div className="card border-0 shadow-sm h-100" style={{ 
                      borderRadius: '12px',
                      transition: 'transform 0.2s, box-shadow 0.2s',
                      cursor: 'pointer'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-4px)';
                      e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.12)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
                    }}>
                      <div className="card-body p-4">
                        <div className="d-flex justify-content-between align-items-start mb-3">
                          <h5 className="card-title mb-0 fw-bold" style={{ color: '#2c3e50' }}>
                            {scan.examination_type}
                          </h5>
                          <div style={{
                            background: getStatusColor(scan.status),
                            color: 'white',
                            padding: '0.25rem 0.75rem',
                            borderRadius: '20px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            textTransform: 'uppercase'
                          }}>
                            {scan.status}
                          </div>
                        </div>
                        <div className="mb-2">
                          <small className="text-muted fw-semibold">Scan Number</small>
                          <p className="mb-0">{scan.scan_number}</p>
                        </div>
                        <div className="mb-2">
                          <small className="text-muted fw-semibold">Body Region</small>
                          <p className="mb-0">{scan.body_region}</p>
                        </div>
                        <div className="mb-2">
                          <small className="text-muted fw-semibold">Scan Date</small>
                          <p className="mb-0">{new Date(scan.scan_date).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                          })}</p>
                        </div>
                        {scan.status === 'completed' && (
                          <button className="btn btn-sm w-100 mt-3" style={{
                            background: '#0f4c81',
                            color: 'white',
                            borderRadius: '6px',
                            fontWeight: 500
                          }}>
                            View Details
                          </button>
                        )}
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
            <div className="d-flex justify-content-between align-items-center mb-4">
              <h4 className="mb-0 fw-bold" style={{ color: '#2c3e50' }}>Published Reports</h4>
            </div>
            {loading ? (
              <div className="text-center py-5">
                <div className="spinner-border text-primary" />
              </div>
            ) : reports.length === 0 ? (
              <div className="card border-0 shadow-sm" style={{ borderRadius: '12px' }}>
                <div className="card-body text-center py-5">
                  <div style={{ fontSize: '3rem', opacity: 0.3 }}>📋</div>
                  <p className="text-muted mb-0">No reports available</p>
                </div>
              </div>
            ) : (
              <div className="row g-4">
                {reports.map((report) => (
                  <div key={report.id} className="col-12">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '12px' }}>
                      <div className="card-body p-4">
                        <div className="d-flex justify-content-between align-items-start">
                          <div className="flex-grow-1">
                            <h5 className="fw-bold mb-2" style={{ color: '#2c3e50' }}>
                              {report.report_title}
                            </h5>
                            <p className="mb-2" style={{ lineHeight: 1.6 }}>{report.impression}</p>
                            <small className="text-muted">
                              📅 Published on {new Date(report.published_at).toLocaleDateString('en-US', {
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric'
                              })}
                            </small>
                          </div>
                          <button className="btn btn-outline-primary btn-sm ms-3" style={{
                            borderRadius: '6px',
                            padding: '0.5rem 1.25rem'
                          }}>
                            View Full Report
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div className="row justify-content-center">
            <div className="col-lg-10">
              <ChatInterface />
              
              {/* Medical Disclaimer */}
              <div className="alert alert-warning border-0 shadow-sm mt-4" style={{ 
                borderRadius: '12px',
                borderLeft: '4px solid #ffc107'
              }}>
                <div className="d-flex align-items-start">
                  <div style={{ fontSize: '1.5rem', marginRight: '1rem' }}>⚠️</div>
                  <div>
                    <strong className="d-block mb-1">Medical Disclaimer</strong>
                    <small style={{ lineHeight: 1.6 }}>
                      This AI assistant provides general medical information for educational purposes only. 
                      It does not replace professional medical advice, diagnosis, or treatment. 
                      Always consult your healthcare provider for medical concerns. 
                      In case of emergency, call 911.
                    </small>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PatientPortal;