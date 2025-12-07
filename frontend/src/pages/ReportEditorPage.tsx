import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { radiologistService, type ReportData } from '../services/api';

interface Report {
  id: string;
  report_number: string;
  report_title: string;
  clinical_indication: string;
  technique: string;
  findings: string;
  impression: string;
  recommendations: string;
  report_status: string;
  scan_number: string;
  patient_name: string;
}

const ReportEditorPage = () => {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);

  // Editable fields
  const [reportTitle, setReportTitle] = useState('');
  const [clinicalIndication, setClinicalIndication] = useState('');
  const [technique, setTechnique] = useState('');
  const [findings, setFindings] = useState('');
  const [impression, setImpression] = useState('');
  const [recommendations, setRecommendations] = useState('');

  useEffect(() => {
    fetchDraftReport();
  }, [scanId]);

  const fetchDraftReport = async () => {
    if (!scanId) return;
    
    setLoading(true);
    try {
      const response = await radiologistService.getDraftReport(scanId);
      const data = response.data;
      setReport(data);
      
      // Populate form with AI-generated content
      setReportTitle(data.report_title || '');
      setClinicalIndication(data.clinical_indication || '');
      setTechnique(data.technique || '');
      setFindings(data.findings || '');
      setImpression(data.impression || '');
      setRecommendations(data.recommendations || '');
    } catch (err) {
      console.error('Error fetching report:', err);
      alert('Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!report) return;
    
    setSaving(true);
    try {
      const reportData: ReportData = {
        report_title: reportTitle,
        clinical_indication: clinicalIndication,
        technique,
        findings,
        impression,
        recommendations,
      };

      await radiologistService.updateReport(report.id, reportData);
      alert('✓ Draft saved successfully');
    } catch (err) {
      console.error('Error saving draft:', err);
      alert('Failed to save draft');
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!report) return;
    
    if (!window.confirm(
      'Publish this report to the patient?\n\n' +
      'Once published, the patient will be able to view this report in their portal.'
    )) {
      return;
    }

    setPublishing(true);
    try {
      // Save any changes first
      await handleSaveDraft();
      
      // Publish report
      await radiologistService.publishReport(report.id);
      
      alert('✓ Report published successfully!\n\nThe patient can now view this report.');
      
      // Navigate back to queue
      navigate('/radiologist');
      
    } catch (err) {
      console.error('Error publishing report:', err);
      alert('Failed to publish report');
      setPublishing(false);
    }
  };

  if (loading) {
    return (
      <div className="container mt-5">
        <div className="text-center p-5">
          <div className="spinner-border" />
          <p className="mt-3">Loading report...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <nav className="navbar navbar-dark bg-success">
        <div className="container-fluid">
          <button 
            className="btn btn-outline-light btn-sm"
            onClick={() => navigate('/radiologist')}
          >
            ← Back to Queue
          </button>
          <span className="navbar-brand">Report Editor</span>
          <div>
            <button 
              className="btn btn-light btn-sm me-2"
              onClick={handleSaveDraft}
              disabled={saving}
            >
              {saving ? 'Saving...' : '💾 Save Draft'}
            </button>
            <button 
              className="btn btn-warning btn-sm"
              onClick={handlePublish}
              disabled={publishing}
            >
              {publishing ? 'Publishing...' : '📤 Publish to Patient'}
            </button>
          </div>
        </div>
      </nav>

      <div className="container-fluid mt-4">
        <div className="row">
          {/* Report Preview */}
          <div className="col-lg-6">
            <div className="card border-info">
              <div className="card-header bg-info text-white">
                <h5 className="mb-0">Report Preview</h5>
              </div>
              <div className="card-body" style={{ backgroundColor: '#f8f9fa' }}>
                <div className="medical-report">
                  <h4 className="text-center mb-4">{reportTitle || 'Radiology Report'}</h4>
                  
                  <div className="mb-3">
                    <p><strong>Patient:</strong> {report?.patient_name}</p>
                    <p><strong>Scan Number:</strong> {report?.scan_number}</p>
                    <p><strong>Report Number:</strong> {report?.report_number}</p>
                  </div>

                  <hr />

                  {clinicalIndication && (
                    <div className="mb-3">
                      <h6 className="fw-bold">CLINICAL INDICATION:</h6>
                      <p>{clinicalIndication}</p>
                    </div>
                  )}

                  {technique && (
                    <div className="mb-3">
                      <h6 className="fw-bold">TECHNIQUE:</h6>
                      <p>{technique}</p>
                    </div>
                  )}

                  <div className="mb-3">
                    <h6 className="fw-bold">FINDINGS:</h6>
                    <p style={{ whiteSpace: 'pre-wrap' }}>{findings}</p>
                  </div>

                  <div className="mb-3">
                    <h6 className="fw-bold">IMPRESSION:</h6>
                    <p style={{ whiteSpace: 'pre-wrap' }}>{impression}</p>
                  </div>

                  {recommendations && (
                    <div className="mb-3">
                      <h6 className="fw-bold">RECOMMENDATIONS:</h6>
                      <p style={{ whiteSpace: 'pre-wrap' }}>{recommendations}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Report Editor */}
          <div className="col-lg-6">
            <div className="card">
              <div className="card-header">
                <h5 className="mb-0">Edit Report</h5>
                <small className="text-muted">AI-generated content. Review and edit as needed.</small>
              </div>
              <div className="card-body">
                <div className="mb-3">
                  <label className="form-label fw-bold">Report Title</label>
                  <input 
                    type="text"
                    className="form-control"
                    value={reportTitle}
                    onChange={(e) => setReportTitle(e.target.value)}
                    placeholder="e.g., Chest X-Ray Report"
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label fw-bold">Clinical Indication</label>
                  <textarea 
                    className="form-control"
                    rows={2}
                    value={clinicalIndication}
                    onChange={(e) => setClinicalIndication(e.target.value)}
                    placeholder="Reason for examination..."
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label fw-bold">Technique</label>
                  <textarea 
                    className="form-control"
                    rows={2}
                    value={technique}
                    onChange={(e) => setTechnique(e.target.value)}
                    placeholder="Imaging technique used..."
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label fw-bold">Findings</label>
                  <textarea 
                    className="form-control"
                    rows={6}
                    value={findings}
                    onChange={(e) => setFindings(e.target.value)}
                    placeholder="Detailed findings..."
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label fw-bold">Impression</label>
                  <textarea 
                    className="form-control"
                    rows={4}
                    value={impression}
                    onChange={(e) => setImpression(e.target.value)}
                    placeholder="Summary and impression..."
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label fw-bold">Recommendations</label>
                  <textarea 
                    className="form-control"
                    rows={3}
                    value={recommendations}
                    onChange={(e) => setRecommendations(e.target.value)}
                    placeholder="Follow-up recommendations..."
                  />
                </div>

                <div className="alert alert-info">
                  <small>
                    <strong>💡 Tip:</strong> Review AI-generated content carefully. 
                    Edit any sections that need clarification or correction.
                  </small>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Action Bar */}
        <div className="row mt-4 mb-4">
          <div className="col-12">
            <div className="card bg-light">
              <div className="card-body">
                <div className="d-flex justify-content-between align-items-center">
                  <div>
                    <h6 className="mb-0">Report Status: <span className="badge bg-warning">{report?.report_status || 'Draft'}</span></h6>
                  </div>
                  <div>
                    <button 
                      className="btn btn-secondary me-2"
                      onClick={() => navigate('/radiologist')}
                    >
                      Cancel
                    </button>
                    <button 
                      className="btn btn-primary me-2"
                      onClick={handleSaveDraft}
                      disabled={saving}
                    >
                      {saving ? 'Saving...' : 'Save Draft'}
                    </button>
                    <button 
                      className="btn btn-success btn-lg"
                      onClick={handlePublish}
                      disabled={publishing}
                    >
                      {publishing ? 'Publishing...' : '📤 Publish to Patient'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportEditorPage;