import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await login(email, password);
    
    if (!result.success) {
      setError(result.error || 'Login failed. Please check your credentials.');
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 50%, #246d93 100%)',
      padding: '2rem'
    }}>
      <div style={{ width: '100%', maxWidth: '440px' }}>
        <div className="card shadow-lg border-0" style={{ borderRadius: '16px', overflow: 'hidden' }}>
          {/* Header */}
          <div className="card-header text-white text-center py-4 border-0" style={{
            background: 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 100%)'
          }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>⛨</div>
            <h2 className="mb-1" style={{ fontWeight: 600, fontSize: '1.75rem' }}>MedScanAI Platform</h2>
            <p className="mb-0" style={{ fontSize: '0.9rem', opacity: 0.9 }}>
              AI-Assisted Medical Imaging System
            </p>
          </div>

          {/* Body */}
          <div className="card-body p-4">
            {error && (
              <div className="alert alert-danger d-flex align-items-center" role="alert">
                <svg width="20" height="20" fill="currentColor" className="me-2" viewBox="0 0 16 16">
                  <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                  <path d="M7.002 11a1 1 0 1 1 2 0 1 1 0 0 1-2 0zM7.1 4.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 4.995z"/>
                </svg>
                <div>{error}</div>
              </div>
            )}
            
            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label htmlFor="email" className="form-label fw-semibold" style={{ color: '#2c3e50' }}>
                  Email Address
                </label>
                <input
                  type="email"
                  className="form-control form-control-lg"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your.email@example.com"
                  required
                  disabled={loading}
                  style={{
                    borderRadius: '8px',
                    border: '2px solid #e0e6ed',
                    padding: '0.75rem 1rem'
                  }}
                />
              </div>
              
              <div className="mb-4">
                <label htmlFor="password" className="form-label fw-semibold" style={{ color: '#2c3e50' }}>
                  Password
                </label>
                <input
                  type="password"
                  className="form-control form-control-lg"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  disabled={loading}
                  style={{
                    borderRadius: '8px',
                    border: '2px solid #e0e6ed',
                    padding: '0.75rem 1rem'
                  }}
                />
              </div>
              
              <button 
                type="submit" 
                className="btn btn-lg w-100 text-white fw-semibold"
                disabled={loading}
                style={{
                  background: 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 100%)',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '0.875rem',
                  fontSize: '1.05rem',
                  transition: 'transform 0.2s, box-shadow 0.2s'
                }}
                onMouseEnter={(e) => {
                  if (!loading) {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = '0 8px 16px rgba(15, 76, 129, 0.3)';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                {loading ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2" />
                    Signing in...
                  </>
                ) : (
                  'Sign In'
                )}
              </button>
            </form>
          </div>

          {/* Footer */}
          <div className="card-footer text-center border-0" style={{ 
            background: '#f8f9fa',
            padding: '1.25rem'
          }}>
            <p className="mb-2" style={{ fontSize: '0.85rem', color: '#6c757d', fontWeight: 500 }}>
              Demo Credentials
            </p>
            <div style={{ fontSize: '0.8rem', color: '#495057', lineHeight: 1.6 }}>
              <strong>Radiologist:</strong> radiologist@hospital.com<br />
              <strong>Patient:</strong> patient@email.com<br />
              <strong>Password:</strong> demo123
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;