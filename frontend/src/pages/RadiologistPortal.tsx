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
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScans();
  }, [activeView]);

  const handleScanClick = (scanId: string) => {
    navigate(`/radiologist/scan/${scanId}`);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const scans = activeView === 'pending' ? pendingScans : completedScans;

  const getUrgencyStyle = (urgency: string) => {
    const styles: Record<string, { bg: string; color: string }> = {
      'Emergent': { bg: '#dc3545', color: 'white' },
      'Urgent': { bg: '#ffc107', color: '#000' },
      'Routine': { bg: '#28a745', color: 'white' }
    };
    return styles[urgency] || styles.Routine;
  };

  const getStatusStyle = (status: string) => {
    const styles: Record<string, { bg: string; color: string }> = {
      'pending': { bg: '#6c757d', color: 'white' },
      'in_progress': { bg: '#17a2b8', color: 'white' },
      'ai_analyzed': { bg: '#0f4c81', color: 'white' },
      'completed': { bg: '#28a745', color: 'white' }
    };
    return styles[status] || styles.pending;
  };

  return (
    <div style={{ minHeight: '100vh', background: '#f5f7fa' }}>
      {/* Professional Header */}
      <nav className="navbar navbar-expand-lg navbar-dark shadow-sm" style={{ 
        background: 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 100%)',
        borderBottom: '3px solid #0a3557'
      }}>
        <div className="container-fluid px-4">
          <div className="d-flex align-items-center">
            <div style={{ fontSize: '1.75rem', marginRight: '0.75rem' }}>⚕️</div>
            <div>
              <h5 className="mb-0 fw-bold text-white" style={{ fontSize: '1.25rem' }}>
                Radiologist Workstation
              </h5>
              <small style={{ color: 'rgba(255,255,255,0.85)', fontSize: '0.85rem' }}>
                {user?.first_name} {user?.last_name}
              </small>
            </div>
          </div>
          <button 
            className="btn btn-outline-light btn-sm"
            onClick={handleLogout}
            style={{ borderRadius: '6px', padding: '0.5rem 1.25rem', fontWeight: 500 }}
          >
            Sign Out
          </button>
        </div>
      </nav>

      <div className="container-fluid px-4 py-4">
        {/* Professional Tabs with Badge */}
        <ul className="nav nav-pills mb-4" style={{ gap: '0.5rem' }}>
          <li className="nav-item">
            <button
              className={`nav-link d-flex align-items-center ${activeView === 'pending' ? 'active' : ''}`}
              onClick={() => setActiveView('pending')}
              style={{
                borderRadius: '8px',
                padding: '0.65rem 1.5rem',
                fontWeight: 500,
                border: 'none',
                background: activeView === 'pending' ? '#0f4c81' : 'white',
                color: activeView === 'pending' ? 'white' : '#495057',
                transition: 'all 0.2s',
                boxShadow: activeView === 'pending' ? '0 4px 12px rgba(15, 76, 129, 0.2)' : 'none'
              }}
            >
              <span style={{ marginRight: '0.5rem' }}>⏳</span>
              Pending Queue
              {pendingScans.length > 0 && (
                <span className="badge bg-danger ms-2" style={{ 
                  borderRadius: '10px',
                  padding: '0.25rem 0.6rem',
                  fontSize: '0.75rem'
                }}>
                  {pendingScans.length}
                </span>
              )}
            </button>
          </li>
          <li className="nav-item">
            <button
              className={`nav-link ${activeView === 'completed' ? 'active' : ''}`}
              onClick={() => setActiveView('completed')}
              style={{
                borderRadius: '8px',
                padding: '0.65rem 1.5rem',
                fontWeight: 500,
                border: 'none',
                background: activeView === 'completed' ? '#0f4c81' : 'white',
                color: activeView === 'completed' ? 'white' : '#495057',
                transition: 'all 0.2s',
                boxShadow: activeView === 'completed' ? '0 4px 12px rgba(15, 76, 129, 0.2)' : 'none'
              }}
            >
              <span style={{ marginRight: '0.5rem' }}>✅</span>
              Completed
            </button>
          </li>
          <li className="nav-item">
            <button
              className={`nav-link ${activeView === 'profile' ? 'active' : ''}`}
              onClick={() => setActiveView('profile')}
              style={{
                borderRadius: '8px',
                padding: '0.65rem 1.5rem',
                fontWeight: 500,
                border: 'none',
                background: activeView === 'profile' ? '#0f4c81' : 'white',
                color: activeView === 'profile' ? 'white' : '#495057',
                transition: 'all 0.2s',
                boxShadow: activeView === 'profile' ? '0 4px 12px rgba(15, 76, 129, 0.2)' : 'none'
              }}
            >
              <span style={{ marginRight: '0.5rem' }}>👤</span>
              My Profile
            </button>
          </li>
        </ul>

        {/* Profile View */}
        {activeView === 'profile' && (
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
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '12px' }}>
                      <div className="card-body p-4">
                        <h5 className="mb-4 fw-bold" style={{ color: '#0f4c81' }}>
                          Personal Information
                        </h5>
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
                      </div>
                    </div>
                  </div>

                  {/* Professional Information */}
                  <div className="col-md-6">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '12px' }}>
                      <div className="card-body p-4">
                        <h5 className="mb-4 fw-bold" style={{ color: '#0f4c81' }}>
                          Professional Information
                        </h5>
                        <div className="mb-3">
                          <label className="text-muted small fw-semibold mb-1">License Number</label>
                          <p className="mb-0 fw-semibold" style={{ fontSize: '1.05rem' }}>
                            {profile?.license_number || 'N/A'}
                          </p>
                        </div>
                        <div className="mb-3">
                          <label className="text-muted small fw-semibold mb-1">Specialization</label>
                          <p className="mb-0">{profile?.specialization || 'Not specified'}</p>
                        </div>
                        <div className="mb-3">
                          <label className="text-muted small fw-semibold mb-1">Experience</label>
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

                  {/* Statistics */}
                  <div className="col-12">
                    <div className="card border-0 shadow-sm" style={{ 
                      borderRadius: '12px',
                      background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)'
                    }}>
                      <div className="card-body p-4">
                        <h5 className="mb-4 fw-bold" style={{ color: '#0f4c81' }}>
                          📊 Performance Summary
                        </h5>
                        <div className="row text-center">
                          <div className="col-md-3">
                            <div className="p-3">
                              <h2 className="fw-bold mb-1" style={{ color: '#0f4c81' }}>
                                {completedScans.length}
                              </h2>
                              <p className="text-muted mb-0 small">Completed Cases</p>
                            </div>
                          </div>
                          <div className="col-md-3">
                            <div className="p-3">
                              <h2 className="fw-bold mb-1" style={{ color: '#ffc107' }}>
                                {pendingScans.length}
                              </h2>
                              <p className="text-muted mb-0 small">Pending Review</p>
                            </div>
                          </div>
                          <div className="col-md-3">
                            <div className="p-3">
                              <h2 className="fw-bold mb-1" style={{ color: '#28a745' }}>
                                {completedScans.length + pendingScans.length}
                              </h2>
                              <p className="text-muted mb-0 small">Total Cases</p>
                            </div>
                          </div>
                          <div className="col-md-3">
                            <div className="p-3">
                              <h2 className="fw-bold mb-1" style={{ color: '#17a2b8' }}>
                                —
                              </h2>
                              <p className="text-muted mb-0 small">This Month</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Scans View */}
        {(activeView === 'pending' || activeView === 'completed') && (
          <>
            <div className="d-flex justify-content-between align-items-center mb-4">
              <div>
                <h4 className="mb-1 fw-bold" style={{ color: '#2c3e50' }}>
                  {activeView === 'pending' ? '⏳ Scan Queue' : '✅ Completed Cases'}
                </h4>
                <p className="text-muted mb-0 small">
                  {activeView === 'pending' 
                    ? 'Review and diagnose pending scans' 
                    : 'View your completed diagnostic workflows'}
                </p>
              </div>
              <button 
                className="btn btn-outline-primary"
                onClick={fetchScans}
                style={{
                  borderRadius: '8px',
                  padding: '0.5rem 1.25rem',
                  fontWeight: 500
                }}
              >
                🔄 Refresh
              </button>
            </div>

            {loading ? (
              <div className="text-center py-5">
                <div className="spinner-border text-primary" />
                <p className="text-muted mt-3">Loading scans...</p>
              </div>
            ) : scans.length === 0 ? (
              <div className="card border-0 shadow-sm" style={{ borderRadius: '12px' }}>
                <div className="card-body text-center py-5">
                  <div style={{ fontSize: '3rem', opacity: 0.3 }}>
                    {activeView === 'pending' ? '✅' : '📋'}
                  </div>
                  <h5 className="fw-bold mb-2" style={{ color: '#2c3e50' }}>
                    {activeView === 'pending' ? 'All Caught Up!' : 'No Completed Cases'}
                  </h5>
                  <p className="text-muted mb-0">
                    {activeView === 'pending' 
                      ? 'There are no scans pending review at this time.'
                      : 'You haven\'t completed any cases yet.'}
                  </p>
                </div>
              </div>
            ) : (
              <div className="row g-4">
                {scans.map((scan) => {
                  const urgencyStyle = getUrgencyStyle(scan.urgency_level);
                  const statusStyle = getStatusStyle(scan.status);
                  
                  return (
                    <div key={scan.id} className="col-md-6 col-xl-4">
                      <div 
                        className="card border-0 shadow-sm h-100"
                        style={{ 
                          borderRadius: '12px',
                          cursor: 'pointer',
                          transition: 'all 0.2s'
                        }}
                        onClick={() => handleScanClick(scan.id)}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.transform = 'translateY(-4px)';
                          e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.15)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = 'translateY(0)';
                          e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
                        }}
                      >
                        {/* Card Header with Badges */}
                        <div className="card-header border-0 bg-white d-flex justify-content-between align-items-center" style={{
                          padding: '1rem 1.25rem',
                          borderRadius: '12px 12px 0 0'
                        }}>
                          <div style={{
                            background: urgencyStyle.bg,
                            color: urgencyStyle.color,
                            padding: '0.35rem 0.85rem',
                            borderRadius: '6px',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            letterSpacing: '0.5px'
                          }}>
                            {scan.urgency_level === 'Emergent' && '🚨 '}
                            {scan.urgency_level}
                          </div>
                          <div style={{
                            background: statusStyle.bg,
                            color: statusStyle.color,
                            padding: '0.35rem 0.85rem',
                            borderRadius: '6px',
                            fontSize: '0.7rem',
                            fontWeight: 600,
                            textTransform: 'uppercase'
                          }}>
                            {scan.status.replace('_', ' ')}
                          </div>
                        </div>

                        {/* Card Body */}
                        <div className="card-body p-4">
                          <div className="mb-3">
                            <h5 className="fw-bold mb-1" style={{ color: '#2c3e50', fontSize: '1.15rem' }}>
                              {scan.patient_name}
                            </h5>
                            <small className="text-muted">Patient ID: {scan.patient_id}</small>
                          </div>

                          <div className="mb-2">
                            <small className="text-muted fw-semibold d-block mb-1">Scan Number</small>
                            <p className="mb-0" style={{ fontSize: '0.9rem', fontFamily: 'monospace' }}>
                              {scan.scan_number}
                            </p>
                          </div>

                          <div className="row mb-2">
                            <div className="col-6">
                              <small className="text-muted fw-semibold d-block mb-1">Exam Type</small>
                              <p className="mb-0" style={{ fontSize: '0.9rem' }}>{scan.examination_type}</p>
                            </div>
                            <div className="col-6">
                              <small className="text-muted fw-semibold d-block mb-1">Region</small>
                              <p className="mb-0" style={{ fontSize: '0.9rem' }}>{scan.body_region}</p>
                            </div>
                          </div>

                          <div className="mb-0">
                            <small className="text-muted fw-semibold d-block mb-1">Scan Date</small>
                            <p className="mb-0" style={{ fontSize: '0.9rem' }}>
                              {new Date(scan.scan_date).toLocaleDateString('en-US', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </p>
                          </div>
                        </div>

                        {/* Card Footer with Action */}
                        <div className="card-footer border-0 bg-white" style={{ 
                          padding: '1rem 1.25rem',
                          borderRadius: '0 0 12px 12px'
                        }}>
                          <button 
                            className="btn w-100 text-white fw-semibold"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleScanClick(scan.id);
                            }}
                            style={{
                              background: 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 100%)',
                              border: 'none',
                              borderRadius: '8px',
                              padding: '0.65rem',
                              fontSize: '0.95rem'
                            }}
                          >
                            {activeView === 'pending' ? '🔬 Review Scan' : '📋 View Details'}
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default RadiologistPortal;