-- MedScanAI PLATFORM DATABASE SCHEMA
-- Dual-Role System: Radiologist & Patient Portal
-- Technology: PostgreSQL

-- UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- USERS & AUTHENTICATION
CREATE TYPE user_role AS ENUM ('patient', 'radiologist', 'admin');
CREATE TYPE user_status AS ENUM ('active', 'inactive', 'suspended');

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL,
    status user_status DEFAULT 'active',
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    
    -- Indexes
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_status ON users(status);

-- PATIENT PROFILES
CREATE TYPE gender_type AS ENUM ('Male', 'Female', 'Other', 'Prefer not to say');

CREATE TABLE patient_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    patient_id VARCHAR(50) UNIQUE NOT NULL, -- Maps to Patient_ID from CSV
    age_years INTEGER,
    weight_kg DECIMAL(5,2),
    height_cm DECIMAL(5,2),
    gender gender_type,
    address TEXT,
    emergency_contact_name VARCHAR(200),
    emergency_contact_phone VARCHAR(20),
    blood_type VARCHAR(5),
    allergies TEXT[],
    medical_history TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_patient_profiles_user_id ON patient_profiles(user_id);
CREATE INDEX idx_patient_profiles_patient_id ON patient_profiles(patient_id);

-- RADIOLOGIST PROFILES
CREATE TABLE radiologist_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    license_number VARCHAR(100) UNIQUE NOT NULL,
    specialization VARCHAR(200),
    years_of_experience INTEGER,
    institution VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_radiologist_profiles_user_id ON radiologist_profiles(user_id);

-- SCANS & IMAGING
CREATE TYPE examination_type AS ENUM ('X-ray', 'CT', 'MRI', 'PET', 'Ultrasound');
CREATE TYPE body_region AS ENUM ('Chest', 'Head', 'Abdomen', 'Pelvis', 'Spine', 'Extremities');
CREATE TYPE urgency_level AS ENUM ('Routine', 'Urgent', 'Emergent');
CREATE TYPE scan_status AS ENUM ('pending', 'in_progress', 'ai_analyzed', 'radiologist_reviewed', 'completed', 'cancelled');

CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,
    scan_number VARCHAR(50) UNIQUE NOT NULL,
    
    -- Clinical Information
    examination_type examination_type NOT NULL,
    body_region body_region NOT NULL,
    urgency_level urgency_level DEFAULT 'Routine',
    presenting_symptoms TEXT[],
    current_medications TEXT[],
    previous_surgeries TEXT[],
    
    -- Scan Details
    scan_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    imaging_facility VARCHAR(200),
    referring_physician VARCHAR(200),
    clinical_notes TEXT,
    
    -- Workflow Status
    status scan_status DEFAULT 'pending',
    assigned_radiologist_id UUID REFERENCES radiologist_profiles(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ai_analysis_started_at TIMESTAMP WITH TIME ZONE,
    ai_analysis_completed_at TIMESTAMP WITH TIME ZONE,
    radiologist_review_started_at TIMESTAMP WITH TIME ZONE,
    radiologist_review_completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_scans_patient_id ON scans(patient_id);
CREATE INDEX idx_scans_status ON scans(status);
CREATE INDEX idx_scans_assigned_radiologist ON scans(assigned_radiologist_id);
CREATE INDEX idx_scans_scan_date ON scans(scan_date DESC);
CREATE INDEX idx_scans_urgency ON scans(urgency_level);

-- SCAN IMAGES (Multiple images per scan)
CREATE TABLE scan_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    image_path TEXT NOT NULL, -- Original image path
    image_url TEXT, -- Cloud storage URL if applicable
    image_order INTEGER DEFAULT 1,
    file_size_bytes BIGINT,
    image_width INTEGER,
    image_height INTEGER,
    image_format VARCHAR(10),
    dicom_metadata JSONB, -- Store DICOM tags if applicable
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scan_images_scan_id ON scan_images(scan_id);

-- AI PREDICTIONS
CREATE TYPE prediction_class AS ENUM ('Normal', 'Tuberculosis', 'Lung_Cancer', 'Other_Abnormality');

CREATE TABLE ai_predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    
    -- Model Information
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    inference_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Prediction Results
    predicted_class prediction_class NOT NULL,
    confidence_score DECIMAL(5,4) NOT NULL, -- 0.0000 to 1.0000
    
    -- Class Probabilities (JSON for flexibility)
    class_probabilities JSONB NOT NULL, -- e.g., {"Normal": 0.05, "Tuberculosis": 0.92, "Lung_Cancer": 0.03}
    
    -- Region Detection (if applicable)
    detected_regions JSONB, -- Array of bounding boxes with coordinates and labels
    
    -- Processing Metadata
    inference_time_ms INTEGER,
    preprocessing_applied JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_predictions_scan_id ON ai_predictions(scan_id);
CREATE INDEX idx_ai_predictions_predicted_class ON ai_predictions(predicted_class);
CREATE INDEX idx_ai_predictions_confidence ON ai_predictions(confidence_score DESC);

-- GRAD-CAM VISUALIZATIONS
CREATE TABLE gradcam_outputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ai_prediction_id UUID NOT NULL REFERENCES ai_predictions(id) ON DELETE CASCADE,
    scan_image_id UUID NOT NULL REFERENCES scan_images(id) ON DELETE CASCADE,
    
    -- Grad-CAM Data
    heatmap_path TEXT NOT NULL, -- Path to generated heatmap image
    heatmap_url TEXT, -- Cloud storage URL
    overlay_path TEXT, -- Path to overlay image (original + heatmap)
    overlay_url TEXT,
    
    -- Technical Details
    target_layer VARCHAR(100), -- Which layer was used for Grad-CAM
    target_class prediction_class,
    
    -- Metadata
    generation_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_gradcam_outputs_prediction_id ON gradcam_outputs(ai_prediction_id);
CREATE INDEX idx_gradcam_outputs_scan_image_id ON gradcam_outputs(scan_image_id);

-- RADIOLOGIST FEEDBACK & OVERRIDES
CREATE TYPE feedback_type AS ENUM ('accept', 'partial_override', 'full_override', 'reject');
CREATE TYPE diagnosis_class AS ENUM ('Normal', 'Tuberculosis', 'Lung_Cancer', 'Other_Abnormality', 'Inconclusive');

CREATE TABLE radiologist_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    ai_prediction_id UUID NOT NULL REFERENCES ai_predictions(id) ON DELETE CASCADE,
    radiologist_id UUID NOT NULL REFERENCES radiologist_profiles(id) ON DELETE CASCADE,
    
    -- Feedback Details
    feedback_type feedback_type NOT NULL,
    
    -- AI vs Radiologist Diagnosis
    ai_diagnosis prediction_class NOT NULL,
    radiologist_diagnosis diagnosis_class NOT NULL,
    
    -- Detailed Feedback
    clinical_notes TEXT,
    disagreement_reason TEXT, -- Why radiologist disagreed with AI
    additional_findings TEXT,
    
    -- Confidence & Quality
    radiologist_confidence DECIMAL(3,2), -- 0.00 to 1.00
    image_quality_rating INTEGER CHECK (image_quality_rating BETWEEN 1 AND 5),
    
    -- Timestamps
    feedback_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_radiologist_feedback_scan_id ON radiologist_feedback(scan_id);
CREATE INDEX idx_radiologist_feedback_radiologist_id ON radiologist_feedback(radiologist_id);
CREATE INDEX idx_radiologist_feedback_type ON radiologist_feedback(feedback_type);
CREATE INDEX idx_radiologist_feedback_timestamp ON radiologist_feedback(feedback_timestamp DESC);

-- REPORTS
CREATE TYPE report_status AS ENUM ('draft', 'pending_review', 'approved', 'published', 'revised', 'archived');
CREATE TYPE report_type AS ENUM ('preliminary_ai', 'final_radiologist');

CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    report_number VARCHAR(50) UNIQUE NOT NULL,
    
    -- Report Metadata
    report_type report_type NOT NULL,
    report_status report_status DEFAULT 'draft',
    
    -- Content
    report_title VARCHAR(500),
    clinical_indication TEXT,
    technique TEXT,
    findings TEXT NOT NULL,
    impression TEXT NOT NULL,
    recommendations TEXT,
    
    -- AI-Generated Content (if applicable)
    ai_generated_content JSONB, -- Store original AI-generated text
    ai_model_version VARCHAR(50),
    
    -- Radiologist Information
    created_by_radiologist_id UUID REFERENCES radiologist_profiles(id),
    approved_by_radiologist_id UUID REFERENCES radiologist_profiles(id),
    
    -- Version Control
    version INTEGER DEFAULT 1,
    previous_version_id UUID REFERENCES reports(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP WITH TIME ZONE,
    published_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit Trail
    edit_history JSONB -- Track all edits made to the report
);

CREATE INDEX idx_reports_scan_id ON reports(scan_id);
CREATE INDEX idx_reports_status ON reports(report_status);
CREATE INDEX idx_reports_created_by ON reports(created_by_radiologist_id);
CREATE INDEX idx_reports_published_at ON reports(published_at DESC);

-- REPORT PUBLICATION STATUS
CREATE TABLE report_publications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    
    -- Publication Details
    published_by_radiologist_id UUID NOT NULL REFERENCES radiologist_profiles(id),
    publication_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Visibility Control
    visible_to_patient BOOLEAN DEFAULT TRUE,
    visibility_start_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    visibility_end_date TIMESTAMP WITH TIME ZONE, -- Optional: auto-archive after certain date
    
    -- Unpublication (if needed)
    unpublished_at TIMESTAMP WITH TIME ZONE,
    unpublished_by_radiologist_id UUID REFERENCES radiologist_profiles(id),
    unpublish_reason TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_report_publications_report_id ON report_publications(report_id);
CREATE INDEX idx_report_publications_visible ON report_publications(visible_to_patient);

-- AUDIT TRAIL & SYSTEM LOGS
CREATE TYPE audit_action AS ENUM (
    'user_login', 'user_logout', 
    'scan_created', 'scan_updated', 'scan_deleted',
    'ai_analysis_started', 'ai_analysis_completed',
    'report_created', 'report_updated', 'report_published', 'report_unpublished',
    'feedback_submitted', 'settings_changed'
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action audit_action NOT NULL,
    entity_type VARCHAR(50), -- e.g., 'scan', 'report', 'user'
    entity_id UUID,
    
    -- Change Details
    old_values JSONB,
    new_values JSONB,
    
    -- Request Metadata
    ip_address INET,
    user_agent TEXT,
    
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);

-- ML MODEL TRAINING DATA (For Continuous Learning)
CREATE TABLE training_data_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID NOT NULL REFERENCES scans(id),
    ai_prediction_id UUID NOT NULL REFERENCES ai_predictions(id),
    radiologist_feedback_id UUID NOT NULL REFERENCES radiologist_feedback(id),
    
    -- Training Flags
    used_for_training BOOLEAN DEFAULT FALSE,
    training_batch_id VARCHAR(100),
    training_date TIMESTAMP WITH TIME ZONE,
    
    -- Quality Control
    data_quality_score DECIMAL(3,2),
    include_in_training BOOLEAN DEFAULT TRUE,
    exclusion_reason TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_training_queue_used ON training_data_queue(used_for_training);
CREATE INDEX idx_training_queue_scan_id ON training_data_queue(scan_id);

-- NOTIFICATIONS & ALERTS
CREATE TYPE notification_type AS ENUM (
    'scan_completed', 'report_published', 'report_updated',
    'urgent_scan_assigned', 'feedback_required', 'system_alert'
);
CREATE TYPE notification_status AS ENUM ('unread', 'read', 'archived');

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type notification_type NOT NULL,
    status notification_status DEFAULT 'unread',
    
    -- Content
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    action_url TEXT, -- Link to relevant page
    
    -- Related Entities
    related_scan_id UUID REFERENCES scans(id),
    related_report_id UUID REFERENCES reports(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- SYSTEM SETTINGS & CONFIGURATION
CREATE TABLE system_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value JSONB NOT NULL,
    description TEXT,
    last_updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- VIEWS FOR COMMON QUERIES
-- View: Complete Scan Information with Patient Details
CREATE VIEW v_scan_details AS
SELECT 
    s.id as scan_id,
    s.scan_number,
    s.examination_type,
    s.body_region,
    s.urgency_level,
    s.status as scan_status,
    s.scan_date,
    u.id as patient_user_id,
    u.first_name as patient_first_name,
    u.last_name as patient_last_name,
    pp.patient_id,
    pp.age_years,
    pp.gender,
    s.presenting_symptoms,
    s.current_medications,
    s.previous_surgeries,
    rad_u.first_name as radiologist_first_name,
    rad_u.last_name as radiologist_last_name,
    s.created_at,
    s.ai_analysis_completed_at,
    s.radiologist_review_completed_at
FROM scans s
JOIN patient_profiles pp ON s.patient_id = pp.id
JOIN users u ON pp.user_id = u.id
LEFT JOIN radiologist_profiles rp ON s.assigned_radiologist_id = rp.id
LEFT JOIN users rad_u ON rp.user_id = rad_u.id;

-- View: Pending Scans for Radiologists
CREATE VIEW v_pending_scans AS
SELECT 
    s.id,
    s.scan_number,
    s.urgency_level,
    s.examination_type,
    s.body_region,
    s.scan_date,
    u.first_name || ' ' || u.last_name as patient_name,
    pp.patient_id,
    s.status,
    s.assigned_radiologist_id
FROM scans s
JOIN patient_profiles pp ON s.patient_id = pp.id
JOIN users u ON pp.user_id = u.id
WHERE s.status IN ('pending', 'in_progress', 'ai_analyzed')
ORDER BY 
    CASE s.urgency_level
        WHEN 'Emergent' THEN 1
        WHEN 'Urgent' THEN 2
        WHEN 'Routine' THEN 3
    END,
    s.scan_date ASC;

-- View: Published Reports for Patients
CREATE VIEW v_patient_reports AS
SELECT 
    r.id as report_id,
    r.report_number,
    r.report_title,
    r.findings,
    r.impression,
    r.recommendations,
    r.published_at,
    s.scan_number,
    s.examination_type,
    s.body_region,
    s.scan_date,
    pp.patient_id,
    u.id as patient_user_id
FROM reports r
JOIN scans s ON r.scan_id = s.id
JOIN patient_profiles pp ON s.patient_id = pp.id
JOIN users u ON pp.user_id = u.id
JOIN report_publications rp ON r.id = rp.report_id
WHERE r.report_status = 'published'
AND rp.visible_to_patient = TRUE
AND rp.unpublished_at IS NULL;

-- TRIGGERS FOR AUTO-UPDATING TIMESTAMPS
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_patient_profiles_updated_at BEFORE UPDATE ON patient_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_radiologist_profiles_updated_at BEFORE UPDATE ON radiologist_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scans_updated_at BEFORE UPDATE ON scans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reports_updated_at BEFORE UPDATE ON reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();