# RPM Connected Care AI Platform · V3.3

Synthetic healthcare product portfolio demonstrating a connected Remote Patient Monitoring workflow. All patients, credentials, measurements, reports, rules and workflows are synthetic portfolio content.

## V3.3 foundation before Research Analytics

- RPM Fit, Enrollment & Kit Transition workflow for acute-care discharge candidates.
- Human enrollment gate: Fit Score is decision support and never auto-enrolls a patient.
- Care-path-specific kit configuration so ECG and spirometry are included only when appropriate to the selected pathway/order.
- Fulfillment methods: ship to home or provide during acute-care discharge.
- Enrollment, kit-delivery and activation statuses from candidate through active monitoring.
- `Enroll in RPM & add to My Patients` writes the candidate into the shared session patient registry; Patient 360 can then find the patient immediately. Trends begin after the first reading.
- More polished ECG and spirometry PDFs with colored clinical-style curves, identifiers and additional result context.
- Modernized PDF view/download controls and a distinct pulse-oximeter-style SpO2 icon.

## Important safety / product notes

The RPM Fit Score and cut points are illustrative product-design assumptions, not validated clinical criteria. Production use would require clinical governance, validation, equity/bias review, security, identity controls, consent, device workflow validation and organization-approved protocols. ECG classifications are treated as device-reported inputs. Synthetic spirometry reference values are illustrative and do not implement validated reference equations.

## Demo Admin

Username: `Admin`  
Password: `ADMIN`

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```
