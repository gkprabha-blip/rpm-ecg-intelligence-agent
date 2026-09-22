# RPM Connected Care AI Platform — V3.0

Synthetic healthcare product-management portfolio prototype built with Streamlit. No real patient data is used.

## V3.0 highlights
- Demo authentication and role-based navigation for Patient, Clinician, Provider, RPM Admin, Integrations, and Portfolio Admin.
- Admin-only **Logins & Roles** page with masked/revealable demo passwords and access descriptions.
- Default portfolio session opens as **Admin**; users can sign out to test other roles.
- PDF previews are rendered as images for Streamlit Cloud/browser reliability, with PDF download fallback.
- ECG and spirometry history tables display newest timestamps first.
- Refined metric/table typography and tighter trend-unit placement.
- Separate patient-sample save action.
- Existing V2.9 population prioritization, search/filtering, education, questionnaires, care pathways, spirometry, ECG, EHR and audit workflows retained.

## Demo credentials
- Admin / ADMIN
- Patient / Patient Password
- Clinician / Clinician Password
- Provider / Provider Password
- RPM Admin / RPM Admin Password
- Integrations / Integrations Password

These credentials intentionally demonstrate portfolio RBAC only. Production healthcare systems should use enterprise identity/SSO, MFA, server-side authorization, secure secret management and auditable least-privilege access.
