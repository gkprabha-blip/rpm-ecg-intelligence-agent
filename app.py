import io, json, random, math
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

st.set_page_config(page_title='RPM Connected Care AI Platform', page_icon='🫀', layout='wide')

# ---------- Demo data/state ----------
PATIENTS = {
    'SYN-1001': {'name':'Maya Patel','mrn':'SYN-MRN-1001','dob':'1964-05-14','care_plan':'Cardiology','baseline_spo2':97,'baseline_weight':164.2},
    'SYN-1002': {'name':'Daniel Brooks','mrn':'SYN-MRN-1002','dob':'1958-11-02','care_plan':'Cirrhosis','baseline_spo2':96,'baseline_weight':182.0},
    'SYN-1003': {'name':'Elena Garcia','mrn':'SYN-MRN-1003','dob':'1971-03-28','care_plan':'Cardiology','baseline_spo2':98,'baseline_weight':151.4},
    'SYN-1004': {'name':'Robert Chen','mrn':'SYN-MRN-1004','dob':'1967-08-09','care_plan':'Cardiology','baseline_spo2':97,'baseline_weight':176.8},
}

LOINC = {'SpO2':'59408-5','Heart Rate':'8867-4','Body Weight':'29463-7','Systolic BP':'8480-6','Diastolic BP':'8462-4'}

if 'events' not in st.session_state:
    now = datetime.now().replace(second=0, microsecond=0)
    st.session_state.events = [
        {'event_id':'EVT-001','patient_id':'SYN-1001','timestamp':(now-timedelta(hours=2)).isoformat(),'ecg':'Normal Sinus Rhythm','ecg_hr':74,'spo2':97,'weight':164.4,'sys':124,'dia':78,'sob':False,'chest':False,'dizzy':False,'meds':True,'pdf_ok':True,'source':'Seed'},
        {'event_id':'EVT-002','patient_id':'SYN-1002','timestamp':(now-timedelta(hours=1)).isoformat(),'ecg':'Atrial Fibrillation','ecg_hr':118,'spo2':92,'weight':185.8,'sys':146,'dia':92,'sob':True,'chest':True,'dizzy':False,'meds':True,'pdf_ok':True,'source':'Seed'},
        {'event_id':'EVT-003','patient_id':'SYN-1003','timestamp':(now-timedelta(minutes=35)).isoformat(),'ecg':'Unclassified','ecg_hr':89,'spo2':96,'weight':151.6,'sys':128,'dia':80,'sob':False,'chest':False,'dizzy':True,'meds':True,'pdf_ok':False,'source':'Seed'},
    ]
if 'audit' not in st.session_state:
    st.session_state.audit = []

def assess(e):
    p = PATIENTS[e['patient_id']]
    reasons=[]; score=0
    if e['ecg'] not in ['Normal Sinus Rhythm']:
        reasons.append(f"Device-reported ECG classification: {e['ecg']}"); score += 3 if e['ecg']=='Atrial Fibrillation' else 2
    if e['spo2'] <= 92: reasons.append(f"SpO₂ {e['spo2']}% is below configured demo threshold"); score += 2
    elif e['spo2'] <= 94: reasons.append(f"SpO₂ {e['spo2']}% differs from baseline"); score += 1
    if e['ecg_hr'] >= 100 or e['ecg_hr'] < 50: reasons.append(f"ECG heart rate {e['ecg_hr']} bpm outside configured demo range"); score += 2
    if e['weight'] - p['baseline_weight'] >= 3: reasons.append(f"Weight +{e['weight']-p['baseline_weight']:.1f} lb from synthetic baseline"); score += 1
    if e['sob']: reasons.append('Daily questionnaire: shortness of breath = Yes'); score += 2
    if e['chest']: reasons.append('Daily questionnaire: chest discomfort = Yes'); score += 2
    if e['dizzy']: reasons.append('Daily questionnaire: dizziness = Yes'); score += 1
    if not e['pdf_ok']: reasons.append('ECG document failed identifier validation'); score += 1
    priority = 'HIGH' if score >= 5 else 'MEDIUM' if score >= 2 else 'LOW'
    return priority, reasons, score

