import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import PatientPortal from './pages/PatientPortal';
import RadiologistPortal from './pages/RadiologistPortal';
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
            <Route
              path="/radiologist/*"
              element={
                <ProtectedRoute allowedRole="radiologist">
                  <RadiologistPortal />
                </ProtectedRoute>
              }
            />
            
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