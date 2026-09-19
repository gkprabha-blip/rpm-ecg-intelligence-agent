# RPM ECG Intelligence Agent

Portfolio prototype demonstrating AI Product Owner thinking for Remote Patient Monitoring (RPM), inspired by real-world healthcare product workflows and implemented with **100% synthetic patient data**.

## What it showcases
- KardiaMobile 6L device-reported ECG classifications
- Connected RPM ecosystem: ECG, SpO2, weight, continuous vitals, questionnaires
- Patient tablet / vendor clinical dashboard workflow
- Explainable exception prioritization and human-in-the-loop review
- Missing-reading/device-support routing
- Simulated LOINC-to-EHR flowsheet mapping and reconciliation
- ECG PDF route: vendor → Cloverleaf → OnBase → Epic Media
- Document identifier/compliance validation
- Product epics, user story, guardrails, and AI-product KPIs

## Safety / scope
This is a portfolio demonstration, not a medical device, diagnostic system, or clinical decision support product. All names, IDs, measurements, thresholds, and scenarios are synthetic. The prototype consumes a device-reported ECG classification and does not interpret ECG waveforms. Demo thresholds are illustrative and must not be used for patient care.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

## Recommended public deployment
1. Create a GitHub repository and add `app.py`, `requirements.txt`, and this README.
2. Use Streamlit Community Cloud to deploy the repository's `app.py`.
3. Put the live demo URL and GitHub repository URL on your resume/LinkedIn under **AI Product Portfolio**.
4. During interviews, open the Command Center, select SYN-1002, explain the correlated alert, then show Integration & Compliance and Product Owner View.

## Suggested resume entry
**RPM ECG Intelligence Agent — AI Product Owner Portfolio Project**
Designed and prototyped a multi-agent RPM workflow using synthetic patient data to correlate device-reported ECG classifications, vitals, weight and questionnaires; prioritize review workflows; identify device/data-integrity exceptions; simulate LOINC/EHR integration and ECG document routing; and demonstrate human-in-the-loop AI guardrails and product evaluation metrics.
