# RPM Connected Care AI Platform — v2.3

Synthetic portfolio prototype for demonstrating end-to-end Remote Patient Monitoring product workflows. No real PHI is included and the application is not for clinical use.

## v2.3 highlights
- ECG PDF action moved to the top of each ECG document record.
- Patient-specific alert threshold controls are clearly separated from current readings.
- Trend charts show actual values, timestamps, source/provenance, device name, event ID, and threshold status on hover.
- Red trend points indicate readings outside configured patient thresholds; purple dashed lines represent configured min/max thresholds.
- Added respiratory rate, skin temperature, and continuous glucose monitoring trends.
- Cardiology demo uses Everion as a continuous wearable for HR, SpO2, RR, and skin temperature; Cirrhosis demonstrates more individual-device collection for SpO2, BP/HR, and weight.
- Added Nonin Pulse Oximeter, Welch Allyn BP Device, Welch Allyn Weighing Device, and Dexcom G7 CGM device labels.
- Dexcom G7 is represented as a continuous glucose monitor (CGM); CGM measures interstitial glucose and is not a conventional finger-stick blood glucose meter.
- Device vs clinician-assisted manual provenance remains visible throughout trends and hover details.

## Run
```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

## Safety
All patients, MRNs, readings, questionnaires, alerts, thresholds, ECG waveforms, and EHR workflows are synthetic demonstration data. Thresholds are demo configuration values and are not clinical recommendations. Clinical decisions remain human-in-the-loop.

## v2.4 additions
- Create/Add New Patient from both Clinical Command Center and Mock EHR.
- Shared in-session Master Patient Index (MPI) so both entry points create into one registry.
- Duplicate prevention: exact normalized name + DOB + phone blocks creation; name + DOB triggers possible-duplicate review.
- Auto-generated synthetic MRN after duplicate check passes.
- Demographics, address, phone/email, insurance, next of kin, relationship/contact, RPM care plan and assigned clinician.
- Dedicated Patient Identity & Duplicate Prevention page explaining the matching workflow.
- Trend visualization: manual clinician-assisted readings are purple; out-of-threshold readings are red; configured min/max thresholds are teal dashed lines.

All data and workflows are synthetic portfolio demonstrations and are not clinical recommendations or production patient-matching logic.