def ecg_pdf_bytes(e, valid=True):
    p = PATIENTS[e['patient_id']]
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=letter); W,H=letter
    for page in range(1,3):
        # identifiers on every page if valid; intentionally omit MRN on page 2 for failed demo
        c.setFont('Helvetica-Bold', 10)
        ident = f"Patient: {p['name']}   |   MRN: {p['mrn']}   |   DOB: {p['dob']}"
        if not valid and page == 2:
            ident = f"Patient: {p['name']}   |   MRN: [MISSING]   |   DOB: {p['dob']}"
        c.drawString(0.55*inch, H-0.45*inch, ident)
        c.setFont('Helvetica-Bold',16); c.drawString(0.55*inch,H-0.85*inch,'Synthetic 6-Lead ECG Demonstration Report')
        c.setFont('Helvetica',9); c.drawString(0.55*inch,H-1.08*inch,'Portfolio prototype — simulated waveform; not a diagnostic ECG report.')
        c.setFont('Helvetica',10)
        c.drawString(0.55*inch,H-1.4*inch,f"Recording ID: {e['event_id']}   Recorded: {e['timestamp'][:16].replace('T',' ')}")
        c.drawString(0.55*inch,H-1.62*inch,f"Device-reported classification: {e['ecg']}   Heart rate: {e['ecg_hr']} bpm")
        leads=['I','II','III','aVR','aVL','aVF']
        y0=H-2.05*inch
        for i,lead in enumerate(leads):
            y=y0-i*0.72*inch
            c.setFont('Helvetica-Bold',9); c.drawString(0.55*inch,y+0.15*inch,lead)
            # grid-ish baseline and synthetic waveform
            c.setLineWidth(0.3); c.line(0.9*inch,y,7.8*inch,y)
            pts=[]
            for x in range(0,620):
                xx=0.9*inch+x*0.011*inch
                phase=(x%70)/70
                val=2.5*math.sin(x/8)
                if 0.43<phase<0.47: val += 18*(1-abs(phase-0.45)/0.02)
                if 0.47<=phase<0.50: val -= 9*(1-abs(phase-0.485)/0.015)
                yy=y+val*(1 if lead not in ['aVR'] else -1)
                pts.append((xx,yy))
            c.setLineWidth(0.7)
            for a,b in zip(pts[:-1],pts[1:]): c.line(a[0],a[1],b[0],b[1])
        c.setFont('Helvetica-Oblique',8); c.drawString(0.55*inch,0.45*inch,f"Page {page} of 2 | SYNTHETIC DATA ONLY | Human review required")
        c.showPage()
    c.save(); return buf.getvalue()

def fhir_bundle(e):
    p=PATIENTS[e['patient_id']]
    obs=[]
    vals=[('SpO2',e['spo2'],'%'),('Heart Rate',e['ecg_hr'],'/min'),('Body Weight',e['weight'],'lb'),('Systolic BP',e['sys'],'mmHg'),('Diastolic BP',e['dia'],'mmHg')]
    for label,val,unit in vals:
        obs.append({'resourceType':'Observation','status':'final','code':{'coding':[{'system':'http://loinc.org','code':LOINC[label],'display':label}]},'subject':{'reference':f"Patient/{e['patient_id']}"},'effectiveDateTime':e['timestamp'],'valueQuantity':{'value':val,'unit':unit}})
    return {'resourceType':'Bundle','type':'transaction','patient':{'id':e['patient_id'],'mrn':p['mrn'],'name':p['name']},'entry':obs,'ecg':{'classification':e['ecg'],'reportId':e['event_id']},'questionnaire':{'shortnessOfBreath':e['sob'],'chestDiscomfort':e['chest'],'dizziness':e['dizzy'],'medicationTaken':e['meds']}}

def log(event_id, step, status='SUCCESS'):
    st.session_state.audit.append({'time':datetime.now().strftime('%H:%M:%S'),'event_id':event_id,'step':step,'status':status})

# ---------- UI ----------
st.title('🫀 RPM Connected Care AI Platform')
st.caption('Agentic AI • Connected Devices • ECG • API/FHIR • EHR Interoperability • 100% synthetic data')
st.info('Portfolio prototype only. It does not diagnose, treat, or provide medical advice. ECG classifications are treated as device-reported inputs; clinical decisions remain human-in-the-loop.')

menu = st.sidebar.radio('Navigate', ['1 · Patient Data Ingestion','2 · Clinical Command Center','3 · Patient 360','4 · ECG Documents','5 · AI Agent','6 · Integration Hub / API','7 · Mock EHR','8 · Data Lineage & Audit','9 · Architecture & Product'])

events = st.session_state.events

def latest_for(pid):
    es=[e for e in events if e['patient_id']==pid]
    return sorted(es,key=lambda x:x['timestamp'])[-1] if es else None

if menu.startswith('1'):
    st.header('Patient Data Ingestion')
    st.write('Simulate the patient-home workflow: questionnaire + connected-device readings + device-reported ECG result. Click **Ingest** and the same event becomes visible across the dashboard, patient record, API, PDF workflow, and mock EHR.')
    pid=st.selectbox('Synthetic patient', list(PATIENTS), format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']} · {PATIENTS[x]['care_plan']}")
    c1,c2,c3=st.columns(3)
    with c1:
        ecg=st.selectbox('KardiaMobile 6L — device-reported classification',['Normal Sinus Rhythm','Atrial Fibrillation','Bradycardia','Tachycardia','Unclassified','Sinus Rhythm with PVCs','Sinus Rhythm with SVE','Sinus Rhythm with Wide QRS'])
        hr=st.number_input('ECG heart rate (bpm)',35,180,74)
    with c2:
        spo2=st.number_input('SpO₂ (%)',70,100,97)
        wt=st.number_input('Weight (lb)',80.0,350.0,float(PATIENTS[pid]['baseline_weight']),0.1)
    with c3:
        sys=st.number_input('Systolic BP',70,220,124); dia=st.number_input('Diastolic BP',40,140,78)
        pdf_ok=st.checkbox('ECG PDF has required patient identifiers on every page',True)
    st.subheader('Daily questionnaire')
    q1,q2,q3,q4=st.columns(4)
    sob=q1.checkbox('Shortness of breath'); chest=q2.checkbox('Chest discomfort'); dizzy=q3.checkbox('Dizziness'); meds=q4.checkbox('Medication taken',True)
    if st.button('▶ Ingest Patient Data', type='primary'):
        eid=f"EVT-{len(events)+1:03d}"
        e={'event_id':eid,'patient_id':pid,'timestamp':datetime.now().replace(microsecond=0).isoformat(),'ecg':ecg,'ecg_hr':int(hr),'spo2':int(spo2),'weight':float(wt),'sys':int(sys),'dia':int(dia),'sob':sob,'chest':chest,'dizzy':dizzy,'meds':meds,'pdf_ok':pdf_ok,'source':'Manual demo ingestion'}
        events.append(e)
        for step in ['Patient tablet received Bluetooth/device data','Vendor cloud ingestion API accepted payload','Clinical dashboard patient record updated','AI orchestrator evaluated event','FHIR/EHR-ready payload generated','ECG PDF generated and validated']:
            log(eid,step,'SUCCESS' if (pdf_ok or 'PDF' not in step) else 'HELD')
        st.success(f'{eid} ingested. Open Clinical Command Center, Patient 360, Integration Hub, ECG Documents, or Mock EHR to follow the same event.')
        st.json(fhir_bundle(e))

elif menu.startswith('2'):
    st.header('Clinical Command Center')
    rows=[]
    for pid,p in PATIENTS.items():
        e=latest_for(pid)
        if e:
            pri,reasons,score=assess(e)
            rows.append({'Patient':p['name'],'MRN':p['mrn'],'Care Plan':p['care_plan'],'ECG':e['ecg'],'HR':e['ecg_hr'],'SpO₂':e['spo2'],'Weight':e['weight'],'Priority':pri,'Event':e['event_id']})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.subheader('Active workflow alerts')
    for pid in PATIENTS:
        e=latest_for(pid)
        if not e: continue
        pri,reasons,_=assess(e)
        if pri!='LOW':
            with st.expander(f"{pri} · {PATIENTS[pid]['name']} · {e['event_id']} · {e['ecg']}"):
                for r in reasons: st.write('• '+r)
                st.write('**Recommended workflow:** Route for clinician review according to configured RPM protocol.' if pri=='HIGH' else '**Recommended workflow:** Review trend / repeat measurement / assess device or patient workflow as appropriate.')

elif menu.startswith('3'):
    st.header('Patient 360')
    pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']}")
    p=PATIENTS[pid]; e=latest_for(pid)
    st.subheader(f"{p['name']} · {p['mrn']}")
    a,b,c,d=st.columns(4); a.metric('Care plan',p['care_plan']); b.metric('DOB',p['dob']); c.metric('Baseline SpO₂',f"{p['baseline_spo2']}%"); d.metric('Baseline weight',f"{p['baseline_weight']} lb")
    if e:
        pri,reasons,_=assess(e)
        st.markdown(f"### Latest event: {e['event_id']} — **{pri} priority**")
        m1,m2,m3,m4,m5=st.columns(5); m1.metric('ECG',e['ecg']); m2.metric('ECG HR',f"{e['ecg_hr']} bpm"); m3.metric('SpO₂',f"{e['spo2']}%"); m4.metric('Weight',f"{e['weight']} lb"); m5.metric('BP',f"{e['sys']}/{e['dia']}")
        st.write('**Questionnaire:**', {'Shortness of breath':e['sob'],'Chest discomfort':e['chest'],'Dizziness':e['dizzy'],'Medication taken':e['meds']})
        st.write('**Why the agent prioritized this event:**'); [st.write('• '+r) for r in reasons] if reasons else st.write('No configured exception detected.')
        st.write('**Devices:** KardiaMobile 6L · Pulse oximeter · Weight scale · wearable vitals · patient tablet (simulated connected state)')
        hist=pd.DataFrame([x for x in events if x['patient_id']==pid])
        if len(hist): st.dataframe(hist[['timestamp','event_id','ecg','ecg_hr','spo2','weight','sys','dia']],use_container_width=True,hide_index=True)

elif menu.startswith('4'):
    st.header('ECG Documents')
    pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']}")
    es=[e for e in events if e['patient_id']==pid]
    if not es: st.warning('No ECG events yet. Ingest one first.')
    for e in reversed(es):
        with st.expander(f"{e['event_id']} · {e['timestamp'][:16].replace('T',' ')} · {e['ecg']}", expanded=(e==es[-1])):
            st.write('**Document validation**')
            p=PATIENTS[pid]
            checks={'Patient name on every page':True,'MRN on every page':e['pdf_ok'],'DOB on every page':True,'ECG timestamp':True,'Patient association':True}
            st.dataframe(pd.DataFrame([{'Check':k,'Result':'PASS' if v else 'FAIL'} for k,v in checks.items()]),hide_index=True,use_container_width=True)
            if e['pdf_ok']: st.success('DOCUMENT VALIDATION PASSED — eligible for downstream document transmission.')
            else: st.error('DOCUMENT VALIDATION FAILED — held; simulated EHR Media filing blocked.')
            pdf=ecg_pdf_bytes(e,e['pdf_ok'])
            st.download_button('Download / View synthetic ECG PDF',pdf,file_name=f"{e['event_id']}_{p['mrn']}.pdf",mime='application/pdf',key='pdf'+e['event_id'])
            st.caption('The generated report prints synthetic patient identifiers in the header of each page. Failed demo cases intentionally show a missing MRN on page 2.')

elif menu.startswith('5'):
    st.header('AI Agent')
    st.write('The orchestrator routes each RPM event through monitoring, adherence, integration, and document-integrity checks. The prototype uses deterministic guardrails so the demo is reproducible and does not require an external AI API.')
    pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:PATIENTS[x]['name']); e=latest_for(pid)
    if e:
        pri,reasons,score=assess(e)
        st.metric('Workflow priority',pri); st.progress(min(score/10,1.0))
        st.subheader('Agent-generated clinician review summary')
        if reasons:
            st.write(f"Latest RPM event {e['event_id']} was prioritized as {pri}. " + ' '.join(reasons) + ' Clinical interpretation and action remain with the clinician.')
        else: st.write('No configured workflow exception detected in the latest synthetic event. Continue monitoring according to the care plan.')
        st.subheader('Agent routing')
        route=[('Monitoring Agent','Evaluated ECG classification, vitals, trends and questionnaire','COMPLETE'),('Adherence Agent','Checked expected measurement availability','COMPLETE'),('Integration Agent','Prepared structured EHR-ready payload','COMPLETE'),('Document Agent','Validated patient identifiers on ECG PDF','COMPLETE' if e['pdf_ok'] else 'HELD')]
        st.dataframe(pd.DataFrame(route,columns=['Agent','Action','Status']),hide_index=True,use_container_width=True)

elif menu.startswith('6'):
    st.header('Integration Hub / API')
    st.write('This screen exposes the normalized RPM event and an EHR-ready FHIR-style transformation. It is a **simulation of an integration API**, not a live Epic endpoint.')
    pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']}"); e=latest_for(pid)
    if e:
        tab1,tab2,tab3=st.tabs(['Normalized RPM JSON','FHIR-style Bundle','Mapping Table'])
        with tab1:
            normalized={'eventId':e['event_id'],'patient':PATIENTS[pid],'carePlan':PATIENTS[pid]['care_plan'],'deviceData':{'ecgClassification':e['ecg'],'ecgHeartRate':e['ecg_hr'],'spo2':e['spo2'],'weight':e['weight'],'bloodPressure':{'systolic':e['sys'],'diastolic':e['dia']}},'questionnaire':{'shortnessOfBreath':e['sob'],'chestDiscomfort':e['chest'],'dizziness':e['dizzy'],'medicationTaken':e['meds']},'ecgDocument':{'reportId':e['event_id'],'identifierValidation':'PASS' if e['pdf_ok'] else 'FAIL'}}
            st.code(json.dumps(normalized,indent=2),language='json')
            st.download_button('Download normalized JSON',json.dumps(normalized,indent=2),file_name=f"{e['event_id']}_rpm.json",mime='application/json')
        with tab2:
            fb=fhir_bundle(e); st.code(json.dumps(fb,indent=2),language='json'); st.download_button('Download EHR-ready FHIR-style JSON',json.dumps(fb,indent=2),file_name=f"{e['event_id']}_fhir.json",mime='application/json')
        with tab3:
            st.dataframe(pd.DataFrame([{'Source':'Pulse oximeter','Field':'SpO₂','LOINC':LOINC['SpO2'],'Destination':'EHR flowsheet / Observation'}, {'Source':'ECG device','Field':'Heart rate','LOINC':LOINC['Heart Rate'],'Destination':'EHR flowsheet / Observation'}, {'Source':'Scale','Field':'Weight','LOINC':LOINC['Body Weight'],'Destination':'EHR flowsheet / Observation'}, {'Source':'BP wearable','Field':'Systolic BP','LOINC':LOINC['Systolic BP'],'Destination':'EHR flowsheet / Observation'}, {'Source':'ECG report','Field':'PDF','LOINC':'N/A','Destination':'Cloverleaf → OnBase → EHR Media (simulated)'}]),hide_index=True,use_container_width=True)

elif menu.startswith('7'):
    st.header('Mock EHR')
    pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']}"); es=[e for e in events if e['patient_id']==pid]
    t1,t2=st.tabs(['Flowsheets','Media'])
    with t1:
        if es:
            st.dataframe(pd.DataFrame([{'Date/Time':e['timestamp'][:16].replace('T',' '),'SpO₂':e['spo2'],'Heart Rate':e['ecg_hr'],'Weight':e['weight'],'BP':f"{e['sys']}/{e['dia']}",'ECG device result':e['ecg']} for e in es]),hide_index=True,use_container_width=True)
        else: st.info('No flowsheet data.')
    with t2:
        filed=[e for e in es if e['pdf_ok']]
        held=[e for e in es if not e['pdf_ok']]
        st.subheader('Filed to Media (simulated)')
        for e in filed:
            st.write(f"📄 {e['event_id']}.pdf · Remote ECG · Source: RPM Vendor · Status: FILED")
            st.download_button('View PDF',ecg_pdf_bytes(e,True),file_name=f"{e['event_id']}.pdf",mime='application/pdf',key='ehr'+e['event_id'])
        if held:
            st.subheader('Held before Media')
            for e in held: st.error(f"{e['event_id']} — document identifier validation failed; not filed to mock EHR Media.")

elif menu.startswith('8'):
    st.header('Data Lineage & Audit')
    if events:
        e=st.selectbox('Trace event',events,format_func=lambda x:f"{x['event_id']} · {PATIENTS[x['patient_id']]['name']} · {x['timestamp'][:16].replace('T',' ')}")
        steps=[('1','Patient home',f"ECG={e['ecg']}; SpO₂={e['spo2']}%; weight={e['weight']} lb; questionnaire captured"),('2','Bluetooth / tablet','Connected-device values collected by patient app (simulated)'),('3','Vendor ingestion API','Normalized RPM event accepted'),('4','Clinical dashboard','Patient record updated; workflow priority calculated'),('5','Integration API','LOINC-coded/FHIR-style payload prepared'),('6','Structured EHR path','Vitals and ECG values available in mock flowsheet'),('7','Document path','ECG PDF → Cloverleaf → OnBase → Media simulation' if e['pdf_ok'] else 'ECG PDF HELD because document identifier validation failed')]
        for n,title,desc in steps: st.markdown(f"**{n}. {title}**  \n{desc}")
    st.subheader('Session audit log')
    if st.session_state.audit: st.dataframe(pd.DataFrame(st.session_state.audit),hide_index=True,use_container_width=True)
    else: st.caption('Ingest a new event to populate the live audit log.')

else:
    st.header('Architecture & Product Story')
    st.code('''PATIENT HOME\n  KardiaMobile 6L + SpO2 + Scale + Wearables + Questionnaire\n                    │ Bluetooth\n                    ▼\n              Patient Tablet\n                    │\n                    ▼\n             Vendor RPM Cloud\n          ┌─────────┴─────────┐\n          ▼                   ▼\n Clinical Dashboard        ECG PDF\n          │                   │\n          ▼                   ▼\n RPM Integration API     Cloverleaf\n          │                   │\n          ▼                   ▼\n FHIR/LOINC Mapping         OnBase\n          │                   │\n          ▼                   ▼\n   Mock EHR Flowsheet    Mock EHR Media\n\nAI ORCHESTRATOR: Monitoring + Adherence + Integration + Document Integrity\nHUMAN-IN-THE-LOOP: clinician review remains authoritative''')
    st.subheader('Product Owner framing')
    st.write('**Problem:** RPM programs generate device data, patient-reported information, alerts, and documents across multiple systems. Clinicians need a coherent review workflow and downstream EHR data must be complete, traceable, and safely associated with the correct patient.')
    st.write('**MVP epics:** Connected-device ingestion · Clinical command center · Patient 360 · AI workflow prioritization · ECG document integrity · EHR transformation · Data lineage/audit.')
    st.write('**Guardrails:** synthetic data only; no autonomous diagnosis; device classifications are treated as source inputs; document failures are held; every downstream event is traceable; clinician remains decision-maker.')
    st.write('**KPIs:** data completeness, alert precision, false-positive rate, document validation pass rate, EHR delivery success, time-to-review, clinician override rate, unsupported-claim rate.')
