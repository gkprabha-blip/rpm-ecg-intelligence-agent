# RPM Connected Care AI Platform v2.5

Synthetic portfolio prototype for remote patient monitoring. No real PHI; not for clinical use.

## v2.5 additions
- Patient-registration required fields and validation: DOB MM/DD/YYYY, U.S. state dropdown, city/ZIP/phone validation, insurance and next-of-kin fields.
- Next-of-kin relationship dropdown modeled on common patient/related-person relationships.
- Care-plan enrollment duration and next-review fields. RPM has no universal fixed program duration; duration is clinician-defined for acute/chronic monitoring.
- Daily questionnaire templates for Cardiology, Cirrhosis/Liver Disease, Hypertension, Diabetes/CGM, Heart Failure, COPD/Pulmonary, Chronic Kidney Disease, and Post-Surgical Recovery.
- Patient Samples: optional cough/breathing audio recording and patient photo capture from the Patient Home page; linked to the patient/event and visible in Patient 360 and Mock EHR Media.
- Existing MPI duplicate prevention, trends, thresholds, device provenance, ECG PDF, communications, interventions, API/FHIR simulation, and audit trail remain.
