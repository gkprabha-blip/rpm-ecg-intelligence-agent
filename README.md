# Connected Care Intelligence Platform — V5.1

## UI/UX redesign
V5.1 applies the Connected Care Intelligence design direction: an enterprise clinical command-center foundation, a seven-stage patient journey (Identify → Enroll → Prepare → Activate → Monitor → Intervene → Learn), and contextual clinical/research intelligence. It preserves the V4.2 unified patient/research architecture and existing workflows while modernizing navigation, hierarchy, dashboard surfaces, role context, cards, and key clinical/research pages.

# RPM Connected Care AI Platform · V5.1

A 100% synthetic Streamlit portfolio prototype demonstrating end-to-end Remote Patient Monitoring (RPM), connected devices, clinical workflows, EHR integration, human-in-the-loop AI prioritization, transition-to-home operations, and longitudinal research analytics.

## V5.1 — Unified Patient / Research Data Architecture

V5.1 aligns the operational and research portions of the prototype around one synthetic enterprise patient ecosystem. The application no longer presents the 240-person research population as a disconnected parallel universe.

The unified model separates **identity** from **lifecycle-specific views**:

- **Enterprise Registry / Mock EHR / MPI:** the broad synthetic patient population, including active, completed, and transition-candidate records.
- **RPM Fit & Transition Queue:** current discharge/transition candidates only.
- **Clinical Command Center:** active RPM monitoring population only; completed/historical records do not clutter today's work queue.
- **Research Analytics:** governed research-eligible longitudinal records using `RSP-####` Research Participant IDs. Operational names/MRNs are suppressed from research views by default.
- **Patient Identity & Duplicate Prevention:** shows the shared enterprise registry, lifecycle state, and research linkage where applicable.

This demonstrates the product principle: **one enterprise patient ecosystem, multiple role- and lifecycle-specific views.** Operational MRN and Research Participant ID are deliberately different identifiers.

## RPM Fit UX improvements

V5.1 improves the transition queue with accessible status styling: RPM FIT uses green, REVIEW / ENABLE uses amber, and NOT CURRENTLY FIT uses neutral slate/gray so it is not confused with a clinical emergency. Text remains present so meaning never depends on color alone.

The `Why Flagged` column is wider/wrapped, and every selected candidate has a visible **Why this patient was flagged** panel with the full rationale, Fit Segment, score, expected discharge, and the factors used in the synthetic screening workflow. Users no longer need to discover a double-click interaction to understand the rationale.

## Architecture & Product Story

The Architecture page now explicitly shows three connected layers:

1. **Operational Patient Layer:** MPI → acute/discharge → RPM Fit → enrollment → kit/fulfillment → activation → monitoring → intervention → EHR.
2. **Longitudinal Data Layer:** enrollment episodes → devices → readings → questionnaires → ECG/spirometry → messages → alerts → interventions → outcomes.
3. **Research Data Layer:** governed research eligibility → de-identification/pseudonymization → Research Participant ID → longitudinal research dataset → cohorts → quality checks → analysis/reports → hypothesis → validation → governed pathway improvement.

Research findings do not automatically change individual treatment. Associations are exploratory unless a study design and validation support causal inference.

## Research Analytics Center

The Research Analytics Center retains the 12 purpose-specific research cohorts introduced in V4.1, including lung transplant home spirometry, COPD monitoring, pulmonary rehabilitation, pneumonitis/recovery, cardiac rhythm/6L ECG, heart failure post-discharge, CAD recovery, hypertension, diabetes/CGM, CKD/AKI transition, and post-surgical recovery.

It includes Research Overview, Cohort Catalog, Cohort Explorer, Spirometry Research, 6L ECG Research, Reports & Exports, Research Question Builder, and a plain-language Research Analytics Guide covering clinical efficiency, patient outcomes, patient safety, data quality, interpretation, and limitations.

## Exports

Research data can be downloaded as CSV or a structured Excel workbook (`.xlsx`) with report summary, participant, longitudinal observation, spirometry, ECG, and intervention/outcome sheets. CSV/XLSX are Google-Sheets-compatible export formats; the prototype does not claim authenticated Google Workspace integration.

## Safety / scope

All people, identifiers, measurements, thresholds, outcomes, credentials, workflows, and research results are synthetic. This portfolio prototype is not a medical device, diagnostic system, validated clinical score, or treatment recommendation engine. ECG classifications are device-reported inputs. Spirometry reference fields are illustrative. Human clinicians remain the final decision-makers.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```


## V5.1 UI/UX correction pass
- Fixes clipped global product header by reserving safe top spacing and reducing oversized brand typography.
- Rebuilds sidebar alignment and typography; navigation displays clean labels without implementation numbering.
- Adds lifecycle context to relevant pages so Identify, Enroll, Prepare, Activate, Monitor, Intervene and Learn are attached to the work being performed rather than appearing only on two pages.
- RPM Fit & Transition explicitly highlights Identify → Enroll → Prepare → Activate.
- Adds a clearer demo-password visibility header and a subtle visibility control.
- Preserves V4.2 unified patient/research architecture and V5.0 workflows.

## V6.2 — Connected Care Intelligence Platform UX redesign
V6.2 rebuilds the application shell around the approved hybrid UX direction: enterprise clinical command center + contextual patient journey + focused intelligence. It preserves the V4.2/V5.1 unified synthetic patient/research architecture while introducing a compact navy navigation rail, global search surface, stage-aware page headers, denser enterprise workspace layout, command-center workspace tabs, refined cards/tables, and clearer role context. Lifecycle labels are shown where the work occurs (Identify, Enroll, Prepare, Activate, Monitor, Intervene, Learn) rather than repeating the entire journey ribbon on every page.


## V6.2 UX refinement
- Larger, left-aligned page and section headings.
- Wider, more readable navigation with larger section labels and menu typography.
- RPM Fit queue redesigned as candidate cards with the complete Why Flagged rationale visible without double-clicking.
- Stronger visual hierarchy while preserving the V4.2 unified data architecture and V6 workflow shell.


## V6.2 UX architecture
V6.2 replaces the always-expanded sidebar with task-first workspaces. Only the selected workspace reveals its pages, reducing navigation overload while preserving role-based access. It also increases sidebar, page-title, section-heading, tab, and explanatory-text hierarchy and keeps RPM Fit rationales visible in full candidate cards. The information architecture follows established enterprise shell and side-navigation principles: shallow hierarchy, clear current location, task-oriented grouping, progressive disclosure, and accessible text states in addition to color.
