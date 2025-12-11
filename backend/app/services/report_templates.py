"""
Report Templates Module
Generates clear, focused diagnostic reports for patients
"""
from datetime import datetime
from typing import Dict
from app.models.scan import Scan


def capitalize_for_display(value: str, field_type: str) -> str:
    """Capitalize lowercase enum values for UI display."""
    if field_type == 'examination_type':
        return {
            'xray': 'X-ray', 
            'ct': 'CT', 
            'mri': 'MRI', 
            'pet': 'PET', 
            'ultrasound': 'Ultrasound'
        }.get(value, value)
    elif field_type in ['body_region', 'urgency_level']:
        return value.capitalize()
    return value


def generate_report_template(
    scan: Scan, 
    predicted_class: str, 
    confidence: float, 
    radiologist_name: str
) -> Dict[str, str]:
    """Generate patient-focused diagnostic report."""
    
    exam_display = capitalize_for_display(scan.examination_type.value, 'examination_type')
    diagnosis_lower = predicted_class.lower()
    
    if diagnosis_lower == "tuberculosis":
        return generate_tuberculosis_report(exam_display)
    elif diagnosis_lower in ["adenocarcinoma", "squamous_cell_carcinoma", 
                             "large_cell_carcinoma", "lung_cancer"]:
        return generate_lung_cancer_report(exam_display)
    elif diagnosis_lower == "other_abnormality":
        return generate_abnormality_report(exam_display)
    elif diagnosis_lower == "inconclusive":
        return generate_inconclusive_report(exam_display)
    else:  # normal
        return generate_normal_report(exam_display)


def generate_tuberculosis_report(exam_display: str) -> Dict[str, str]:
    """TB diagnosis report."""
    return {
        "title": f"{exam_display} - Chest",
        
        "indication": "Evaluation for respiratory symptoms including cough, fever, and night sweats.",
        
        "technique": f"{exam_display} of the chest performed with standard imaging protocol.",
        
        "findings": """Bilateral infiltrates identified in both upper lung zones. A cavity measuring 2.5 cm is present in the right upper lobe. Multiple small nodules are scattered throughout both lungs. Small fluid collections noted around the lungs. Enlarged lymph nodes visible in the chest.""",
        
        "impression": """Imaging findings are consistent with active tuberculosis infection affecting both lungs.

The pattern shows:
- Upper lobe disease with cavity formation
- Widespread small nodules suggesting infection spread
- Lymph node enlargement
- Fluid around the lungs""",
        
        "recommendations": """IMMEDIATE NEXT STEPS:
1. Start isolation precautions to prevent spread to others
2. Sputum testing needed to confirm TB bacteria
3. Blood tests including HIV screening
4. Begin TB medication treatment (4 medications typically)
5. Infectious disease doctor consultation

FOLLOW-UP CARE:
- Repeat chest X-ray in 2 months to check treatment response
- Monthly check-ups during treatment
- Liver function monitoring due to medications
- Contact tracing for close contacts

IMPORTANT: TB is treatable with 6-9 months of medication. Completing the full treatment course is essential."""
    }


def generate_lung_cancer_report(exam_display: str) -> Dict[str, str]:
    """Lung cancer diagnosis report."""
    return {
        "title": f"{exam_display} - Chest",
        
        "indication": "Evaluation of abnormal chest imaging findings.",
        
        "technique": f"Contrast-enhanced {exam_display} of the chest performed.",
        
        "findings": """A 3.2 cm mass with irregular borders identified in the right upper lung. The mass shows areas of tissue death in the center. Several enlarged lymph nodes detected in the chest, measuring up to 2.1 cm. Small amount of fluid present around the right lung.""",
        
        "impression": """Findings are highly concerning for lung cancer.

Key findings:
- 3.2 cm lung mass in right upper lobe with irregular borders
- Enlarged lymph nodes in the chest
- Preliminary staging suggests locally advanced disease
- Additional testing needed for complete evaluation""",
        
        "recommendations": """URGENT NEXT STEPS (Within 1-2 Weeks):
1. Biopsy procedure to confirm diagnosis and determine cancer type
2. PET scan to evaluate full extent of disease
3. Brain MRI to check for spread
4. Blood tests and additional CT scans
5. Appointments with cancer specialists (oncology, surgery)

ADDITIONAL TESTING:
- Molecular testing on biopsy sample (guides treatment options)
- Lung function tests
- Heart evaluation

TREATMENT PLANNING:
- Multidisciplinary cancer team review
- Treatment options may include surgery, chemotherapy, radiation, or targeted therapy
- Early supportive care consultation

IMPORTANT: Many treatment options are available. The next step is confirming the diagnosis with a biopsy."""
    }


