import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import PatientPortal from './pages/PatientPortal';
import RadiologistPortal from './pages/RadiologistPortal';
import ScanDetailPage from './pages/ScanDetailPage';
import AIAnalysisPage from './pages/AIAnalysisPage';
import ReportEditorPage from './pages/ReportEditorPage';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthProvider } from './contexts/AuthContext';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="app">
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<LoginPage />} />
            
            {/* Protected Routes - Patient */}
            <Route
              path="/patient/*"
              element={
                <ProtectedRoute allowedRole="patient">
                  <PatientPortal />
                </ProtectedRoute>
              }
            />
            
            {/* Protected Routes - Radiologist */}
            <Route path="/radiologist" element={
              <ProtectedRoute allowedRole="radiologist">
                <RadiologistPortal />
              </ProtectedRoute>
            } />
            
            <Route path="/radiologist/scan/:scanId" element={
              <ProtectedRoute allowedRole="radiologist">
                <ScanDetailPage />
              </ProtectedRoute>
            } />
            
            <Route path="/radiologist/scan/:scanId/analysis" element={
              <ProtectedRoute allowedRole="radiologist">
                <AIAnalysisPage />
              </ProtectedRoute>
            } />
            
            <Route path="/radiologist/scan/:scanId/report" element={
              <ProtectedRoute allowedRole="radiologist">
                <ReportEditorPage />
              </ProtectedRoute>
            } />
            
            {/* Default Route */}
            <Route path="/" element={<Navigate to="/login" replace />} />
            
            {/* 404 Route */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;