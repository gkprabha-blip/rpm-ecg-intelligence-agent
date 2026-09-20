# RPM Connected Care AI Platform — v2.1

Portfolio prototype based on a synthetic Remote Patient Monitoring workflow. It demonstrates connected-device ingestion, longitudinal trends, device-reported ECG classifications, workflow alerts, human-in-the-loop clinician intervention, ECG PDF integrity, API/FHIR-style transformation, and simulated EHR flowsheet/Media routing.

## What changed in v2.1
- New ingestion is clearly separated from existing stored history.
- Every ingestion creates a new timestamped event; it does not overwrite prior readings.
- Seven-day SpO2, heart-rate, and weight trends are visible in Patient 360.
- Clinical Command Center shows alert and outreach status.
- Clinician Interventions screen supports phone call, secure chat/message, video call, voicemail/unreachable, and care-team escalation.
- Patient 360 and Mock EHR show communication history.
- Data lineage now includes the human-intervention step.
- Raw JSON is no longer shown immediately after ingestion; it remains in Integration Hub / API.
- Synthetic ECG PDF retains patient name, MRN, and DOB on every page for passing cases; a deliberate failed case demonstrates document hold behavior.

## Run locally
```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

## Deploy
Replace `app.py`, `requirements.txt`, and `README.md` in the existing GitHub repository. Streamlit Community Cloud should automatically redeploy the existing app URL from the main branch.

## Demo sequence
1. Patient Data Ingestion — select a patient, compare the previous reading, enter a new reading, and ingest it.
2. Clinical Command Center — show the resulting alert and outreach status.
3. Patient 360 & Trends — show the seven-day trend and event history.
4. Clinician Interventions — document a phone call or secure chat and outcome.
5. Return to Command Center — show that the alert now has a documented intervention.
6. ECG Documents — open/download the synthetic ECG report and show identifiers on every page.
7. Integration Hub / API — show normalized JSON and FHIR-style EHR payload.
8. Mock EHR — show flowsheet values, Media PDFs, and care-team communications.
9. Data Lineage & Audit — trace the event end to end.

> Synthetic data only. Portfolio demonstration only. Not for diagnosis, treatment, or clinical use.
