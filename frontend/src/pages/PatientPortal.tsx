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
  presenting_symptoms?: string[];
  clinical_notes?: string;
}

interface ScanDetail extends Scan {
  patient_name: string;
  patient_id: string;
  current_medications?: string[];
  previous_surgeries?: string[];
  images?: Array<{
    url: string;
    size: number;
    format?: string;
    order?: number;
  }>;
}

interface Report {
  id: string;
  report_number: string;
  report_title: string;
  impression: string;
  published_at: string;
  scan_number?: string;
  examination_type?: string;
}

interface ReportDetail extends Report {
  clinical_indication?: string;
  technique?: string;
  findings: string;
  recommendations?: string;
  patient_name: string;
  scan_date: string;
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
  
  // Detail modals
  const [selectedScan, setSelectedScan] = useState<ScanDetail | null>(null);
  const [selectedReport, setSelectedReport] = useState<ReportDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

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

  const handleViewScanDetails = async (scanId: string) => {
    setLoadingDetail(true);
    try {
      const response = await patientService.getScanById(scanId);
      setSelectedScan(response.data);
    } catch (err) {
      console.error('Error loading scan:', err);
      alert('Failed to load scan details');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleViewReportDetails = async (reportId: string) => {
    setLoadingDetail(true);
    try {
      const response = await patientService.getReportById(reportId);
      setSelectedReport(response.data);
    } catch (err) {
      console.error('Error loading report:', err);
      alert('Failed to load report details');
    } finally {
      setLoadingDetail(false);
    }
  };

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
      {/* Rest of component continues... */}
      {/* Header */}
      <nav className="navbar navbar-dark shadow-sm" style={{
        background: 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 100%)',
        borderBottom: '3px solid #0a3557'
      }}>
        <div className="container-fluid px-4">
          <span className="navbar-brand fw-bold">
            ⛨ MedScanAI - Patient Portal
          </span>
          <div className="d-flex align-items-center">
            <span className="text-white me-3">
              Welcome, {user?.first_name}
            </span>
            <button 
              className="btn btn-outline-light btn-sm"
              onClick={handleLogout}
              style={{ borderRadius: '6px', padding: '0.5rem 1.25rem' }}
            >
              Logout
            </button>
          </div>
        </div>
      </nav>

      {/* Tabs */}
      <div className="container-fluid px-4 py-4">
        <ul className="nav nav-tabs mb-4" style={{ borderBottom: '2px solid #dee2e6' }}>
          {['profile', 'scans', 'reports', 'chat'].map((tab) => (
            <li className="nav-item" key={tab}>
              <button
                className={`nav-link ${activeTab === tab ? 'active' : ''}`}
                onClick={() => setActiveTab(tab)}
                style={{
                  border: 'none',
                  borderBottom: activeTab === tab ? '3px solid #0f4c81' : '3px solid transparent',
                  background: activeTab === tab ? '#f8f9fa' : 'transparent',
                  color: activeTab === tab ? '#0f4c81' : '#6c757d',
                  fontWeight: activeTab === tab ? 600 : 400,
                  padding: '0.75rem 1.5rem',
                  transition: 'all 0.2s'
                }}
              >
                {tab === 'profile' && '👤 My Profile'}
                {tab === 'scans' && '🔬 My Scans'}
                {tab === 'reports' && '📋 My Reports'}
                {tab === 'chat' && '💬 AI Assistant'}
              </button>
            </li>
          ))}
        </ul>

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div className="row g-4">
            <div className="col-md-6">
              <div className="card border-0 shadow-sm h-100" style={{ borderRadius: '12px' }}>
                <div className="card-body p-4">
                  <h5 className="mb-4 fw-bold" style={{ color: '#0f4c81' }}>Personal Information</h5>
                  <div className="mb-3">
                    <label className="text-muted small fw-semibold mb-1">Patient ID</label>
                    <p className="mb-0 fw-semibold">{profile?.patient_id || 'N/A'}</p>
                  </div>
                  <div className="mb-3">
                    <label className="text-muted small fw-semibold mb-1">Full Name</label>
                    <p className="mb-0">{profile?.first_name} {profile?.last_name}</p>
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

            <div className="col-md-6">
              <div className="card border-0 shadow-sm h-100" style={{ borderRadius: '12px' }}>
                <div className="card-body p-4">
                  <h5 className="mb-4 fw-bold" style={{ color: '#0f4c81' }}>Medical Information</h5>
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
                    <div 
                      className="card border-0 shadow-sm h-100" 
                      style={{ 
                        borderRadius: '12px',
                        transition: 'transform 0.2s, box-shadow 0.2s',
                        cursor: 'pointer'
                      }}
                      onClick={() => handleViewScanDetails(scan.id)}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translateY(-4px)';
                        e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.12)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
                      }}
                    >
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
                            {scan.status.replace('_', ' ')}
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
                  <small className="text-muted">Reports will appear here once published by your radiologist</small>
                </div>
              </div>
            ) : (
              <div className="row g-4">
                {reports.map((report) => (
                  <div key={report.id} className="col-12">
                    <div 
                      className="card border-0 shadow-sm" 
                      style={{ 
                        borderRadius: '12px',
                        cursor: 'pointer',
                        transition: 'transform 0.2s, box-shadow 0.2s'
                      }}
                      onClick={() => handleViewReportDetails(report.id)}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.12)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
                      }}
                    >
                      <div className="card-body p-4">
                        <div className="d-flex justify-content-between align-items-start">
                          <div className="flex-grow-1">
                            <h5 className="fw-bold mb-2" style={{ color: '#2c3e50' }}>
                              {report.report_title}
                            </h5>
                            <p className="mb-2 text-muted" style={{ fontSize: '0.95rem' }}>
                              {report.scan_number} • {report.examination_type}
                            </p>
                            <p className="mb-2" style={{ lineHeight: 1.6 }}>{report.impression}</p>
                            <small className="text-muted">
                              📅 Published on {new Date(report.published_at).toLocaleDateString('en-US', {
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric'
                              })}
                            </small>
                          </div>
                          <div className="ms-3">
                            <button 
                              className="btn btn-primary btn-sm"
                              style={{
                                borderRadius: '6px',
                                padding: '0.5rem 1.25rem'
                              }}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleViewReportDetails(report.id);
                              }}
                            >
                              View Report →
                            </button>
                          </div>
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

      {/* Scan Detail Modal */}
      {selectedScan && (
        <div 
          className="modal show d-block" 
          style={{ background: 'rgba(0,0,0,0.5)' }}
          onClick={() => setSelectedScan(null)}
        >
          <div 
            className="modal-dialog modal-xl modal-dialog-scrollable"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-content" style={{ borderRadius: '12px' }}>
              <div className="modal-header" style={{ 
                background: 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 100%)',
                color: 'white',
                borderRadius: '12px 12px 0 0'
              }}>
                <h5 className="modal-title fw-bold">Scan Details: {selectedScan.scan_number}</h5>
                <button 
                  type="button" 
                  className="btn-close btn-close-white" 
                  onClick={() => setSelectedScan(null)}
                />
              </div>
              <div className="modal-body p-4">
                <div className="row g-4">
                  <div className="col-md-6">
                    <h6 className="fw-bold mb-3">Scan Information</h6>
                    <div className="mb-2">
                      <small className="text-muted fw-semibold">Examination Type</small>
                      <p className="mb-0">{selectedScan.examination_type}</p>
                    </div>
                    <div className="mb-2">
                      <small className="text-muted fw-semibold">Body Region</small>
                      <p className="mb-0">{selectedScan.body_region}</p>
                    </div>
                    <div className="mb-2">
                      <small className="text-muted fw-semibold">Urgency</small>
                      <p className="mb-0">{selectedScan.urgency_level}</p>
                    </div>
                    <div className="mb-2">
                      <small className="text-muted fw-semibold">Status</small>
                      <p className="mb-0">
                        <span className="badge" style={{ background: getStatusColor(selectedScan.status) }}>
                          {selectedScan.status.replace('_', ' ').toUpperCase()}
                        </span>
                      </p>
                    </div>
                    <div className="mb-2">
                      <small className="text-muted fw-semibold">Scan Date</small>
                      <p className="mb-0">{new Date(selectedScan.scan_date).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}</p>
                    </div>
                  </div>

                  <div className="col-md-6">
                    <h6 className="fw-bold mb-3">Clinical Information</h6>
                    {selectedScan.presenting_symptoms && selectedScan.presenting_symptoms.length > 0 && (
                      <div className="mb-3">
                        <small className="text-muted fw-semibold">Symptoms</small>
                        <ul className="mb-0 ps-3">
                          {selectedScan.presenting_symptoms.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {selectedScan.current_medications && selectedScan.current_medications.length > 0 && (
                      <div className="mb-3">
                        <small className="text-muted fw-semibold">Medications</small>
                        <ul className="mb-0 ps-3">
                          {selectedScan.current_medications.map((m, i) => (
                            <li key={i}>{m}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {selectedScan.clinical_notes && (
                      <div>
                        <small className="text-muted fw-semibold">Clinical Notes</small>
                        <p className="mb-0">{selectedScan.clinical_notes}</p>
                      </div>
                    )}
                  </div>

                  {selectedScan.images && selectedScan.images.length > 0 && (
                    <div className="col-12">
                      <h6 className="fw-bold mb-3">Scan Images</h6>
                      <div className="row g-3">
                        {selectedScan.images.map((image, idx) => (
                          <div key={idx} className="col-md-6">
                            <img 
                              src={image.url} 
                              alt={`Scan ${image.order || idx + 1}`}
                              className="img-fluid rounded"
                              style={{ 
                                maxHeight: '300px', 
                                width: '100%',
                                objectFit: 'contain',
                                backgroundColor: '#000'
                              }}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <div className="modal-footer">
                <button 
                  className="btn btn-secondary" 
                  onClick={() => setSelectedScan(null)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Report Detail Modal */}
      {selectedReport && (
        <div 
          className="modal show d-block" 
          style={{ background: 'rgba(0,0,0,0.5)' }}
          onClick={() => setSelectedReport(null)}
        >
          <div 
            className="modal-dialog modal-xl modal-dialog-scrollable"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-content" style={{ borderRadius: '12px' }}>
              <div className="modal-header" style={{ 
                background: 'linear-gradient(135deg, #28a745 0%, #20c997 100%)',
                color: 'white',
                borderRadius: '12px 12px 0 0'
              }}>
                <h5 className="modal-title fw-bold">📋 {selectedReport.report_title}</h5>
                <button 
                  type="button" 
                  className="btn-close btn-close-white" 
                  onClick={() => setSelectedReport(null)}
                />
              </div>
              <div className="modal-body p-4" style={{ background: '#f8f9fa' }}>
                <div className="card border-0 mb-3">
                  <div className="card-body">
                    <div className="row mb-3">
                      <div className="col-md-6">
                        <small className="text-muted fw-semibold">Patient</small>
                        <p className="mb-0">{selectedReport.patient_name}</p>
                      </div>
                      <div className="col-md-6">
                        <small className="text-muted fw-semibold">Report Number</small>
                        <p className="mb-0">{selectedReport.report_number}</p>
                      </div>
                    </div>
                    <div className="row">
                      <div className="col-md-6">
                        <small className="text-muted fw-semibold">Scan Number</small>
                        <p className="mb-0">{selectedReport.scan_number}</p>
                      </div>
                      <div className="col-md-6">
                        <small className="text-muted fw-semibold">Published</small>
                        <p className="mb-0">{new Date(selectedReport.published_at).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric'
                        })}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {selectedReport.clinical_indication && (
                  <div className="mb-4">
                    <h6 className="fw-bold mb-2">CLINICAL INDICATION:</h6>
                    <p>{selectedReport.clinical_indication}</p>
                  </div>
                )}

                {selectedReport.technique && (
                  <div className="mb-4">
                    <h6 className="fw-bold mb-2">TECHNIQUE:</h6>
                    <p>{selectedReport.technique}</p>
                  </div>
                )}

                <div className="mb-4">
                  <h6 className="fw-bold mb-2">FINDINGS:</h6>
                  <p style={{ whiteSpace: 'pre-wrap' }}>{selectedReport.findings}</p>
                </div>

                <div className="mb-4">
                  <h6 className="fw-bold mb-2">IMPRESSION:</h6>
                  <p style={{ whiteSpace: 'pre-wrap' }}>{selectedReport.impression}</p>
                </div>

                {selectedReport.recommendations && (
                  <div className="mb-4">
                    <h6 className="fw-bold mb-2">RECOMMENDATIONS:</h6>
                    <p style={{ whiteSpace: 'pre-wrap' }}>{selectedReport.recommendations}</p>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button 
                  className="btn btn-secondary" 
                  onClick={() => setSelectedReport(null)}
                >
                  Close
                </button>
                <button 
                  className="btn btn-primary"
                  onClick={() => {
                    window.print();
                  }}
                >
                  🖨️ Print Report
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Loading Detail Modal */}
      {loadingDetail && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow-lg" style={{ borderRadius: '12px' }}>
              <div className="modal-body text-center py-5">
                <div className="spinner-border text-primary mb-3" />
                <p className="mb-0">Loading details...</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PatientPortal;