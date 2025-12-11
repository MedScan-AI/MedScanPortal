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
  created_at: string;
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
  const [activeTab, setActiveTab] = useState<'pending' | 'completed' | 'profile'>('pending');
  const [scans, setScans] = useState<Scan[]>([]);
  const [profile, setProfile] = useState<RadiologistProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'pending') {
        const response = await radiologistService.getPendingScans();
        setScans(response.data);
      } else if (activeTab === 'completed') {
        const response = await radiologistService.getCompletedScans();
        setScans(response.data);
      } else if (activeTab === 'profile') {
        const response = await radiologistService.getProfile();
        setProfile(response.data);
      }
    } catch (err) {
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { bg: string; text: string }> = {
      pending: { bg: '#ffc107', text: '#000' },
      in_progress: { bg: '#17a2b8', text: '#fff' },
      ai_analyzed: { bg: '#28a745', text: '#fff' },
      completed: { bg: '#0f4c81', text: '#fff' }
    };
    
    const config = statusConfig[status] || { bg: '#6c757d', text: '#fff' };
    
    return (
      <span style={{
        background: config.bg,
        color: config.text,
        padding: '0.35rem 0.75rem',
        borderRadius: '20px',
        fontSize: '0.75rem',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.5px'
      }}>
        {status.replace('_', ' ')}
      </span>
    );
  };

  const getUrgencyBadge = (urgency: string) => {
    const urgencyConfig: Record<string, string> = {
      'Routine': 'success',
      'Urgent': 'warning',
      'Emergent': 'danger'
    };
    
    const variant = urgencyConfig[urgency] || 'secondary';
    
    return (
      <span className={`badge bg-${variant}`} style={{
        fontSize: '0.8rem',
        fontWeight: 500,
        padding: '0.4rem 0.8rem'
      }}>
        {urgency}
      </span>
    );
  };

  return (
    <div style={{ minHeight: '100vh', background: '#f5f7fa' }}>
      {/* Professional Navigation Bar */}
      <nav className="navbar navbar-dark shadow-sm" style={{
        background: 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 100%)',
        borderBottom: '3px solid #0a3557'
      }}>
        <div className="container-fluid px-4">
          <span className="navbar-brand fw-bold fs-5">
            MedScanAI - Radiologist Portal
          </span>
          <div className="d-flex align-items-center gap-3">
            <span className="text-white">
              Dr. {user?.first_name} {user?.last_name}
            </span>
            <button 
              className="btn btn-outline-light btn-sm"
              onClick={handleLogout}
              style={{ 
                borderRadius: '6px', 
                padding: '0.5rem 1.25rem',
                fontWeight: 500
              }}
            >
              Logout
            </button>
          </div>
        </div>
      </nav>

      {/* Tabs */}
      <div className="container-fluid px-4 py-4">
        <ul className="nav nav-tabs mb-4" style={{ borderBottom: '2px solid #dee2e6' }}>
          <li className="nav-item">
            <button
              className={`nav-link ${activeTab === 'pending' ? 'active' : ''}`}
              onClick={() => setActiveTab('pending')}
              style={{
                border: 'none',
                borderBottom: activeTab === 'pending' ? '3px solid #0f4c81' : '3px solid transparent',
                background: activeTab === 'pending' ? '#f8f9fa' : 'transparent',
                color: activeTab === 'pending' ? '#0f4c81' : '#6c757d',
                fontWeight: activeTab === 'pending' ? 600 : 400,
                padding: '0.75rem 1.5rem',
                transition: 'all 0.2s'
              }}
            >
              📋 Pending Queue
            </button>
          </li>
          <li className="nav-item">
            <button
              className={`nav-link ${activeTab === 'completed' ? 'active' : ''}`}
              onClick={() => setActiveTab('completed')}
              style={{
                border: 'none',
                borderBottom: activeTab === 'completed' ? '3px solid #0f4c81' : '3px solid transparent',
                background: activeTab === 'completed' ? '#f8f9fa' : 'transparent',
                color: activeTab === 'completed' ? '#0f4c81' : '#6c757d',
                fontWeight: activeTab === 'completed' ? 600 : 400,
                padding: '0.75rem 1.5rem',
                transition: 'all 0.2s'
              }}
            >
              ✅ Completed Cases
            </button>
          </li>
          <li className="nav-item">
            <button
              className={`nav-link ${activeTab === 'profile' ? 'active' : ''}`}
              onClick={() => setActiveTab('profile')}
              style={{
                border: 'none',
                borderBottom: activeTab === 'profile' ? '3px solid #0f4c81' : '3px solid transparent',
                background: activeTab === 'profile' ? '#f8f9fa' : 'transparent',
                color: activeTab === 'profile' ? '#0f4c81' : '#6c757d',
                fontWeight: activeTab === 'profile' ? 600 : 400,
                padding: '0.75rem 1.5rem',
                transition: 'all 0.2s'
              }}
            >
              👤 My Profile
            </button>
          </li>
        </ul>

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div>
            {loading ? (
              <div className="text-center py-5">
                <div className="spinner-border text-primary" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
                <p className="mt-3 text-muted">Loading profile...</p>
              </div>
            ) : (
              <div className="row g-4">
                {/* Personal Information */}
                <div className="col-md-6">
                  <div className="card border-0 shadow-sm h-100" style={{ borderRadius: '12px' }}>
                    <div className="card-body p-4">
                      <h5 className="mb-4 fw-bold" style={{ color: '#0f4c81' }}>
                        👤 Personal Information
                      </h5>
                      <div className="mb-3">
                        <label className="text-muted small fw-semibold mb-1">Full Name</label>
                        <p className="mb-0 fw-semibold" style={{ fontSize: '1.05rem' }}>
                          Dr. {profile?.first_name} {profile?.last_name}
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
                    </div>
                  </div>
                </div>

                {/* Professional Information */}
                <div className="col-md-6">
                  <div className="card border-0 shadow-sm h-100" style={{ borderRadius: '12px' }}>
                    <div className="card-body p-4">
                      <h5 className="mb-4 fw-bold" style={{ color: '#0f4c81' }}>
                        🩺 Professional Information
                      </h5>
                      <div className="mb-3">
                        <label className="text-muted small fw-semibold mb-1">License Number</label>
                        <p className="mb-0 fw-semibold" style={{ 
                          fontSize: '1.05rem',
                          fontFamily: 'monospace'
                        }}>
                          {profile?.license_number || 'N/A'}
                        </p>
                      </div>
                      <div className="mb-3">
                        <label className="text-muted small fw-semibold mb-1">Specialization</label>
                        <p className="mb-0">{profile?.specialization || 'Not specified'}</p>
                      </div>
                      <div className="mb-3">
                        <label className="text-muted small fw-semibold mb-1">Years of Experience</label>
                        <p className="mb-0">
                          {profile?.years_of_experience ? `${profile.years_of_experience} years` : 'N/A'}
                        </p>
                      </div>
                      <div className="mb-3">
                        <label className="text-muted small fw-semibold mb-1">Institution</label>
                        <p className="mb-0">{profile?.institution || 'Not specified'}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Statistics Card */}
                <div className="col-12">
                  <div className="card border-0 shadow-sm" style={{ 
                    borderRadius: '12px',
                    background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)'
                  }}>
                    <div className="card-body p-4">
                      <h5 className="mb-4 fw-bold" style={{ color: '#0f4c81' }}>
                        📊 Performance Overview
                      </h5>
                      <div className="row text-center">
                        <div className="col-md-4">
                          <div className="p-3">
                            <div style={{
                              fontSize: '2.5rem',
                              fontWeight: 'bold',
                              color: '#28a745',
                              marginBottom: '0.5rem'
                            }}>
                              —
                            </div>
                            <p className="text-muted mb-0 fw-semibold">Cases This Week</p>
                          </div>
                        </div>
                        <div className="col-md-4">
                          <div className="p-3">
                            <div style={{
                              fontSize: '2.5rem',
                              fontWeight: 'bold',
                              color: '#0f4c81',
                              marginBottom: '0.5rem'
                            }}>
                              —
                            </div>
                            <p className="text-muted mb-0 fw-semibold">Cases This Month</p>
                          </div>
                        </div>
                        <div className="col-md-4">
                          <div className="p-3">
                            <div style={{
                              fontSize: '2.5rem',
                              fontWeight: 'bold',
                              color: '#17a2b8',
                              marginBottom: '0.5rem'
                            }}>
                              —
                            </div>
                            <p className="text-muted mb-0 fw-semibold">Total Career Cases</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Scans View (Pending/Completed) */}
        {(activeTab === 'pending' || activeTab === 'completed') && (
          <div>
            <div className="d-flex justify-content-between align-items-center mb-4">
              <h4 className="mb-0 fw-bold" style={{ color: '#2c3e50' }}>
                {activeTab === 'pending' ? 'Pending Scans' : 'Completed Scans'}
              </h4>
              <span className="badge bg-primary" style={{ 
                fontSize: '0.9rem',
                padding: '0.5rem 1rem',
                fontWeight: 500
              }}>
                {scans.length} {scans.length === 1 ? 'scan' : 'scans'}
              </span>
            </div>

            {loading ? (
              <div className="text-center py-5">
                <div className="spinner-border text-primary" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
                <p className="mt-3 text-muted">Loading scans...</p>
              </div>
            ) : scans.length === 0 ? (
              <div className="card border-0 shadow-sm" style={{ borderRadius: '12px' }}>
                <div className="card-body text-center py-5">
                  <svg 
                    width="64" 
                    height="64" 
                    fill="currentColor" 
                    className="text-muted mb-3" 
                    viewBox="0 0 16 16"
                  >
                    <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                    <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z"/>
                  </svg>
                  <p className="text-muted mb-0">
                    {activeTab === 'pending' ? 'No pending scans' : 'No completed scans'}
                  </p>
                </div>
              </div>
            ) : (
              <div className="table-responsive">
                <table className="table table-hover align-middle" style={{ background: 'white', borderRadius: '12px' }}>
                  <thead style={{ background: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                    <tr>
                      <th className="fw-semibold" style={{ padding: '1rem' }}>Patient</th>
                      <th className="fw-semibold">Scan Number</th>
                      <th className="fw-semibold">Exam Type</th>
                      <th className="fw-semibold">Region</th>
                      <th className="fw-semibold">Urgency</th>
                      <th className="fw-semibold">Status</th>
                      <th className="fw-semibold">Date</th>
                      <th className="fw-semibold text-end">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scans.map((scan) => (
                      <tr 
                        key={scan.id}
                        style={{ 
                          cursor: 'pointer',
                          transition: 'background 0.2s'
                        }}
                        onClick={() => navigate(`/radiologist/scan/${scan.id}`)}
                        onMouseEnter={(e) => e.currentTarget.style.background = '#f8f9fa'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                      >
                        <td style={{ padding: '1rem' }}>
                          <div className="fw-semibold">{scan.patient_name}</div>
                          <small className="text-muted">{scan.patient_id}</small>
                        </td>
                        <td>
                          <span style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>
                            {scan.scan_number}
                          </span>
                        </td>
                        <td>{scan.examination_type}</td>
                        <td>{scan.body_region}</td>
                        <td>{getUrgencyBadge(scan.urgency_level)}</td>
                        <td>{getStatusBadge(scan.status)}</td>
                        <td>
                          <small>
                            {new Date(scan.scan_date).toLocaleDateString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric'
                            })}
                          </small>
                        </td>
                        <td className="text-end">
                          <button 
                            className="btn btn-sm btn-primary"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/radiologist/scan/${scan.id}`);
                            }}
                            style={{
                              borderRadius: '6px',
                              padding: '0.4rem 1rem',
                              fontWeight: 500
                            }}
                          >
                            Review
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default RadiologistPortal;