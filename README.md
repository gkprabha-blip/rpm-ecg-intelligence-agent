# RPM Connected Care AI Platform v3.4

Synthetic healthcare product portfolio demonstrating end-to-end Remote Patient Monitoring workflows. All patients, measurements, credentials, rules, reports, and workflows are synthetic portfolio content.

## v3.4 refinement release
- Removes remaining legacy emoji-style PDF/save actions in the corrected workflows and uses modern Material Symbols actions.
- ECG Trend is now a single rounded clinical card containing trend graph, complete result-history table, historical result selector, inline PDF preview, and PDF download.
- Historical ECG reports can be selected by date/time and downloaded, rather than limiting the Patient 360 experience to the latest result.
- Spirometry Trend uses the same interaction pattern: graph, table, historical selector, preview, and download inside one clinical card.
- Spirometry PDF plotting regions were moved lower and resized to prevent the flow-volume and volume-time curves from colliding with the measurement table and explanatory text.
- Architecture & Product Story now begins with the complete RPM operating workflow: acute-care discharge planning → RPM Fit → human review → consent/care path → kit configuration/fulfillment → receipt/pairing/training → active monitoring → alert/intervention → EHR/audit.
- Research Analytics is intentionally deferred to a later release.

## Safety / portfolio boundary
The app is not a medical device and does not diagnose, prescribe, or autonomously enroll patients. ECG classifications are synthetic device-reported inputs. Spirometry reference fields are illustrative. Human clinical review remains required.
