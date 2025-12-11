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
  const [unpublishing, setUnpublishing] = useState(false);

  const [reportTitle, setReportTitle] = useState('');
  const [clinicalIndication, setClinicalIndication] = useState('');
  const [technique, setTechnique] = useState('');
  const [findings, setFindings] = useState('');
  const [impression, setImpression] = useState('');
  const [recommendations, setRecommendations] = useState('');

  const isPublished = report?.report_status === 'published';

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
      
      setReportTitle(data.report_title || '');
      setClinicalIndication(data.clinical_indication || '');
      setTechnique(data.technique || '');
      setFindings(data.findings || '');
      setImpression(data.impression || '');
      setRecommendations(data.recommendations || '');
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (err) {
      alert('Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!report) return;
    
    if (isPublished) {
      alert('Cannot edit a published report. Please unpublish it first.');
      return;
    }
    
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
      alert('Draft saved successfully');
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (err) {
      alert('Failed to save draft');
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!report) return;
    
    if (!window.confirm(
      'Publish this report to the patient?\n\n' +
      'Once published:\n' +
      '• The patient will be able to view this report\n' +
      '• You will NOT be able to edit it unless you unpublish it first\n\n' +
      'Continue?'
    )) {
      return;
    }

    setPublishing(true);
    try {
      // Save any pending changes first
      await handleSaveDraft();
      
      // Then publish
      await radiologistService.publishReport(report.id);
      
      alert('Report published successfully!\n\nThe patient can now view this report.');
      
      // Refresh to get updated status
      await fetchDraftReport();
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (err) {
      alert('Failed to publish report');
    } finally {
      setPublishing(false);
    }
  };

  const handleUnpublish = async () => {
    if (!report) return;
    
    if (!window.confirm(
      'Unpublish this report?\n\n' +
      ' This will:\n' +
      '• Hide the report from the patient\n' +
      '• Require re-publishing for patient to see it again\n\n' +
      'Continue?'
    )) {
      return;
    }

    setUnpublishing(true);
    try {
      await radiologistService.unpublishReport(report.id);
      
      alert('Report unpublished successfully!\n\nYou can now edit the report.');
      
      // Refresh to get updated status
      await fetchDraftReport();
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (err) {
      alert('Failed to unpublish report');
    } finally {
      setUnpublishing(false);
    }
  };

  if (loading) {
    return (
      <div className="container mt-5">
        <div className="text-center p-5">
          <div className="spinner-border text-primary" />
          <p className="mt-3 text-muted">Loading report...</p>
        </div>
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
            onClick={() => navigate('/radiologist')}
            style={{ borderRadius: '6px', padding: '0.5rem 1.25rem' }}
          >
            ← Back to Queue
          </button>
          <div className="d-flex align-items-center">
            <span className="navbar-brand fw-bold me-3">Report Editor</span>
            {isPublished && (
              <span className="badge bg-success" style={{ 
                fontSize: '0.85rem',
                padding: '0.5rem 1rem'
              }}>
                ✓ Published
              </span>
            )}
            {!isPublished && (
              <span className="badge bg-warning text-dark" style={{ 
                fontSize: '0.85rem',
                padding: '0.5rem 1rem'
              }}>
                 Draft
              </span>
            )}
          </div>
          <div className="d-flex gap-2">
            {isPublished ? (
              <button 
                className="btn btn-warning btn-sm"
                onClick={handleUnpublish}
                disabled={unpublishing}
                style={{ fontWeight: 500 }}
              >
                {unpublishing ? 'Unpublishing...' : '🔓 Unpublish Report'}
              </button>
            ) : (
              <>
                <button 
                  className="btn btn-light btn-sm"
                  onClick={handleSaveDraft}
                  disabled={saving}
                  style={{ fontWeight: 500 }}
                >
                  {saving ? 'Saving...' : '💾 Save Draft'}
                </button>
                <button 
                  className="btn btn-success btn-sm"
                  onClick={handlePublish}
                  disabled={publishing}
                  style={{ fontWeight: 500 }}
                >
                  {publishing ? 'Publishing...' : '✓ Publish Report'}
                </button>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Alert Banner for Published Reports */}
      {isPublished && (
        <div className="alert alert-info border-0 m-4" style={{ 
          borderRadius: '12px',
          borderLeft: '4px solid #0dcaf0'
        }}>
          <div className="d-flex align-items-start">
            <div style={{ fontSize: '1.5rem', marginRight: '1rem' }}>🔒</div>
            <div>
              <strong className="d-block mb-1">This report is published and visible to the patient</strong>
              <small style={{ lineHeight: 1.6 }}>
                Editing is disabled. Click "Unpublish Report" in the top-right to make changes.
              </small>
            </div>
          </div>
        </div>
      )}

      <div className="container-fluid px-4 py-4">
        <div className="row g-4">
          {/* Preview */}
          <div className="col-lg-6">
            <div className="card border-0 shadow-sm" style={{ borderRadius: '12px' }}>
              <div className="card-header text-white border-0" style={{
                background: isPublished 
                  ? 'linear-gradient(135deg, #28a745 0%, #20c997 100%)'
                  : 'linear-gradient(135deg, #17a2b8 0%, #20c997 100%)',
                borderRadius: '12px 12px 0 0',
                padding: '1rem 1.25rem'
              }}>
                <h6 className="mb-0 fw-bold">📄 Report Preview</h6>
              </div>
              <div className="card-body p-4" style={{ backgroundColor: '#f8f9fa' }}>
                <h5 className="text-center mb-4 fw-bold">{reportTitle || 'Radiology Report'}</h5>
                
                <div className="mb-3">
                  <p className="mb-1"><strong>Patient:</strong> {report?.patient_name}</p>
                  <p className="mb-1"><strong>Scan:</strong> {report?.scan_number}</p>
                  <p className="mb-0"><strong>Report:</strong> {report?.report_number}</p>
                </div>

                <hr />

                {clinicalIndication && (
                  <div className="mb-3">
                    <h6 className="fw-bold text-uppercase small">Clinical Indication</h6>
                    <p className="mb-0">{clinicalIndication}</p>
                  </div>
                )}

                {technique && (
                  <div className="mb-3">
                    <h6 className="fw-bold text-uppercase small">Technique</h6>
                    <p className="mb-0">{technique}</p>
                  </div>
                )}

                <div className="mb-3">
                  <h6 className="fw-bold text-uppercase small">Findings</h6>
                  <p className="mb-0" style={{ whiteSpace: 'pre-wrap' }}>{findings}</p>
                </div>

                <div className="mb-3">
                  <h6 className="fw-bold text-uppercase small">Impression</h6>
                  <p className="mb-0" style={{ whiteSpace: 'pre-wrap' }}>{impression}</p>
                </div>

                {recommendations && (
                  <div className="mb-3">
                    <h6 className="fw-bold text-uppercase small">Recommendations</h6>
                    <p className="mb-0" style={{ whiteSpace: 'pre-wrap' }}>{recommendations}</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Editor */}
          <div className="col-lg-6">
            <div className="card border-0 shadow-sm" style={{ borderRadius: '12px' }}>
              <div className="card-header bg-light border-0" style={{
                borderRadius: '12px 12px 0 0',
                padding: '1rem 1.25rem'
              }}>
                <h6 className="mb-0 fw-bold">✏️ Edit Report</h6>
                <small className="text-muted">
                  {isPublished 
                    ? 'Report is locked - unpublish to edit' 
                    : 'Review and edit AI-generated content'}
                </small>
              </div>
              <div className="card-body p-4">
                <div className="mb-3">
                  <label className="form-label fw-semibold small">Report Title</label>
                  <input 
                    type="text"
                    className="form-control"
                    value={reportTitle}
                    onChange={(e) => setReportTitle(e.target.value)}
                    placeholder="e.g., Chest X-Ray Report"
                    disabled={isPublished}
                    style={{
                      background: isPublished ? '#e9ecef' : 'white',
                      cursor: isPublished ? 'not-allowed' : 'text'
                    }}
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label fw-semibold small">Clinical Indication</label>
                  <textarea 
                    className="form-control"
                    rows={2}
                    value={clinicalIndication}
                    onChange={(e) => setClinicalIndication(e.target.value)}
                    placeholder="Reason for examination..."
                    disabled={isPublished}
                    style={{
                      background: isPublished ? '#e9ecef' : 'white',
                      cursor: isPublished ? 'not-allowed' : 'text'
                    }}
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label fw-semibold small">Technique</label>
                  <textarea 
                    className="form-control"
                    rows={2}
                    value={technique}
                    onChange={(e) => setTechnique(e.target.value)}
                    placeholder="Imaging technique..."
                    disabled={isPublished}
                    style={{
                      background: isPublished ? '#e9ecef' : 'white',
                      cursor: isPublished ? 'not-allowed' : 'text'
                    }}
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label fw-semibold small">Findings</label>
                  <textarea 
                    className="form-control"
                    rows={6}
                    value={findings}
                    onChange={(e) => setFindings(e.target.value)}
                    placeholder="Detailed findings..."
                    disabled={isPublished}
                    style={{
                      background: isPublished ? '#e9ecef' : 'white',
                      cursor: isPublished ? 'not-allowed' : 'text'
                    }}
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label fw-semibold small">Impression</label>
                  <textarea 
                    className="form-control"
                    rows={4}
                    value={impression}
                    onChange={(e) => setImpression(e.target.value)}
                    placeholder="Summary..."
                    disabled={isPublished}
                    style={{
                      background: isPublished ? '#e9ecef' : 'white',
                      cursor: isPublished ? 'not-allowed' : 'text'
                    }}
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label fw-semibold small">Recommendations</label>
                  <textarea 
                    className="form-control"
                    rows={3}
                    value={recommendations}
                    onChange={(e) => setRecommendations(e.target.value)}
                    placeholder="Follow-up recommendations..."
                    disabled={isPublished}
                    style={{
                      background: isPublished ? '#e9ecef' : 'white',
                      cursor: isPublished ? 'not-allowed' : 'text'
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Action Bar */}
        <div className="row mt-4 mb-4">
          <div className="col-12">
            <div className="card border-0 shadow-sm" style={{ borderRadius: '12px' }}>
              <div className="card-body">
                <div className="d-flex justify-content-between align-items-center">
                  <div>
                    <span className="text-muted small">Report Status: </span>
                    {isPublished ? (
                      <span className="badge bg-success ms-2" style={{ 
                        fontSize: '0.9rem',
                        padding: '0.5rem 0.85rem'
                      }}>
                        ✓ Published to Patient
                      </span>
                    ) : (
                      <span className="badge bg-warning text-dark ms-2" style={{ 
                        fontSize: '0.9rem',
                        padding: '0.5rem 0.85rem'
                      }}>
                         Draft (Not Visible to Patient)
                      </span>
                    )}
                  </div>
                  <div className="d-flex gap-2">
                    <button 
                      className="btn btn-secondary"
                      onClick={() => navigate('/radiologist')}
                    >
                      Cancel
                    </button>
                    {isPublished ? (
                      <button 
                        className="btn btn-warning"
                        onClick={handleUnpublish}
                        disabled={unpublishing}
                      >
                        {unpublishing ? 'Unpublishing...' : '🔓 Unpublish to Edit'}
                      </button>
                    ) : (
                      <>
                        <button 
                          className="btn btn-primary"
                          onClick={handleSaveDraft}
                          disabled={saving}
                        >
                          {saving ? 'Saving...' : '💾 Save Draft'}
                        </button>
                        <button 
                          className="btn btn-success"
                          onClick={handlePublish}
                          disabled={publishing}
                        >
                          {publishing ? 'Publishing...' : '✓ Publish to Patient'}
                        </button>
                      </>
                    )}
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