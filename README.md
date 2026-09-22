# RPM Connected Care AI Platform — v2.2

Synthetic healthcare product portfolio prototype demonstrating an end-to-end Remote Patient Monitoring workflow.

## What v2.2 adds
- Patient Home & Daily Check-In with separate patient/device vs clinician-assisted entry provenance
- Cardiology and Cirrhosis daily questionnaire templates and questionnaire history
- Patient-specific min/max alert thresholds
- 7-day SpO2, heart-rate, and weight charts with visible values and rich hover details
- Device vs manual-entry provenance in trend points
- Wearable/device connectivity, battery, and internet status
- Assigned clinicians per patient
- Two-way secure-chat workflow simulator with automated acknowledgement and clinician notification
- Video-call workflow simulator (no real camera/audio)
- Clinical Command Center, Patient 360, alerts, clinician interventions, ECG PDF validation, API/FHIR view, mock EHR, lineage/audit
- Fixes navigation ambiguity between screen 1 and screens 10/11

## Safety
100% synthetic data. Portfolio demonstration only. Not a diagnostic system, medical device, production EHR integration, or live telehealth service. Patient-specific thresholds are demo values and not clinical recommendations.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud
Replace `app.py`, `requirements.txt`, and `README.md` in the existing GitHub repository. Streamlit should redeploy from the main branch.
