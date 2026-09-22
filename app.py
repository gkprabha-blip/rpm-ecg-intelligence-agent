import io, json, math, re, base64
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import fitz
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

st.set_page_config(page_title='RPM Connected Care AI Platform v3.0', page_icon='🫀', layout='wide')

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

CARE_PLANS=['Cardiology','Cirrhosis / Liver Disease','Hypertension','Diabetes / CGM','Heart Failure','COPD / Pulmonary','Chronic Kidney Disease','Post-Surgical Recovery','CAR-T','Acute Kidney Injury (AKI)','Joint / Knee Replacement','Pneumonitis','Pancreatectomy','Neutropenic Fever','Coronary Artery Disease (CAD)','Lung Transplant','Respiratory Infection - Pediatric','Respiratory Infection - Adult','Pulmonary Home Rehab']
CLINICIANS=['Dr. John Doe','Dr. Aisha Morgan','Dr. Samuel Lee','Dr. Elena Rivera']
US_STATES=['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC']
NOK_RELATIONSHIPS=['Spouse / Partner','Mother','Father','Parent','Daughter','Son','Child','Sister','Brother','Sibling','Grandparent','Grandchild','Aunt','Uncle','Cousin','Guardian','Caregiver','Friend','Emergency Contact','Next of Kin','Other']
# RPM has no universal fixed enrollment duration. These are portfolio defaults only; clinician can change them.
CARE_PLAN_DEFAULTS={p:('Ongoing / clinician-defined',90) for p in CARE_PLANS}
CARE_PLAN_DEFAULTS.update({'Post-Surgical Recovery':('Short-term / clinician-defined',30),'Joint / Knee Replacement':('Short-term / clinician-defined',60),'Pancreatectomy':('Short-term / clinician-defined',60),'Respiratory Infection - Pediatric':('Short-term / clinician-defined',14),'Respiratory Infection - Adult':('Short-term / clinician-defined',14),'Acute Kidney Injury (AKI)':('Clinician-defined',30),'CAR-T':('Clinician-defined',30),'Neutropenic Fever':('Clinician-defined',14)})

SPIROMETRY_PLANS={'COPD / Pulmonary','Pneumonitis','Lung Transplant','Respiratory Infection - Pediatric','Respiratory Infection - Adult','Pulmonary Home Rehab'}

EDUCATION_LIBRARY={
 'Cardiology':[('Know your heart symptoms','Recognize changes in breathing, chest symptoms, swelling, and when to contact your care team.','https://www.nhlbi.nih.gov/health/heart-failure'),('Medicines and daily monitoring','Why taking medicines and tracking symptoms/vitals consistently matters.','https://www.nhlbi.nih.gov/health/heart-failure/living-with')],
 'Cirrhosis / Liver Disease':[('Living with cirrhosis','Daily self-management, medicines, nutrition, and symptoms to report.','https://www.niddk.nih.gov/health-information/liver-disease/cirrhosis'),('Watch for complications','Know why swelling, confusion, bleeding, or infection symptoms need prompt clinical review.','https://www.niddk.nih.gov/health-information/liver-disease/cirrhosis/symptoms-causes')],
 'Hypertension':[('Understanding high blood pressure','Learn why regular BP checks and treatment matter.','https://www.fda.gov/consumers/health-education-resources/hypertension'),('Heart-healthy habits','Review sodium, activity, medicines, tobacco, and alcohol considerations with your care team.','https://www.nhlbi.nih.gov/health/high-blood-pressure/living-with')],
 'Diabetes / CGM':[('Using CGM safely','Understand trends, alerts, sensor care, and when a confirmatory glucose check may be needed.','https://www.niddk.nih.gov/health-information/diabetes/overview/managing-diabetes/continuous-glucose-monitoring'),('Daily diabetes self-care','Medicines, meals, activity, glucose monitoring, and symptoms to report.','https://www.niddk.nih.gov/health-information/diabetes/overview/managing-diabetes')],
 'Heart Failure':[('Daily heart-failure self-check','Track symptoms, weight, swelling, breathing, and medicines.','https://www.nhlbi.nih.gov/health/heart-failure/living-with'),('Know when symptoms change','Learn why worsening breathlessness, swelling, or rapid weight change should be reported.','https://www.nhlbi.nih.gov/health/heart-failure/symptoms')],
 'COPD / Pulmonary':[('What is COPD?','A short overview of COPD symptoms and monitoring.','https://www.nhlbi.nih.gov/health/copd'),('Learn about spirometry','How spirometry measures lung function and why repeatable technique matters.','https://www.nhlbi.nih.gov/health-topics/education-and-awareness/copd-learn-more-breathe-better/copd-videos'),('Pulmonary rehabilitation','Exercise, education, and breathing techniques used in supervised pulmonary rehabilitation.','https://www.nhlbi.nih.gov/health/pulmonary-rehabilitation')],
 'Chronic Kidney Disease':[('Living with CKD','Learn about medicines, BP, nutrition, and follow-up.','https://www.niddk.nih.gov/health-information/kidney-disease/chronic-kidney-disease-ckd/managing'),('Track fluid-related symptoms','Why weight, swelling, breathing, and urine changes can matter to your care team.','https://www.niddk.nih.gov/health-information/kidney-disease/chronic-kidney-disease-ckd/symptoms-causes')],
 'Post-Surgical Recovery':[('Recovery at home','Follow your discharge plan, medicines, activity guidance, wound care, and follow-up instructions.','https://medlineplus.gov/aftersurgery.html'),('When to contact your team','Report concerning fever, wound changes, breathing problems, or worsening symptoms according to your discharge plan.','https://medlineplus.gov/aftersurgery.html')],
 'CAR-T':[('CAR-T treatment basics','A short overview of CAR-T infusion and monitoring after treatment.','https://www.cancer.gov/about-cancer/treatment/types/immunotherapy/t-cell-transfer-therapy'),('Symptoms that require rapid contact','CAR-T can cause serious inflammatory and neurologic side effects; follow your oncology team’s emergency instructions.','https://www.cancer.gov/about-cancer/treatment/types/immunotherapy/t-cell-transfer-therapy')],
 'Acute Kidney Injury (AKI)':[('Understanding acute kidney injury','Learn why kidney function can change quickly and why follow-up labs, medicines, and hydration instructions are individualized.','https://www.niddk.nih.gov/health-information/kidney-disease/acute-kidney-injury'),('Medication and follow-up safety','Review all medicines and follow your clinical team’s instructions for labs, fluids, and follow-up.','https://www.niddk.nih.gov/health-information/kidney-disease/acute-kidney-injury')],
 'Joint / Knee Replacement':[('Recovery after joint replacement','Follow your surgical team’s mobility, pain-control, wound-care, and rehabilitation plan.','https://orthoinfo.aaos.org/en/treatment/total-knee-replacement/'),('Safe movement and rehabilitation','Complete prescribed exercises and report concerning wound or clot-related symptoms promptly.','https://orthoinfo.aaos.org/en/recovery/activities-after-knee-replacement/')],
 'Pneumonitis':[('Understanding pneumonitis','Learn about inflammation of lung tissue, symptoms, and the importance of follow-up.','https://www.mayoclinic.org/diseases-conditions/pneumonitis/symptoms-causes/syc-20352623'),('Track breathing changes','Report worsening cough, breathlessness, fever, or oxygen changes according to your care plan.','https://www.mayoclinic.org/diseases-conditions/pneumonitis/symptoms-causes/syc-20352623')],
 'Pancreatectomy':[('Recovery and nutrition after pancreatic surgery','Follow your surgical team’s nutrition, glucose, enzyme, wound, and activity instructions.','https://www.niddk.nih.gov/health-information/digestive-diseases/pancreatitis/treatment'),('Symptoms to report','Report worsening abdominal pain, fever, vomiting, wound changes, or glucose concerns to your team.','https://www.niddk.nih.gov/health-information/digestive-diseases/pancreatitis/symptoms-causes')],
 'Neutropenic Fever':[('Infection risk during neutropenia','Fever during neutropenia can require urgent medical assessment; follow your oncology team’s temperature and emergency instructions.','https://www.cancer.gov/about-cancer/treatment/side-effects/infection'),('Reducing infection exposure','Review hand hygiene, food safety, and exposure precautions recommended by your oncology team.','https://www.cancer.gov/about-cancer/treatment/side-effects/infection')],
 'Coronary Artery Disease (CAD)':[('Understanding coronary artery disease','Learn how narrowed coronary arteries affect the heart and how treatment reduces risk.','https://www.nhlbi.nih.gov/health/coronary-heart-disease'),('Cardiac rehabilitation','Supervised exercise, education, and risk-factor management can be part of recovery and prevention.','https://www.mayoclinic.org/tests-procedures/cardiac-rehabilitation/about/pac-20385192')],
 'Lung Transplant':[('Daily life after lung transplant','Medicines, infection prevention, rehabilitation, testing, and symptoms to report are central to follow-up.','https://www.mayoclinic.org/care/lung-transplant/process/recovery'),('Pulmonary function monitoring','Your transplant team may use pulmonary function testing and rehabilitation as part of follow-up.','https://www.mayoclinic.org/departments-centers/lung-transplant/sections/overview/ovc-20212476')],
 'Respiratory Infection - Pediatric':[('Caring for a child with a respiratory infection','Monitor breathing, hydration, fever, and activity; follow the child’s clinician instructions.','https://www.cdc.gov/respiratory-viruses/about/index.html'),('Know breathing warning signs','Seek prompt care for breathing difficulty or other concerning symptoms according to pediatric guidance.','https://www.cdc.gov/respiratory-viruses/prevention/precautions-when-sick.html')],
 'Respiratory Infection - Adult':[('Respiratory infection self-care','Monitor symptoms, hydration, breathing, and fever; follow testing and treatment instructions.','https://www.cdc.gov/respiratory-viruses/about/index.html'),('Protect others while sick','Follow current respiratory-virus precautions and your clinician’s guidance.','https://www.cdc.gov/respiratory-viruses/prevention/precautions-when-sick.html')],
 'Pulmonary Home Rehab':[('Pulmonary rehabilitation at home','Practice the breathing and activity plan prescribed by your pulmonary rehabilitation team.','https://www.nhlbi.nih.gov/health/pulmonary-rehabilitation'),('Breathing techniques and activity','Learn safe pacing, breathing techniques, and why regular supervised activity matters.','https://www.nhlbi.nih.gov/health/pulmonary-rehabilitation')]
}

