# RPM Connected Care AI Platform · V4.0

A 100% synthetic Streamlit portfolio demonstrating end-to-end Remote Patient Monitoring product design: discharge/RPM Fit screening, human-reviewed enrollment, care-path-specific kit fulfillment and activation, longitudinal monitoring, ECG/spirometry documents, clinical workflows, EHR integration, auditability, and a new Research Analytics Center.

## V4.0 — Research Analytics Center
- **Research Analytics Overview** — cohort and observation volume, spirometry sessions, 6L ECG recordings, flagged observations and population distribution.
- **Cohort Explorer** — filter synthetic/de-identified participants by care path, cohort and trajectory. Operational MRNs are hidden from research views by default.
- **Spirometry Research** — longitudinal FEV1, FVC, FEV1/FVC, PEF, personal-baseline change, technical quality, SpO2, symptoms, alerts, interventions and outcomes.
- **6L ECG Research** — device-reported classification burden, HR, symptoms, alerts, interventions and outcomes. The prototype does not interpret ECG waveforms.
- **Reports & Exports** — report catalog covering lung-function trajectory, spirometry quality/adherence, ECG event burden, symptom/device relationships, alert-to-intervention, care-path comparisons, missingness/data quality, clinical efficiency, patient safety and patient outcomes.
- **Research Question Builder** — define an exploratory population, measure and outcome/context.
- **Research Analytics Guide** — plain-language explanations for researchers, clinicians, physicians, operations and non-research users, including clinical-efficiency, patient-outcome and patient-safety measurement frameworks.
- **Exports** — CSV and multi-sheet Excel workbooks; both can be imported into Google Sheets. Direct Google Sheets write-back is intentionally not simulated without OAuth/API integration.

## Synthetic research dataset
V4.0 generates a deterministic synthetic cohort of 240 research participants with thousands of longitudinal observations across pulmonary and cardiac RPM pathways. It intentionally includes stable, improving, declining and intermittent trajectories; missing observations; spirometry quality variation; device-reported ECG categories; symptoms; alerts; human interventions; and synthetic outcomes.

## Research guardrails
This is a portfolio demonstration, not clinical evidence, a medical device, or a diagnostic/treatment system. All participants, measurements, thresholds, associations and outcomes are synthetic. Research views use Research Participant IDs rather than operational MRNs by default. Automatically generated summaries are descriptive/exploratory and must not be interpreted as causal effects. Production research would require protocol/governance review, validated endpoints, appropriate statistical methods, privacy controls, bias/equity assessment and prospective validation as applicable.

## Demo authentication
The app starts signed in as **Admin** for portfolio review. Demo accounts include Patient, Clinician, Provider, RPM Admin, Integrations, Researcher and Admin. Credentials are visible to Admin under **Logins & Roles**. These simple credentials are portfolio-only; production healthcare systems should use enterprise identity/SSO, MFA, server-side authorization and auditable least-privilege controls.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deployment
Replace `app.py`, `README.md`, and `requirements.txt` in the GitHub repository. Keep `.streamlit/config.toml` unless intentionally changing the theme. Streamlit Community Cloud will redeploy from the repository.
