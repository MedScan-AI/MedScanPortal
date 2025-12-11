import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { radiologistService, type FeedbackData } from '../services/api';

interface AIResult {
  prediction_id: string;
  predicted_class: string;
  confidence_score: number;
  class_probabilities: Record<string, number>;
  gradcam_url?: string;
  original_image_url?: string;
}

const AIAnalysisPage = () => {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const [results, setResults] = useState<AIResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  
  const [decision, setDecision] = useState<'accept' | 'override'>('accept');
  const [overrideDiagnosis, setOverrideDiagnosis] = useState('');
  const [clinicalNotes, setClinicalNotes] = useState('');
  const [disagreementReason, setDisagreementReason] = useState('');
  const [confidence, setConfidence] = useState(5);
  const [imageQuality, setImageQuality] = useState(5);

  useEffect(() => {
    fetchAIResults();
  }, [scanId]);

  const fetchAIResults = async () => {
    if (!scanId) return;
    
    setLoading(true);
    try {
      const response = await radiologistService.getAIResults(scanId);
      setResults(response.data);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (err) {
      alert('Failed to load AI results');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitFeedback = async () => {
    if (!scanId || !results) return;
    
    if (decision === 'override' && !overrideDiagnosis) {
      alert('Please select a diagnosis for override');
      return;
    }

    if (decision === 'override' && !disagreementReason.trim()) {
      alert('Please provide a reason for overriding AI diagnosis');
      return;
    }

    setSubmitting(true);
    
    try {
      const feedbackData: FeedbackData = {
        feedback_type: decision === 'accept' ? 'accept' : 'full_override',
        radiologist_diagnosis: decision === 'accept' ? results.predicted_class : overrideDiagnosis,
        ai_diagnosis: results.predicted_class,
        clinical_notes: clinicalNotes,
        disagreement_reason: decision === 'override' ? disagreementReason : undefined,
        radiologist_confidence: confidence / 10,
        image_quality_rating: imageQuality,
      };

      await radiologistService.submitFeedback(scanId, feedbackData);
      alert('Diagnosis submitted successfully!\n\nScan will be synced to MLOps pipeline.');
      navigate(`/radiologist/scan/${scanId}/report`);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (err) {
      alert('Failed to submit diagnosis');
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="container mt-5">
        <div className="text-center p-5">
          <div className="spinner-border text-primary" />
          <p className="mt-3 text-muted">Loading AI results...</p>
        </div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="container mt-5">
        <div className="alert alert-warning">AI results not available</div>
        <button className="btn btn-primary" onClick={() => navigate(-1)}>
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f5f7fa' }}>
      {/* Navigation */}
      <nav className="navbar navbar-dark shadow-sm" style={{
        background: 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 100%)',
        borderBottom: '3px solid #0a3557'
      }}>
        <div className="container-fluid px-4">
          <button 
            className="btn btn-outline-light btn-sm"
            onClick={() => navigate(`/radiologist/scan/${scanId}`)}
            style={{ borderRadius: '6px', padding: '0.5rem 1.25rem' }}
          >
            Back to Scan
          </button>
          <span className="navbar-brand fw-bold">AI Analysis Results</span>
          <div style={{ width: '120px' }} /> {/* Spacer */}
        </div>
      </nav>

      <div className="container-fluid px-4 py-4">
        <div className="row g-4">
          {/* AI Results */}
          <div className="col-lg-6">
            <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: '12px' }}>
              <div className="card-header bg-primary text-white border-0" style={{
                borderRadius: '12px 12px 0 0',
                padding: '1rem 1.25rem'
              }}>
                <h6 className="mb-0 fw-bold">AI Prediction</h6>
              </div>
              <div className="card-body p-4">
                <div className="text-center mb-4">
                  <h2 className="display-6 fw-bold mb-2">{results.predicted_class}</h2>
                  <p className="lead mb-3">
                    Confidence: <strong>{(results.confidence_score * 100).toFixed(1)}%</strong>
                  </p>
                  <div className="progress" style={{ height: '24px' }}>
                    <div 
                      className="progress-bar bg-success" 
                      style={{ width: `${results.confidence_score * 100}%` }}
                    >
                      {(results.confidence_score * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>

                <h6 className="fw-semibold mb-3">Class Probabilities</h6>
                <div className="small">
                  {Object.entries(results.class_probabilities).map(([className, prob]) => (
                    <div key={className} className="mb-2">
                      <div className="d-flex justify-content-between mb-1">
                        <span>{className}</span>
                        <span className="fw-semibold">{(prob * 100).toFixed(1)}%</span>
                      </div>
                      <div className="progress" style={{ height: '8px' }}>
                        <div 
                          className="progress-bar bg-info" 
                          style={{ width: `${prob * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* GradCAM */}
            {results.gradcam_url && (
              <div className="card border-0 shadow-sm" style={{ borderRadius: '12px' }}>
                <div className="card-header bg-success text-white border-0" style={{
                  borderRadius: '12px 12px 0 0',
                  padding: '1rem 1.25rem'
                }}>
                  <h6 className="mb-0 fw-bold">Activation Map</h6>
                </div>
                <div className="card-body p-4">
                  <img 
                    src={results.gradcam_url} 
                    alt="Grad-CAM Heatmap"
                    className="img-fluid rounded"
                    style={{ backgroundColor: '#000' }}
                  />
                  <p className="text-muted small mt-2 mb-0">
                    Heatmap highlights regions that influenced the AI decision
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Radiologist Decision */}
          <div className="col-lg-6">
            <div className="card border-0 shadow-sm" style={{ borderRadius: '12px' }}>
              <div className="card-header bg-warning border-0" style={{
                borderRadius: '12px 12px 0 0',
                padding: '1rem 1.25rem'
              }}>
                <h6 className="mb-0 fw-bold">Your Diagnosis</h6>
              </div>
              <div className="card-body p-4">
                {/* Decision */}
                <div className="mb-4">
                  <label className="form-label fw-semibold small">Decision</label>
                  <div className="btn-group w-100" role="group">
                    <input 
                      type="radio" 
                      className="btn-check" 
                      name="decision" 
                      id="accept"
                      checked={decision === 'accept'}
                      onChange={() => setDecision('accept')}
                    />
                    <label className="btn btn-outline-success" htmlFor="accept">
                      Accept AI
                    </label>

                    <input 
                      type="radio" 
                      className="btn-check" 
                      name="decision" 
                      id="override"
                      checked={decision === 'override'}
                      onChange={() => setDecision('override')}
                    />
                    <label className="btn btn-outline-warning" htmlFor="override">
                      Override
                    </label>
                  </div>
                </div>

                {/* Override Options */}
                {decision === 'override' && (
                  <div className="mb-3 p-3 bg-light rounded">
                    <label className="form-label fw-semibold small">Your Diagnosis</label>
                    <select 
                      className="form-select mb-3"
                      value={overrideDiagnosis}
                      onChange={(e) => setOverrideDiagnosis(e.target.value)}
                    >
                      <option value="">Select diagnosis...</option>
                      <option value="Normal">Normal</option>
                      <option value="Tuberculosis">Tuberculosis</option>
                      <option value="Lung_Cancer">Lung Cancer</option>
                      <option value="Other_Abnormality">Other Abnormality</option>
                      <option value="Inconclusive">Inconclusive</option>
                    </select>

                    <label className="form-label fw-semibold small">Reason for Override</label>
                    <textarea 
                      className="form-control"
                      rows={3}
                      value={disagreementReason}
                      onChange={(e) => setDisagreementReason(e.target.value)}
                      placeholder="Explain why you disagree with AI prediction..."
                    />
                  </div>
                )}

                {/* Clinical Notes */}
                <div className="mb-3">
                  <label className="form-label fw-semibold small">Clinical Notes</label>
                  <textarea 
                    className="form-control"
                    rows={4}
                    value={clinicalNotes}
                    onChange={(e) => setClinicalNotes(e.target.value)}
                    placeholder="Add your clinical observations..."
                  />
                </div>

                {/* Ratings */}
                <div className="row mb-3">
                  <div className="col-6">
                    <label className="form-label fw-semibold small">
                      Confidence: {confidence}/10
                    </label>
                    <input 
                      type="range" 
                      className="form-range"
                      min="1" 
                      max="10" 
                      value={confidence}
                      onChange={(e) => setConfidence(Number(e.target.value))}
                    />
                  </div>
                  <div className="col-6">
                    <label className="form-label fw-semibold small">
                      Image Quality: {imageQuality}/5
                    </label>
                    <input 
                      type="range" 
                      className="form-range"
                      min="1" 
                      max="5" 
                      value={imageQuality}
                      onChange={(e) => setImageQuality(Number(e.target.value))}
                    />
                  </div>
                </div>

                {/* Submit */}
                <div className="d-grid">
                  <button 
                    className="btn btn-lg btn-primary"
                    onClick={handleSubmitFeedback}
                    disabled={submitting}
                    style={{ borderRadius: '8px', fontWeight: 500 }}
                  >
                    {submitting ? 'Submitting...' : 'Submit Diagnosis'}
                  </button>
                </div>

                <p className="text-muted small mt-3 mb-0">
                  Your feedback will be used to improve the AI model.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIAnalysisPage;