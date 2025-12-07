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
  
  // Feedback form state
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
    } catch (err) {
      console.error('Error fetching AI results:', err);
      alert('Failed to load AI results');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitFeedback = async () => {
    if (!scanId || !results) return;
    
    // Validation
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
        radiologist_confidence: confidence / 10, // Convert 1-10 to 0.1-1.0
        image_quality_rating: imageQuality,
      };

      await radiologistService.submitFeedback(scanId, feedbackData);
      
      alert('✓ Diagnosis submitted successfully!\n\nScan will be synced to MLOps pipeline for model training.');
      
      // Navigate to report page
      navigate(`/radiologist/scan/${scanId}/report`);
      
    } catch (err) {
      console.error('Error submitting feedback:', err);
      alert('Failed to submit diagnosis');
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="container mt-5">
        <div className="text-center p-5">
          <div className="spinner-border spinner-border-lg" />
          <p className="mt-3">Analyzing scan with AI...</p>
          <small className="text-muted">This may take 10-30 seconds</small>
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
    <div>
      {/* Header */}
      <nav className="navbar navbar-dark bg-dark">
        <div className="container-fluid">
          <button 
            className="btn btn-outline-light btn-sm"
            onClick={() => navigate(`/radiologist/scan/${scanId}`)}
          >
            ← Back to Scan Details
          </button>
          <span className="navbar-brand">AI Analysis Results</span>
          <span />
        </div>
      </nav>

      <div className="container-fluid mt-4">
        <div className="row">
          {/* AI Results Column */}
          <div className="col-lg-6">
            <div className="card mb-3">
              <div className="card-header bg-primary text-white">
                <h5 className="mb-0">AI Prediction</h5>
              </div>
              <div className="card-body">
                <div className="text-center mb-4">
                  <h2 className="display-4">{results.predicted_class}</h2>
                  <p className="lead">
                    Confidence: <strong>{(results.confidence_score * 100).toFixed(1)}%</strong>
                  </p>
                  <div className="progress" style={{ height: '30px' }}>
                    <div 
                      className="progress-bar bg-success" 
                      style={{ width: `${results.confidence_score * 100}%` }}
                    >
                      {(results.confidence_score * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>

                <h6>Class Probabilities:</h6>
                <table className="table table-sm">
                  <tbody>
                    {Object.entries(results.class_probabilities).map(([className, prob]) => (
                      <tr key={className}>
                        <td>{className}</td>
                        <td>
                          <div className="progress">
                            <div 
                              className="progress-bar" 
                              style={{ width: `${prob * 100}%` }}
                            >
                              {(prob * 100).toFixed(1)}%
                            </div>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Grad-CAM Visualization */}
            <div className="card mb-3">
              <div className="card-header bg-success text-white">
                <h5 className="mb-0">Grad-CAM Visualization</h5>
              </div>
              <div className="card-body">
                {results.gradcam_url ? (
                  <div>
                    <img 
                      src={results.gradcam_url} 
                      alt="Grad-CAM Heatmap"
                      className="img-fluid rounded"
                      style={{ backgroundColor: '#000' }}
                    />
                    <p className="text-muted small mt-2">
                      Heatmap shows regions that influenced the AI's decision
                    </p>
                  </div>
                ) : (
                  <p className="text-muted">Grad-CAM visualization not available</p>
                )}
              </div>
            </div>
          </div>

          {/* Radiologist Decision Column */}
          <div className="col-lg-6">
            <div className="card border-warning">
              <div className="card-header bg-warning">
                <h5 className="mb-0">Your Diagnosis</h5>
              </div>
              <div className="card-body">
                {/* Accept or Override */}
                <div className="mb-4">
                  <label className="form-label fw-bold">Decision:</label>
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
                      ✓ Accept AI Diagnosis
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
                      ⚠ Override AI Diagnosis
                    </label>
                  </div>
                </div>

                {/* Override Diagnosis Selection */}
                {decision === 'override' && (
                  <div className="mb-3 alert alert-warning">
                    <label className="form-label fw-bold">Your Diagnosis:</label>
                    <select 
                      className="form-select"
                      value={overrideDiagnosis}
                      onChange={(e) => setOverrideDiagnosis(e.target.value)}
                      required
                    >
                      <option value="">Select diagnosis...</option>
                      <option value="Normal">Normal</option>
                      <option value="Tuberculosis">Tuberculosis</option>
                      <option value="Lung_Cancer">Lung Cancer</option>
                      <option value="Other_Abnormality">Other Abnormality</option>
                      <option value="Inconclusive">Inconclusive</option>
                    </select>

                    <label className="form-label fw-bold mt-3">Reason for Override:</label>
                    <textarea 
                      className="form-control"
                      rows={3}
                      value={disagreementReason}
                      onChange={(e) => setDisagreementReason(e.target.value)}
                      placeholder="Explain why you disagree with AI prediction..."
                      required
                    />
                  </div>
                )}

                {/* Clinical Notes */}
                <div className="mb-3">
                  <label className="form-label fw-bold">Clinical Notes:</label>
                  <textarea 
                    className="form-control"
                    rows={4}
                    value={clinicalNotes}
                    onChange={(e) => setClinicalNotes(e.target.value)}
                    placeholder="Add your clinical observations, findings, or recommendations..."
                  />
                </div>

                {/* Confidence Rating */}
                <div className="mb-3">
                  <label className="form-label fw-bold">
                    Your Confidence: {confidence}/10
                  </label>
                  <input 
                    type="range" 
                    className="form-range"
                    min="1" 
                    max="10" 
                    value={confidence}
                    onChange={(e) => setConfidence(Number(e.target.value))}
                  />
                  <div className="d-flex justify-content-between">
                    <small>Low</small>
                    <small>High</small>
                  </div>
                </div>

                {/* Image Quality */}
                <div className="mb-4">
                  <label className="form-label fw-bold">
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
                  <div className="d-flex justify-content-between">
                    <small>Poor</small>
                    <small>Excellent</small>
                  </div>
                </div>

                {/* Submit Button */}
                <div className="d-grid">
                  <button 
                    className="btn btn-lg btn-primary"
                    onClick={handleSubmitFeedback}
                    disabled={submitting}
                  >
                    {submitting ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2" />
                        Submitting...
                      </>
                    ) : (
                      '✓ Submit Diagnosis & Continue to Report'
                    )}
                  </button>
                </div>

                <p className="text-muted small mt-3 mb-0">
                  <strong>Note:</strong> Your feedback will be used to improve the AI model. 
                  {decision === 'accept' ? (
                    ' Accepting AI diagnosis helps validate model performance.'
                  ) : (
                    ' Overrides help the model learn from its mistakes.'
                  )}
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