DEMO_PATIENT_SPECS=[
 ('SYN-1005','Amelia Johnson','CAR-T',96,142.0,92),('SYN-1006','Marcus Green','Acute Kidney Injury (AKI)',97,188.0,80),('SYN-1007','Sophia Turner','Joint / Knee Replacement',98,165.0,76),('SYN-1008','Noah Williams','Pneumonitis',93,174.0,96),('SYN-1009','Isabella Martin','Pancreatectomy',97,132.0,84),('SYN-1010','Ethan Davis','Neutropenic Fever',96,156.0,108),('SYN-1011','Olivia Brown','Coronary Artery Disease (CAD)',97,171.0,88),('SYN-1012','Liam Wilson','Lung Transplant',95,149.0,90),('SYN-1013','Ava Thompson','Respiratory Infection - Pediatric',94,82.0,112),('SYN-1014','James Anderson','Respiratory Infection - Adult',92,181.0,102),('SYN-1015','Mia Martinez','Pulmonary Home Rehab',95,158.0,86),('SYN-1016','Lucas Clark','Hypertension',98,190.0,78),('SYN-1017','Emma Lewis','Diabetes / CGM',97,168.0,80),('SYN-1018','Henry Walker','Heart Failure',91,201.0,116),('SYN-1019','Charlotte Hall','COPD / Pulmonary',89,146.0,105),('SYN-1020','Benjamin Young','Chronic Kidney Disease',96,196.0,82),('SYN-1021','Harper King','Post-Surgical Recovery',98,154.0,75)
]
for _pid,_name,_plan,_spo2,_wt,_hr in DEMO_PATIENT_SPECS:
    if _pid not in PATIENTS:
        PATIENTS[_pid]={'name':_name,'clinician':CLINICIANS[int(_pid[-1])%len(CLINICIANS)],'mrn':'SYN-MRN-'+_pid.split('-')[1],'dob':'1970-01-15','care_plan':_plan,'baseline_spo2':max(_spo2,95),'baseline_weight':_wt,'baseline_hr':min(_hr,82),'baseline_fev1':2.40,'address':'100 Demo Way','city':'Austin','state':'TX','zip':'78701','phone':'512-555-'+_pid[-4:],'email':'','insurance':'Demo Health Plan','member_id':'DEMO-'+_pid[-4:],'next_of_kin':'Synthetic Family Contact','nok_relationship':'Family','nok_phone':'512-555-0199','program_duration':CARE_PLAN_DEFAULTS.get(_plan,('Clinician-defined',90))[0],'review_days':CARE_PLAN_DEFAULTS.get(_plan,('Clinician-defined',90))[1]}

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
    st.session_state.thresholds[pid]={'spo2_min':92,'spo2_max':100,'hr_min':50,'hr_max':110,'weight_min':80.0,'weight_max':350.0,'sys_min':90,'sys_max':160,'dia_min':50,'dia_max':100,'rr_min':10,'rr_max':24,'temp_min':34.0,'temp_max':38.0,'glucose_min':70,'glucose_max':180,'fev1_pct_min':80}
    common=[{'device':'KardiaMobile 6L','type':'ECG · individual','connected':True,'battery':100,'wifi':True},{'device':'Dexcom G7 CGM','type':'Glucose · continuous','connected':True,'battery':100,'wifi':True},{'device':'RPM Tablet','type':'Gateway','connected':True,'battery':100,'wifi':True}]
    if p['care_plan']=='Cardiology': care=[{'device':'Everion','type':'Continuous · HR / SpO₂ / RR / skin temperature','connected':True,'battery':100,'wifi':True},{'device':'Welch Allyn BP Device','type':'Individual · BP','connected':True,'battery':100,'wifi':True},{'device':'Welch Allyn Weighing Device','type':'Individual · weight','connected':True,'battery':100,'wifi':True}]
    else: care=[{'device':'Nonin Pulse Oximeter','type':'Individual · SpO₂','connected':True,'battery':100,'wifi':True},{'device':'Welch Allyn BP Device','type':'Individual · BP / HR','connected':True,'battery':100,'wifi':True},{'device':'Welch Allyn Weighing Device','type':'Individual · weight','connected':True,'battery':100,'wifi':True},{'device':'Everion','type':'Wearable · RR / skin temperature','connected':True,'battery':100,'wifi':True}]
    
    if p['care_plan'] in SPIROMETRY_PLANS: common.insert(0,{'device':'Home Spirometer','type':'Individual · FEV1 / FVC / FEV1:FVC / PEF','connected':True,'battery':88,'wifi':True})
    st.session_state.devices[pid]=care+common

def patient_creation_panel(origin,key):
    st.subheader('➕ Create / Add New Patient')
    st.caption(f'Entry point: {origin}. Both entry points use the same demo Master Patient Index and duplicate-check service. Fields marked * are required.')
    with st.form(f'create_patient_{key}',clear_on_submit=False):
        c1,c2,c3=st.columns(3)
        first=c1.text_input('First name :red[*]')
        last=c2.text_input('Last name :red[*]')
        dob=c3.date_input('Date of birth (MM/DD/YYYY) :red[*]',value=datetime(1970,1,1).date(),max_value=datetime.now().date(),format='MM/DD/YYYY')
        age=max(0,(datetime.now().date()-dob).days//365); st.caption(f'Calculated age: {age}')
        c1,c2,c3=st.columns(3)
        phone=c1.text_input('Phone number :red[*]',placeholder='512-555-0123')
        email=c2.text_input('Email (optional)',placeholder='patient@example.com')
        clinician=c3.selectbox('Assigned clinician :red[*]',CLINICIANS)
        address=st.text_input('Street address :red[*]',placeholder='123 Main St')
        c1,c2,c3=st.columns(3)
        city=c1.text_input('City :red[*]',placeholder='Austin')
        state=c2.selectbox('State :red[*]',US_STATES,index=US_STATES.index('TX'))
        zipcode=c3.text_input('ZIP code :red[*]',placeholder='78701 or 78701-1234',max_chars=10)
        care=st.selectbox('RPM care plan :red[*]',CARE_PLANS)
        default_label,default_days=CARE_PLAN_DEFAULTS[care]
        c1,c2=st.columns(2)
        duration=c1.selectbox('Program duration / enrollment plan :red[*]',['Ongoing / clinician-defined','30 days','60 days','90 days','180 days','12 months','Custom'])
        review_days=c2.number_input('Next care-plan review in (days) :red[*]',min_value=7,max_value=365,value=default_days,step=7)
        st.caption('RPM can be used for acute or chronic conditions; there is no universal fixed enrollment duration. The clinician sets duration and review timing based on the care plan.')
        c1,c2=st.columns(2); insurance=c1.text_input('Insurance plan :red[*]'); member=c2.text_input('Insurance member ID :red[*]')
        st.markdown('**Next of kin / emergency contact**')
        c1,c2,c3=st.columns(3)
        nok=c1.text_input('Contact name :red[*]')
        rel=c2.selectbox('Relationship to patient :red[*]',NOK_RELATIONSHIPS)
        nokphone=c3.text_input('Contact phone :red[*]',placeholder='512-555-0199')
        submitted=st.form_submit_button('Create Patient',type='primary')
    if submitted:
        errors=[]
        required={'First name':first,'Last name':last,'Phone':phone,'Street address':address,'City':city,'ZIP code':zipcode,'Insurance plan':insurance,'Insurance member ID':member,'Next-of-kin name':nok,'Next-of-kin phone':nokphone}
        errors += [f'{k} is required.' for k,v in required.items() if not str(v).strip()]
        if city.strip() and not re.fullmatch(r"[A-Za-z .'-]{2,60}",city.strip()): errors.append('City should contain letters, spaces, apostrophes, periods, or hyphens only.')
        if zipcode.strip() and not re.fullmatch(r'\d{5}(-\d{4})?',zipcode.strip()): errors.append('ZIP code must be 5 digits or ZIP+4 (for example 78701 or 78701-1234).')
        if phone.strip() and len(re.sub(r'\D','',phone)) != 10: errors.append('Patient phone number must contain 10 digits.')
        if nokphone.strip() and len(re.sub(r'\D','',nokphone)) != 10: errors.append('Next-of-kin phone number must contain 10 digits.')
        if dob > datetime.now().date(): errors.append('Date of birth cannot be in the future.')
        if errors:
            for err in errors: st.error(err)
            return
        exact,possible=find_duplicate(first,last,dob,phone)
        if exact:
            ep=PATIENTS[exact[0]]; st.error(f"Duplicate prevented. Matching patient already exists: {ep['name']} · {ep['mrn']}. Match criteria: normalized legal name + DOB + phone.")
        elif possible:
            ep=PATIENTS[possible[0]]; st.warning(f"Possible duplicate found: {ep['name']} · {ep['mrn']} has the same normalized name + DOB. Creation is blocked in this demo pending identity review.")
        else:
            pid,mrn=next_patient_ids(); PATIENTS[pid]={'name':f'{first.strip()} {last.strip()}','clinician':clinician,'mrn':mrn,'dob':str(dob),'care_plan':care,'program_duration':duration,'review_days':int(review_days),'enrollment_date':datetime.now().date().isoformat(),'next_review_date':(datetime.now().date()+timedelta(days=int(review_days))).isoformat(),'address':address,'city':city,'state':state,'zip':zipcode,'phone':phone,'email':email,'insurance':insurance,'member_id':member,'next_of_kin':nok,'nok_relationship':rel,'nok_phone':nokphone,'baseline_spo2':97,'baseline_weight':170.0,'baseline_hr':75}
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
if 'patient_samples' not in st.session_state: st.session_state.patient_samples=[]
if 'last_ingested' not in st.session_state: st.session_state.last_ingested=None
if 'thresholds' not in st.session_state:
    st.session_state.thresholds={pid:{'spo2_min':92,'spo2_max':100,'hr_min':50,'hr_max':110,'weight_min':p['baseline_weight']-5,'weight_max':p['baseline_weight']+5,'sys_min':90,'sys_max':160,'dia_min':50,'dia_max':100,'rr_min':10,'rr_max':24,'temp_min':34.0,'temp_max':38.0,'glucose_min':70,'glucose_max':180,'fev1_pct_min':80} for pid,p in PATIENTS.items()}
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
if 'education_assignments' not in st.session_state: st.session_state.education_assignments=[]
if 'questionnaire_assignments' not in st.session_state: st.session_state.questionnaire_assignments=[]

events=st.session_state.events
# Ensure every demo care pathway has at least one patient with 7 days of normal/alert examples.
for _pid,_name,_plan,_spo2,_wt,_hr in DEMO_PATIENT_SPECS:
    if not any(e['patient_id']==_pid for e in events):
        for _d in range(7):
            _alert=(_d==6 and _pid in {'SYN-1005','SYN-1008','SYN-1010','SYN-1012','SYN-1013','SYN-1014','SYN-1018','SYN-1019'})
            _base=PATIENTS[_pid]; _ts=(datetime.now()-timedelta(days=6-_d)).replace(hour=8,minute=20,second=0,microsecond=0)
            _fev1=2.40-(0.65 if _alert and _plan in SPIROMETRY_PLANS else .03*_d)
            _fvc=3.20-(0.45 if _alert and _plan in SPIROMETRY_PLANS else .02*_d)
            _eid=f'EVT-{len(events)+1:03d}'
            events.append({'event_id':_eid,'patient_id':_pid,'timestamp':_ts.isoformat(),'ecg':'Tachycardia' if _alert and _plan in {'CAR-T','Neutropenic Fever','Heart Failure','Coronary Artery Disease (CAD)'} else 'Normal Sinus Rhythm','ecg_hr':_hr if _alert else _base['baseline_hr'],'spo2':_spo2 if _alert else _base['baseline_spo2'],'weight':_wt+(4 if _alert and _plan in {'Heart Failure','Acute Kidney Injury (AKI)','Chronic Kidney Disease'} else 0),'rr':28 if _alert and _plan in SPIROMETRY_PLANS else 17,'skin_temp':38.4 if _alert and _plan in {'CAR-T','Neutropenic Fever','Respiratory Infection - Pediatric','Respiratory Infection - Adult'} else 36.6,'glucose':205 if _alert and _plan in {'Diabetes / CGM','Pancreatectomy'} else 112,'sys':88 if _alert and _plan=='CAR-T' else 126,'dia':58 if _alert and _plan=='CAR-T' else 78,'sob':bool(_alert and _plan in SPIROMETRY_PLANS),'chest':bool(_alert and _plan=='Coronary Artery Disease (CAD)'),'dizzy':False,'meds':True,'questionnaire':{},'pdf_ok':True,'source':'Device','fev1':_fev1,'fvc':_fvc,'fev1_fvc':(_fev1/_fvc*100),'pef':360 if _alert and _plan in SPIROMETRY_PLANS else 450,'fev1_pct_baseline':_fev1/_base.get('baseline_fev1',2.4)*100,'spirometry_quality':'Acceptable simulated maneuver'})

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
    if e.get('fev1') is not None and PATIENTS[e['patient_id']]['care_plan'] in SPIROMETRY_PLANS and e.get('fev1_pct_baseline',100) < st.session_state.thresholds[e['patient_id']].get('fev1_pct_min',80): reasons.append(f"FEV1 is {e.get('fev1_pct_baseline',0):.0f}% of synthetic personal baseline — below configured {st.session_state.thresholds[e['patient_id']].get('fev1_pct_min',80)}% limit"); score+=2
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

def trend_chart(pid, field, title, unit, min_key=None, max_key=None, display_unit=None):
    es=patient_events(pid)[-7:]; x=[pd.to_datetime(e['timestamp']) for e in es]; raw=[e.get(field) for e in es]
    src=[e.get('source','Device') for e in es]; symbols=['circle' if 'Device' in a else 'diamond' for a in src]
    t=st.session_state.thresholds[pid]; raw_lo=t.get(min_key) if min_key else None; raw_hi=t.get(max_key) if max_key else None
    def cv(v):
        if v is None: return v
        if field=='weight' and display_unit=='kg': return v/2.2046226218
        if field=='skin_temp' and display_unit=='°F': return v*9/5+32
        return v
    y=[cv(v) for v in raw]; lo=cv(raw_lo); hi=cv(raw_hi)
    colors=['#D62728' if (raw_lo is not None and v<raw_lo) or (raw_hi is not None and v>raw_hi) else ('#7B2CBF' if 'Manual' in src[i] else '#2878B5') for i,v in enumerate(raw)]
    custom=[]
    for e in es:
        device=source_device(PATIENTS[pid]['care_plan'], field, e.get('source','Device'))
        custom.append([e['event_id'],e.get('source','Device'),device,e['ecg']])
    shown_unit=display_unit or unit
    labels=[f'{v:.1f}' if isinstance(v,float) else str(v) for v in y]
    fig=go.Figure(go.Scatter(x=x,y=y,mode='lines+markers+text',text=labels,textposition='top center',line={'color':'#7A7A7A'},marker={'size':11,'symbol':symbols,'color':colors},customdata=custom,hovertemplate='<b>Value:</b> %{y:.1f} '+shown_unit+'<br><b>Timestamp:</b> %{x|%b %d, %Y %I:%M %p}<br><b>Entry source:</b> %{customdata[1]}<br><b>Device:</b> %{customdata[2]}<br><b>Event:</b> %{customdata[0]}<br><b>ECG:</b> %{customdata[3]}<extra></extra>'))
    if lo is not None: fig.add_hline(y=lo,line_dash='dash',line_color='#008C95',annotation_text='Min threshold')
    if hi is not None: fig.add_hline(y=hi,line_dash='dash',line_color='#008C95',annotation_text='Max threshold')
    fig.update_layout(title=title,height=310,margin=dict(l=20,r=20,t=55,b=20),yaxis_title=shown_unit,hovermode='closest')
    st.plotly_chart(fig,use_container_width=True)
    st.caption('● Device-generated   ◆ Manual clinician-assisted   🔵 Device-generated in-range   🟣 Manual clinician-assisted in-range   🔴 Out-of-threshold reading   Teal dashed lines = configured min/max limits')

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
    common_meds=('meds','Did you take medications as directed today?')
    templates={
      'Cardiology':[('sob','Shortness of breath?'),('chest','Chest discomfort?'),('palpitations','Palpitations or rapid heartbeat?'),('dizzy','Dizziness or lightheadedness?'),('swelling','New/increased swelling in feet or ankles?'),('fatigue','Unusual fatigue?'),common_meds],
      'Cirrhosis / Liver Disease':[('abdominal_swelling','Increased abdominal swelling?'),('leg_swelling','New/increased leg or ankle swelling?'),('sob','Shortness of breath?'),('nausea','Nausea or vomiting?'),('appetite','Reduced appetite?'),('confusion','New confusion or difficulty concentrating?'),('sleepiness','Unusual sleepiness?'),('bleeding','Blood in vomit or stool reported?'),common_meds],
      'Hypertension':[('headache','New or severe headache?'),('dizzy','Dizziness or lightheadedness?'),('vision','New vision changes?'),('chest','Chest discomfort?'),('sob','Shortness of breath?'),common_meds],
      'Diabetes / CGM':[('hypo_symptoms','Shaking, sweating, confusion, or other low-glucose symptoms?'),('hyper_symptoms','Increased thirst or urination?'),('nausea','Nausea or vomiting?'),('food','Were you able to eat as planned today?'),('sensor_issue','Any CGM sensor or connectivity issue?'),common_meds],
      'Heart Failure':[('sob','Shortness of breath?'),('orthopnea','More difficulty breathing while lying flat?'),('swelling','New/increased leg or ankle swelling?'),('fatigue','Unusual fatigue?'),('weight_concern','Do you feel your weight/fluid retention increased?'),('chest','Chest discomfort?'),common_meds],
      'COPD / Pulmonary':[('sob','More shortness of breath than usual?'),('cough','New or increased cough?'),('sputum','Change in mucus/sputum amount or color?'),('wheeze','More wheezing than usual?'),('feverish','Feeling feverish or chilled?'),('rescue_inhaler','Needed rescue inhaler more than usual?'),common_meds],
      'Chronic Kidney Disease':[('swelling','New/increased swelling?'),('sob','Shortness of breath?'),('urine','Noticeable change in urine output?'),('nausea','Nausea or vomiting?'),('fatigue','Unusual fatigue?'),('appetite','Reduced appetite?'),common_meds],
      'Post-Surgical Recovery':[('pain','Pain worse than expected today?'),('feverish','Feeling feverish or chilled?'),('wound_redness','Increasing redness around incision/wound?'),('drainage','New/increased wound drainage?'),('swelling','New/increased swelling?'),('mobility','Difficulty with expected walking/activity?'),common_meds],
      'CAR-T':[('feverish','Fever or chills?'),('sob','Shortness of breath?'),('dizzy','Dizziness or faintness?'),('confusion','New confusion, trouble speaking, or unusual behavior?'),('headache','New or worsening headache?'),('nausea','Nausea or vomiting?'),common_meds],
      'Acute Kidney Injury (AKI)':[('urine','Reduced or noticeably changed urine output?'),('swelling','New swelling?'),('sob','Shortness of breath?'),('nausea','Nausea or vomiting?'),('confusion','New confusion or unusual sleepiness?'),('intake','Difficulty keeping up with the fluid plan provided by your care team?'),common_meds],
      'Joint / Knee Replacement':[('pain','Pain worse than expected?'),('wound_redness','Increasing incision redness/warmth?'),('drainage','New or increased drainage?'),('feverish','Fever or chills?'),('calf','New calf pain or swelling?'),('mobility','Difficulty completing prescribed walking/exercises?'),common_meds],
      'Pneumonitis':[('sob','More shortness of breath than usual?'),('cough','New or worsening dry cough?'),('feverish','Fever or chills?'),('chest','Chest discomfort?'),('activity','More difficulty with normal activity?'),common_meds],
      'Pancreatectomy':[('pain','Increasing abdominal pain?'),('nausea','Nausea or vomiting?'),('feverish','Fever or chills?'),('wound_redness','Incision redness or drainage?'),('appetite','Difficulty eating or drinking?'),('glucose_symptoms','Symptoms of unusually high or low glucose?'),common_meds],
      'Neutropenic Fever':[('feverish','Fever or chills?'),('sore_throat','New sore throat or mouth sores?'),('cough','New cough?'),('urinary','Burning or pain with urination?'),('diarrhea','New diarrhea?'),('line_site','Redness, pain, or drainage around a line/port?'),common_meds],
      'Coronary Artery Disease (CAD)':[('chest','Chest pressure, pain, or tightness?'),('sob','Shortness of breath?'),('palpitations','Palpitations?'),('dizzy','Dizziness or faintness?'),('fatigue','Unusual fatigue with activity?'),common_meds],
      'Lung Transplant':[('sob','More shortness of breath than your usual baseline?'),('cough','New or increased cough?'),('feverish','Fever or chills?'),('sputum','Change in sputum?'),('spirometry_change','Home spirometry lower than your usual baseline?'),('med_issue','Any problem taking anti-rejection medicines as scheduled?'),common_meds],
      'Respiratory Infection - Pediatric':[('feverish','Fever today?'),('breathing','Breathing faster or harder than usual?'),('cough','Cough worse today?'),('hydration','Drinking less or fewer wet diapers/urination?'),('activity','Less alert or active than usual?'),('wheeze','Wheezing or noisy breathing?')],
      'Respiratory Infection - Adult':[('feverish','Fever or chills?'),('sob','Shortness of breath?'),('cough','Cough worse today?'),('sputum','Change in mucus/sputum?'),('chest','Chest discomfort?'),('hydration','Difficulty drinking enough fluids?'),common_meds],
      'Pulmonary Home Rehab':[('sob','Breathlessness worse than your usual baseline?'),('exercise','Were you able to complete today’s prescribed rehab activity?'),('dizzy','Dizziness during exercise?'),('chest','Chest discomfort during exercise?'),('cough','New or increased cough?'),('oxygen','Any issue using prescribed oxygen or respiratory equipment?'),common_meds]
    }
    return templates.get(plan,templates['Cardiology'])

def spirometry_pdf_bytes(e):
    p=PATIENTS[e['patient_id']]; buf=io.BytesIO(); c=canvas.Canvas(buf,pagesize=letter); W,H=letter
    fev1=float(e.get('fev1') or 0); fvc=float(e.get('fvc') or 0); ratio=(fev1/fvc if fvc else 0); pef=float(e.get('pef') or 0)
    # Synthetic reference fields are intentionally illustrative; this portfolio does not calculate clinical reference equations.
    pred_fev1=float(p.get('baseline_fev1',max(fev1,2.4))); pred_fvc=max(3.2,pred_fev1/0.78); lln_fev1=pred_fev1*0.80; lln_fvc=pred_fvc*0.80; lln_ratio=0.70
    def z(actual,pred): return (actual-pred)/(max(pred*.12,.15))
    c.setFont('Helvetica-Bold',10); c.drawString(.45*inch,H-.4*inch,f"Patient: {p['name']}   |   MRN: {p['mrn']}   |   DOB: {p['dob']}")
    c.setFont('Helvetica-Bold',15); c.drawString(.45*inch,H-.75*inch,'Synthetic Home Spirometry Result')
    c.setFont('Helvetica',8.5); c.drawString(.45*inch,H-.98*inch,'Portfolio demonstration patterned after standardized PFT-report concepts; synthetic values/reference ranges; not for diagnosis.')
    c.drawString(.45*inch,H-1.18*inch,f"Recording: {e['event_id']}   Date/time: {e['timestamp'][:16].replace('T',' ')}   Quality: {e.get('spirometry_quality','Simulated maneuver')}")
    # table
    y=H-1.62*inch; cols=[.45,1.75,2.55,3.35,4.15,5.0,6.0]; headers=['Parameter','Unit','Measured','LLN*','Z-score*','% predicted*','Personal baseline']
    c.setFont('Helvetica-Bold',8.5)
    for x,h in zip(cols,headers): c.drawString(x*inch,y,h)
    c.line(.45*inch,y-.08*inch,7.7*inch,y-.08*inch); y-=.30*inch
    rows=[('FEV1','L',fev1,lln_fev1,z(fev1,pred_fev1),100*fev1/pred_fev1,100*fev1/pred_fev1),('FVC','L',fvc,lln_fvc,z(fvc,pred_fvc),100*fvc/pred_fvc,None),('FEV1/FVC','ratio',ratio,lln_ratio,z(ratio,.78),None,None),('PEF','L/min',pef,None,None,None,None)]
    c.setFont('Helvetica',8.5)
    for name,unit,actual,lln,zv,pct,base in rows:
        vals=[name,unit,f'{actual:.2f}' if name!='PEF' else f'{actual:.0f}',f'{lln:.2f}' if lln is not None else '—',f'{zv:.2f}' if zv is not None else '—',f'{pct:.0f}%' if pct is not None else '—',f'{base:.0f}%' if base is not None else '—']
        for x,v in zip(cols,vals): c.drawString(x*inch,y,str(v))
        y-=.25*inch
    c.setFont('Helvetica-Oblique',7.5); c.drawString(.45*inch,y-.03*inch,'* Synthetic illustrative reference fields only; no GLI/clinical reference equation is calculated in this portfolio prototype.')
    # Flow-volume loop
    fy=H-4.25*inch; fx=.7*inch; fw=3.0*inch; fh=1.65*inch
    c.setFont('Helvetica-Bold',9); c.drawString(fx,fy+fh+.16*inch,'Flow–Volume Loop (synthetic)')
    c.line(fx,fy,fx+fw,fy); c.line(fx,fy-.65*inch,fx,fy+fh)
    c.setFont('Helvetica',7); c.drawString(fx+fw-.45*inch,fy-.16*inch,'Volume (L)'); c.saveState(); c.translate(fx-.18*inch,fy+.25*inch); c.rotate(90); c.drawString(0,0,'Flow (L/s)'); c.restoreState()
    pts=[]
    for i in range(100):
        frac=i/99; vol=fvc*frac; flow=(pef/60.0)*(1-math.exp(-frac*28))*math.exp(-frac*2.0); pts.append((fx+(vol/max(fvc,1))*fw,fy+(flow/max(pef/60.0,1))*fh))
    for a,b in zip(pts[:-1],pts[1:]): c.line(a[0],a[1],b[0],b[1])
    insp=[]
    for i in range(100):
        frac=i/99; vol=fvc*(1-frac); flow=-0.45*(pef/60.0)*math.sin(math.pi*frac); insp.append((fx+(vol/max(fvc,1))*fw,fy+(flow/max(pef/60.0,1))*fh))
    for a,b in zip(insp[:-1],insp[1:]): c.line(a[0],a[1],b[0],b[1])
    # Volume-time curve
    tx=4.35*inch; ty=fy; tw=3.0*inch; th=1.65*inch
    c.setFont('Helvetica-Bold',9); c.drawString(tx,ty+th+.16*inch,'Volume–Time Curve (synthetic)')
    c.line(tx,ty,tx+tw,ty); c.line(tx,ty,tx,ty+th); c.setFont('Helvetica',7); c.drawString(tx+tw-.35*inch,ty-.16*inch,'Time (s)'); c.saveState(); c.translate(tx-.18*inch,ty+.25*inch); c.rotate(90); c.drawString(0,0,'Volume (L)'); c.restoreState()
    vt=[]
    for i in range(121):
        t=6*i/120; vol=fvc*(1-math.exp(-t/0.85)); vt.append((tx+(t/6)*tw,ty+(vol/max(fvc,1))*th))
    for a,b in zip(vt[:-1],vt[1:]): c.line(a[0],a[1],b[0],b[1])
    c.setFont('Helvetica-Bold',9); c.drawString(.45*inch,1.15*inch,'Workflow flag:')
    flag='Review — FEV1 below configured personal-baseline alert limit.' if e.get('fev1_pct_baseline',100)<st.session_state.thresholds[e['patient_id']].get('fev1_pct_min',80) else 'Routine monitoring — no configured FEV1 baseline exception.'
    c.setFont('Helvetica',8.5); c.drawString(1.25*inch,1.15*inch,flag)
    c.setFont('Helvetica-Oblique',7.5); c.drawString(.45*inch,.55*inch,'SYNTHETIC DATA ONLY | Human clinical review required | Report design is original portfolio UI, not a copied clinical report.')
    c.save(); return buf.getvalue()

def priority_badge(priority):
    return {'HIGH':'🔴 HIGH','MEDIUM':'🟡 MEDIUM','LOW':'🟢 LOW','AWAITING DATA':'⚪ AWAITING DATA'}.get(priority, priority)

def priority_rank(priority):
    return {'HIGH':1,'MEDIUM':2,'LOW':3,'AWAITING DATA':4}.get(priority,9)

def patient_name_matches(pid, query):
    q=(query or '').strip().lower()
    if not q: return True
    p=PATIENTS[pid]
    hay=' '.join([p.get('name',''),p.get('mrn',''),p.get('care_plan',''),p.get('clinician','')]).lower()
    return q in hay

def patient_picker(label,key,query_label='Search patient by name, MRN, care plan, or clinician'):
    q=st.text_input('🔎 '+query_label,key=key+'_search',placeholder='Start typing a patient last name, MRN, care plan, or clinician…')
    ids=[pid for pid in PATIENTS if patient_name_matches(pid,q)]
    if not ids:
        st.warning('No matching patients. Clear or change the search text.')
        ids=list(PATIENTS)
    default_pid=st.session_state.get(key+'_preferred')
    idx=ids.index(default_pid) if default_pid in ids else 0
    return st.selectbox(label,ids,index=idx,format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']} · {PATIENTS[x]['care_plan']}",key=key+'_select')

def show_pdf_inline(pdf_bytes,height=760):
    try:
        doc=fitz.open(stream=pdf_bytes,filetype='pdf')
        for i,page in enumerate(doc):
            pix=page.get_pixmap(matrix=fitz.Matrix(1.45,1.45),alpha=False)
            st.image(pix.tobytes('png'),caption=f'Result PDF · page {i+1}',use_container_width=True)
    except Exception:
        st.warning('Inline preview is unavailable in this browser. Use Download PDF below.')

def education_for(plan): return EDUCATION_LIBRARY.get(plan,[])

# --- V3.0 demo authentication / role-based navigation ---
DEMO_ACCOUNTS={
 'Patient':{'password':'Patient Password','role':'Patient','description':'Own patient experience, daily tasks, education, messages and results.'},
 'Clinician':{'password':'Clinician Password','role':'Clinician / RPM Nurse','description':'Assigned-patient Command Center, Patient 360, interventions, education/questionnaires and communications.'},
 'Provider':{'password':'Provider Password','role':'Provider / Physician','description':'Clinical review, escalations, trends/reports and intervention review.'},
 'RPM Admin':{'password':'RPM Admin Password','role':'RPM Administrator','description':'Enrollment, assignments, care pathways and operational configuration.'},
 'Integrations':{'password':'Integrations Password','role':'Integrations / Support','description':'Integration Hub, device/interface status, EHR delivery, documents and lineage troubleshooting.'},
 'Admin':{'password':'ADMIN','role':'Portfolio Administrator','description':'Full portfolio access, including Logins & Roles.'}}
if 'auth_user' not in st.session_state: st.session_state.auth_user='Admin'
st.markdown('<style>[data-testid="stMetricLabel"] p{font-size:1rem!important;font-weight:700!important}[data-testid="stMetricValue"]{font-size:1.45rem!important;font-weight:600!important}.small-trend-title{font-size:1.05rem;font-weight:700;margin-top:.35rem}.role-chip{font-size:.88rem;font-weight:600}</style>',unsafe_allow_html=True)
def login_screen():
    st.title('🫀 RPM Connected Care AI Platform · v3.0')
    st.subheader('🔐 Secure Demo Sign In')
    st.info('Portfolio Demonstration Environment — all patients, credentials, measurements and workflows are synthetic. Demo authentication illustrates RBAC concepts and is not production healthcare security.')
    u=st.text_input('Username'); pw=st.text_input('Password',type='password')
    if st.button('Sign in',type='primary'):
        acct=DEMO_ACCOUNTS.get(u)
        if acct and pw==acct['password']:
            st.session_state.auth_user=u; st.session_state.selected_menu='1 · Today / Care Plan' if u=='Patient' else ('9 · Integration Hub / API' if u=='Integrations' else '4 · Clinical Command Center & Action Queue'); st.rerun()
        else: st.error('Invalid demo username or password.')
if not st.session_state.get('auth_user'): login_screen(); st.stop()
CURRENT_USER=st.session_state.auth_user; CURRENT_ROLE=DEMO_ACCOUNTS[CURRENT_USER]['role']
st.title('🫀 RPM Connected Care AI Platform · v3.0')
st.caption(f'Patient Experience • Clinical Operations • Integration • AI & Product • 100% synthetic portfolio data • Signed in as {CURRENT_USER} ({CURRENT_ROLE})')
st.info('Portfolio prototype only. It does not diagnose, treat, or provide medical advice. ECG classifications are device-reported inputs; clinical decisions remain human-in-the-loop.')
patient_menu=['1 · Today / Care Plan','2 · Patient Home & Daily Check-In','3 · Communication Center','3A · Education Center']
clinical_menu=['4 · Clinical Command Center & Action Queue','4A · Education & Questionnaire Library','5 · Patient 360 & Trends','6 · Clinician Interventions','7 · Care Coordination']
integration_menu=['8 · ECG & Spirometry Documents','9 · Integration Hub / API','10 · Mock EHR','11 · Patient Identity & Duplicate Prevention','12 · Data Lineage & Audit']
ai_menu=['13 · AI Agent Center','14 · Care Pathway Engine','15 · Architecture & Product']
if CURRENT_USER=='Admin': ai_menu.append('15A · Logins & Roles')
if 'selected_menu' not in st.session_state:
    st.session_state.selected_menu=patient_menu[0]

def nav_group(title, items):
    st.sidebar.markdown(f'### {title}')
    for item in items:
        active=st.session_state.selected_menu==item
        label=('▸ ' if active else '') + item
        if st.sidebar.button(label,key='nav_'+item,use_container_width=True,type='primary' if active else 'secondary'):
            st.session_state.selected_menu=item
            st.rerun()

if CURRENT_USER=='Patient': nav_group('👤 PATIENT EXPERIENCE',patient_menu)
elif CURRENT_USER=='Integrations': nav_group('🔗 INTEGRATION',integration_menu)
elif CURRENT_USER in ['Clinician','Provider']:
    nav_group('🩺 CLINICAL EXPERIENCE',clinical_menu); nav_group('🔗 INTEGRATION',[x for x in integration_menu if x.startswith(('8 ·','10 ·','12 ·'))])
elif CURRENT_USER=='RPM Admin':
    nav_group('👤 PATIENT EXPERIENCE',patient_menu); nav_group('🩺 CLINICAL EXPERIENCE',clinical_menu); nav_group('🔗 INTEGRATION',integration_menu); nav_group('🤖 AI & PRODUCT',['14 · Care Pathway Engine','15 · Architecture & Product'])
else:
    nav_group('👤 PATIENT EXPERIENCE',patient_menu); nav_group('🩺 CLINICAL EXPERIENCE',clinical_menu); nav_group('🔗 INTEGRATION',integration_menu); nav_group('🤖 AI & PRODUCT',ai_menu)
st.sidebar.divider(); st.sidebar.markdown(f'<span class="role-chip">Signed in as: {CURRENT_USER}<br>{CURRENT_ROLE}</span>',unsafe_allow_html=True)
if st.sidebar.button('Sign out',use_container_width=True): st.session_state.auth_user=None; st.rerun()
menu=st.session_state.selected_menu

if menu.startswith('1 ·'):
    st.header('🏠 Today / Care Plan')
    st.caption('Patient-facing daily worklist: what is due, what is complete, device readiness, and how to contact the care team.')
    pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['care_plan']}",key='today_patient')
    p=PATIENTS[pid]; es=patient_events(pid); latest=es[-1] if es else None
    st.subheader(f"Good day, {p['name']}")
    st.write(f"**Care plan:** {p['care_plan']}  |  **Assigned clinician:** {p['clinician']}  |  **Program:** {p.get('program_duration','Ongoing / clinician-defined')}  |  **Next review:** {p.get('next_review_date','Clinician-defined')}")
    submitted_today=bool(latest and latest['timestamp'][:10]==datetime.now().date().isoformat())
    _edu=[a for a in st.session_state.education_assignments if a['patient_id']==pid and not a.get('completed',False)]; _adhocq=[a for a in st.session_state.questionnaire_assignments if a['patient_id']==pid and not a.get('completed',False)]; tasks=[('Connected-device readings',submitted_today),('Daily care-plan questionnaire',submitted_today),('Medication check-in',submitted_today),('ECG when scheduled/requested',submitted_today and latest.get('ecg') not in [None,'Not collected']),('Assigned education',len(_edu)==0),('Ad-hoc questionnaire',len(_adhocq)==0),('Review care-team messages',not any(m['patient_id']==pid and m['sender']=='Clinician' and not m.get('read',False) for m in st.session_state.messages))]
    done=sum(int(x[1]) for x in tasks); st.progress(done/len(tasks),text=f'{done} of {len(tasks)} daily tasks complete')
    for task,ok in tasks: st.write(('✅' if ok else '○')+' '+task)
    st.subheader('Device readiness')
    for d in st.session_state.devices.get(pid,[]):
        batt=d.get('battery',0); icon='🟢' if batt>=60 else ('🟡' if batt>=25 else '🔴'); conn='Connected' if d.get('connected') else 'Disconnected'; wifi='📶' if d.get('wifi') else '⚠️ Offline'
        st.write(f"{icon} **{d['device']}** — {conn} · Battery {batt}% · {wifi} · {d['type']}")
    st.info('Use **Patient Home & Daily Check-In** to simulate today’s measurements, questionnaire, ECG, or requested patient sample. Use **Communication Center** for chat/video simulation.')

elif menu.startswith('2 ·'):
    st.header('📱 Patient Home & Daily Check-In')
    st.info('PATIENT-HOME SIMULATOR — This page simulates a patient tablet/app receiving connected-device readings and the patient completing today’s care-plan questionnaire. Clinician-assisted entry is available for missed submissions.')
    pid=patient_picker('Synthetic patient','home_patient')
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
    fev1=fvc=pef=None
    if p['care_plan'] in SPIROMETRY_PLANS:
        st.subheader('🫁 Home Spirometry')
        sc1,sc2,sc3=st.columns(3); fev1=sc1.number_input('FEV1 (L)',0.3,6.0,float(p.get('baseline_fev1',2.4)),step=.05); fvc=sc2.number_input('FVC (L)',0.5,8.0,3.2,step=.05); pef=sc3.number_input('PEF (L/min)',50,800,450); st.caption('FEV1/FVC and percent of the synthetic personal FEV1 baseline are calculated automatically. These demo values are not diagnostic thresholds.')
    entered_by=''
    if mode.startswith('Clinician'): entered_by=st.selectbox('Clinician entering patient-reported data',['Dr. John Doe','Dr. Aisha Morgan','Dr. Samuel Lee','RPM Nurse - Demo'])
    st.caption('Save the readings here before moving on. This creates a NEW timestamped RPM event, preserves history, updates trends, evaluates workflow alerts, and prepares the EHR-ready payload.')
    if st.button("📤 Submit & Save Today's Readings" if mode.startswith('Patient') else '☎️ Save Clinician-Assisted Readings',type='primary'):
        nums=[int(x['event_id'].split('-')[1]) for x in events]; eid=f"EVT-{max(nums)+1:03d}"; source='Device' if mode.startswith('Patient') else f'Manual - {entered_by} via outreach'
        e={'event_id':eid,'patient_id':pid,'timestamp':datetime.now().replace(microsecond=0).isoformat(),'ecg':ecg,'ecg_hr':int(hr),'spo2':int(spo2),'weight':float(wt),'rr':int(rr),'skin_temp':float(skin_temp),'glucose':int(glucose),'sys':int(sys),'dia':int(dia),'sob':False,'chest':False,'dizzy':False,'meds':True,'questionnaire':{},'pdf_ok':pdf_ok,'source':source,'fev1':fev1,'fvc':fvc,'fev1_fvc':(fev1/fvc*100 if fev1 and fvc else None),'pef':pef,'fev1_pct_baseline':(fev1/p.get('baseline_fev1',2.4)*100 if fev1 else None),'spirometry_quality':'Acceptable simulated maneuver' if fev1 else None}; events.append(e); st.session_state.last_ingested=eid
        for step in ['RPM data ingested','Clinical dashboard updated','Threshold/AI alert evaluation completed','EHR-ready payload generated']: log(eid,step)
        pri,reasons,_=assess(e); st.success(f'{eid} saved as a NEW timestamped RPM event. Existing history was preserved. Source: {source}.'); a,b,c=st.columns(3); a.metric('Priority',pri); b.metric('SpO₂',f"{spo2}%"); c.metric('Heart rate',f"{hr} bpm")
        if reasons: st.warning('Alert reasons: '+' | '.join(reasons))

    st.subheader(f"📋 {p['care_plan']} Daily Questionnaire")
    answers={}
    for key,q in questionnaire_for(p['care_plan']): answers[key]=st.radio(q,['No','Yes'],horizontal=True,key=f'q_{pid}_{key}',index=1 if key=='meds' else 0)
    if st.button('💾 Save Daily Questionnaire',key='save_q_'+pid):
        target=latest_for(pid)
        if target:
            target['questionnaire']=answers; target['sob']=answers.get('sob')=='Yes'; target['chest']=answers.get('chest')=='Yes'; target['dizzy']=answers.get('dizzy')=='Yes'; target['meds']=answers.get('meds')=='Yes'; log(target['event_id'],'Daily questionnaire submitted'); st.success('Daily questionnaire saved to the latest patient event.')
        else: st.warning('Save today’s readings first, then save the questionnaire.')

    st.subheader('🎙️📷 Patient Samples')
    st.caption('Optional patient-generated media. Samples use their own save action and are routed to the clinical review queue.')
    audio_sample=st.audio_input('Record cough / breathing audio (optional)')
    image_sample=st.camera_input('Take a patient photo / symptom image (optional)')
    sample_note=st.text_input('Sample note (optional)',placeholder='Example: cough sample after morning questionnaire')
    if st.button('💾 Save Patient Sample',key='save_sample_'+pid):
        saved=0; target=latest_for(pid); link_event=target['event_id'] if target else 'NO-EVENT'
        for media_obj,media_type,ext in [(audio_sample,'Cough / breathing audio','wav'),(image_sample,'Patient image','jpg')]:
            if media_obj is not None:
                st.session_state.patient_samples.append({'sample_id':f"SMP-{len(st.session_state.patient_samples)+1:03d}",'patient_id':pid,'event_id':link_event,'timestamp':datetime.now().replace(microsecond=0).isoformat(),'type':media_type,'note':sample_note,'filename':f"{pid}_{link_event}_{media_type.split()[0].lower()}.{ext}",'mime':'audio/wav' if ext=='wav' else 'image/jpeg','bytes':media_obj.getvalue(),'reviewed':False}); saved+=1
        if saved:
            log(link_event,f'{saved} patient sample(s) captured and routed to clinical review'); st.success(f'{saved} patient sample(s) saved and routed to the Clinical Command Center.')
        else: st.warning('Add an audio or image sample before saving.')

elif menu.startswith('3A ·'):
    st.header('🎓 Patient Education Center')
    pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['care_plan']}",key='edu_patient'); p=PATIENTS[pid]
    st.caption('Bite-sized education assigned by the care team plus general education for the enrolled care plan. Source links open authoritative public health/clinical education pages.')
    assigned=[a for a in st.session_state.education_assignments if a['patient_id']==pid]
    if assigned:
        st.subheader('Assigned education tasks')
        for a in assigned:
            st.write(('✅ ' if a.get('completed') else '○ ')+f"**{a['title']}** — {a['summary']}"); st.link_button('View material',a['url'])
            if not a.get('completed') and st.button('Mark viewed / complete',key='complete_'+a['assignment_id']): a['completed']=True; a['completed_at']=datetime.now().isoformat(); st.rerun()
    else: st.info('No clinician-assigned education is waiting.')
    st.subheader(f"General {p['care_plan']} education")
    for i,(title,summary,url) in enumerate(education_for(p['care_plan']),1): st.markdown(f'**{title}**'); st.write(summary); st.link_button(f'Open source {i}',url)
    adhoc=[a for a in st.session_state.questionnaire_assignments if a['patient_id']==pid and not a.get('completed')]
    if adhoc:
        st.subheader('📋 Ad-hoc questionnaire requested by care team')
        a=adhoc[0]; ans={}
        for key,q in questionnaire_for(a['plan']): ans[key]=st.radio(q,['No','Yes'],horizontal=True,key='adhoc_'+a['assignment_id']+'_'+key)
        if st.button('Submit ad-hoc questionnaire',type='primary'):
            a['completed']=True; a['completed_at']=datetime.now().isoformat(); a['answers']=ans; st.success('Questionnaire submitted to the clinical team.')

