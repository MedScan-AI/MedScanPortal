import axios, { type AxiosResponse, type InternalAxiosRequestConfig, type AxiosError } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// API Service Functions

export const authService = {
  login: (email: string, password: string) => api.post('/auth/login', { email, password }),
  logout: () => api.post('/auth/logout'),
  getCurrentUser: () => api.get('/auth/me'),
};

export const patientService = {
  getScans: () => api.get('/patient/scans'),
  getScanById: (scanId: string) => api.get(`/patient/scans/${scanId}`),
  getReports: () => api.get('/patient/reports'),
  getReportById: (reportId: string) => api.get(`/patient/reports/${reportId}`),
  getProfile: () => api.get('/patient/profile'),
};

interface FeedbackData {
  feedback_type: string;
  radiologist_diagnosis: string;
  clinical_notes?: string;
  disagreement_reason?: string;
  additional_findings?: string;
  radiologist_confidence?: number;
  image_quality_rating?: number;
}

interface ReportData {
  report_title?: string;
  findings?: string;
  impression?: string;
  recommendations?: string;
}

export const radiologistService = {
  getPendingScans: () => api.get('/radiologist/scans/pending'),
  getCompletedScans: () => api.get('/radiologist/scans/completed'),
  getScanById: (scanId: string) => api.get(`/radiologist/scans/${scanId}`),
  startAIAnalysis: (scanId: string) => api.post(`/radiologist/scans/${scanId}/analyze`),
  submitFeedback: (scanId: string, feedbackData: FeedbackData) => 
    api.post(`/radiologist/scans/${scanId}/feedback`, feedbackData),
  updateReport: (reportId: string, reportData: ReportData) => 
    api.put(`/radiologist/reports/${reportId}`, reportData),
  publishReport: (reportId: string) => 
    api.post(`/radiologist/reports/${reportId}/publish`),
  unpublishReport: (reportId: string) => 
    api.post(`/radiologist/reports/${reportId}/unpublish`),
  getProfile: () => api.get('/radiologist/profile'),
};