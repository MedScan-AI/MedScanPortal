import axios, { type AxiosResponse, type InternalAxiosRequestConfig, type AxiosError } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// Auth Service
export const authService = {
  login: (email: string, password: string) => api.post('/auth/login', { email, password }),
  logout: () => api.post('/auth/logout'),
  getCurrentUser: () => api.get('/auth/me'),
};

// Patient Service
export const patientService = {
  getScans: () => api.get('/patient/scans'),
  getScanById: (scanId: string) => api.get(`/patient/scans/${scanId}`),
  getReports: () => api.get('/patient/reports'),
  getReportById: (reportId: string) => api.get(`/patient/reports/${reportId}`),
  getProfile: () => api.get('/patient/profile'),
};

// Radiologist Service
interface FeedbackData {
  feedback_type: string;
  radiologist_diagnosis: string;
  ai_diagnosis?: string;
  clinical_notes?: string;
  disagreement_reason?: string;
  additional_findings?: string;
  radiologist_confidence?: number;
  image_quality_rating?: number;
}

interface ReportData {
  report_title?: string;
  clinical_indication?: string;
  technique?: string;
  findings?: string;
  impression?: string;
  recommendations?: string;
}

export const radiologistService = {
  // Scans
  getPendingScans: () => api.get('/radiologist/scans/pending'),
  getCompletedScans: () => api.get('/radiologist/scans/completed'),
  getScanById: (scanId: string) => api.get(`/radiologist/scans/${scanId}`),
  
  // Images - getScanImages uses the scan details endpoint (images are included)
  getScanImages: async (scanId: string) => {
    const response = await api.get(`/radiologist/scans/${scanId}`);
    // Extract images from scan details response
    return {
      data: response.data.images || []
    };
  },
  
  uploadImage: (scanId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/radiologist/scans/${scanId}/upload-image`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  
  // AI Analysis
  startAIAnalysis: (scanId: string) => api.post(`/radiologist/scans/${scanId}/analyze`),
  
  // AI Results - return mock data for now (will be implemented)
  getAIResults: async (scanId: string) => {
    // TODO: Implement actual endpoint to get AI results
    // For now, return mock data
    return {
      data: {
        prediction_id: '123',
        predicted_class: 'Tuberculosis',
        confidence_score: 0.87,
        class_probabilities: {
          'Normal': 0.13,
          'Tuberculosis': 0.87
        },
        gradcam_url: null,
        original_image_url: null
      }
    };
  },
  
  // Feedback & Diagnosis
  submitFeedback: (scanId: string, feedbackData: FeedbackData) => 
    api.post(`/radiologist/scans/${scanId}/feedback`, feedbackData),
  
  // Reports - mock for now
  getDraftReport: async (scanId: string) => {
    // TODO: Implement actual endpoint
    return {
      data: {
        id: '123',
        report_number: 'RPT-001',
        report_title: 'Chest X-Ray Report',
        clinical_indication: 'Evaluation for TB',
        technique: 'Chest X-ray PA and lateral views',
        findings: 'AI-generated findings will appear here...',
        impression: 'AI-generated impression...',
        recommendations: 'AI-generated recommendations...',
        report_status: 'draft',
        scan_number: 'SCAN-001',
        patient_name: 'Patient Name'
      }
    };
  },
  
  updateReport: (reportId: string, reportData: ReportData) => 
    api.put(`/radiologist/reports/${reportId}`, reportData),
  
  publishReport: (reportId: string) => 
    api.post(`/radiologist/reports/${reportId}/publish`),
  
  unpublishReport: (reportId: string) => 
    api.post(`/radiologist/reports/${reportId}/unpublish`),
  
  // Profile
  getProfile: () => api.get('/radiologist/profile'),
};

export type { FeedbackData, ReportData };