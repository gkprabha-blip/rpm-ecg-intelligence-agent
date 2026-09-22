# RPM Connected Care AI Platform — v2.6

Synthetic portfolio prototype for demonstrating end-to-end remote patient monitoring product design. It is not a medical device, diagnostic system, clinical protocol, or live EHR integration.

## V2.7 product structure

### Patient Experience
- Today / Care Plan daily task list and completion progress
- Patient Home & Daily Check-In with device/manual provenance
- Care-plan-specific questionnaires, ECG, connected devices and Patient Samples
- Patient/clinician chat and simulated video workflow

### Clinical Experience
- Clinical Command Center with actionable work queue
- Patient 360 trends, configurable thresholds and provenance
- Clinician interventions and closed-loop documentation
- Care Coordination for home nursing, labs, device replacement, mobile imaging, DME and support

### Integration
- ECG document validation and synthetic PDF
- Normalized API and FHIR-style payload viewer
- Mock EHR flowsheet/media/communications
- Shared MPI duplicate prevention
- End-to-end lineage and audit trail

### AI & Product
- AI Agent Center for workflow prioritization
- Configurable Care Pathway Engine
- Architecture, guardrails, epics and KPIs

## Safety
All patients, MRNs, readings, questionnaires, thresholds, alerts, documents and workflows are synthetic. Thresholds and pathway examples are for product demonstration only and are not clinical recommendations. The prototype does not diagnose, prescribe, or replace clinician judgment.

## Run
```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```


## V2.7 updates
- Neutral teal threshold controls; red is reserved for actual out-of-threshold readings/alerts.
- Weight display can switch between lb and kg; skin temperature between °C and °F, including trend and threshold views.
- New patient cough audio/photo samples create Clinical Command Center review alerts and are directly reviewable there.
- Patient samples remain available in Patient Home, Patient 360, and Mock EHR Media.