elif menu.startswith('4 ·'):
    st.header('🩺 Clinical Command Center & Action Queue')
    st.caption('A work-management view that separates clinical, engagement, and technical exceptions and shows the next operational action.')
    aq=[]
    for _pid,_p in PATIENTS.items():
        _e=latest_for(_pid)
        if _e:
            _pri,_reasons,_=assess(_e); _unread=sum(1 for m in st.session_state.messages if m['patient_id']==_pid and m['sender']=='Patient' and not m.get('read',False)); _bad=[d for d in st.session_state.devices.get(_pid,[]) if not d.get('connected') or not d.get('wifi') or d.get('battery',100)<25]
            _samples=[m for m in st.session_state.patient_samples if m['patient_id']==_pid and not m.get('reviewed',False)]
            if _samples:
                _reason=f"New patient sample received: {_samples[-1]['type']}"; _action='Review patient sample'; _pri='MEDIUM' if _pri=='LOW' else _pri
            else:
                _reason=(_reasons[0] if _reasons else ('Unread patient message' if _unread else ('Device connectivity/battery exception' if _bad else 'Stable / routine monitoring')))
                _action='Provider/RN review' if _pri in ['HIGH','MEDIUM'] else ('Respond to patient' if _unread else ('Technical outreach' if _bad else 'Monitor'))
            aq.append({'Priority':priority_badge(_pri),'Patient':_p['name'],'Care Plan':_p['care_plan'],'Reason':_reason,'Assigned clinician':_p['clinician'],'Next action':_action,'_rank':priority_rank(_pri)})
    if aq:
        st.markdown('**Action Queue** — priority is the first column: 🔴 HIGH, 🟡 MEDIUM, 🟢 LOW. Use the filters to narrow the worklist.')
        aqdf=pd.DataFrame(aq)
        f1,f2,f3=st.columns(3)
        aq_search=f1.text_input('🔎 Search action queue',key='aq_search',placeholder='Patient, reason, care plan, clinician…')
        aq_plan=f2.multiselect('Filter care plan',sorted(aqdf['Care Plan'].unique()),key='aq_plan')
        aq_pri=f3.multiselect('Filter priority',['🔴 HIGH','🟡 MEDIUM','🟢 LOW'],key='aq_pri')
        if aq_search: aqdf=aqdf[aqdf.astype(str).apply(lambda r:r.str.contains(aq_search,case=False,na=False).any(),axis=1)]
        if aq_plan: aqdf=aqdf[aqdf['Care Plan'].isin(aq_plan)]
        if aq_pri: aqdf=aqdf[aqdf['Priority'].isin(aq_pri)]
        aqdf=aqdf.sort_values('_rank').drop(columns=['_rank'])
        st.dataframe(aqdf,hide_index=True,use_container_width=True)
    st.divider()
    st.write('Population view for clinicians: alerts, assigned clinician, connectivity, device status, and patient communications.')
    with st.expander('➕ Create Patient / Add New Patient'):
        patient_creation_panel('Clinical Dashboard','clinical')
    rows=[]
    for pid,p in PATIENTS.items():
        e=latest_for(pid); devs=st.session_state.devices.get(pid,[]); problems=sum((not d['connected']) or (not d['wifi']) or d['battery']<30 for d in devs); unread=sum(m['patient_id']==pid and m['sender']=='Patient' and not m.get('read',False) for m in st.session_state.messages); new_samples=sum(m['patient_id']==pid and not m.get('reviewed',False) for m in st.session_state.patient_samples)
        if e: pri,_,_=assess(e); spo=e['spo2']; hr=e['ecg_hr']; ast=alert_status(e)
        else: pri='AWAITING DATA'; spo='—'; hr='—'; ast='No RPM reading yet'
        rows.append({'Priority':priority_badge(pri),'Patient':p['name'],'MRN':p['mrn'],'Assigned clinician':p['clinician'],'Care Plan':p['care_plan'],'SpO₂':spo,'HR':hr,'Alert status':ast,'Device issues':problems,'Unread chat':unread,'New samples':new_samples,'_pid':pid,'_rank':priority_rank(pri)})
    popdf=pd.DataFrame(rows)
    st.markdown('**Population filters**')
    f1,f2,f3,f4=st.columns(4)
    pop_search=f1.text_input('🔎 Global search',key='pop_search',placeholder='Last name, MRN, care plan…')
    pop_plan=f2.multiselect('Care plan',sorted(popdf['Care Plan'].unique()),key='pop_plan')
    pop_pri=f3.multiselect('Priority',['🔴 HIGH','🟡 MEDIUM','🟢 LOW','⚪ AWAITING DATA'],key='pop_pri')
    pop_clin=f4.multiselect('Assigned clinician',sorted(popdf['Assigned clinician'].unique()),key='pop_clin')
    if pop_search: popdf=popdf[popdf.astype(str).apply(lambda r:r.str.contains(pop_search,case=False,na=False).any(),axis=1)]
    if pop_plan: popdf=popdf[popdf['Care Plan'].isin(pop_plan)]
    if pop_pri: popdf=popdf[popdf['Priority'].isin(pop_pri)]
    if pop_clin: popdf=popdf[popdf['Assigned clinician'].isin(pop_clin)]
    popdf=popdf.sort_values('_rank')
    display_pop=popdf.drop(columns=['_pid','_rank'])
    st.caption('Click/select a patient row to open that patient directly in Patient 360 & Trends.')
    selected=st.dataframe(display_pop,hide_index=True,use_container_width=True,on_select='rerun',selection_mode='single-row',key='population_table')
    if selected.selection.rows:
        ridx=selected.selection.rows[0]
        chosen_pid=popdf.iloc[ridx]['_pid']
        st.session_state['trends_patient_preferred']=chosen_pid
        st.session_state.selected_menu='5 · Patient 360 & Trends'
        st.rerun()
    pid=patient_picker('Open patient clinical view','command_patient','Search assigned patient by name, MRN, care plan, or clinician')
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
    st.subheader('Education & ad-hoc task status')
    _ed=[a for a in st.session_state.education_assignments if a['patient_id']==pid]; _qs=[a for a in st.session_state.questionnaire_assignments if a['patient_id']==pid]
    st.write(f"Education completed: {sum(1 for a in _ed if a.get('completed'))}/{len(_ed)} assigned | Ad-hoc questionnaires completed: {sum(1 for a in _qs if a.get('completed'))}/{len(_qs)} assigned")
    st.subheader('Latest daily questionnaire')
    qa=e.get('questionnaire',{'sob':'Yes' if e.get('sob') else 'No','chest':'Yes' if e.get('chest') else 'No','dizzy':'Yes' if e.get('dizzy') else 'No','meds':'Yes' if e.get('meds') else 'No'}); st.dataframe(pd.DataFrame([{'Question / field':k.replace('_',' ').title(),'Patient answer':v} for k,v in qa.items()]),hide_index=True,use_container_width=True)
    st.subheader('Alert reasons'); [st.write('• '+r) for r in reasons] if reasons else st.success('No active configured threshold exception.')
    clinical_samples=[m for m in st.session_state.patient_samples if m['patient_id']==pid]
    if clinical_samples:
        pending=[m for m in clinical_samples if not m.get('reviewed',False)]
        if pending: st.error(f"🎙️📷 {len(pending)} NEW patient sample(s) require clinical review.")
        st.subheader('🎙️📷 Patient Samples — Clinical Review')
        for m in reversed(clinical_samples):
            status='NEW — review required' if not m.get('reviewed',False) else 'Reviewed'
            st.write(f"**{m['sample_id']} · {m['type']} · {status}**  |  {m['timestamp'][:16].replace('T',' ')}  |  {m['note'] or 'No note'}")
            if m['mime'].startswith('audio'): st.audio(m['bytes'])
            elif m['mime'].startswith('image'): st.image(m['bytes'],width=320)
            if not m.get('reviewed',False) and st.button(f"Mark {m['sample_id']} reviewed",key='review_'+m['sample_id']):
                m['reviewed']=True; log(m['event_id'],f"Patient sample {m['sample_id']} reviewed by clinician"); st.rerun()
    unread=[m for m in st.session_state.messages if m['patient_id']==pid and m['sender']=='Patient' and not m.get('read',False)]
    if unread: st.error(f"💬 {len(unread)} unread patient message(s). Open Communication Center for timely intervention.")

elif menu.startswith('4A ·'):
    st.header('📚 Education & Questionnaire Library')
    st.caption('Clinician-facing library for assigning bite-sized education and ad-hoc care-plan questionnaires. Education links point to authoritative public sources; the summaries and task workflow are portfolio content.')
    pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['care_plan']}",key='lib_patient'); plan=PATIENTS[pid]['care_plan']
    t1,t2=st.tabs(['Patient education','Questionnaires'])
    with t1:
        st.subheader(f'{plan} education')
        for i,(title,summary,url) in enumerate(education_for(plan),1):
            st.markdown(f'**Day {i} / Topic {i}: {title}**'); st.write(summary); st.link_button('Open authoritative source',url)
            if st.button(f'Send to {PATIENTS[pid]["name"]}',key=f'sendedu_{pid}_{i}'):
                st.session_state.education_assignments.append({'assignment_id':f'EDU-{len(st.session_state.education_assignments)+1:03d}','patient_id':pid,'plan':plan,'title':title,'summary':summary,'url':url,'assigned_by':PATIENTS[pid]['clinician'],'assigned_at':datetime.now().isoformat(),'completed':False}); st.success('Education assigned to patient Today / Education Center.')
    with t2:
        st.subheader(f'{plan} questionnaire template')
        st.dataframe(pd.DataFrame([{'Question':q} for _,q in questionnaire_for(plan)]),hide_index=True,use_container_width=True)
        if st.button('Send this questionnaire ad hoc',type='primary'):
            st.session_state.questionnaire_assignments.append({'assignment_id':f'Q-{len(st.session_state.questionnaire_assignments)+1:03d}','patient_id':pid,'plan':plan,'assigned_by':PATIENTS[pid]['clinician'],'assigned_at':datetime.now().isoformat(),'completed':False}); st.success('Ad-hoc questionnaire sent to patient.')

elif menu.startswith('5 ·'):
    st.header('👤 Patient 360 & Trends')
    st.caption('Trend interpretation: baseline = patient’s recent typical range; threshold = clinician-configured alert boundary; current reading = actual measurement. Teal dashed lines are thresholds, purple points are manual entries, and red points are out-of-threshold readings.')
    pid=patient_picker('Patient','trends_patient'); p=PATIENTS[pid]
    st.info(f"Care plan: {p['care_plan']} | Program duration: {p.get('program_duration','Ongoing / clinician-defined')} | Next review: {p.get('next_review_date','Clinician-defined')}"); e=latest_for(pid)
    if not e:
        st.info('Patient is enrolled but has no RPM readings yet. Demographics and devices are available; trends begin after the first submission.')
        st.write({'MRN':p['mrn'],'DOB':p['dob'],'Phone':p.get('phone'),'Care plan':p['care_plan'],'Assigned clinician':p['clinician']}); st.dataframe(device_table(pid),hide_index=True,use_container_width=True); st.stop()
    pri,reasons,_=assess(e)
    left,right=st.columns([3,1])
    with left:
        a,b,c,d=st.columns(4); a.metric('Care plan',p['care_plan']); b.metric('Assigned clinician',p['clinician']); c.metric('Latest source',e.get('source','Device')); d.metric('Priority',pri)
        st.subheader('Wearables & connectivity'); st.dataframe(device_table(pid),hide_index=True,use_container_width=True)
        st.subheader('7-day longitudinal trends')
        trend_chart(pid,'spo2','SpO₂ Trend','%','spo2_min','spo2_max')
        trend_chart(pid,'ecg_hr','Heart Rate Trend','bpm','hr_min','hr_max')
        wh,wu=st.columns([1.35,1],vertical_alignment='bottom'); wh.markdown('<div class="small-trend-title">⚖️ Weight Trend</div>',unsafe_allow_html=True); weight_unit=wu.selectbox('Display unit',['lb','kg'],key='weight_trend_unit_'+pid,label_visibility='visible')
        trend_chart(pid,'weight','Weight',weight_unit,'weight_min','weight_max',weight_unit)
        trend_chart(pid,'rr','Respiratory Rate Trend','breaths/min','rr_min','rr_max')
        th,tu=st.columns([1.55,1],vertical_alignment='bottom'); th.markdown('<div class="small-trend-title">🌡️ Skin Temperature Trend</div>',unsafe_allow_html=True); temp_unit=tu.selectbox('Display unit',['°C','°F'],key='temp_trend_unit_'+pid,label_visibility='visible')
        trend_chart(pid,'skin_temp','Skin Temperature',temp_unit,'temp_min','temp_max',temp_unit)
        trend_chart(pid,'glucose','Glucose (CGM) Trend','mg/dL','glucose_min','glucose_max')
        if p['care_plan'] in SPIROMETRY_PLANS:
            sh,sb=st.columns([4,1]); sh.subheader('🫁 Spirometry Trends')
            _sp=[x for x in patient_events(pid)[-7:] if x.get('fev1') is not None]
            if _sp:
                latest_sp=_sp[-1]
                if sb.button('📄 Result PDF',key='spiro_pdf_'+pid,use_container_width=True): st.session_state['show_spiro_pdf_'+pid]=not st.session_state.get('show_spiro_pdf_'+pid,False)
                _df=pd.DataFrame([{'Date':x['timestamp'][:10],'FEV1 (L)':round(x['fev1'],2),'FVC (L)':round(x['fvc'],2),'FEV1/FVC':round(x['fev1']/x['fvc'],2),'PEF (L/min)':round(x['pef'],0),'FEV1 % personal baseline':round(x['fev1_pct_baseline'],0)} for x in reversed(_sp)]); st.line_chart(_df.set_index('Date')[['FEV1 (L)','FVC (L)']]); st.dataframe(_df,hide_index=True,use_container_width=True)
                if st.session_state.get('show_spiro_pdf_'+pid,False):
                    _pdf=spirometry_pdf_bytes(latest_sp); show_pdf_inline(_pdf); st.download_button('⬇️ Download Spirometry PDF',_pdf,file_name=f"{latest_sp['event_id']}_spirometry.pdf",mime='application/pdf',key='dl_spiro_'+pid)
                st.caption('Synthetic home-spirometry values. The alert engine compares FEV1 with the patient’s synthetic personal baseline; this is a portfolio rule, not a diagnostic criterion.')
        eh,eb=st.columns([4,1]); eh.subheader('ECG classification history')
        if eb.button('📄 Result PDF',key='ecg_pdf_trend_'+pid,use_container_width=True): st.session_state['show_ecg_pdf_'+pid]=not st.session_state.get('show_ecg_pdf_'+pid,False)
        st.dataframe(pd.DataFrame([{'Timestamp':x['timestamp'][:16].replace('T',' '),'Classification':x['ecg'],'Source':x.get('source','Device')} for x in reversed(patient_events(pid)[-7:])]),hide_index=True,use_container_width=True)
        if st.session_state.get('show_ecg_pdf_'+pid,False):
            _epdf=ecg_pdf_bytes(e,e.get('pdf_ok',True)); show_pdf_inline(_epdf); st.download_button('⬇️ Download ECG PDF',_epdf,file_name=f"{e['event_id']}_ecg.pdf",mime='application/pdf',key='dl_ecg_'+pid)
        st.subheader('🎙️📷 Patient Samples')
        ps=[m for m in st.session_state.patient_samples if m['patient_id']==pid]
        if ps:
            st.dataframe(pd.DataFrame([{'Sample ID':m['sample_id'],'Date/Time':m['timestamp'][:16].replace('T',' '),'Type':m['type'],'Note':m['note'],'Linked event':m['event_id']} for m in ps]),hide_index=True,use_container_width=True)
        else: st.caption('No patient-generated audio or image samples in this demo session.')
        st.subheader('Daily questionnaire history')
        for x in reversed(patient_events(pid)[-7:]):
            with st.expander(f"{x['timestamp'][:10]} · {x['event_id']} · {x.get('source','Device')}"):
                qa=x.get('questionnaire',{'sob':'Yes' if x.get('sob') else 'No','chest':'Yes' if x.get('chest') else 'No','dizzy':'Yes' if x.get('dizzy') else 'No','meds':'Yes' if x.get('meds') else 'No'}); st.dataframe(pd.DataFrame([{'Question / field':k.replace('_',' ').title(),'Answer':v} for k,v in qa.items()]),hide_index=True,use_container_width=True)
    with right:
        st.subheader('⚙️ Patient Alert Threshold Settings'); st.info("These controls SET the patient-specific minimum and maximum limits. They are not today’s readings. Threshold controls use the app’s TEAL accent so they are visually neutral. Trend points turn RED only when an actual reading falls outside the configured limits; teal dashed lines show those configured limits. Manual clinician-assisted readings appear purple so provenance is visible at a glance.")
        t=st.session_state.thresholds[pid]
        t['spo2_min'],t['spo2_max']=st.slider('SpO₂ (%) min / max',70,100,(int(t['spo2_min']),int(t['spo2_max'])))
        t['hr_min'],t['hr_max']=st.slider('Heart rate (bpm) min / max',30,180,(int(t['hr_min']),int(t['hr_max'])))
        st.markdown('**Weight threshold**')
        threshold_weight_unit=st.selectbox('Weight threshold unit',['lb','kg'],index=0 if weight_unit=='lb' else 1,key='weight_threshold_unit_'+pid)
        if threshold_weight_unit=='kg':
            wmin=st.number_input('Weight minimum (kg)',36.0,159.0,float(t['weight_min']/2.2046226218),step=.2); wmax=st.number_input('Weight maximum (kg)',36.0,159.0,float(t['weight_max']/2.2046226218),step=.2); t['weight_min']=wmin*2.2046226218; t['weight_max']=wmax*2.2046226218
        else:
            t['weight_min']=st.number_input('Weight minimum (lb)',80.0,350.0,float(t['weight_min']),step=.5); t['weight_max']=st.number_input('Weight maximum (lb)',80.0,350.0,float(t['weight_max']),step=.5)
        t['sys_min'],t['sys_max']=st.slider('Systolic BP min / max',70,220,(int(t['sys_min']),int(t['sys_max'])))
        t['dia_min'],t['dia_max']=st.slider('Diastolic BP min / max',40,140,(int(t['dia_min']),int(t['dia_max']))); t['rr_min'],t['rr_max']=st.slider('Respiratory rate min / max',6,40,(int(t['rr_min']),int(t['rr_max'])))
        st.markdown('**Skin temperature threshold**')
        threshold_temp_unit=st.selectbox('Skin temperature threshold unit',['°C','°F'],index=0 if temp_unit=='°C' else 1,key='temp_threshold_unit_'+pid)
        if threshold_temp_unit=='°F':
            flo=t['temp_min']*9/5+32; fhi=t['temp_max']*9/5+32; nflo,nfhi=st.slider('Skin temperature °F min / max',82.0,109.5,(float(flo),float(fhi)),step=.1); t['temp_min']=(nflo-32)*5/9; t['temp_max']=(nfhi-32)*5/9
        else: t['temp_min'],t['temp_max']=st.slider('Skin temperature °C min / max',28.0,43.0,(float(t['temp_min']),float(t['temp_max'])),step=.1)
        t['glucose_min'],t['glucose_max']=st.slider('CGM glucose mg/dL min / max',40,400,(int(t['glucose_min']),int(t['glucose_max'])))
        if p['care_plan'] in SPIROMETRY_PLANS: t['fev1_pct_min']=st.slider('FEV1 alert limit — % of personal baseline',50,100,int(t.get('fev1_pct_min',80)))
        st.success('Thresholds active for this synthetic patient.')
        st.caption('In a real clinical product, threshold changes would require role-based authorization, clinical governance and audit logging.')
elif menu.startswith('7 ·'):
    st.header('🏡 Care Coordination')
    st.caption('Synthetic operational workflow for services that may be needed beyond remote data collection.')
    if 'service_requests' not in st.session_state: st.session_state.service_requests=[]
    pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']}",key='svc_patient')
    c1,c2=st.columns(2)
    service=c1.selectbox('Service',['Home nurse visit','Mobile lab / phlebotomy','Device replacement','Mobile imaging','Technical support','DME support','Transportation support'])
    priority=c2.selectbox('Operational priority',['Routine','Soon','Urgent workflow review'])
    note=st.text_area('Reason / coordination note')
    if st.button('Create service request',type='primary'):
        rec={'Request ID':f"SR-{len(st.session_state.service_requests)+1:03d}",'Patient':PATIENTS[pid]['name'],'Service':service,'Priority':priority,'Status':'Requested','Created':datetime.now().strftime('%b %d, %I:%M %p'),'Note':note}
        st.session_state.service_requests.append(rec); st.success(f"{rec['Request ID']} created.")
    rows=[r for r in st.session_state.service_requests if r['Patient']==PATIENTS[pid]['name']]
    if rows: st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)

elif menu.startswith('8 ·'):
    st.header('ECG & Spirometry Documents'); pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']}"); es=patient_events(pid)
    for e in reversed(es[-4:]):
        with st.expander(f"{e['event_id']} · {e['timestamp'][:16].replace('T',' ')} · {e['ecg']}",expanded=(e==es[-1])):
            st.download_button('📄 Download / View synthetic ECG PDF',ecg_pdf_bytes(e,e['pdf_ok']),file_name=f"{e['event_id']}_{PATIENTS[pid]['mrn']}.pdf",mime='application/pdf',key='pdf'+e['event_id'],type='primary')
            checks={'Patient name on every page':True,'MRN on every page':e['pdf_ok'],'DOB on every page':True,'ECG timestamp':True,'Patient association':True}; st.dataframe(pd.DataFrame([{'Check':k,'Result':'PASS' if v else 'FAIL'} for k,v in checks.items()]),hide_index=True,use_container_width=True)
            st.success('DOCUMENT VALIDATION PASSED — eligible for downstream transmission.') if e['pdf_ok'] else st.error('DOCUMENT VALIDATION FAILED — held; mock EHR Media filing blocked.')

elif menu.startswith('13 ·'):
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

elif menu.startswith('3 ·'):
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

elif menu.startswith('9 ·'):
    st.header('Integration Hub / API'); st.write('Normalized RPM event + EHR-ready FHIR-style transformation. This is a simulation, not a live Epic endpoint.'); pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']}"); e=latest_for(pid)
    normalized={'eventId':e['event_id'],'patient':PATIENTS[pid],'carePlan':PATIENTS[pid]['care_plan'],'deviceData':{'ecgClassification':e['ecg'],'ecgHeartRate':e['ecg_hr'],'spo2':e['spo2'],'weight':e['weight'],'bloodPressure':{'systolic':e['sys'],'diastolic':e['dia']}},'questionnaire':{'shortnessOfBreath':e['sob'],'chestDiscomfort':e['chest'],'dizziness':e['dizzy'],'medicationTaken':e['meds']},'ecgDocument':{'reportId':e['event_id'],'identifierValidation':'PASS' if e['pdf_ok'] else 'FAIL'}}
    t1,t2,t3=st.tabs(['Normalized RPM JSON','FHIR-style Bundle','Mapping Table'])
    with t1: st.code(json.dumps(normalized,indent=2),language='json'); st.download_button('Download normalized JSON',json.dumps(normalized,indent=2),file_name=f"{e['event_id']}_rpm.json",mime='application/json')
    with t2: fb=fhir_bundle(e); st.code(json.dumps(fb,indent=2),language='json'); st.download_button('Download EHR-ready FHIR-style JSON',json.dumps(fb,indent=2),file_name=f"{e['event_id']}_fhir.json",mime='application/json')
    with t3: st.dataframe(pd.DataFrame([{'Source':'Pulse oximeter','Field':'SpO₂','LOINC':LOINC['SpO2'],'Destination':'EHR flowsheet / Observation'},{'Source':'ECG device','Field':'Heart rate','LOINC':LOINC['Heart Rate'],'Destination':'EHR flowsheet / Observation'},{'Source':'Scale','Field':'Weight','LOINC':LOINC['Body Weight'],'Destination':'EHR flowsheet / Observation'},{'Source':'BP wearable','Field':'Systolic BP','LOINC':LOINC['Systolic BP'],'Destination':'EHR flowsheet / Observation'},{'Source':'Everion','Field':'Respiratory rate / skin temperature','LOINC':LOINC['Respiratory Rate']+' / '+LOINC['Skin Temperature'],'Destination':'EHR flowsheet / Observation'},{'Source':'Dexcom G7 CGM','Field':'Glucose','LOINC':LOINC['Glucose'],'Destination':'EHR flowsheet / Observation'},{'Source':'ECG report','Field':'PDF','LOINC':'N/A','Destination':'Cloverleaf → OnBase → EHR Media (simulated)'}]),hide_index=True,use_container_width=True)

