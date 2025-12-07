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
}

interface ScanImage {
  id: string;
  url: string;
  order: number;
  size_bytes: number;
  format: string;
}

const ScanDetailPage = () => {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [images, setImages] = useState<ScanImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [startingAnalysis, setStartingAnalysis] = useState(false);

  useEffect(() => {
    fetchScanDetails();
  }, [scanId]);

  const fetchScanDetails = async () => {
    if (!scanId) return;
    
    setLoading(true);
    try {
      // Fetch scan details
      const scanResponse = await radiologistService.getScanById(scanId);
      setScan(scanResponse.data);
      
      // Fetch images
      const imagesResponse = await radiologistService.getScanImages(scanId);
      setImages(imagesResponse.data);
    } catch (err) {
      console.error('Error fetching scan:', err);
      alert('Failed to load scan details');
    } finally {
      setLoading(false);
    }
  };

  const handleStartAnalysis = async () => {
    if (!scanId) return;
    
    setStartingAnalysis(true);
    try {
      await radiologistService.startAIAnalysis(scanId);
      // Navigate to AI analysis results page
      navigate(`/radiologist/scan/${scanId}/analysis`);
    } catch (err) {
      console.error('Error starting analysis:', err);
      alert('Failed to start AI analysis');
      setStartingAnalysis(false);
    }
  };

  if (loading) {
    return (
      <div className="container mt-5">
        <div className="text-center p-5">
          <div className="spinner-border" />
          <p className="mt-3">Loading scan details...</p>
        </div>
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="container mt-5">
        <div className="alert alert-danger">Scan not found</div>
        <button className="btn btn-primary" onClick={() => navigate('/radiologist')}>
          Back to Queue
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <nav className="navbar navbar-dark bg-primary">
        <div className="container-fluid">
          <button 
            className="btn btn-outline-light btn-sm"
            onClick={() => navigate('/radiologist')}
          >
            ← Back to Queue
          </button>
          <span className="navbar-brand">Scan Review: {scan.scan_number}</span>
          <span className={`badge ${
            scan.urgency_level === 'Emergent' ? 'bg-danger' : 
            scan.urgency_level === 'Urgent' ? 'bg-warning' : 
            'bg-success'
          }`}>
            {scan.urgency_level}
          </span>
        </div>
      </nav>

      <div className="container-fluid mt-4">
        <div className="row">
          {/* Left Column: Patient Info */}
          <div className="col-lg-4">
            <div className="card mb-3">
              <div className="card-header bg-info text-white">
                <h5 className="mb-0">Patient Information</h5>
              </div>
              <div className="card-body">
                <p><strong>Name:</strong> {scan.patient_name}</p>
                <p><strong>Patient ID:</strong> {scan.patient_id}</p>
                <p><strong>Scan Number:</strong> {scan.scan_number}</p>
                <p><strong>Exam Type:</strong> {scan.examination_type}</p>
                <p><strong>Body Region:</strong> {scan.body_region}</p>
                <p><strong>Date:</strong> {new Date(scan.scan_date).toLocaleDateString()}</p>
                <p><strong>Status:</strong> <span className="badge bg-secondary">{scan.status}</span></p>
              </div>
            </div>

            {/* Clinical Information */}
            <div className="card mb-3">
              <div className="card-header bg-warning">
                <h6 className="mb-0">Clinical Information</h6>
              </div>
              <div className="card-body">
                <div className="mb-3">
                  <strong>Presenting Symptoms:</strong>
                  {scan.presenting_symptoms && scan.presenting_symptoms.length > 0 ? (
                    <ul className="mb-0 mt-2">
                      {scan.presenting_symptoms.map((symptom, idx) => (
                        <li key={idx}>{symptom}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted mb-0">None reported</p>
                  )}
                </div>

                <div className="mb-3">
                  <strong>Current Medications:</strong>
                  {scan.current_medications && scan.current_medications.length > 0 ? (
                    <ul className="mb-0 mt-2">
                      {scan.current_medications.map((med, idx) => (
                        <li key={idx}>{med}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted mb-0">None</p>
                  )}
                </div>

                <div className="mb-0">
                  <strong>Previous Surgeries:</strong>
                  {scan.previous_surgeries && scan.previous_surgeries.length > 0 ? (
                    <ul className="mb-0 mt-2">
                      {scan.previous_surgeries.map((surgery, idx) => (
                        <li key={idx}>{surgery}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted mb-0">None</p>
                  )}
                </div>
              </div>
            </div>

            {/* Clinical Notes */}
            {scan.clinical_notes && (
              <div className="card mb-3">
                <div className="card-header">
                  <h6 className="mb-0">Clinical Notes</h6>
                </div>
                <div className="card-body">
                  <p className="mb-0">{scan.clinical_notes}</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Images & Actions */}
          <div className="col-lg-8">
            <div className="card mb-3">
              <div className="card-header bg-secondary text-white">
                <h5 className="mb-0">Scan Images</h5>
              </div>
              <div className="card-body">
                {images.length === 0 ? (
                  <div className="alert alert-warning">
                    No images uploaded yet
                  </div>
                ) : (
                  <div className="row">
                    {images.map((image) => (
                      <div key={image.id} className="col-md-6 mb-3">
                        <div className="card">
                          <img 
                            src={image.url} 
                            alt={`Scan ${image.order}`}
                            className="card-img-top"
                            style={{ 
                              height: '300px', 
                              objectFit: 'contain',
                              backgroundColor: '#000'
                            }}
                          />
                          <div className="card-body">
                            <small className="text-muted">
                              Image {image.order} • {image.format.toUpperCase()} • 
                              {(image.size_bytes / 1024).toFixed(0)} KB
                            </small>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Action Button */}
            {scan.status === 'pending' && images.length > 0 && (
              <div className="card border-primary">
                <div className="card-body text-center">
                  <h5 className="card-title">Ready to Analyze</h5>
                  <p className="card-text">
                    Start AI-assisted analysis to get preliminary diagnosis and Grad-CAM visualization
                  </p>
                  <button 
                    className="btn btn-primary btn-lg"
                    onClick={handleStartAnalysis}
                    disabled={startingAnalysis}
                  >
                    {startingAnalysis ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2" />
                        Running Analysis...
                      </>
                    ) : (
                      '🤖 Start AI-Assisted Analysis'
                    )}
                  </button>
                </div>
              </div>
            )}

            {scan.status === 'ai_analyzed' && (
              <div className="alert alert-success">
                <strong>✓ AI Analysis Complete</strong>
                <button 
                  className="btn btn-success btn-sm ms-3"
                  onClick={() => navigate(`/radiologist/scan/${scanId}/analysis`)}
                >
                  View AI Results →
                </button>
              </div>
            )}

            {scan.status === 'completed' && (
              <div className="alert alert-info">
                <strong>✓ Scan Completed</strong>
                <button 
                  className="btn btn-info btn-sm ms-3"
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