# RPM Connected Care AI Platform

A portfolio-ready, synthetic-data prototype inspired by real-world remote patient monitoring product workflows. It demonstrates how connected ECG, vitals, patient questionnaires, clinical dashboards, AI workflow prioritization, integration APIs, LOINC/FHIR-style transformations, ECG PDF document validation, and EHR flowsheet/Media workflows can fit together.

> **Important:** Portfolio demonstration only. All patients and clinical data are synthetic. The application is not a medical device, does not diagnose, and must not be used for clinical care.

## Demo flow
1. Open **Patient Data Ingestion**.
2. Select a synthetic Cardiology or Cirrhosis RPM patient.
3. Enter a device-reported ECG classification, HR, SpO2, weight, BP, and questionnaire answers.
4. Click **Ingest Patient Data**.
5. Open **Clinical Command Center** to see the event and workflow priority.
6. Open **Patient 360** for the individual RPM record.
7. Open **ECG Documents** to generate/download the synthetic two-page ECG PDF. Patient name/MRN/DOB appear on each page in passing cases; failed cases intentionally omit the MRN on page 2.
8. Open **Integration Hub / API** to inspect/download normalized JSON and an EHR-ready FHIR-style JSON payload with LOINC-coded observations.
9. Open **Mock EHR** to see structured values in Flowsheets and validated PDFs in Media.
10. Open **Data Lineage & Audit** to trace the event end-to-end.

## Architecture demonstrated
Patient devices → Bluetooth/tablet → vendor RPM cloud → clinical dashboard → AI orchestrator → integration API → LOINC/FHIR-style mapping → mock EHR flowsheets.

ECG PDF follows a separate simulated document path: vendor → Cloverleaf → OnBase → mock EHR Media.

## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud
If this repository is already connected to Streamlit Community Cloud, replace/update `app.py`, `requirements.txt`, and `README.md` in the same GitHub repository. Streamlit normally redeploys automatically from the `main` branch.

Main file: `app.py`

## Interview positioning
This prototype is designed to showcase AI Product Owner / Technical Product Owner skills: problem framing, workflow design, connected-device ingestion, healthcare interoperability, human-in-the-loop AI, document safety controls, product metrics, and end-to-end data lineage.