elif menu.startswith('10 ·'):
    st.header('Mock EHR');
    with st.expander('➕ Create Patient / Add New Patient'):
        patient_creation_panel('Mock EHR','ehr')
    pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']}"); es=patient_events(pid); t1,t2,t3=st.tabs(['Flowsheets','Media','Care-team communications'])
    with t1: st.dataframe(pd.DataFrame([{'Date/Time':e['timestamp'][:16].replace('T',' '),'SpO₂':e['spo2'],'Heart Rate':e['ecg_hr'],'Weight':e['weight'],'BP':f"{e['sys']}/{e['dia']}",'ECG device result':e['ecg'],'FEV1 (L)':e.get('fev1'),'FVC (L)':e.get('fvc'),'FEV1/FVC %':round(e.get('fev1_fvc'),1) if e.get('fev1_fvc') else None,'PEF L/min':e.get('pef')} for e in es]),hide_index=True,use_container_width=True)
    with t2:
        st.subheader('RPM Documents & Patient Samples')
        ps=[m for m in st.session_state.patient_samples if m['patient_id']==pid]
        for m in ps:
            st.write(f"🎙️📷 {m['sample_id']} · {m['type']} · {m['timestamp'][:16].replace('T',' ')} · {m['note']}")
            st.download_button(f"Open / download {m['sample_id']}",m['bytes'],file_name=m['filename'],mime=m['mime'],key='media'+m['sample_id'])
        for e in [x for x in es if x['pdf_ok']]: st.write(f"📄 {e['event_id']}.pdf · Remote ECG · Source: RPM Vendor · Status: FILED"); st.download_button('View PDF',ecg_pdf_bytes(e,True),file_name=f"{e['event_id']}.pdf",mime='application/pdf',key='ehr'+e['event_id'])
        for e in [x for x in es if x.get('fev1') is not None]: st.write(f"🫁 {e['event_id']}_spirometry.pdf · Home Spirometry · Status: FILED"); st.download_button('View Spirometry PDF',spirometry_pdf_bytes(e),file_name=f"{e['event_id']}_spirometry.pdf",mime='application/pdf',key='ehrsp'+e['event_id'])
        for e in [x for x in es if not x['pdf_ok']]: st.error(f"{e['event_id']} — identifier validation failed; not filed to mock EHR Media.")
    with t3:
        ints=[x for x in st.session_state.interventions if x['patient_id']==pid]; st.dataframe(pd.DataFrame(ints),hide_index=True,use_container_width=True) if ints else st.caption('No documented communication.')

elif menu.startswith('12 ·'):
    st.header('Data Lineage & Audit'); e=st.selectbox('Trace event',events,format_func=lambda x:f"{x['event_id']} · {PATIENTS[x['patient_id']]['name']} · {x['timestamp'][:16].replace('T',' ')}")
    pri,_,_=assess(e); ints=interventions_for_event(e['event_id']); steps=[('1','Patient home',f"ECG={e['ecg']}; SpO₂={e['spo2']}%; weight={e['weight']} lb; questionnaire captured"),('2','Bluetooth / tablet','Connected-device values collected by patient app (simulated)'),('3','Vendor ingestion API','Normalized RPM event accepted'),('4','Clinical dashboard',f'Patient record updated; {pri} workflow priority calculated'),('5','Human intervention',f"{ints[-1]['channel']} — {ints[-1]['status']}" if ints else 'No communication documented yet'),('6','Integration API','LOINC-coded/FHIR-style payload prepared'),('7','Structured EHR path','Vitals and ECG values available in mock flowsheet'),('8','Document path','ECG PDF → Cloverleaf → OnBase → Media simulation' if e['pdf_ok'] else 'ECG PDF HELD because identifier validation failed')]
    for n,title,desc in steps: st.markdown(f'**{n}. {title}**  \n{desc}')
    st.subheader('Session audit log'); st.dataframe(pd.DataFrame(st.session_state.audit),hide_index=True,use_container_width=True) if st.session_state.audit else st.caption('Ingest or document an intervention to populate the live audit log.')

elif menu.startswith('14 ·'):
    st.header('🧭 Care Pathway Engine')
    st.caption('Configurable synthetic pathways translate a care plan into daily tasks, monitoring cadence, conditional work, and escalation. They are portfolio examples, not validated clinical protocols.')
    plan=st.selectbox('Care pathway',CARE_PLANS,key='pathway_plan')
    pathway_map={
      'Cardiology':['Continuous HR/SpO₂/RR/skin temperature','BP and weight','Daily symptom questionnaire','ECG when scheduled or triggered','Medication check-in','Conditional clinician outreach'],
      'Cirrhosis / Liver Disease':['SpO₂, BP/HR and weight','Daily liver-disease symptom questionnaire','Medication check-in','Conditional photo/audio sample','Clinician outreach for configured exceptions'],
      'Hypertension':['BP/HR','Medication check-in','Symptoms questionnaire','Trend review'],
      'Diabetes / CGM':['Continuous glucose','Medication check-in','Symptoms questionnaire','Trend review'],
      'Heart Failure':['Weight, BP/HR, SpO₂','Daily symptom questionnaire','Medication check-in','Conditional ECG','Escalation for configured multi-signal exceptions'],
      'COPD / Pulmonary':['SpO₂ and RR','Daily respiratory questionnaire','Optional cough audio sample','Technical/device adherence review'],
      'Chronic Kidney Disease':['Weight and BP','Daily symptom questionnaire','Medication check-in','Care-plan review'],
      'Post-Surgical Recovery':['Vitals','Pain/recovery questionnaire','Optional wound/photo sample','Short-term review cadence'],
      'CAR-T':['Frequent vitals','Fever/neurologic symptom questionnaire','Medication check-in','Rapid clinical escalation workflow'],
      'Acute Kidney Injury (AKI)':['BP, weight, urine/symptom check','Medication review','Follow-up coordination'],
      'Joint / Knee Replacement':['Pain, mobility, wound questionnaire','Optional wound photo','Rehabilitation task tracking'],
      'Pneumonitis':['SpO₂, RR, home spirometry','Cough/breathing questionnaire','Optional cough sample'],
      'Pancreatectomy':['Vitals, weight, CGM','Nutrition/glucose/recovery questionnaire','Wound photo when requested'],
      'Neutropenic Fever':['Temperature and vitals','Infection symptom questionnaire','Urgent human review workflow'],
      'Coronary Artery Disease (CAD)':['BP/HR, symptoms, activity','Medication check-in','ECG when scheduled/triggered'],
      'Lung Transplant':['SpO₂, RR, home spirometry','Daily transplant symptom questionnaire','Medication adherence','Spirometry trend / PDF'],
      'Respiratory Infection - Pediatric':['SpO₂, RR, temperature','Caregiver questionnaire','Optional cough audio','Home spirometry when age/plan appropriate'],
      'Respiratory Infection - Adult':['SpO₂, RR, temperature','Respiratory questionnaire','Optional cough audio','Home spirometry when ordered'],
      'Pulmonary Home Rehab':['SpO₂, RR, home spirometry','Rehab activity questionnaire','Education and exercise tasks']}
    st.subheader(f'{plan} — Daily/conditional tasks')
    for x in pathway_map.get(plan,[]): st.write('• '+x)
    st.subheader('Escalation model')
    st.write('**Level 1 — Technical:** disconnected device, low battery, missing transmission → troubleshooting/support.')
    st.write('**Level 2 — RPM team:** symptom response, missing questionnaire, single configured threshold exception → review/outreach.')
    st.write('**Level 3 — Provider:** persistent or multi-signal exception, device-reported abnormal ECG → provider review.')
    st.write('**Level 4 — Organization-defined urgent workflow:** handled according to the health system’s approved protocol; the prototype does not make autonomous treatment decisions.')

elif menu.startswith('15 ·'):
    st.header('🏗️ Architecture & Product Story'); st.info('V3.0 is organized into four product layers: Patient Experience → Clinical Experience → Integration → AI & Product. The design is inspired by common connected-care/RPM patterns, while all implementation, data, rules, and UI here are synthetic portfolio content.'); st.code('''PATIENT HOME\n  KardiaMobile 6L + Everion/individual vitals + Dexcom G7 CGM + Questionnaire\n                    │ Bluetooth\n                    ▼\n              Patient Tablet\n                    │\n                    ▼\n             Vendor RPM Cloud\n          ┌─────────┴─────────┐\n          ▼                   ▼\n Clinical Dashboard        ECG PDF\n          │                   │\n          ▼                   ▼\n AI Alert / Trend Layer   Document Validation\n          │                   │\n          ▼                   ▼\n Clinician Outreach      Cloverleaf → OnBase\n          │                   │\n          ▼                   ▼\n RPM Integration API     Mock EHR Media\n          │\n          ▼\n FHIR/LOINC Mapping → Mock EHR Flowsheet\n\nCLOSED LOOP: Alert → Human review → Call/Chat → Outcome → Audit trail''')
    st.write('**MVP epics:** validated patient registration + MPI duplicate prevention · care-plan enrollment duration/review · care-plan-specific daily + ad-hoc questionnaires · bite-sized patient education completion · patient-generated audio/image samples · home spirometry + PDF · timestamped device ingestion · longitudinal trends · clinical command center · AI workflow prioritization · clinician intervention · ECG document integrity · EHR transformation · lineage/audit.')
    st.write('**Guardrails:** synthetic data only; no autonomous diagnosis; device classifications treated as source inputs; failed documents held; clinician remains decision-maker.')
    st.write('**KPIs:** alert precision, time-to-review, time-to-patient-contact, intervention completion, false-positive rate, data completeness, document validation pass rate, EHR delivery success, clinician override rate.')


elif menu.startswith('15A ·') and CURRENT_USER=='Admin':
    st.header('🔐 Logins & Roles')
    st.caption('Admin-only portfolio view. Demo passwords are intentionally simple and are not a production authentication pattern.')
    st.info('Production healthcare applications should use enterprise identity/SSO, MFA, server-side authorization, secure secret storage, least-privilege access and auditable access controls.')
    h=st.columns([1.1,1.5,1.8,3.4]); h[0].markdown('**Username**'); h[1].markdown('**Role**'); h[2].markdown('**Password**'); h[3].markdown('**Access / functionality**')
    for username,acct in DEMO_ACCOUNTS.items():
        c1,c2,c3,c4=st.columns([1.1,1.5,1.8,3.4],vertical_alignment='center'); c1.write(username); c2.write(acct['role']); key='reveal_'+username.replace(' ','_')
        if key not in st.session_state: st.session_state[key]=False
        pc,eye=c3.columns([4,1]); pc.code(acct['password'] if st.session_state[key] else '••••••••••••',language=None)
        if eye.button('👁',key='eye_'+username,help='Show/hide demo password'): st.session_state[key]=not st.session_state[key]; st.rerun()
        c4.write(acct['description'])

elif menu.startswith('11 ·'):
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