def generate_normal_report(exam_display: str) -> Dict[str, str]:
    """Normal/clear report."""
    return {
        "title": f"{exam_display} - Chest",
        
        "indication": "Routine health screening.",
        
        "technique": f"{exam_display} of the chest performed.",
        
        "findings": """Both lungs are clear with normal appearance. No masses, nodules, or suspicious areas identified. Heart size is normal. No fluid around the lungs. Bones visible on the image show no abnormalities.""",
        
        "impression": """Normal chest imaging study.

No abnormalities detected.""",
        
        "recommendations": """FOLLOW-UP:
- No immediate imaging follow-up needed
- Continue routine health check-ups with your primary doctor

WHEN TO RETURN:
Contact your doctor if you develop:
- Persistent cough lasting more than 3 weeks
- Chest pain or shortness of breath
- Coughing up blood
- Unexplained weight loss or fever

PREVENTIVE CARE:
- Avoid tobacco and secondhand smoke
- Stay current with vaccinations
- Maintain healthy lifestyle with regular exercise"""
    }


def generate_abnormality_report(exam_display: str) -> Dict[str, str]:
    """Non-specific abnormality report."""
    return {
        "title": f"{exam_display} - Chest",
        
        "indication": "Evaluation of chest symptoms.",
        
        "technique": f"{exam_display} of the chest performed.",
        
        "findings": """An area of increased density identified in the right lower lung. No masses or cavities seen. No fluid around the lungs. Lymph nodes appear normal in size.""",
        
        "impression": """Abnormal finding in the right lower lung.

Most likely possibilities:
- Pneumonia (lung infection)
- Inflammation
- Atypical infection

Does not show features of tuberculosis or cancer.""",
        
        "recommendations": """IMMEDIATE CARE:
1. Antibiotic treatment if infection suspected
2. Blood tests to check infection markers
3. Symptom monitoring

FOLLOW-UP:
- Repeat chest X-ray in 4-6 weeks to confirm clearing
- Earlier imaging if symptoms worsen
- Return if fever persists or breathing difficulty develops

MONITORING:
- Track temperature and symptoms
- Seek immediate care if condition worsens"""
    }


def generate_inconclusive_report(exam_display: str) -> Dict[str, str]:
    """Inconclusive findings report."""
    return {
        "title": f"{exam_display} - Chest",
        
        "indication": "Follow-up evaluation needed for unclear findings.",
        
        "technique": f"{exam_display} of the chest performed.",
        
        "findings": """Subtle opacity noted in the right upper lung area. The finding is difficult to fully characterize on this study. Remaining lung fields appear clear. Heart and other structures appear normal.""",
        
        "impression": """Findings require additional evaluation.

The subtle opacity could represent:
- Minor infection or inflammation
- Normal variant or overlapping structures  
- Early stage process requiring monitoring

Cannot definitively rule out or confirm abnormality on current images.""",
        
        "recommendations": """ADDITIONAL IMAGING NEEDED:
1. CT scan recommended for better evaluation
   OR
2. Repeat chest X-ray in 1-2 weeks
3. Comparison with any prior imaging if available

CLINICAL CORRELATION:
- Discuss symptoms with your doctor
- Physical examination findings
- Review your medical history

TIMING:
- Additional imaging within 1-2 weeks recommended
- Sooner if you have symptoms"""
    }