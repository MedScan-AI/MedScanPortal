import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { radiologistService } from '../services/api';

interface ScanDetail {
  id: string;
  scan_number: string;
  patient_name: string;
  patient_id: string;
  examination_type: string;
  body_region: string;
  urgency_level: string;
  status: string;
  scan_date: string;
  presenting_symptoms?: string[];
  current_medications?: string[];
  previous_surgeries?: string[];
  clinical_notes?: string;
  images?: Array<{
    url: string;
    gcs_path?: string;
    size: number;
    format?: string;
    order?: number;
  }>;
}

const ScanDetailPage = () => {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [startingAnalysis, setStartingAnalysis] = useState(false);

  useEffect(() => {
    fetchScanDetails();
  }, [scanId]);

  const fetchScanDetails = async () => {
    if (!scanId) return;
    
    setLoading(true);
    setError('');
    
    try {
      console.log('Fetching scan:', scanId);
      const response = await radiologistService.getScanById(scanId);
      console.log('Scan response:', response.data);
      setScan(response.data);
      
    } catch (err: any) {
      console.error('Error fetching scan:', err);
      setError(err.response?.data?.detail || 'Failed to load scan details');
    } finally {
      setLoading(false);
    }
  };

  const handleStartAnalysis = async () => {
    if (!scanId) return;
    
    setStartingAnalysis(true);
    try {
      console.log('Starting AI analysis...');
      await radiologistService.startAIAnalysis(scanId);
      
      alert('✓ AI analysis started! This will take 30-60 seconds...\n\nRefresh the page in a minute to see results.');
      
      // Refresh to see updated status
      setTimeout(() => {
        fetchScanDetails();
        setStartingAnalysis(false);
      }, 2000);
      
    } catch (err: any) {
      console.error('Error starting analysis:', err);
      alert(err.response?.data?.detail || 'Failed to start AI analysis');
      setStartingAnalysis(false);
    }
  };

  if (loading) {
    return (
      <div className="container mt-5">
        <div className="text-center p-5">
          <div className="spinner-border text-primary" />
          <p className="mt-3">Loading scan details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mt-5">
        <div className="alert alert-danger">
          <h5>Error</h5>
          <p>{error}</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/radiologist')}>
          ← Back to Queue
        </button>
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="container mt-5">
        <div className="alert alert-warning">Scan not found</div>
        <button className="btn btn-primary" onClick={() => navigate('/radiologist')}>
          ← Back to Queue
        </button>
      </div>
    );
  }

  const images = scan.images || [];

  return (
    <div style={{ minHeight: '100vh', background: '#f5f7fa' }}>
      {/* Header */}
      <nav className="navbar navbar-dark shadow-sm" style={{
        background: 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 100%)',
        borderBottom: '3px solid #0a3557'
      }}>
        <div className="container-fluid px-4">
          <button 
            className="btn btn-outline-light btn-sm"
            onClick={() => navigate('/radiologist')}
            style={{ borderRadius: '6px', padding: '0.5rem 1.25rem' }}
          >
            ← Back to Queue
          </button>
          <span className="navbar-brand fw-bold">Scan Review: {scan.scan_number}</span>
          <span className={`badge ${
            scan.urgency_level === 'Emergent' ? 'bg-danger' : 
            scan.urgency_level === 'Urgent' ? 'bg-warning text-dark' : 
            'bg-success'
          }`} style={{ padding: '0.5rem 0.85rem', fontSize: '0.85rem' }}>
            {scan.urgency_level}
          </span>
        </div>
      </nav>

      <div className="container-fluid px-4 py-4">
        <div className="row g-4">
          {/* Left Column */}
          <div className="col-lg-4">
            {/* Patient Info */}
            <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: '12px' }}>
              <div className="card-header text-white border-0" style={{
                background: 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 100%)',
                borderRadius: '12px 12px 0 0',
                padding: '1rem 1.25rem'
              }}>
                <h5 className="mb-0 fw-bold">👤 Patient Information</h5>
              </div>
              <div className="card-body p-4">
                <div className="mb-3">
                  <label className="text-muted small fw-semibold mb-1">Patient Name</label>
                  <p className="mb-0 fw-bold" style={{ fontSize: '1.05rem' }}>{scan.patient_name}</p>
                </div>
                <div className="mb-3">
                  <label className="text-muted small fw-semibold mb-1">Patient ID</label>
                  <p className="mb-0">{scan.patient_id}</p>
                </div>
                <div className="mb-3">
                  <label className="text-muted small fw-semibold mb-1">Scan Number</label>
                  <p className="mb-0" style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>
                    {scan.scan_number}
                  </p>
                </div>
                <div className="row mb-3">
                  <div className="col-6">
                    <label className="text-muted small fw-semibold mb-1">Exam Type</label>
                    <p className="mb-0">{scan.examination_type}</p>
                  </div>
                  <div className="col-6">
                    <label className="text-muted small fw-semibold mb-1">Region</label>
                    <p className="mb-0">{scan.body_region}</p>
                  </div>
                </div>
                <div className="mb-3">
                  <label className="text-muted small fw-semibold mb-1">Scan Date</label>
                  <p className="mb-0">
                    {new Date(scan.scan_date).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric'
                    })}
                  </p>
                </div>
                <div>
                  <label className="text-muted small fw-semibold mb-1">Status</label>
                  <p className="mb-0">
                    <span className="badge bg-secondary px-3 py-2">
                      {scan.status.replace('_', ' ').toUpperCase()}
                    </span>
                  </p>
                </div>
              </div>
            </div>

            {/* Clinical Info */}
            <div className="card border-0 shadow-sm" style={{ borderRadius: '12px' }}>
              <div className="card-header bg-warning border-0" style={{
                borderRadius: '12px 12px 0 0',
                padding: '1rem 1.25rem'
              }}>
                <h6 className="mb-0 fw-bold">⚕️ Clinical Information</h6>
              </div>
              <div className="card-body p-4">
                <div className="mb-3">
                  <label className="text-muted small fw-semibold mb-2">Symptoms</label>
                  {scan.presenting_symptoms && scan.presenting_symptoms.length > 0 ? (
                    <ul className="mb-0 ps-3">
                      {scan.presenting_symptoms.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted small mb-0">None</p>
                  )}
                </div>
                <div className="mb-3">
                  <label className="text-muted small fw-semibold mb-2">Medications</label>
                  {scan.current_medications && scan.current_medications.length > 0 ? (
                    <ul className="mb-0 ps-3">
                      {scan.current_medications.map((m, i) => (
                        <li key={i}>{m}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted small mb-0">None</p>
                  )}
                </div>
                <div>
                  <label className="text-muted small fw-semibold mb-2">Surgeries</label>
                  {scan.previous_surgeries && scan.previous_surgeries.length > 0 ? (
                    <ul className="mb-0 ps-3">
                      {scan.previous_surgeries.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted small mb-0">None</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column */}
          <div className="col-lg-8">
            {/* Images */}
            <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: '12px' }}>
              <div className="card-header border-0" style={{
                background: '#2c3e50',
                color: 'white',
                borderRadius: '12px 12px 0 0',
                padding: '1rem 1.25rem'
              }}>
                <h5 className="mb-0 fw-bold">🔬 Scan Images</h5>
              </div>
              <div className="card-body p-4">
                {images.length === 0 ? (
                  <div className="alert alert-warning">No images uploaded</div>
                ) : (
                  <div className="row g-3">
                    {images.map((image, idx) => (
                      <div key={idx} className="col-md-6">
                        <div className="card">
                          <img 
                            src={image.url} 
                            alt={`Scan ${image.order || idx + 1}`}
                            className="card-img-top"
                            style={{ 
                              height: '300px', 
                              objectFit: 'contain',
                              backgroundColor: '#000'
                            }}
                            onError={(e) => {
                              console.error('Image load error:', image.url);
                              e.currentTarget.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg"/>';
                            }}
                          />
                          <div className="card-body">
                            <small className="text-muted">
                              Image {image.order || idx + 1} • 
                              {image.format ? image.format.toUpperCase() : 'JPG'} • 
                              {(image.size / 1024).toFixed(0)} KB
                            </small>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Action Cards */}
            {scan.status === 'pending' && images.length > 0 && (
              <div className="card border-0 shadow-sm" style={{ 
                borderRadius: '12px',
                background: 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)',
                borderLeft: '4px solid #0f4c81'
              }}>
                <div className="card-body text-center p-5">
                  <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🤖</div>
                  <h5 className="fw-bold mb-3" style={{ color: '#0f4c81' }}>Ready for AI Analysis</h5>
                  <p className="text-muted mb-4">
                    Start AI-assisted analysis to get preliminary diagnosis and visualization
                  </p>
                  <button 
                    className="btn btn-lg text-white fw-semibold"
                    onClick={handleStartAnalysis}
                    disabled={startingAnalysis}
                    style={{
                      background: 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 100%)',
                      border: 'none',
                      borderRadius: '8px',
                      padding: '0.875rem 2.5rem'
                    }}
                  >
                    {startingAnalysis ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2" />
                        Starting Analysis...
                      </>
                    ) : (
                      '🚀 Start AI Analysis'
                    )}
                  </button>
                </div>
              </div>
            )}

            {scan.status === 'in_progress' && (
              <div className="alert alert-info">
                <div className="d-flex align-items-center">
                  <div className="spinner-border spinner-border-sm me-3" />
                  <div>
                    <strong>AI Analysis in Progress...</strong>
                    <p className="mb-0 small">This may take 30-60 seconds. Refresh the page to see results.</p>
                  </div>
                </div>
              </div>
            )}

            {scan.status === 'ai_analyzed' && (
              <div className="card border-0 shadow-sm" style={{ 
                borderRadius: '12px',
                background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)',
                borderLeft: '4px solid #28a745'
              }}>
                <div className="card-body text-center p-4">
                  <h5 className="fw-bold mb-3" style={{ color: '#28a745' }}>
                    ✓ AI Analysis Complete
                  </h5>
                  <button 
                    className="btn btn-success btn-lg"
                    onClick={() => navigate(`/radiologist/scan/${scanId}/analysis`)}
                    style={{ borderRadius: '8px', padding: '0.75rem 2rem' }}
                  >
                    View AI Results & Submit Diagnosis →
                  </button>
                </div>
              </div>
            )}

            {scan.status === 'completed' && (
              <div className="alert alert-primary">
                <strong>✓ Diagnosis Complete</strong>
                <button 
                  className="btn btn-primary btn-sm ms-3"
                  onClick={() => navigate(`/radiologist/scan/${scanId}/report`)}
                >
                  View Report →
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScanDetailPage;