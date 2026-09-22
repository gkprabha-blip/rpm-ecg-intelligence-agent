import io, json, math
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

st.set_page_config(page_title='RPM Connected Care AI Platform v2.4', page_icon='🫀', layout='wide')

PATIENTS = {
    'SYN-1001': {'name':'Maya Patel','clinician':'Dr. John Doe','mrn':'SYN-MRN-1001','dob':'1964-05-14','care_plan':'Cardiology','baseline_spo2':97,'baseline_weight':164.2,'baseline_hr':74},
    'SYN-1002': {'name':'Daniel Brooks','clinician':'Dr. Aisha Morgan','mrn':'SYN-MRN-1002','dob':'1958-11-02','care_plan':'Cirrhosis','baseline_spo2':96,'baseline_weight':182.0,'baseline_hr':76},
    'SYN-1003': {'name':'Elena Garcia','clinician':'Dr. John Doe','mrn':'SYN-MRN-1003','dob':'1971-03-28','care_plan':'Cardiology','baseline_spo2':98,'baseline_weight':151.4,'baseline_hr':70},
    'SYN-1004': {'name':'Robert Chen','clinician':'Dr. Samuel Lee','mrn':'SYN-MRN-1004','dob':'1967-08-09','care_plan':'Cardiology','baseline_spo2':97,'baseline_weight':176.8,'baseline_hr':72},
}

# Persist a shared patient registry so patient creation from either the Clinical Dashboard
# or Mock EHR writes to the same Master Patient Index (MPI) in this demo session.
if 'patients' not in st.session_state:
    for _pid,_p in PATIENTS.items():
        _p.update({'address':'100 Demo Way','city':'Austin','state':'TX','zip':'78701','phone':f'512-555-{1000+int(_pid[-1]):04d}','email':'','insurance':'Demo Health Plan','member_id':f'DEMO-{_pid[-4:]}','next_of_kin':'Synthetic Family Contact','nok_relationship':'Family','nok_phone':'512-555-0199'})
    st.session_state.patients = PATIENTS
PATIENTS = st.session_state.patients

CARE_PLANS=['Cardiology','Cirrhosis / Liver Disease','Hypertension','Diabetes / CGM','Heart Failure','COPD / Pulmonary','Chronic Kidney Disease','Post-Surgical Recovery']
CLINICIANS=['Dr. John Doe','Dr. Aisha Morgan','Dr. Samuel Lee','Dr. Elena Rivera']

def norm_text(v): return ''.join(ch.lower() for ch in str(v).strip() if ch.isalnum())
def next_patient_ids():
    nums=[int(k.split('-')[-1]) for k in PATIENTS if k.startswith('SYN-') and k.split('-')[-1].isdigit()]
    n=max(nums+[1000])+1
    return f'SYN-{n}', f'SYN-MRN-{n}'
def find_duplicate(first,last,dob,phone):
    name=norm_text(first+last); ph=norm_text(phone)
    exact=[]; possible=[]
    for pid,p in PATIENTS.items():
        pname=norm_text(p.get('name','')); pdob=str(p.get('dob','')); pphone=norm_text(p.get('phone',''))
        if pname==name and pdob==str(dob) and ph and pphone==ph: exact.append(pid)
        elif pname==name and pdob==str(dob): possible.append(pid)
    return exact,possible

def setup_new_patient(pid):
    p=PATIENTS[pid]
    st.session_state.thresholds[pid]={'spo2_min':92,'spo2_max':100,'hr_min':50,'hr_max':110,'weight_min':80.0,'weight_max':350.0,'sys_min':90,'sys_max':160,'dia_min':50,'dia_max':100,'rr_min':10,'rr_max':24,'temp_min':34.0,'temp_max':38.0,'glucose_min':70,'glucose_max':180}
    common=[{'device':'KardiaMobile 6L','type':'ECG · individual','connected':True,'battery':100,'wifi':True},{'device':'Dexcom G7 CGM','type':'Glucose · continuous','connected':True,'battery':100,'wifi':True},{'device':'RPM Tablet','type':'Gateway','connected':True,'battery':100,'wifi':True}]
    if p['care_plan']=='Cardiology': care=[{'device':'Everion','type':'Continuous · HR / SpO₂ / RR / skin temperature','connected':True,'battery':100,'wifi':True},{'device':'Welch Allyn BP Device','type':'Individual · BP','connected':True,'battery':100,'wifi':True},{'device':'Welch Allyn Weighing Device','type':'Individual · weight','connected':True,'battery':100,'wifi':True}]
    else: care=[{'device':'Nonin Pulse Oximeter','type':'Individual · SpO₂','connected':True,'battery':100,'wifi':True},{'device':'Welch Allyn BP Device','type':'Individual · BP / HR','connected':True,'battery':100,'wifi':True},{'device':'Welch Allyn Weighing Device','type':'Individual · weight','connected':True,'battery':100,'wifi':True},{'device':'Everion','type':'Wearable · RR / skin temperature','connected':True,'battery':100,'wifi':True}]
    st.session_state.devices[pid]=care+common

def patient_creation_panel(origin,key):
    st.subheader('➕ Create / Add New Patient')
    st.caption(f'Entry point: {origin}. Both entry points use the same demo Master Patient Index and duplicate-check service.')
    with st.form(f'create_patient_{key}',clear_on_submit=False):
        c1,c2,c3=st.columns(3)
        first=c1.text_input('First name'); last=c2.text_input('Last name'); dob=c3.date_input('Date of birth',value=datetime(1970,1,1).date())
        age=max(0,(datetime.now().date()-dob).days//365); st.caption(f'Calculated age: {age}')
        c1,c2,c3=st.columns(3); phone=c1.text_input('Phone number'); email=c2.text_input('Email (optional)'); clinician=c3.selectbox('Assigned clinician',CLINICIANS)
        address=st.text_input('Street address'); c1,c2,c3=st.columns(3); city=c1.text_input('City'); state=c2.text_input('State',value='TX'); zipcode=c3.text_input('ZIP code')
        care=st.selectbox('RPM care plan',CARE_PLANS)
        c1,c2=st.columns(2); insurance=c1.text_input('Insurance plan'); member=c2.text_input('Insurance member ID')
        c1,c2,c3=st.columns(3); nok=c1.text_input('Next of kin'); rel=c2.text_input('Relationship to patient'); nokphone=c3.text_input('Next-of-kin contact number')
        submitted=st.form_submit_button('Create Patient',type='primary')
    if submitted:
        if not first.strip() or not last.strip() or not phone.strip(): st.error('First name, last name, and phone number are required for this demo identity check.'); return
        exact,possible=find_duplicate(first,last,dob,phone)
        if exact:
            ep=PATIENTS[exact[0]]; st.error(f"Duplicate prevented. Matching patient already exists: {ep['name']} · {ep['mrn']}. Match criteria: normalized legal name + DOB + phone.")
        elif possible:
            ep=PATIENTS[possible[0]]; st.warning(f"Possible duplicate found: {ep['name']} · {ep['mrn']} has the same normalized name + DOB. Creation is blocked in this demo pending identity review.")
        else:
            pid,mrn=next_patient_ids(); PATIENTS[pid]={'name':f'{first.strip()} {last.strip()}','clinician':clinician,'mrn':mrn,'dob':str(dob),'care_plan':care,'address':address,'city':city,'state':state,'zip':zipcode,'phone':phone,'email':email,'insurance':insurance,'member_id':member,'next_of_kin':nok,'nok_relationship':rel,'nok_phone':nokphone,'baseline_spo2':97,'baseline_weight':170.0,'baseline_hr':75}
            setup_new_patient(pid); st.session_state.audit.append({'time':datetime.now().strftime('%H:%M:%S'),'event_id':pid,'step':f'Patient created from {origin}; MPI duplicate check passed','status':'SUCCESS'}); st.success(f"Patient created once in shared registry: {PATIENTS[pid]['name']} · MRN {mrn}. The patient is now visible from both Clinical Dashboard and Mock EHR.")

LOINC = {'SpO2':'59408-5','Heart Rate':'8867-4','Body Weight':'29463-7','Systolic BP':'8480-6','Diastolic BP':'8462-4','Respiratory Rate':'9279-1','Skin Temperature':'39106-0','Glucose':'14743-9'}


def seed_history():
    now = datetime.now().replace(second=0, microsecond=0)
    rows=[]; n=1
    patterns={
        'SYN-1001': [(98,163.9,72,'Normal Sinus Rhythm'),(98,164.0,73,'Normal Sinus Rhythm'),(97,164.1,72,'Normal Sinus Rhythm'),(97,164.2,74,'Normal Sinus Rhythm'),(96,164.6,78,'Normal Sinus Rhythm'),(95,165.2,84,'Normal Sinus Rhythm'),(97,164.4,74,'Normal Sinus Rhythm')],
        'SYN-1002': [(97,182.0,74,'Normal Sinus Rhythm'),(97,182.2,75,'Normal Sinus Rhythm'),(96,182.5,76,'Normal Sinus Rhythm'),(95,183.0,82,'Normal Sinus Rhythm'),(94,183.8,91,'Tachycardia'),(93,184.7,104,'Tachycardia'),(92,185.8,118,'Atrial Fibrillation')],
        'SYN-1003': [(98,151.3,69,'Normal Sinus Rhythm'),(98,151.4,70,'Normal Sinus Rhythm'),(98,151.5,71,'Normal Sinus Rhythm'),(97,151.4,72,'Normal Sinus Rhythm'),(97,151.6,75,'Normal Sinus Rhythm'),(96,151.5,82,'Unclassified'),(96,151.6,89,'Unclassified')],
        'SYN-1004': [(98,176.7,71,'Normal Sinus Rhythm'),(97,176.8,72,'Normal Sinus Rhythm'),(97,176.9,72,'Normal Sinus Rhythm'),(97,176.8,73,'Normal Sinus Rhythm'),(97,176.9,72,'Normal Sinus Rhythm'),(96,177.0,74,'Normal Sinus Rhythm'),(97,176.8,72,'Normal Sinus Rhythm')],
    }
    for pid, vals in patterns.items():
        for d,(spo2,wt,hr,ecg) in enumerate(vals):
            ts=(now-timedelta(days=6-d)).replace(hour=8,minute=15+d*3)
            last=(d==6)
            rows.append({'event_id':f'EVT-{n:03d}','patient_id':pid,'timestamp':ts.isoformat(),'ecg':ecg,'ecg_hr':hr,'spo2':spo2,'weight':wt,'rr':(22 if pid=='SYN-1002' and last else 16+d%3),'skin_temp':(37.4 if pid=='SYN-1002' and last else 36.2+d*.05),'glucose':(178 if pid=='SYN-1002' and last else 104+d*3),'sys':146 if pid=='SYN-1002' and last else 124,'dia':92 if pid=='SYN-1002' and last else 78,'sob':pid=='SYN-1002' and last,'chest':pid=='SYN-1002' and last,'dizzy':pid=='SYN-1003' and last,'meds':True,'pdf_ok':not(pid=='SYN-1003' and last),'source':'Device' if d!=4 else 'Manual - clinician phone outreach'})
            n+=1
    return rows

if 'events' not in st.session_state: st.session_state.events=seed_history()
if 'audit' not in st.session_state: st.session_state.audit=[]
if 'interventions' not in st.session_state:
    st.session_state.interventions=[{'intervention_id':'INT-001','patient_id':'SYN-1002','event_id':'EVT-014','timestamp':datetime.now().replace(second=0,microsecond=0).isoformat(),'channel':'Phone call','clinician':'RPM Nurse - Demo','outcome':'Patient reached; symptoms reviewed; escalated to clinician for review.','status':'Completed'}]
if 'last_ingested' not in st.session_state: st.session_state.last_ingested=None
if 'thresholds' not in st.session_state:
    st.session_state.thresholds={pid:{'spo2_min':92,'spo2_max':100,'hr_min':50,'hr_max':110,'weight_min':p['baseline_weight']-5,'weight_max':p['baseline_weight']+5,'sys_min':90,'sys_max':160,'dia_min':50,'dia_max':100,'rr_min':10,'rr_max':24,'temp_min':34.0,'temp_max':38.0,'glucose_min':70,'glucose_max':180} for pid,p in PATIENTS.items()}
if 'devices' not in st.session_state:
    st.session_state.devices={}
    for pid,p in PATIENTS.items():
        common=[{'device':'KardiaMobile 6L','type':'ECG · individual','connected':True,'battery':86,'wifi':True},{'device':'Dexcom G7 CGM','type':'Glucose · continuous','connected':True,'battery':91,'wifi':True},{'device':'RPM Tablet','type':'Gateway','connected':True,'battery':34 if pid=='SYN-1002' else 78,'wifi':pid!='SYN-1003'}]
        if p['care_plan']=='Cardiology':
            care=[{'device':'Everion','type':'Continuous · HR / SpO₂ / RR / skin temperature','connected':True,'battery':72,'wifi':True},{'device':'Welch Allyn BP Device','type':'Individual · BP','connected':True,'battery':64,'wifi':True},{'device':'Welch Allyn Weighing Device','type':'Individual · weight','connected':True,'battery':55,'wifi':True}]
        else:
            care=[{'device':'Nonin Pulse Oximeter','type':'Individual · SpO₂','connected':True,'battery':72,'wifi':True},{'device':'Welch Allyn BP Device','type':'Individual · BP / HR','connected':True,'battery':64,'wifi':True},{'device':'Welch Allyn Weighing Device','type':'Individual · weight','connected':True,'battery':55,'wifi':True},{'device':'Everion','type':'Wearable · RR / skin temperature','connected':True,'battery':68,'wifi':True}]
        st.session_state.devices[pid]=care+common
if 'messages' not in st.session_state:
    st.session_state.messages=[]
if 'video_calls' not in st.session_state: st.session_state.video_calls=[]

events=st.session_state.events

def patient_events(pid): return sorted([e for e in events if e['patient_id']==pid],key=lambda x:x['timestamp'])
def latest_for(pid):
    es=patient_events(pid); return es[-1] if es else None

def assess(e):
    p=PATIENTS[e['patient_id']]; t=st.session_state.thresholds[e['patient_id']]; reasons=[]; score=0
    if e['ecg']!='Normal Sinus Rhythm': reasons.append(f"Device-reported ECG classification: {e['ecg']}"); score += 3 if e['ecg']=='Atrial Fibrillation' else 2
    if e['spo2'] < t['spo2_min'] or e['spo2'] > t['spo2_max']: reasons.append(f"SpO₂ {e['spo2']}% outside patient threshold {t['spo2_min']}–{t['spo2_max']}%"); score+=2
    if e['ecg_hr'] < t['hr_min'] or e['ecg_hr'] > t['hr_max']: reasons.append(f"Heart rate {e['ecg_hr']} bpm outside patient threshold {t['hr_min']}–{t['hr_max']}"); score+=2
    if e['weight'] < t['weight_min'] or e['weight'] > t['weight_max']: reasons.append(f"Weight {e['weight']:.1f} lb outside patient threshold {t['weight_min']:.1f}–{t['weight_max']:.1f} lb"); score+=1
    if e['sys'] < t['sys_min'] or e['sys'] > t['sys_max'] or e['dia'] < t['dia_min'] or e['dia'] > t['dia_max']: reasons.append(f"BP {e['sys']}/{e['dia']} outside patient-specific threshold"); score+=1
    if e.get('rr',16) < t['rr_min'] or e.get('rr',16) > t['rr_max']: reasons.append(f"Respiratory rate {e.get('rr')} outside patient threshold {t['rr_min']}–{t['rr_max']} breaths/min"); score+=1
    if e.get('skin_temp',36.5) < t['temp_min'] or e.get('skin_temp',36.5) > t['temp_max']: reasons.append(f"Skin temperature {e.get('skin_temp')}°C outside patient threshold {t['temp_min']}–{t['temp_max']}°C"); score+=1
    if e.get('glucose',110) < t['glucose_min'] or e.get('glucose',110) > t['glucose_max']: reasons.append(f"CGM glucose {e.get('glucose')} mg/dL outside patient threshold {t['glucose_min']}–{t['glucose_max']} mg/dL"); score+=1
    if e.get('sob'): reasons.append('Daily questionnaire: shortness of breath = Yes'); score+=2
    if e.get('chest'): reasons.append('Daily questionnaire: chest discomfort = Yes'); score+=2
    if e.get('dizzy'): reasons.append('Daily questionnaire: dizziness = Yes'); score+=1
    if not e['pdf_ok']: reasons.append('ECG document failed identifier validation'); score+=1
    return ('HIGH' if score>=5 else 'MEDIUM' if score>=2 else 'LOW'),reasons,score

def interventions_for_event(eid): return [x for x in st.session_state.interventions if x['event_id']==eid]
def alert_status(e):
    pri,_,_=assess(e); ints=interventions_for_event(e['event_id'])
    if pri=='LOW': return 'No active alert'
    if ints: return 'Intervention documented'
    return 'Needs clinician outreach' if pri=='HIGH' else 'Needs review'

def ecg_pdf_bytes(e, valid=True):
    p=PATIENTS[e['patient_id']]; buf=io.BytesIO(); c=canvas.Canvas(buf,pagesize=letter); W,H=letter
    for page in range(1,3):
        c.setFont('Helvetica-Bold',10); ident=f"Patient: {p['name']}   |   MRN: {p['mrn']}   |   DOB: {p['dob']}"
        if not valid and page==2: ident=f"Patient: {p['name']}   |   MRN: [MISSING]   |   DOB: {p['dob']}"
        c.drawString(.55*inch,H-.45*inch,ident); c.setFont('Helvetica-Bold',16); c.drawString(.55*inch,H-.85*inch,'Synthetic 6-Lead ECG Demonstration Report')
        c.setFont('Helvetica',9); c.drawString(.55*inch,H-1.08*inch,'Portfolio prototype — simulated waveform; not a diagnostic ECG report.')
        c.setFont('Helvetica',10); c.drawString(.55*inch,H-1.4*inch,f"Recording ID: {e['event_id']}   Recorded: {e['timestamp'][:16].replace('T',' ')}")
        c.drawString(.55*inch,H-1.62*inch,f"Device-reported classification: {e['ecg']}   Heart rate: {e['ecg_hr']} bpm")
        for i,lead in enumerate(['I','II','III','aVR','aVL','aVF']):
            y=H-2.05*inch-i*.72*inch; c.setFont('Helvetica-Bold',9); c.drawString(.55*inch,y+.15*inch,lead); c.setLineWidth(.3); c.line(.9*inch,y,7.8*inch,y)
            pts=[]
            for x in range(620):
                xx=.9*inch+x*.011*inch; phase=(x%70)/70; val=2.5*math.sin(x/8)
                if .43<phase<.47: val+=18*(1-abs(phase-.45)/.02)
                if .47<=phase<.50: val-=9*(1-abs(phase-.485)/.015)
                pts.append((xx,y+val*(-1 if lead=='aVR' else 1)))
            c.setLineWidth(.7)
            for a,b in zip(pts[:-1],pts[1:]): c.line(a[0],a[1],b[0],b[1])
        c.setFont('Helvetica-Oblique',8); c.drawString(.55*inch,.45*inch,f'Page {page} of 2 | SYNTHETIC DATA ONLY | Human review required'); c.showPage()
    c.save(); return buf.getvalue()

def fhir_bundle(e):
    p=PATIENTS[e['patient_id']]; obs=[]
    for label,val,unit in [('SpO2',e['spo2'],'%'),('Heart Rate',e['ecg_hr'],'/min'),('Body Weight',e['weight'],'lb'),('Systolic BP',e['sys'],'mmHg'),('Diastolic BP',e['dia'],'mmHg'),('Respiratory Rate',e.get('rr',16),'breaths/min'),('Skin Temperature',e.get('skin_temp',36.5),'Cel'),('Glucose',e.get('glucose',110),'mg/dL')]:
        obs.append({'resourceType':'Observation','status':'final','code':{'coding':[{'system':'http://loinc.org','code':LOINC[label],'display':label}]},'subject':{'reference':f"Patient/{e['patient_id']}"},'effectiveDateTime':e['timestamp'],'valueQuantity':{'value':val,'unit':unit}})
    return {'resourceType':'Bundle','type':'transaction','patient':{'id':e['patient_id'],'mrn':p['mrn'],'name':p['name']},'entry':obs,'ecg':{'classification':e['ecg'],'reportId':e['event_id']},'questionnaire':{'shortnessOfBreath':e['sob'],'chestDiscomfort':e['chest'],'dizziness':e['dizzy'],'medicationTaken':e['meds']}}

def log(eid,step,status='SUCCESS'): st.session_state.audit.append({'time':datetime.now().strftime('%H:%M:%S'),'event_id':eid,'step':step,'status':status})

def trend_df(pid):
    es=patient_events(pid)[-7:]
    return pd.DataFrame([{'Date':pd.to_datetime(e['timestamp']).strftime('%b %d'),'SpO₂ (%)':e['spo2'],'Heart Rate (bpm)':e['ecg_hr'],'Weight (lb)':e['weight']} for e in es])

def battery_icon(level):
    return ('🟢' if level>=60 else '🟡' if level>=30 else '🔴') + f" {level}%"

def device_table(pid):
    return pd.DataFrame([{'Device':d['device'],'Measurement / mode':d.get('type',''),'Connected':'🟢 Connected' if d['connected'] else '🔴 Disconnected','Battery':battery_icon(d['battery']),'Internet':'📶 Online' if d['wifi'] else '🚫 Offline'} for d in st.session_state.devices[pid]])

def trend_chart(pid, field, title, unit, min_key=None, max_key=None):
    es=patient_events(pid)[-7:]; x=[pd.to_datetime(e['timestamp']) for e in es]; y=[e.get(field) for e in es]
    src=[e.get('source','Device') for e in es]; symbols=['circle' if 'Device' in a else 'diamond' for a in src]
    t=st.session_state.thresholds[pid]; lo=t.get(min_key) if min_key else None; hi=t.get(max_key) if max_key else None
    colors=['#D62728' if (lo is not None and v<lo) or (hi is not None and v>hi) else ('#7B2CBF' if 'Manual' in src[i] else '#2878B5') for i,v in enumerate(y)]
    custom=[]
    for e in es:
        device=source_device(PATIENTS[pid]['care_plan'], field, e.get('source','Device'))
        custom.append([e['event_id'],e.get('source','Device'),device,e['ecg']])
    fig=go.Figure(go.Scatter(x=x,y=y,mode='lines+markers+text',text=[str(v) for v in y],textposition='top center',line={'color':'#7A7A7A'},marker={'size':11,'symbol':symbols,'color':colors},customdata=custom,hovertemplate='<b>Value:</b> %{y} '+unit+'<br><b>Timestamp:</b> %{x|%b %d, %Y %I:%M %p}<br><b>Entry source:</b> %{customdata[1]}<br><b>Device:</b> %{customdata[2]}<br><b>Event:</b> %{customdata[0]}<br><b>ECG:</b> %{customdata[3]}<extra></extra>'))
    if lo is not None: fig.add_hline(y=lo,line_dash='dash',line_color='#008C95',annotation_text='Min threshold')
    if hi is not None: fig.add_hline(y=hi,line_dash='dash',line_color='#008C95',annotation_text='Max threshold')
    fig.update_layout(title=title,height=310,margin=dict(l=20,r=20,t=55,b=20),yaxis_title=unit,hovermode='closest')
    st.plotly_chart(fig,use_container_width=True)
    st.caption('● Device-generated   ◆ Manual clinician-assisted   🔵 Device-generated normal-range point   🟣 Manual clinician-assisted point   🔴 Out-of-threshold reading   Teal dashed lines = configured min/max limits')

def source_device(plan, field, source):
    if 'Manual' in source: return 'Patient-reported / clinician-entered'
    if field=='ecg_hr': return 'Everion (continuous)' if plan=='Cardiology' else 'Welch Allyn BP Device (individual)'
    if field=='spo2': return 'Everion (continuous)' if plan=='Cardiology' else 'Nonin Pulse Oximeter (individual)'
    if field in ('rr','skin_temp'): return 'Everion (continuous wearable)'
    if field=='weight': return 'Welch Allyn Weighing Device (individual)'
    if field in ('sys','dia'): return 'Welch Allyn BP Device (individual)'
    if field=='glucose': return 'Dexcom G7 CGM (continuous)'
    return 'Connected device'

def questionnaire_for(plan):
    if plan=='Cardiology':
        return [('sob','Shortness of breath?'),('chest','Chest discomfort?'),('palpitations','Palpitations or rapid heartbeat?'),('dizzy','Dizziness or lightheadedness?'),('swelling','New/increased swelling in feet or ankles?'),('fatigue','Unusual fatigue?'),('meds','Did you take medications as directed today?')]
    return [('abdominal_swelling','Increased abdominal swelling?'),('leg_swelling','New/increased leg or ankle swelling?'),('sob','Shortness of breath?'),('nausea','Nausea or vomiting?'),('appetite','Reduced appetite?'),('confusion','New confusion or difficulty concentrating?'),('sleepiness','Unusual sleepiness?'),('bleeding','Blood in vomit or stool reported?'),('meds','Did you take medications as directed today?')]

st.title('🫀 RPM Connected Care AI Platform · v2.3')
st.caption('Patient Daily Check-In • Connected Devices • Thresholds • Trends • Questionnaire • Secure Chat • Video-call Simulation • API/FHIR • Synthetic data')
st.info('Portfolio prototype only. It does not diagnose, treat, or provide medical advice. ECG classifications are device-reported inputs; clinical decisions remain human-in-the-loop.')
menu=st.sidebar.radio('Navigate',['1 · Patient Home & Daily Check-In','2 · Clinical Command Center','3 · Patient 360 & Trends','4 · ECG Documents','5 · AI Agent','6 · Clinician Interventions','7 · Communication Center','8 · Integration Hub / API','9 · Mock EHR','10 · Data Lineage & Audit','11 · Architecture & Product','12 · Patient Identity & Duplicate Prevention'])

if menu.startswith('1 ·'):
    st.header('📱 Patient Home & Daily Check-In')
    st.info('PATIENT-HOME SIMULATOR — This page simulates a patient tablet/app receiving connected-device readings and the patient completing today’s care-plan questionnaire. Clinician-assisted entry is available for missed submissions.')
    pid=st.selectbox('Synthetic patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']} · {PATIENTS[x]['care_plan']}")
    p=PATIENTS[pid]; prior=latest_for(pid); mode=st.radio('Submission source',['Patient tablet + connected devices','Clinician-assisted entry after phone/chat outreach'],horizontal=True)
    st.subheader('Connected devices'); st.dataframe(device_table(pid),hide_index=True,use_container_width=True)
    st.subheader('Previous stored reading')
    if prior:
        c1,c2,c3,c4=st.columns(4); c1.metric('SpO₂',f"{prior['spo2']}%"); c2.metric('ECG HR',f"{prior['ecg_hr']} bpm"); c3.metric('Weight',f"{prior['weight']} lb"); c4.metric('Source',prior.get('source','Device'))
    st.subheader('Today’s new readings')
    c1,c2,c3=st.columns(3)
    with c1:
        ecg=st.selectbox('ECG — device-reported classification',['Normal Sinus Rhythm','Atrial Fibrillation','Bradycardia','Tachycardia','Unclassified','Sinus Rhythm with PVCs','Sinus Rhythm with SVE','Sinus Rhythm with Wide QRS']); hr=st.number_input('ECG heart rate (bpm)',35,180,value=p['baseline_hr'])
    with c2: spo2=st.number_input('SpO₂ (%)',70,100,value=p['baseline_spo2']); wt=st.number_input('Weight (lb)',80.0,350.0,value=float(p['baseline_weight']),step=.1); rr=st.number_input('Respiratory rate (breaths/min)',6,40,value=16)
    with c3: sys=st.number_input('Systolic BP',70,220,124); dia=st.number_input('Diastolic BP',40,140,78); skin_temp=st.number_input('Skin temperature (°C)',28.0,43.0,36.5,step=.1); glucose=st.number_input('CGM glucose (mg/dL)',40,400,110); pdf_ok=st.checkbox('Required identifiers on every ECG PDF page',True)
    st.subheader(f"📋 {p['care_plan']} Daily Questionnaire")
    answers={}
    for key,q in questionnaire_for(p['care_plan']): answers[key]=st.radio(q,['No','Yes'],horizontal=True,key=f'q_{pid}_{key}',index=1 if key=='meds' else 0)
    entered_by=''
    if mode.startswith('Clinician'): entered_by=st.selectbox('Clinician entering patient-reported data',['Dr. John Doe','Dr. Aisha Morgan','Dr. Samuel Lee','RPM Nurse - Demo'])
    if st.button('📤 Simulate Patient Daily Submission' if mode.startswith('Patient') else '☎️ Save Clinician-Assisted Entry',type='primary'):
        nums=[int(x['event_id'].split('-')[1]) for x in events]; eid=f"EVT-{max(nums)+1:03d}"; source='Device' if mode.startswith('Patient') else f'Manual - {entered_by} via outreach'
        e={'event_id':eid,'patient_id':pid,'timestamp':datetime.now().replace(microsecond=0).isoformat(),'ecg':ecg,'ecg_hr':int(hr),'spo2':int(spo2),'weight':float(wt),'rr':int(rr),'skin_temp':float(skin_temp),'glucose':int(glucose),'sys':int(sys),'dia':int(dia),'sob':answers.get('sob')=='Yes','chest':answers.get('chest')=='Yes','dizzy':answers.get('dizzy')=='Yes','meds':answers.get('meds')=='Yes','questionnaire':answers,'pdf_ok':pdf_ok,'source':source}; events.append(e); st.session_state.last_ingested=eid
        for step in ['Daily questionnaire submitted','RPM data ingested','Clinical dashboard updated','Threshold/AI alert evaluation completed','EHR-ready payload generated']: log(eid,step)
        pri,reasons,_=assess(e); st.success(f'{eid} saved as a NEW timestamped RPM event. Existing history was preserved. Source: {source}.'); a,b,c=st.columns(3); a.metric('Priority',pri); b.metric('SpO₂',f"{spo2}%"); c.metric('Heart rate',f"{hr} bpm")
        if reasons: st.warning('Alert reasons: '+' | '.join(reasons))

elif menu.startswith('2 ·'):
    st.header('🩺 Clinical Command Center')
    st.write('Population view for clinicians: alerts, assigned clinician, connectivity, device status, and patient communications.')
    with st.expander('➕ Create Patient / Add New Patient'):
        patient_creation_panel('Clinical Dashboard','clinical')
    rows=[]
    for pid,p in PATIENTS.items():
        e=latest_for(pid); devs=st.session_state.devices.get(pid,[]); problems=sum((not d['connected']) or (not d['wifi']) or d['battery']<30 for d in devs); unread=sum(m['patient_id']==pid and m['sender']=='Patient' and not m.get('read',False) for m in st.session_state.messages)
        if e: pri,_,_=assess(e); spo=e['spo2']; hr=e['ecg_hr']; ast=alert_status(e)
        else: pri='AWAITING DATA'; spo='—'; hr='—'; ast='No RPM reading yet'
        rows.append({'Patient':p['name'],'MRN':p['mrn'],'Assigned clinician':p['clinician'],'Care Plan':p['care_plan'],'SpO₂':spo,'HR':hr,'Priority':pri,'Alert status':ast,'Device issues':problems,'Unread chat':unread})
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    pid=st.selectbox('Open patient clinical view',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} — {PATIENTS[x]['clinician']}")
    p=PATIENTS[pid]; e=latest_for(pid)
    if not e:
        st.info('Patient enrolled. No RPM readings have been received yet. Use Patient Home & Daily Check-In to simulate the first submission.')
        st.subheader('Wearables & connectivity'); st.dataframe(device_table(pid),hide_index=True,use_container_width=True)
        st.stop()
    pri,reasons,_=assess(e)
    a,b,c=st.columns(3); a.metric('Assigned clinician',p['clinician']); b.metric('Priority',pri); c.metric('Alert status',alert_status(e))
    st.subheader('Wearables & connectivity'); st.dataframe(device_table(pid),hide_index=True,use_container_width=True)
    for d in st.session_state.devices[pid]:
        if not d['connected'] or not d['wifi'] or d['battery']<30: st.warning(f"Device attention: {d['device']} — connected={d['connected']}, internet={d['wifi']}, battery={d['battery']}%. Consider patient outreach.")
    st.subheader('Latest daily questionnaire')
    qa=e.get('questionnaire',{'sob':'Yes' if e.get('sob') else 'No','chest':'Yes' if e.get('chest') else 'No','dizzy':'Yes' if e.get('dizzy') else 'No','meds':'Yes' if e.get('meds') else 'No'}); st.dataframe(pd.DataFrame([{'Question / field':k.replace('_',' ').title(),'Patient answer':v} for k,v in qa.items()]),hide_index=True,use_container_width=True)
    st.subheader('Alert reasons'); [st.write('• '+r) for r in reasons] if reasons else st.success('No active configured threshold exception.')
    unread=[m for m in st.session_state.messages if m['patient_id']==pid and m['sender']=='Patient' and not m.get('read',False)]
    if unread: st.error(f"💬 {len(unread)} unread patient message(s). Open Communication Center for timely intervention.")

elif menu.startswith('3 ·'):
    st.header('👤 Patient 360 & Trends')
    pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']}"); p=PATIENTS[pid]; e=latest_for(pid)
    if not e:
        st.info('Patient is enrolled but has no RPM readings yet. Demographics and devices are available; trends begin after the first submission.')
        st.write({'MRN':p['mrn'],'DOB':p['dob'],'Phone':p.get('phone'),'Care plan':p['care_plan'],'Assigned clinician':p['clinician']}); st.dataframe(device_table(pid),hide_index=True,use_container_width=True); st.stop()
    pri,reasons,_=assess(e)
    left,right=st.columns([3,1])
    with left:
        a,b,c,d=st.columns(4); a.metric('Care plan',p['care_plan']); b.metric('Assigned clinician',p['clinician']); c.metric('Latest source',e.get('source','Device')); d.metric('Priority',pri)
        st.subheader('Wearables & connectivity'); st.dataframe(device_table(pid),hide_index=True,use_container_width=True)
        st.subheader('7-day longitudinal trends')
        trend_chart(pid,'spo2','SpO₂ Trend','%','spo2_min','spo2_max'); trend_chart(pid,'ecg_hr','Heart Rate Trend','bpm','hr_min','hr_max'); trend_chart(pid,'weight','Weight Trend','lb','weight_min','weight_max'); trend_chart(pid,'rr','Respiratory Rate Trend','breaths/min','rr_min','rr_max'); trend_chart(pid,'skin_temp','Skin Temperature Trend','°C','temp_min','temp_max'); trend_chart(pid,'glucose','Glucose (CGM) Trend','mg/dL','glucose_min','glucose_max')
        st.subheader('ECG classification history'); st.dataframe(pd.DataFrame([{'Timestamp':x['timestamp'][:16].replace('T',' '),'Classification':x['ecg'],'Source':x.get('source','Device')} for x in patient_events(pid)[-7:]]),hide_index=True,use_container_width=True)
        st.subheader('Daily questionnaire history')
        for x in reversed(patient_events(pid)[-7:]):
            with st.expander(f"{x['timestamp'][:10]} · {x['event_id']} · {x.get('source','Device')}"):
                qa=x.get('questionnaire',{'sob':'Yes' if x.get('sob') else 'No','chest':'Yes' if x.get('chest') else 'No','dizzy':'Yes' if x.get('dizzy') else 'No','meds':'Yes' if x.get('meds') else 'No'}); st.dataframe(pd.DataFrame([{'Question / field':k.replace('_',' ').title(),'Answer':v} for k,v in qa.items()]),hide_index=True,use_container_width=True)
    with right:
        st.subheader('⚙️ Patient Alert Threshold Settings'); st.info('These controls SET the patient-specific minimum and maximum limits. They are not today’s readings. Trend points turn RED only when a reading falls outside the configured limits; teal dashed lines show the configured limits. Manual clinician-assisted readings appear purple so provenance is visible at a glance.')
        t=st.session_state.thresholds[pid]
        t['spo2_min'],t['spo2_max']=st.slider('SpO₂ (%) min / max',70,100,(int(t['spo2_min']),int(t['spo2_max'])))
        t['hr_min'],t['hr_max']=st.slider('Heart rate (bpm) min / max',30,180,(int(t['hr_min']),int(t['hr_max'])))
        t['weight_min']=st.number_input('Weight minimum (lb)',80.0,350.0,float(t['weight_min']),step=.5); t['weight_max']=st.number_input('Weight maximum (lb)',80.0,350.0,float(t['weight_max']),step=.5)
        t['sys_min'],t['sys_max']=st.slider('Systolic BP min / max',70,220,(int(t['sys_min']),int(t['sys_max'])))
        t['dia_min'],t['dia_max']=st.slider('Diastolic BP min / max',40,140,(int(t['dia_min']),int(t['dia_max']))); t['rr_min'],t['rr_max']=st.slider('Respiratory rate min / max',6,40,(int(t['rr_min']),int(t['rr_max']))); t['temp_min'],t['temp_max']=st.slider('Skin temperature °C min / max',28.0,43.0,(float(t['temp_min']),float(t['temp_max'])),step=.1); t['glucose_min'],t['glucose_max']=st.slider('CGM glucose mg/dL min / max',40,400,(int(t['glucose_min']),int(t['glucose_max'])))
        st.success('Thresholds active for this synthetic patient.')
        st.caption('In a real clinical product, threshold changes would require role-based authorization, clinical governance and audit logging.')
elif menu.startswith('4 ·'):
    st.header('ECG Documents'); pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']}"); es=patient_events(pid)
    for e in reversed(es[-4:]):
        with st.expander(f"{e['event_id']} · {e['timestamp'][:16].replace('T',' ')} · {e['ecg']}",expanded=(e==es[-1])):
            st.download_button('📄 Download / View synthetic ECG PDF',ecg_pdf_bytes(e,e['pdf_ok']),file_name=f"{e['event_id']}_{PATIENTS[pid]['mrn']}.pdf",mime='application/pdf',key='pdf'+e['event_id'],type='primary')
            checks={'Patient name on every page':True,'MRN on every page':e['pdf_ok'],'DOB on every page':True,'ECG timestamp':True,'Patient association':True}; st.dataframe(pd.DataFrame([{'Check':k,'Result':'PASS' if v else 'FAIL'} for k,v in checks.items()]),hide_index=True,use_container_width=True)
            st.success('DOCUMENT VALIDATION PASSED — eligible for downstream transmission.') if e['pdf_ok'] else st.error('DOCUMENT VALIDATION FAILED — held; mock EHR Media filing blocked.')

elif menu.startswith('5 ·'):
    st.header('AI Agent'); pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:PATIENTS[x]['name']); e=latest_for(pid); pri,reasons,score=assess(e); st.metric('Workflow priority',pri); st.progress(min(score/10,1.0))
    st.subheader('Agent-generated review summary'); st.write((f"Latest RPM event {e['event_id']} was prioritized as {pri}. "+' '.join(reasons)+ ' Clinical interpretation and action remain with the clinician.') if reasons else 'No configured workflow exception detected. Continue monitoring according to the care plan.')
    st.dataframe(pd.DataFrame([('Monitoring Agent','Evaluated ECG, vitals, longitudinal trends and questionnaire','COMPLETE'),('Adherence Agent','Checked expected measurement availability','COMPLETE'),('Integration Agent','Prepared structured EHR-ready payload','COMPLETE'),('Document Agent','Validated patient identifiers on ECG PDF','COMPLETE' if e['pdf_ok'] else 'HELD'),('Human-in-the-loop','Clinician outreach/intervention','COMPLETE' if interventions_for_event(e['event_id']) else 'PENDING' if pri!='LOW' else 'NOT REQUIRED')],columns=['Agent / Step','Action','Status']),hide_index=True,use_container_width=True)

elif menu.startswith('6 ·'):
    st.header('Clinician Interventions'); st.write('Document the human response to an RPM alert. This creates a visible closed-loop workflow: **alert → clinician review → patient communication → outcome**.')
    alert_events=[e for e in events if assess(e)[0]!='LOW']; e=st.selectbox('Alert event',alert_events,format_func=lambda x:f"{x['event_id']} · {PATIENTS[x['patient_id']]['name']} · {assess(x)[0]} · {x['ecg']}"); pri,reasons,_=assess(e)
    st.write('**Alert reasons:**'); [st.write('• '+r) for r in reasons]
    existing=interventions_for_event(e['event_id'])
    if existing: st.success(f"Existing intervention: {existing[-1]['channel']} — {existing[-1]['outcome']}")
    c1,c2=st.columns(2)
    with c1: channel=st.selectbox('Communication channel',['Phone call','Secure chat / patient message','Video call','Unable to reach — voicemail','Care-team escalation'])
    with c2: clinician=st.text_input('Clinician / RPM team member','RPM Nurse - Demo')
    outcome=st.text_area('Intervention / outcome','Patient contacted; symptoms reviewed; clinician follow-up arranged according to RPM workflow.')
    status=st.selectbox('Status',['Completed','Follow-up required','Unable to reach','Escalated'])
    if st.button('✓ Document Clinician Intervention',type='primary'):
        iid=f"INT-{len(st.session_state.interventions)+1:03d}"; rec={'intervention_id':iid,'patient_id':e['patient_id'],'event_id':e['event_id'],'timestamp':datetime.now().replace(microsecond=0).isoformat(),'channel':channel,'clinician':clinician,'outcome':outcome,'status':status}; st.session_state.interventions.append(rec); log(e['event_id'],f'Clinician intervention documented via {channel}',status.upper()); st.success(f'{iid} saved. The Clinical Command Center and Patient 360 now show the communication as part of the closed-loop alert workflow.')
    st.subheader('Intervention log');
    if st.session_state.interventions: st.dataframe(pd.DataFrame(st.session_state.interventions)[['timestamp','event_id','patient_id','channel','clinician','outcome','status']],hide_index=True,use_container_width=True)

