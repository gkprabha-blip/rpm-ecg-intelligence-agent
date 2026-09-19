import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title='RPM ECG Intelligence Agent', page_icon='❤️', layout='wide')

PATIENTS = [
    {'id':'SYN-1001','name':'Maya Patel','program':'Cardiology RPM','ecg':'Normal Sinus Rhythm','hr':72,'spo2':97,'weight':154.2,'baseline_weight':154.0,'symptom':'None','pdf':'Validated','epic':'Mapped','device':'Connected'},
    {'id':'SYN-1002','name':'Daniel Brooks','program':'Cardiology RPM','ecg':'Atrial Fibrillation','hr':118,'spo2':92,'weight':188.6,'baseline_weight':184.8,'symptom':'Shortness of breath','pdf':'Validated','epic':'Mapped','device':'Connected'},
    {'id':'SYN-1003','name':'Priya Raman','program':'Cirrhosis RPM','ecg':'Bradycardia','hr':46,'spo2':95,'weight':132.1,'baseline_weight':132.4,'symptom':'Dizziness','pdf':'Validated','epic':'Mapped','device':'Connected'},
    {'id':'SYN-1004','name':'James Wilson','program':'Cardiology RPM','ecg':'Tachycardia','hr':112,'spo2':96,'weight':201.0,'baseline_weight':200.5,'symptom':'Palpitations','pdf':'Validated','epic':'Mapped','device':'Connected'},
    {'id':'SYN-1005','name':'Elena Garcia','program':'Cirrhosis RPM','ecg':'Unclassified','hr':83,'spo2':97,'weight':146.0,'baseline_weight':145.7,'symptom':'None','pdf':'Validated','epic':'Mapped','device':'Connected'},
    {'id':'SYN-1006','name':'Noah Thompson','program':'Cardiology RPM','ecg':'Sinus Rhythm with PVCs','hr':78,'spo2':96,'weight':173.0,'baseline_weight':172.7,'symptom':'None','pdf':'Validated','epic':'Mapped','device':'Connected'},
    {'id':'SYN-1007','name':'Aisha Khan','program':'Cardiology RPM','ecg':'Normal Sinus Rhythm','hr':70,'spo2':98,'weight':161.3,'baseline_weight':161.0,'symptom':'None','pdf':'Identifier Missing - Page 2','epic':'Held','device':'Connected'},
    {'id':'SYN-1008','name':'Robert Chen','program':'Cirrhosis RPM','ecg':'No reading received','hr':74,'spo2':96,'weight':169.1,'baseline_weight':169.0,'symptom':'None','pdf':'Not received','epic':'No ECG result','device':'ECG disconnected'},
]

def assess(p):
    reasons=[]; priority='LOW'; route='Continue monitoring'
    if p['ecg'] in ['Atrial Fibrillation','Bradycardia','Tachycardia']:
        priority='HIGH'; reasons.append(f"Device-reported ECG classification: {p['ecg']}"); route='Clinician review queue'
    elif p['ecg'] in ['Unclassified','Sinus Rhythm with PVCs','Sinus Rhythm with SVE','Sinus Rhythm with Wide QRS']:
        priority='MEDIUM'; reasons.append(f"ECG result requires review: {p['ecg']}"); route='Clinician review / repeat reading per protocol'
    if p['spo2'] < 94:
        priority='HIGH'; reasons.append(f"SpO₂ {p['spo2']}% is below configured demo threshold")
    if p['weight'] - p['baseline_weight'] >= 3:
        priority='HIGH'; reasons.append(f"Weight increased {p['weight']-p['baseline_weight']:.1f} lb from synthetic baseline")
    if p['symptom'] != 'None':
        reasons.append(f"Questionnaire symptom: {p['symptom']}")
        if priority=='LOW': priority='MEDIUM'; route='Clinician review queue'
    if p['device'] != 'Connected':
        priority='WORKFLOW'; reasons.append('Expected ECG reading not received while other RPM data are available'); route='Device support / patient outreach'
    if p['pdf'] not in ['Validated','Not received']:
        priority='DATA INTEGRITY'; reasons.append(p['pdf']); route='Hold document; compliance/integration review'
    if not reasons: reasons=['No configured exception detected in current synthetic readings']
    return priority, reasons, route

for p in PATIENTS:
    p['priority'], p['reasons'], p['route'] = assess(p)

st.title('❤️ RPM ECG Intelligence Agent')
st.caption('AI Product Owner Portfolio Prototype • Synthetic data only • Not for diagnosis or clinical use')

with st.sidebar:
    st.header('Portfolio Demo')
    page=st.radio('Navigate', ['Command Center','Patient Review','Integration & Compliance','Architecture','Product Owner View'])
    st.divider()
    st.info('This prototype consumes device-reported ECG classifications. It does not interpret ECG waveforms or make diagnoses.')

if page=='Command Center':
    st.subheader('RPM Command Center')
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Synthetic patients',len(PATIENTS))
    c2.metric('High-priority review',sum(p['priority']=='HIGH' for p in PATIENTS))
    c3.metric('Workflow exceptions',sum(p['priority']=='WORKFLOW' for p in PATIENTS))
    c4.metric('Data-integrity holds',sum(p['priority']=='DATA INTEGRITY' for p in PATIENTS))
    df=pd.DataFrame([{k:p[k] for k in ['id','name','program','ecg','hr','spo2','weight','symptom','priority','route']} for p in PATIENTS])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.subheader('What the agent does')
    st.write('Correlates device-reported ECG classification, vitals, weight, questionnaire responses, device connectivity, document validation and simulated EHR integration status; then routes exceptions to the appropriate human workflow.')