elif menu.startswith('7 ·'):
    st.header('💬 Communication Center')
    st.write('Two-way secure-chat and video-call workflow simulator. This demonstrates product behavior; it is not a live telehealth service.')
    pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · Assigned: {PATIENTS[x]['clinician']}"); p=PATIENTS[pid]
    role=st.radio('Test as',['Patient','Clinician'],horizontal=True)
    st.info(f"Patient: {p['name']}  |  Assigned clinician: {p['clinician']}")
    msgs=[m for m in st.session_state.messages if m['patient_id']==pid]
    for m in msgs:
        who='👤 Patient' if m['sender']=='Patient' else f"🩺 {m['clinician']}"
        st.markdown(f"**{who} · {m['timestamp']}**  \n{m['text']}")
    textmsg=st.text_input('Message',key=f'msg_{pid}_{role}',placeholder='Type a test message...')
    if st.button('Send message',type='primary') and textmsg.strip():
        now=datetime.now().strftime('%b %d, %I:%M %p'); st.session_state.messages.append({'patient_id':pid,'sender':role,'clinician':p['clinician'],'timestamp':now,'text':textmsg.strip(),'read':role=='Clinician'})
        if role=='Patient':
            auto=f"Thank you for contacting {p['clinician']}. They will be with you shortly. If this is an emergency, use your local emergency services rather than this demo chat."
            st.session_state.messages.append({'patient_id':pid,'sender':'Clinician','clinician':p['clinician'],'timestamp':now,'text':auto,'read':True,'automated':True}); st.error(f"🔔 Clinician alert created: new patient message from {p['name']}.")
        else:
            for m in st.session_state.messages:
                if m['patient_id']==pid and m['sender']=='Patient': m['read']=True
        st.rerun()
    st.divider(); st.subheader('📹 Video-call simulation')
    if st.button('Start simulated video call'):
        st.session_state.video_calls.append({'patient_id':pid,'clinician':p['clinician'],'timestamp':datetime.now().isoformat(timespec='minutes'),'status':'Connected (simulated)'}); st.success(f"Simulated video session connected between {p['name']} and {p['clinician']}. No real camera/audio is transmitted in this portfolio app.")
    vc=[v for v in st.session_state.video_calls if v['patient_id']==pid]
    if vc: st.dataframe(pd.DataFrame(vc),hide_index=True,use_container_width=True)

elif menu.startswith('8 ·'):
    st.header('Integration Hub / API'); st.write('Normalized RPM event + EHR-ready FHIR-style transformation. This is a simulation, not a live Epic endpoint.'); pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']}"); e=latest_for(pid)
    normalized={'eventId':e['event_id'],'patient':PATIENTS[pid],'carePlan':PATIENTS[pid]['care_plan'],'deviceData':{'ecgClassification':e['ecg'],'ecgHeartRate':e['ecg_hr'],'spo2':e['spo2'],'weight':e['weight'],'bloodPressure':{'systolic':e['sys'],'diastolic':e['dia']}},'questionnaire':{'shortnessOfBreath':e['sob'],'chestDiscomfort':e['chest'],'dizziness':e['dizzy'],'medicationTaken':e['meds']},'ecgDocument':{'reportId':e['event_id'],'identifierValidation':'PASS' if e['pdf_ok'] else 'FAIL'}}
    t1,t2,t3=st.tabs(['Normalized RPM JSON','FHIR-style Bundle','Mapping Table'])
    with t1: st.code(json.dumps(normalized,indent=2),language='json'); st.download_button('Download normalized JSON',json.dumps(normalized,indent=2),file_name=f"{e['event_id']}_rpm.json",mime='application/json')
    with t2: fb=fhir_bundle(e); st.code(json.dumps(fb,indent=2),language='json'); st.download_button('Download EHR-ready FHIR-style JSON',json.dumps(fb,indent=2),file_name=f"{e['event_id']}_fhir.json",mime='application/json')
    with t3: st.dataframe(pd.DataFrame([{'Source':'Pulse oximeter','Field':'SpO₂','LOINC':LOINC['SpO2'],'Destination':'EHR flowsheet / Observation'},{'Source':'ECG device','Field':'Heart rate','LOINC':LOINC['Heart Rate'],'Destination':'EHR flowsheet / Observation'},{'Source':'Scale','Field':'Weight','LOINC':LOINC['Body Weight'],'Destination':'EHR flowsheet / Observation'},{'Source':'BP wearable','Field':'Systolic BP','LOINC':LOINC['Systolic BP'],'Destination':'EHR flowsheet / Observation'},{'Source':'Everion','Field':'Respiratory rate / skin temperature','LOINC':LOINC['Respiratory Rate']+' / '+LOINC['Skin Temperature'],'Destination':'EHR flowsheet / Observation'},{'Source':'Dexcom G7 CGM','Field':'Glucose','LOINC':LOINC['Glucose'],'Destination':'EHR flowsheet / Observation'},{'Source':'ECG report','Field':'PDF','LOINC':'N/A','Destination':'Cloverleaf → OnBase → EHR Media (simulated)'}]),hide_index=True,use_container_width=True)

elif menu.startswith('9 ·'):
    st.header('Mock EHR');
    with st.expander('➕ Create Patient / Add New Patient'):
        patient_creation_panel('Mock EHR','ehr')
    pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']}"); es=patient_events(pid); t1,t2,t3=st.tabs(['Flowsheets','Media','Care-team communications'])
    with t1: st.dataframe(pd.DataFrame([{'Date/Time':e['timestamp'][:16].replace('T',' '),'SpO₂':e['spo2'],'Heart Rate':e['ecg_hr'],'Weight':e['weight'],'BP':f"{e['sys']}/{e['dia']}",'ECG device result':e['ecg']} for e in es]),hide_index=True,use_container_width=True)
    with t2:
        for e in [x for x in es if x['pdf_ok']]: st.write(f"📄 {e['event_id']}.pdf · Remote ECG · Source: RPM Vendor · Status: FILED"); st.download_button('View PDF',ecg_pdf_bytes(e,True),file_name=f"{e['event_id']}.pdf",mime='application/pdf',key='ehr'+e['event_id'])
        for e in [x for x in es if not x['pdf_ok']]: st.error(f"{e['event_id']} — identifier validation failed; not filed to mock EHR Media.")
    with t3:
        ints=[x for x in st.session_state.interventions if x['patient_id']==pid]; st.dataframe(pd.DataFrame(ints),hide_index=True,use_container_width=True) if ints else st.caption('No documented communication.')

elif menu.startswith('10 ·'):
    st.header('Data Lineage & Audit'); e=st.selectbox('Trace event',events,format_func=lambda x:f"{x['event_id']} · {PATIENTS[x['patient_id']]['name']} · {x['timestamp'][:16].replace('T',' ')}")
    pri,_,_=assess(e); ints=interventions_for_event(e['event_id']); steps=[('1','Patient home',f"ECG={e['ecg']}; SpO₂={e['spo2']}%; weight={e['weight']} lb; questionnaire captured"),('2','Bluetooth / tablet','Connected-device values collected by patient app (simulated)'),('3','Vendor ingestion API','Normalized RPM event accepted'),('4','Clinical dashboard',f'Patient record updated; {pri} workflow priority calculated'),('5','Human intervention',f"{ints[-1]['channel']} — {ints[-1]['status']}" if ints else 'No communication documented yet'),('6','Integration API','LOINC-coded/FHIR-style payload prepared'),('7','Structured EHR path','Vitals and ECG values available in mock flowsheet'),('8','Document path','ECG PDF → Cloverleaf → OnBase → Media simulation' if e['pdf_ok'] else 'ECG PDF HELD because identifier validation failed')]
    for n,title,desc in steps: st.markdown(f'**{n}. {title}**  \n{desc}')
    st.subheader('Session audit log'); st.dataframe(pd.DataFrame(st.session_state.audit),hide_index=True,use_container_width=True) if st.session_state.audit else st.caption('Ingest or document an intervention to populate the live audit log.')

elif menu.startswith('11 ·'):
    st.header('Architecture & Product Story'); st.code('''PATIENT HOME\n  KardiaMobile 6L + Everion/individual vitals + Dexcom G7 CGM + Questionnaire\n                    │ Bluetooth\n                    ▼\n              Patient Tablet\n                    │\n                    ▼\n             Vendor RPM Cloud\n          ┌─────────┴─────────┐\n          ▼                   ▼\n Clinical Dashboard        ECG PDF\n          │                   │\n          ▼                   ▼\n AI Alert / Trend Layer   Document Validation\n          │                   │\n          ▼                   ▼\n Clinician Outreach      Cloverleaf → OnBase\n          │                   │\n          ▼                   ▼\n RPM Integration API     Mock EHR Media\n          │\n          ▼\n FHIR/LOINC Mapping → Mock EHR Flowsheet\n\nCLOSED LOOP: Alert → Human review → Call/Chat → Outcome → Audit trail''')
    st.write('**MVP epics:** timestamped device ingestion · longitudinal trends · clinical command center · AI workflow prioritization · clinician intervention · ECG document integrity · EHR transformation · lineage/audit.')
    st.write('**Guardrails:** synthetic data only; no autonomous diagnosis; device classifications treated as source inputs; failed documents held; clinician remains decision-maker.')
    st.write('**KPIs:** alert precision, time-to-review, time-to-patient-contact, intervention completion, false-positive rate, data completeness, document validation pass rate, EHR delivery success, clinician override rate.')


if menu.startswith('12 ·'):
    st.header('🧬 Patient Identity & Duplicate Prevention')
    st.write('Both the Clinical Dashboard and Mock EHR creation buttons call the same shared Master Patient Index (MPI) service in this prototype. That means there is one patient registry, not two independent patient lists.')
    st.subheader('Demo matching logic')
    st.markdown('''**1. Exact/high-confidence match:** normalized legal name + date of birth + phone → creation is blocked and the existing MRN is returned.  
**2. Possible match:** normalized legal name + date of birth → creation is blocked for identity review.  
**3. No match:** a new synthetic MRN is generated and the patient is written once to the shared registry.  
**4. Source is audited:** the audit trail records whether creation started from the Clinical Dashboard or Mock EHR.''')
    st.info('Production systems typically use an Enterprise Master Patient Index (EMPI/MPI), stronger identity attributes, configurable matching rules, role-based access, merge/unmerge governance, and human review for ambiguous matches. This portfolio prototype intentionally uses a simple deterministic rule.')
    st.subheader('Shared patient registry')
    st.dataframe(pd.DataFrame([{'Patient':p['name'],'MRN':p['mrn'],'DOB':p['dob'],'Phone':p.get('phone',''),'Care Plan':p['care_plan'],'Assigned clinician':p['clinician']} for p in PATIENTS.values()]),hide_index=True,use_container_width=True)