elif page=='Patient Review':
    label=st.selectbox('Select synthetic patient',[f"{p['id']} — {p['name']}" for p in PATIENTS])
    p=PATIENTS[[f"{x['id']} — {x['name']}" for x in PATIENTS].index(label)]
    st.subheader(f"{p['name']} • {p['id']}")
    a,b,c,d=st.columns(4); a.metric('Heart rate',f"{p['hr']} bpm"); b.metric('SpO₂',f"{p['spo2']}%"); c.metric('Weight',f"{p['weight']} lb"); d.metric('Priority',p['priority'])
    st.markdown('#### Device-reported ECG classification')
    st.write(p['ecg'])
    st.markdown('#### Agent review')
    for r in p['reasons']: st.write('• '+r)
    st.success('Recommended workflow: '+p['route'])
    st.markdown('#### AI-style clinician summary')
    summary=f"Synthetic RPM review for {p['name']}: ECG workflow reports {p['ecg']}. Current HR is {p['hr']} bpm, SpO₂ {p['spo2']}%, and weight {p['weight']} lb versus synthetic baseline {p['baseline_weight']} lb. Questionnaire response: {p['symptom']}. Priority: {p['priority']}. Route to {p['route'].lower()}. Final interpretation and action remain with the clinician."
    st.text_area('Generated summary',summary,height=150)
    st.markdown('#### Human-in-the-loop decision')
    st.radio('Reviewer action',['Acknowledge','Escalate per protocol','Request repeat ECG','Device support','Dismiss / false positive'],horizontal=True)
    st.text_input('Reviewer note (demo)')
    st.button('Record synthetic review')

elif page=='Integration & Compliance':
    st.subheader('Simulated End-to-End Data Flow')
    st.code('KardiaMobile 6L / Wearables / Scale\n        ↓ Bluetooth\nPatient Tablet + Daily Questionnaire\n        ↓ Vendor Cloud\nClinical Dashboard\n        ├─ structured vitals → LOINC mapping → Interface → Epic Flowsheet\n        └─ ECG PDF → Cloverleaf → OnBase → Epic Media')
    st.markdown('#### Document & integration exceptions')
    df=pd.DataFrame([{'Patient':p['id'],'ECG PDF':p['pdf'],'Epic status':p['epic'],'Device':p['device'],'Agent route':p['route']} for p in PATIENTS])
    st.dataframe(df,use_container_width=True,hide_index=True)
    st.warning('Prototype rule: an ECG document with a required synthetic patient identifier missing is held before simulated EHR ingestion.')
    st.markdown('#### Example interoperability controls')
    st.write('• Validate required identifiers and encounter metadata\n• Validate expected LOINC-to-flowsheet mapping configuration\n• Reconcile vendor observations against simulated EHR receipt\n• Preserve an audit trail for exceptions and reviewer actions')

elif page=='Architecture':
    st.subheader('Agentic Architecture')
    st.code('RPM DATA SOURCES\n   ↓\nORCHESTRATOR AGENT\n   ├── Monitoring Agent — correlates ECG + vitals + questionnaire\n   ├── Adherence Agent — detects missing readings / connectivity issues\n   ├── Integration Agent — checks source-to-EHR delivery\n   └── Document Agent — validates ECG PDF metadata\n              ↓\n      EXPLAINABLE WORK QUEUE\n              ↓\n       HUMAN CLINICIAN / SUPPORT\n              ↓\n        AUDIT + FEEDBACK LOOP')
    st.markdown('#### Guardrails')
    st.write('1. Synthetic data only. 2. No ECG waveform diagnosis. 3. Device classification is treated as source data. 4. Configurable demo thresholds are not medical advice. 5. Human review remains authoritative. 6. All agent actions should be auditable.')

else:
    st.subheader('AI Product Owner View')
    st.markdown('#### Problem statement')
    st.write('RPM teams receive multiple asynchronous signals across devices, questionnaires, documents and EHR interfaces. The prototype demonstrates how an agent can consolidate those signals into explainable, role-appropriate work queues.')
    st.markdown('#### MVP epics')
    st.write('• Multi-device RPM ingestion\n• ECG exception prioritization\n• Questionnaire + vital correlation\n• Missing-data/adherence workflow\n• EHR integration reconciliation\n• ECG PDF compliance validation\n• Human-in-the-loop feedback and audit')
    st.markdown('#### Product KPIs')
    st.write('• Exception precision / false-positive rate\n• Missing-data detection rate\n• Source-to-EHR reconciliation accuracy\n• Unsupported-summary claim rate\n• Human override rate\n• Time from exception to reviewer acknowledgment')
    st.markdown('#### Example user story')
    st.write('As an RPM clinician, I want a prioritized, explainable view of patients whose device-reported ECG result or correlated RPM signals require review so that I can focus attention efficiently while retaining final clinical judgment.')
