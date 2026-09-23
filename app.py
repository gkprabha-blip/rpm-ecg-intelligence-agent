import io, json, math, re, base64, random
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import fitz
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors

st.set_page_config(page_title='Connected Care Intelligence Platform v6.0', page_icon='RPM', layout='wide')

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

# V5.0 unified enterprise registry. Research participants are linked to operational
# patient records through a governed Research Participant ID, while research views
# intentionally suppress MRN/name. Lifecycle status determines which operational
# workspace shows a person; the Command Center is not the enterprise registry.
def seed_unified_enterprise_registry():
    if st.session_state.get('v42_registry_seeded'): return
    first_names=['Amina','Benjamin','Camila','David','Elise','Farah','Gabriel','Hannah','Isaac','Jasmine','Kai','Leila','Mateo','Nora','Owen','Priya','Quinn','Rafael','Sofia','Theo','Uma','Victor','Willa','Xavier','Yara','Zane']
    last_names=['Adams','Bennett','Carter','Diaz','Evans','Foster','Green','Hughes','Ibrahim','Jones','Kim','Lopez','Morgan','Nguyen','Owens','Patel','Reed','Singh','Turner','Usman','Vega','Walker','Xu','Young','Zimmerman']
    plans=['Lung Transplant','COPD / Pulmonary','Pulmonary Home Rehab','Pneumonitis','Respiratory Infection - Adult','Cardiology','Heart Failure','Coronary Artery Disease (CAD)','Hypertension','Diabetes / CGM','Chronic Kidney Disease','Post-Surgical Recovery']
    for i in range(1,241):
        pid=f'ENT-{i:04d}'
        if pid in PATIENTS: continue
        plan=plans[(i-1)%len(plans)]
        lifecycle='Active Monitoring' if i<=80 else 'Completed RPM Episode'
        year=1945+(i*3)%50; month=1+(i%12); day=1+(i%27)
        PATIENTS[pid]={
            'name':f'{first_names[(i-1)%len(first_names)]} {last_names[(i*7)%len(last_names)]}',
            'clinician':['Dr. John Doe','Dr. Aisha Morgan','Dr. Samuel Lee','Dr. Elena Rivera'][i%4],
            'mrn':f'SYN-MRN-{3000+i:04d}','dob':f'{year:04d}-{month:02d}-{day:02d}','care_plan':plan,
            'baseline_spo2':94+(i%5),'baseline_weight':145+(i%65),'baseline_hr':62+(i%25),
            'address':f'{100+i} Synthetic Care Way','city':'Austin','state':'TX','zip':'78701',
            'phone':f'512-555-{3000+i:04d}'[-12:],'email':'','insurance':'Demo Health Plan','member_id':f'DEMO-R-{i:04d}',
            'next_of_kin':'Synthetic Family Contact','nok_relationship':'Family','nok_phone':'512-555-0199',
            'program_duration':'90 days','next_review_date':'Synthetic','lifecycle_status':lifecycle,
            'research_id':f'RSP-{i:04d}','research_eligible':True,'registry_source':'Unified Enterprise Registry'
        }
    # Legacy demonstration patients remain active operational records.
    for p in PATIENTS.values(): p.setdefault('lifecycle_status','Active Monitoring')
    st.session_state.v42_registry_seeded=True
seed_unified_enterprise_registry()

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
if 'transition_workflow' not in st.session_state: st.session_state.transition_workflow={}
if 'kit_orders' not in st.session_state: st.session_state.kit_orders=[]

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
    teal=colors.HexColor('#087F8C'); blue=colors.HexColor('#2F80ED'); navy=colors.HexColor('#183153'); pale=colors.HexColor('#F3FAFB'); grid=colors.HexColor('#D8EEF0')
    for page in range(1,3):
        c.setFillColor(pale); c.roundRect(.35*inch,H-1.35*inch,7.8*inch,.9*inch,12,fill=1,stroke=0)
        c.setFillColor(navy); c.setFont('Helvetica-Bold',10); ident=f"Patient: {p['name']}   |   MRN: {p['mrn']}   |   DOB: {p['dob']}"
        if not valid and page==2: ident=f"Patient: {p['name']}   |   MRN: [MISSING]   |   DOB: {p['dob']}"
        c.drawString(.55*inch,H-.68*inch,ident); c.setFillColor(teal); c.setFont('Helvetica-Bold',17); c.drawString(.55*inch,H-1.05*inch,'6-Lead ECG Result')
        c.setFillColor(navy); c.setFont('Helvetica',8.5); c.drawString(.55*inch,H-1.28*inch,'Synthetic portfolio report • device-reported classification • clinician review required')
        c.setFont('Helvetica-Bold',9); c.drawString(.55*inch,H-1.62*inch,f"Recording {e['event_id']}")
        c.setFont('Helvetica',9); c.drawString(2.1*inch,H-1.62*inch,f"{e['timestamp'][:16].replace('T',' ')}   •   HR {e['ecg_hr']} bpm   •   {e['ecg']}")
        c.setFillColor(blue); c.roundRect(.55*inch,H-2.08*inch,2.1*inch,.28*inch,6,fill=1,stroke=0); c.setFillColor(colors.white); c.setFont('Helvetica-Bold',8); c.drawCentredString(1.6*inch,H-1.985*inch,'DEVICE-REPORTED RESULT')
        c.setFillColor(navy); c.setFont('Helvetica',8); c.drawString(2.85*inch,H-1.98*inch,'Leads: I, II, III, aVR, aVL, aVF   |   Signal quality: Good (synthetic)')
        for i,lead in enumerate(['I','II','III','aVR','aVL','aVF']):
            y=H-2.55*inch-i*.70*inch; x0=.95*inch; x1=7.85*inch
            c.setStrokeColor(grid); c.setLineWidth(.25)
            for gx in range(0,35): c.line(x0+gx*.2*inch,y-.24*inch,x0+gx*.2*inch,y+.28*inch)
            for gy in range(-2,4): c.line(x0,y+gy*.1*inch,x1,y+gy*.1*inch)
            c.setFillColor(teal); c.setFont('Helvetica-Bold',9); c.drawString(.55*inch,y+.05*inch,lead)
            pts=[]
            for x in range(620):
                xx=x0+x*.011*inch; phase=(x%70)/70; val=2.2*math.sin(x/8)
                if .43<phase<.47: val+=18*(1-abs(phase-.45)/.02)
                if .47<=phase<.50: val-=9*(1-abs(phase-.485)/.015)
                pts.append((xx,y+val*(-1 if lead=='aVR' else 1)))
            c.setStrokeColor(blue if i%2==0 else teal); c.setLineWidth(.85)
            for a,b in zip(pts[:-1],pts[1:]): c.line(a[0],a[1],b[0],b[1])
        c.setFillColor(navy); c.setFont('Helvetica-Bold',8.5); c.drawString(.55*inch,.92*inch,'Research-ready fields preserved:')
        c.setFont('Helvetica',8); c.drawString(.55*inch,.72*inch,'recording timestamp • heart rate • device classification • lead set • signal quality • clinician review status')
        c.drawString(.55*inch,.55*inch,'QT/QTc may be captured when measured/reviewed by an authorized clinician; this synthetic report does not calculate QT/QTc.')
        c.setFont('Helvetica-Oblique',7.5); c.drawString(.55*inch,.32*inch,f'Page {page} of 2 | SYNTHETIC DATA ONLY | Not a diagnostic ECG report'); c.showPage()
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
    return ('Good' if level>=60 else 'Low' if level>=30 else 'Critical') + f" · {level}%"

def device_table(pid):
    return pd.DataFrame([{'Device':d['device'],'Measurement / mode':d.get('type',''),'Connected':'Connected' if d['connected'] else 'Disconnected','Battery':battery_icon(d['battery']),'Internet':'Online' if d['wifi'] else 'Offline'} for d in st.session_state.devices[pid]])

def _trend_icon(field):
    icons={
      'spo2':'<svg viewBox="0 0 24 24" fill="none"><rect x="5" y="4" width="14" height="16" rx="5" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="10" r="2.3" stroke="currentColor" stroke-width="1.8"/><path d="M9 15h6M10.5 17h3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
      'ecg_hr':'<svg viewBox="0 0 24 24" fill="none"><path d="M3 12h4l2-6 4 12 3-7 2 3h3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
      'weight':'<svg viewBox="0 0 24 24" fill="none"><path d="M5 7h14l2 13H3L5 7Z" stroke="currentColor" stroke-width="2"/><path d="M9 7a3 3 0 0 1 6 0" stroke="currentColor" stroke-width="2"/></svg>',
      'rr':'<svg viewBox="0 0 24 24" fill="none"><path d="M12 5v14M12 12c-2-4-7-5-8-1-1 5 3 8 8 8M12 12c2-4 7-5 8-1 1 5-3 8-8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
      'skin_temp':'<svg viewBox="0 0 24 24" fill="none"><path d="M10 5a2 2 0 1 1 4 0v8.2a4 4 0 1 1-4 0V5Z" stroke="currentColor" stroke-width="2"/><path d="M12 9v7" stroke="currentColor" stroke-width="2"/></svg>',
      'glucose':'<svg viewBox="0 0 24 24" fill="none"><path d="M12 3s6 7 6 11a6 6 0 1 1-12 0c0-4 6-11 6-11Z" stroke="currentColor" stroke-width="2"/></svg>',
      'ecg':'<svg viewBox="0 0 24 24" fill="none"><rect x="3" y="4" width="18" height="16" rx="3" stroke="currentColor" stroke-width="1.7"/><path d="M5.5 12h3l1.5-4 3 8 2-5 1.5 2H19" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>'}
    return icons.get(field,icons['spo2'])

def trend_chart(pid, field, title, unit, min_key=None, max_key=None, display_unit=None, compact_unit_selector=False):
    with st.container(border=True):
        selected_unit=display_unit or unit
        if compact_unit_selector:
            hc,uc,sp=st.columns([2.5,1.0,4.5],vertical_alignment='center')
            with hc: st.markdown(f'<div class="trend-head">{_trend_icon(field)}<span>{title}</span></div>',unsafe_allow_html=True)
            with uc:
                opts=['lb','kg'] if field=='weight' else ['°C','°F']
                selected_unit=st.selectbox('Display unit',opts,index=opts.index(display_unit) if display_unit in opts else 0,key=f'{field}_trend_unit_{pid}')
        else:
            st.markdown(f'<div class="trend-head">{_trend_icon(field)}<span>{title}</span></div>',unsafe_allow_html=True)
        es=patient_events(pid)[-7:]; x=[pd.to_datetime(e['timestamp']) for e in es]; raw=[e.get(field) for e in es]
        src=[e.get('source','Device') for e in es]; symbols=['circle' if 'Device' in a else 'diamond' for a in src]
        t=st.session_state.thresholds[pid]; raw_lo=t.get(min_key) if min_key else None; raw_hi=t.get(max_key) if max_key else None
        def cv(v):
            if v is None: return v
            if field=='weight' and selected_unit=='kg': return v/2.2046226218
            if field=='skin_temp' and selected_unit=='°F': return v*9/5+32
            return v
        y=[cv(v) for v in raw]; lo=cv(raw_lo); hi=cv(raw_hi)
        colors=['#D92D20' if (raw_lo is not None and v<raw_lo) or (raw_hi is not None and v>raw_hi) else ('#7F56D9' if 'Manual' in src[i] else '#2F80ED') for i,v in enumerate(raw)]
        custom=[]
        for e in es:
            device=source_device(PATIENTS[pid]['care_plan'], field, e.get('source','Device'))
            custom.append([e['event_id'],e.get('source','Device'),device,e['ecg']])
        labels=[f'{v:.1f}' if isinstance(v,float) else str(v) for v in y]
        fig=go.Figure(go.Scatter(x=x,y=y,mode='lines+markers+text',text=labels,textposition='top center',line={'color':'#98A2B3'},marker={'size':10,'symbol':symbols,'color':colors},customdata=custom,hovertemplate='<b>Value:</b> %{y:.1f} '+selected_unit+'<br><b>Timestamp:</b> %{x|%b %d, %Y %I:%M %p}<br><b>Entry source:</b> %{customdata[1]}<br><b>Device:</b> %{customdata[2]}<br><b>Event:</b> %{customdata[0]}<br><b>ECG:</b> %{customdata[3]}<extra></extra>'))
        if lo is not None: fig.add_hline(y=lo,line_dash='dash',line_color='#087F8C',annotation_text='Min threshold')
        if hi is not None: fig.add_hline(y=hi,line_dash='dash',line_color='#087F8C',annotation_text='Max threshold')
        fig.update_layout(height=285,margin=dict(l=15,r=15,t=18,b=10),yaxis_title=selected_unit,hovermode='closest',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig,use_container_width=True)
        st.markdown('<div class="trend-meta">Blue = device in range · Purple = manual entry · Red = outside threshold · Teal dashed = configured threshold</div>',unsafe_allow_html=True)
        return selected_unit

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
    teal=colors.HexColor('#087F8C'); blue=colors.HexColor('#2F80ED'); navy=colors.HexColor('#183153'); pale=colors.HexColor('#F3FAFB'); aqua=colors.HexColor('#42BFC7')
    fev1=float(e.get('fev1') or 0); fvc=float(e.get('fvc') or 0); ratio=(fev1/fvc if fvc else 0); pef=float(e.get('pef') or 0)
    # Synthetic reference fields are intentionally illustrative; this portfolio does not calculate clinical reference equations.
    pred_fev1=float(p.get('baseline_fev1',max(fev1,2.4))); pred_fvc=max(3.2,pred_fev1/0.78); lln_fev1=pred_fev1*0.80; lln_fvc=pred_fvc*0.80; lln_ratio=0.70
    def z(actual,pred): return (actual-pred)/(max(pred*.12,.15))
    c.setFillColor(pale); c.roundRect(.35*inch,H-1.30*inch,7.8*inch,.95*inch,12,fill=1,stroke=0)
    c.setFillColor(navy); c.setFont('Helvetica-Bold',10); c.drawString(.45*inch,H-.4*inch,f"Patient: {p['name']}   |   MRN: {p['mrn']}   |   DOB: {p['dob']}")
    c.setFillColor(teal); c.setFont('Helvetica-Bold',17); c.drawString(.45*inch,H-.75*inch,'Home Spirometry Result')
    c.setFillColor(navy)
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
    fy=H-5.05*inch; fx=.7*inch; fw=3.0*inch; fh=1.42*inch
    c.setFont('Helvetica-Bold',9); c.drawString(fx,fy+fh+.16*inch,'Flow–Volume Loop (synthetic)')
    c.line(fx,fy,fx+fw,fy); c.line(fx,fy-.65*inch,fx,fy+fh)
    c.setFont('Helvetica',7); c.drawString(fx+fw-.45*inch,fy-.16*inch,'Volume (L)'); c.saveState(); c.translate(fx-.18*inch,fy+.25*inch); c.rotate(90); c.drawString(0,0,'Flow (L/s)'); c.restoreState()
    pts=[]
    for i in range(100):
        frac=i/99; vol=fvc*frac; flow=(pef/60.0)*(1-math.exp(-frac*28))*math.exp(-frac*2.0); pts.append((fx+(vol/max(fvc,1))*fw,fy+(flow/max(pef/60.0,1))*fh))
    c.setStrokeColor(blue); c.setLineWidth(1.4)
    for a,b in zip(pts[:-1],pts[1:]): c.line(a[0],a[1],b[0],b[1])
    insp=[]
    for i in range(100):
        frac=i/99; vol=fvc*(1-frac); flow=-0.45*(pef/60.0)*math.sin(math.pi*frac); insp.append((fx+(vol/max(fvc,1))*fw,fy+(flow/max(pef/60.0,1))*fh))
    c.setStrokeColor(teal); c.setLineWidth(1.2)
    for a,b in zip(insp[:-1],insp[1:]): c.line(a[0],a[1],b[0],b[1])
    # Volume-time curve
    tx=4.35*inch; ty=fy; tw=3.0*inch; th=1.65*inch
    c.setFont('Helvetica-Bold',9); c.drawString(tx,ty+th+.16*inch,'Volume–Time Curve (synthetic)')
    c.line(tx,ty,tx+tw,ty); c.line(tx,ty,tx,ty+th); c.setFont('Helvetica',7); c.drawString(tx+tw-.35*inch,ty-.16*inch,'Time (s)'); c.saveState(); c.translate(tx-.18*inch,ty+.25*inch); c.rotate(90); c.drawString(0,0,'Volume (L)'); c.restoreState()
    vt=[]
    for i in range(121):
        t=6*i/120; vol=fvc*(1-math.exp(-t/0.85)); vt.append((tx+(t/6)*tw,ty+(vol/max(fvc,1))*th))
    c.setStrokeColor(aqua); c.setLineWidth(1.5)
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

# --- V3.3 synthetic discharge-to-RPM candidate registry ---
DISCHARGE_CANDIDATES=[
 {'patient':'Avery Johnson','mrn':'ACUTE-2001','care_plan':'Heart Failure','discharge':'Today','condition_fit':3,'measurable':2,'transition_risk':2,'management_need':2,'willing':1,'support':1,'connectivity':1,'team_capacity':1,'hard_stop':False,'reason':'Recent HF admission; weight/BP/HR/SpO2 trending useful after discharge.'},
 {'patient':'Noah Williams','mrn':'ACUTE-2002','care_plan':'Hypertension','discharge':'Tomorrow','condition_fit':3,'measurable':2,'transition_risk':1,'management_need':2,'willing':1,'support':1,'connectivity':1,'team_capacity':1,'hard_stop':False,'reason':'Medication change with need for home BP trend review.'},
 {'patient':'Sophia Martinez','mrn':'ACUTE-2003','care_plan':'Lung Transplant','discharge':'Today','condition_fit':3,'measurable':2,'transition_risk':2,'management_need':2,'willing':1,'support':1,'connectivity':1,'team_capacity':1,'hard_stop':False,'reason':'Post-transplant home SpO2/spirometry/symptom surveillance.'},
 {'patient':'Liam Brown','mrn':'ACUTE-2004','care_plan':'COPD / Pulmonary','discharge':'2 days','condition_fit':3,'measurable':2,'transition_risk':2,'management_need':2,'willing':1,'support':0,'connectivity':1,'team_capacity':1,'hard_stop':False,'reason':'COPD exacerbation; needs device training/support before discharge.'},
 {'patient':'Emma Davis','mrn':'ACUTE-2005','care_plan':'Joint / Knee Replacement','discharge':'Today','condition_fit':2,'measurable':1,'transition_risk':1,'management_need':1,'willing':1,'support':1,'connectivity':1,'team_capacity':1,'hard_stop':False,'reason':'Post-operative recovery may benefit from symptom/activity follow-up.'},
 {'patient':'Oliver Wilson','mrn':'ACUTE-2006','care_plan':'Diabetes / CGM','discharge':'Tomorrow','condition_fit':3,'measurable':2,'transition_risk':2,'management_need':2,'willing':1,'support':1,'connectivity':0,'team_capacity':1,'hard_stop':False,'reason':'Glucose management need; connectivity plan required.'},
 {'patient':'Isabella Moore','mrn':'ACUTE-2007','care_plan':'Acute Kidney Injury (AKI)','discharge':'Today','condition_fit':2,'measurable':1,'transition_risk':2,'management_need':1,'willing':1,'support':1,'connectivity':1,'team_capacity':1,'hard_stop':False,'reason':'Post-AKI transition needs follow-up; labs remain outside this device-only prototype.'},
 {'patient':'Ethan Taylor','mrn':'ACUTE-2008','care_plan':'Cardiology','discharge':'Pending','condition_fit':3,'measurable':2,'transition_risk':2,'management_need':2,'willing':1,'support':1,'connectivity':1,'team_capacity':1,'hard_stop':True,'reason':'Currently clinically unstable; inpatient/urgent management takes precedence over RPM enrollment.'},
 {'patient':'Mia Anderson','mrn':'ACUTE-2009','care_plan':'Respiratory Infection - Adult','discharge':'Tomorrow','condition_fit':2,'measurable':2,'transition_risk':1,'management_need':1,'willing':1,'support':1,'connectivity':1,'team_capacity':1,'hard_stop':False,'reason':'Short-term oxygen/temperature/symptom monitoring may support recovery.'},
 {'patient':'Lucas Thomas','mrn':'ACUTE-2010','care_plan':'Coronary Artery Disease (CAD)','discharge':'2 days','condition_fit':3,'measurable':2,'transition_risk':2,'management_need':2,'willing':0,'support':1,'connectivity':1,'team_capacity':1,'hard_stop':False,'reason':'Clinical fit exists, but patient has not consented to RPM.'}
]
# V5.0: transition candidates are also enterprise-registry patients. They are visible in MPI/Mock EHR,
# but remain out of the active Command Center until human enrollment/activation progresses.
for _i,_r in enumerate(DISCHARGE_CANDIDATES,1):
    _pid=f'ACUTE-{2000+_i}'
    if _pid not in PATIENTS:
        PATIENTS[_pid]={'name':_r['patient'],'clinician':'Dr. Aisha Morgan','mrn':_r['mrn'],'dob':'1965-01-01','care_plan':_r['care_plan'],'baseline_spo2':97,'baseline_weight':170.0,'baseline_hr':74,'address':'200 Transition Home Way','city':'Austin','state':'TX','zip':'78701','phone':f'512-555-{2200+_i:04d}','email':'','insurance':'Demo Health Plan','member_id':f'DEMO-ACUTE-{_i:03d}','next_of_kin':'Synthetic Family Contact','nok_relationship':'Family','nok_phone':'512-555-0199','program_duration':'Not enrolled','next_review_date':'Pending eligibility review','lifecycle_status':'RPM Candidate','research_eligible':False,'registry_source':'Acute Care / Discharge Planning'}
        st.session_state.thresholds[_pid]=default_thresholds(PATIENTS[_pid]) if 'default_thresholds' in globals() else {'spo2_min':92,'spo2_max':100,'hr_min':50,'hr_max':110,'weight_min':165,'weight_max':175,'sys_min':90,'sys_max':160,'dia_min':50,'dia_max':100,'rr_min':10,'rr_max':24,'temp_min':34.0,'temp_max':38.0,'glucose_min':70,'glucose_max':180,'fev1_pct_min':80}
        st.session_state.devices[_pid]=[]
# Care-path-specific demo kit configuration. These are portfolio defaults, not universal clinical requirements.
KIT_MATRIX={
 'Heart Failure':['Connected scale','Blood pressure monitor','Pulse oximeter','RPM tablet / gateway'],
 'Hypertension':['Blood pressure monitor','RPM tablet / gateway'],
 'Lung Transplant':['Home spirometer','Pulse oximeter','Connected scale','Blood pressure monitor','RPM tablet / gateway'],
 'COPD / Pulmonary':['Pulse oximeter','Home spirometer','RPM tablet / gateway'],
 'Joint / Knee Replacement':['Digital thermometer','RPM tablet / gateway'],
 'Diabetes / CGM':['CGM starter supplies','Blood pressure monitor','RPM tablet / gateway'],
 'Acute Kidney Injury (AKI)':['Connected scale','Blood pressure monitor','RPM tablet / gateway'],
 'Cardiology':['6-lead ECG device','Blood pressure monitor','Connected scale','Pulse oximeter / wearable','RPM tablet / gateway'],
 'Respiratory Infection - Adult':['Pulse oximeter','Digital thermometer','RPM tablet / gateway'],
 'Coronary Artery Disease (CAD)':['Blood pressure monitor','Connected scale','6-lead ECG device when ordered','RPM tablet / gateway']}
def kit_for(plan): return KIT_MATRIX.get(plan,['Blood pressure monitor','Pulse oximeter','RPM tablet / gateway'])
def transition_state(mrn):
    return st.session_state.transition_workflow.setdefault(mrn,{'enrollment_status':'Candidate','kit_status':'Not configured','delivery_method':'Ship to home','activation_status':'Not started','patient_id':None})
def enroll_candidate(r):
    wf=transition_state(r['mrn'])
    if wf.get('patient_id') and wf['patient_id'] in PATIENTS: return wf['patient_id']
    n=1000+len(PATIENTS)+1; pid=f'SYN-{n}'
    PATIENTS[pid]={'name':r['patient'],'clinician':'Dr. Aisha Morgan','mrn':f'SYN-MRN-{n}','dob':'1965-01-01','care_plan':r['care_plan'],'baseline_spo2':97,'baseline_weight':170.0,'baseline_hr':74,'address':'200 Transition Home Way','city':'Austin','state':'TX','zip':'78701','phone':'512-555-0200','email':'','insurance':'Demo Health Plan','member_id':f'DEMO-{n}','next_of_kin':'Synthetic Family Contact','nok_relationship':'Family','nok_phone':'512-555-0199','program_duration':'Clinician-defined','next_review_date':'Clinician-defined'}
    st.session_state.devices[pid]=[]
    for d in kit_for(r['care_plan']): st.session_state.devices[pid].append({'device':d,'type':'Care-path kit device','connected':False,'battery':100,'wifi':False})
    st.session_state.thresholds[pid]=default_thresholds(PATIENTS[pid])
    wf['patient_id']=pid; wf['enrollment_status']='Enrolled'; wf['activation_status']='Setup pending'
    st.session_state.audit.append({'time':datetime.now().strftime('%H:%M:%S'),'event_id':r['mrn'],'step':'RPM enrollment created from transition queue','status':'SUCCESS'})
    return pid

def fit_score(r): return sum(r[k] for k in ['condition_fit','measurable','transition_risk','management_need','willing','support','connectivity','team_capacity'])
def fit_bucket(r):
    if r['hard_stop'] or not r['willing']: return 'NOT CURRENTLY FIT'
    sc=fit_score(r)
    return 'RPM FIT' if sc>=9 else ('REVIEW / ENABLE' if sc>=6 else 'NOT CURRENTLY FIT')

# --- V3.0 demo authentication / role-based navigation ---
DEMO_ACCOUNTS={
 'Patient':{'password':'Patient Password','role':'Patient','description':'Own patient experience, daily tasks, education, messages and results.'},
 'Clinician':{'password':'Clinician Password','role':'Clinician / RPM Nurse','description':'Assigned-patient Command Center, Patient 360, interventions, education/questionnaires and communications.'},
 'Provider':{'password':'Provider Password','role':'Provider / Physician','description':'Clinical review, escalations, trends/reports and intervention review.'},
 'RPM Admin':{'password':'RPM Admin Password','role':'RPM Administrator','description':'Enrollment, assignments, care pathways and operational configuration.'},
 'Researcher':{'password':'Researcher Password','role':'Researcher','description':'De-identified Research Analytics Center, cohorts, reports and exports; no operational MRNs by default.'},
 'Integrations':{'password':'Integrations Password','role':'Integrations / Support','description':'Integration Hub, device/interface status, EHR delivery, documents and lineage troubleshooting.'},
 'Admin':{'password':'ADMIN','role':'Portfolio Administrator','description':'Full portfolio access, including Logins & Roles.'}}
if 'auth_user' not in st.session_state: st.session_state.auth_user='Admin'
st.markdown(r'''<style>
:root{--rpm-teal:#087F8C;--rpm-blue:#2563EB;--rpm-navy:#0F2744;--rpm-ink:#172B3A;--rpm-muted:#64748B;--rpm-line:#DCE6EC;--rpm-soft:#F6FAFB;--rpm-green:#15803D;--rpm-amber:#B45309}
.stApp{background:linear-gradient(180deg,#F8FBFC 0,#FFFFFF 300px)}
.block-container{padding-top:3.4rem!important;max-width:1500px!important}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#102B49 0%,#0B2038 100%)!important;border-right:0!important}
[data-testid="stSidebar"] *{color:#E8F0F6}
[data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding-top:1rem!important}
[data-testid="stSidebar"] .stButton{margin:.12rem 0!important}
[data-testid="stSidebar"] .stButton>button{justify-content:flex-start!important;text-align:left!important;padding:.52rem .72rem!important;font-size:.88rem!important;font-weight:650!important;line-height:1.2!important;letter-spacing:.005em!important}
[data-testid="stSidebar"] .stButton>button p{font-size:.88rem!important;font-weight:650!important;text-align:left!important;white-space:normal!important;margin:0!important}
[data-testid="stSidebar"] h3{padding-left:.2rem!important}
[data-testid="stSidebar"] h3{color:#8FB4CE!important;font-size:.72rem!important;letter-spacing:.12em!important;text-transform:uppercase;margin-top:1.1rem!important}
[data-testid="stSidebar"] button{border:0!important;border-radius:10px!important;text-align:left!important;min-height:2.45rem!important;background:transparent!important}
[data-testid="stSidebar"] button:hover{background:rgba(255,255,255,.08)!important}
[data-testid="stSidebar"] button[kind="primary"]{background:#1E5EA8!important;box-shadow:inset 3px 0 0 #5EEAD4!important}
[data-testid="stSidebar"] hr{border-color:rgba(255,255,255,.12)!important}
.rpm-brand{margin:.15rem 0 .35rem!important}.rpm-brand small{font-size:.7rem;color:#64748B;font-weight:700;margin-left:.35rem}
.top-context{display:flex;justify-content:space-between;align-items:center;color:#64748B;font-size:.82rem;border-bottom:1px solid #E7EEF2;padding:0 0 .65rem;margin-bottom:.65rem}.top-user{font-weight:700;color:#334155}
.hero{padding:1.2rem 1.35rem;border:1px solid #DCE6EC;border-radius:18px;background:linear-gradient(135deg,#FFFFFF 0%,#F1FAFA 100%);box-shadow:0 8px 28px rgba(15,39,68,.05);margin:.4rem 0 1rem}.hero-kicker{font-size:.72rem;letter-spacing:.11em;text-transform:uppercase;color:#087F8C;font-weight:800}.hero h1{font-size:1.75rem!important;margin:.2rem 0!important;color:#0F2744}.hero p{color:#64748B;margin:.2rem 0 0;max-width:850px}.journey{display:grid;grid-template-columns:repeat(7,1fr);gap:7px;margin:.7rem 0 1.1rem}.journey-step{border:1px solid #DCE6EC;border-radius:12px;padding:.65rem .55rem;background:#fff;text-align:center;font-size:.77rem;font-weight:750;color:#334155}.journey-step b{display:block;width:24px;height:24px;border-radius:50%;background:#E4F5F4;color:#087F8C;margin:0 auto .35rem;padding-top:3px}.journey-step.active{background:#ECF8F7;border-color:#9DD8D4;color:#075F68}.insight-card{border:1px solid #CFE1EA;border-left:4px solid #087F8C;border-radius:14px;padding:1rem 1.1rem;background:#F8FCFD;margin:.5rem 0 1rem}.insight-card strong{color:#0F2744}.section-eyebrow{font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;color:#087F8C;font-weight:800;margin-bottom:.15rem}
[data-testid="stMetric"]{background:#fff;border:1px solid #DCE6EC;border-radius:14px;padding:.75rem 1rem;box-shadow:0 2px 8px rgba(15,39,68,.035)}
.stButton>button,.stDownloadButton>button{border-radius:10px!important;font-weight:700!important}
.stTabs [data-baseweb="tab-list"]{gap:.25rem;border-bottom:1px solid #DCE6EC}.stTabs [data-baseweb="tab"]{font-weight:700!important}

[data-testid="stMetricLabel"] p{font-size:.96rem!important;font-weight:700!important;color:var(--rpm-ink)!important}
[data-testid="stMetricValue"]{font-size:1.32rem!important;font-weight:650!important}
[data-testid="stDataFrame"] thead th{font-size:1.05rem!important;font-weight:800!important}
[data-testid="stDataFrame"] [role="columnheader"]{font-size:1.05rem!important;font-weight:800!important;color:var(--rpm-ink)!important}
[data-testid="stDataFrame"] [role="columnheader"] *{font-size:1.05rem!important;font-weight:800!important}
h1{font-size:2.05rem!important;font-weight:780!important} h2{font-size:1.55rem!important;font-weight:760!important} h3{font-size:1.22rem!important;font-weight:740!important}
.rpm-brand{display:flex;align-items:center;gap:.65rem;font-size:1.78rem;line-height:1.22;font-weight:780;color:#202938;margin:.1rem 0 .55rem;min-height:46px}.rpm-brand span:last-child{display:flex;align-items:baseline;flex-wrap:wrap;gap:.25rem}.rpm-brand small{white-space:nowrap}
.rpm-logo{display:inline-flex;align-items:center}
.trend-head{display:flex;align-items:center;gap:.5rem;font-size:1.02rem;font-weight:750;color:var(--rpm-ink);margin:.05rem 0 .25rem}
.trend-head svg{width:19px;height:19px;stroke:var(--rpm-teal)}
.trend-meta{font-size:.78rem;color:var(--rpm-muted);margin-top:-.2rem}
div[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--rpm-line)!important;border-radius:16px!important;box-shadow:0 1px 2px rgba(16,24,40,.04);background:#fff}
div[data-testid="stVerticalBlockBorderWrapper"]>div{border-radius:16px!important}
div[data-testid="stSelectbox"] label p{font-size:.78rem!important;font-weight:650!important;color:var(--rpm-muted)!important}
.role-chip{font-size:.82rem;font-weight:650;line-height:1.45}.stage-context{display:flex;align-items:center;gap:.65rem;padding:.72rem .9rem;margin:.15rem 0 .9rem;border:1px solid #CFE5E4;border-radius:12px;background:#F4FBFA;color:#334155}.stage-context strong{color:#075F68}.stage-pill{display:inline-flex;align-items:center;padding:.25rem .58rem;border-radius:999px;background:#087F8C;color:white;font-size:.72rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase;white-space:nowrap}.stage-note{font-size:.86rem;color:#526579}.journey-step.related{background:#F4FBFA;border-color:#BFE0DE;color:#075F68}

/* V6 enterprise shell */
header[data-testid="stHeader"]{height:0!important;background:transparent!important}
#MainMenu,footer{visibility:hidden}
.block-container{padding-top:1.15rem!important;padding-left:1.55rem!important;padding-right:1.55rem!important;max-width:1680px!important}
[data-testid="stSidebar"]{width:248px!important;min-width:248px!important;background:#0B2340!important}
[data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding:.75rem .7rem 1rem!important}
.side-brand{display:flex;align-items:center;gap:.62rem;padding:.45rem .42rem .8rem;margin-bottom:.2rem;border-bottom:1px solid rgba(255,255,255,.11)}
.side-brand b{display:block;color:#F8FBFF;font-size:.86rem;line-height:1.1;letter-spacing:-.01em}.side-brand small{display:block;color:#86A5BE;font-size:.65rem;margin-top:.18rem}
.side-mark{display:flex;align-items:center;justify-content:center;flex:0 0 auto}
[data-testid="stSidebar"] h3{font-size:.65rem!important;letter-spacing:.15em!important;color:#7FA3BD!important;margin:.95rem 0 .25rem!important;padding:0 .52rem!important;font-weight:800!important}
[data-testid="stSidebar"] .stButton>button{border-radius:8px!important;padding:.48rem .58rem!important;min-height:2.25rem!important;font-size:.80rem!important;font-weight:650!important;color:#DCE8F1!important}
[data-testid="stSidebar"] .stButton>button p{font-size:.80rem!important;line-height:1.15!important}
[data-testid="stSidebar"] button[kind="primary"]{background:#18579C!important;box-shadow:inset 3px 0 0 #5EEAD4!important;color:white!important}
.rpm-brand{font-size:1.35rem!important;min-height:34px!important;margin:0 0 .18rem!important;color:#102A43!important}.rpm-logo svg{width:28px!important;height:28px!important}.rpm-brand small{font-size:.62rem!important;color:#7C8B9A!important}
.top-context{margin:0 0 .45rem!important;padding:0 0 .48rem!important;font-size:.76rem!important}.crumb{color:#60758A}.top-user{font-size:.75rem!important}
[data-testid="stTextInput"] input{border-radius:9px!important;border-color:#D6E1E8!important;background:#FFFFFF!important}
.hero{padding:.82rem 1rem!important;border-radius:13px!important;margin:.25rem 0 .7rem!important;box-shadow:0 2px 10px rgba(15,39,68,.035)!important;background:#FFFFFF!important;border:1px solid #DFE8ED!important}
.hero-top{display:flex;justify-content:space-between;align-items:center}.hero h1{font-size:1.48rem!important;line-height:1.15!important;margin:.12rem 0!important}.hero p{font-size:.86rem!important;margin-top:.15rem!important}.hero-kicker{font-size:.64rem!important}.hero-stage{font-size:.64rem;font-weight:850;letter-spacing:.08em;text-transform:uppercase;color:#087F8C;background:#E8F7F5;border:1px solid #B9E2DE;border-radius:999px;padding:.22rem .52rem}
.stage-context{padding:.18rem .1rem!important;margin:0 0 .38rem!important;border:0!important;background:transparent!important;border-radius:0!important;font-size:.73rem!important;color:#728396!important}.stage-context strong{color:#087F8C!important;text-transform:uppercase;letter-spacing:.08em;font-size:.66rem}.stage-dot{width:7px;height:7px;background:#14B8A6;border-radius:50%;display:inline-block;flex:0 0 auto}
.workspace-tabs{display:flex;gap:.25rem;border-bottom:1px solid #DCE6EC;margin:.25rem 0 .75rem;padding-left:.1rem}.workspace-tabs span{font-size:.77rem;font-weight:700;color:#64748B;padding:.5rem .72rem;border-bottom:2px solid transparent}.workspace-tabs span.active{color:#1D4ED8;border-bottom-color:#2563EB;background:#F7FAFF;border-radius:7px 7px 0 0}
[data-testid="stMetric"]{border-radius:10px!important;padding:.62rem .75rem!important;box-shadow:none!important}.insight-card{border-radius:11px!important;padding:.78rem .9rem!important;margin:.4rem 0 .7rem!important}
[data-testid="stDataFrame"]{border:1px solid #E0E8ED;border-radius:10px;overflow:hidden}[data-testid="stDataFrame"] thead th,[data-testid="stDataFrame"] [role="columnheader"]{font-size:.84rem!important}
h1{font-size:2.05rem!important;line-height:1.16!important;font-weight:800!important;text-align:left!important;margin:.55rem 0 .45rem!important}
h2{font-size:1.62rem!important;line-height:1.2!important;font-weight:800!important;text-align:left!important;margin:1rem 0 .5rem!important}
h3{font-size:1.28rem!important;line-height:1.22!important;font-weight:780!important;text-align:left!important;margin:.9rem 0 .42rem!important}
[data-testid="stSidebar"]{min-width:272px!important;max-width:272px!important}
[data-testid="stSidebar"] h3{font-size:.78rem!important;letter-spacing:.13em!important;color:#A9C7DC!important;margin:1.25rem 0 .38rem!important;padding:0 .72rem!important;font-weight:850!important}
[data-testid="stSidebar"] .stButton>button{padding:.66rem .76rem!important;min-height:2.7rem!important;font-size:.92rem!important;font-weight:720!important;line-height:1.22!important;margin:.08rem 0!important}
[data-testid="stSidebar"] .stButton>button p{font-size:.92rem!important;font-weight:720!important;line-height:1.22!important}
.side-brand{padding:.9rem .7rem 1rem!important;margin-bottom:.45rem!important}.side-brand b{font-size:1rem!important}.side-brand small{font-size:.74rem!important}
.hero h1{font-size:1.9rem!important}.hero p{font-size:.98rem!important;line-height:1.5!important}.hero-kicker{font-size:.76rem!important}
.stage-context{font-size:.84rem!important;margin:.15rem 0 .7rem!important}.stage-context strong{font-size:.76rem!important}
.section-eyebrow{font-size:.76rem!important}.insight-card{font-size:.96rem!important;line-height:1.5!important}
.workspace-tabs span{font-size:.9rem!important;padding:.62rem .82rem!important}
.rpm-fit-card{border:1px solid #DCE6EC;border-radius:14px;background:#fff;padding:.95rem 1rem;margin:.55rem 0;box-shadow:0 2px 8px rgba(15,39,68,.035)}
.rpm-fit-card-top{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;margin-bottom:.55rem}.rpm-fit-name{font-size:1.08rem;font-weight:800;color:#102A43}.rpm-fit-meta{font-size:.82rem;color:#64748B;margin-top:.12rem}.rpm-fit-reason{font-size:.93rem;line-height:1.48;color:#334155;background:#F8FAFC;border-radius:9px;padding:.65rem .75rem;margin-top:.55rem}.fit-pill{display:inline-block;border-radius:999px;padding:.28rem .58rem;font-size:.76rem;font-weight:850;white-space:nowrap}.fit-green{background:#E8F7EE;color:#176B3A}.fit-amber{background:#FFF6DB;color:#8A5A00}.fit-slate{background:#EEF2F6;color:#475467}.fit-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.45rem;margin-top:.55rem}.fit-kv{font-size:.78rem;color:#64748B}.fit-kv b{display:block;color:#172B3A;font-size:.86rem;margin-top:.08rem}
@media(max-width:1100px){.fit-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}

/* V6.3 — full-information modern navigation shell, based on V6.1 */
[data-testid="stSidebar"]{min-width:320px!important;max-width:320px!important;width:320px!important;background:#F8FAFC!important;border-right:1px solid #DCE5EC!important}
[data-testid="stSidebar"] *{color:#24364B}
[data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding:.75rem .8rem 1.1rem!important}
.side-brand{background:#0B2948!important;border:0!important;border-radius:14px!important;padding:.9rem .9rem!important;margin:.1rem .05rem .9rem!important;box-shadow:0 5px 18px rgba(15,39,68,.12)}
.side-brand b{font-size:1.03rem!important;color:#FFFFFF!important;letter-spacing:-.015em}.side-brand small{font-size:.73rem!important;color:#B9D0E1!important;margin-top:.2rem!important}
.nav-section{display:flex;align-items:center;gap:.58rem;margin:1.15rem .22rem .35rem;padding:.1rem .25rem}.nav-section-icon{width:30px;height:30px;border-radius:9px;background:#E7F5F5;display:flex;align-items:center;justify-content:center;flex:0 0 auto}.nav-section-icon svg{width:17px;height:17px;stroke:#087F8C;fill:none;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}.nav-section-title{font-size:.82rem;font-weight:850;letter-spacing:.075em;text-transform:uppercase;color:#536A7D}.nav-section-rule{height:1px;background:#E4EBF0;flex:1}
[data-testid="stSidebar"] h3{display:none!important}
[data-testid="stSidebar"] .stButton{margin:.08rem 0!important;padding:0!important}
[data-testid="stSidebar"] .stButton>button{background:transparent!important;border:0!important;border-radius:9px!important;padding:.62rem .72rem .62rem 1rem!important;min-height:2.55rem!important;color:#31465A!important;box-shadow:none!important;font-size:.94rem!important;font-weight:650!important;transition:background .12s ease, color .12s ease, transform .12s ease!important}
[data-testid="stSidebar"] .stButton>button p{font-size:.94rem!important;font-weight:650!important;line-height:1.2!important;color:inherit!important;white-space:normal!important}
[data-testid="stSidebar"] .stButton>button:hover{background:#EDF4F8!important;color:#0B2948!important;transform:translateX(2px)}
[data-testid="stSidebar"] button[kind="primary"]{background:#E6F2FF!important;color:#0B4E91!important;box-shadow:inset 4px 0 0 #087F8C!important;font-weight:800!important}
[data-testid="stSidebar"] button[kind="primary"] p{font-weight:800!important;color:#0B4E91!important}
[data-testid="stSidebar"] hr{border-color:#DCE5EC!important;margin:.9rem .25rem!important}
.role-chip{display:block;background:#EEF4F7;border:1px solid #D9E5EC;border-radius:10px;padding:.65rem .75rem;color:#536A7D!important;font-size:.78rem!important;line-height:1.5!important}
.nav-hint{font-size:.73rem;color:#7A8D9C;margin:.1rem .35rem .55rem;line-height:1.4}.nav-hint b{color:#3D5367}
/* Keep the full app canvas airy while retaining all capabilities */
.block-container{padding-left:2rem!important;padding-right:2rem!important;max-width:1720px!important}
.hero{padding:1.05rem 1.2rem!important}.hero h1{font-size:2rem!important}.hero p{font-size:1rem!important}.section-eyebrow{font-size:.8rem!important}
h2{font-size:1.7rem!important}h3{font-size:1.34rem!important}
</style>''',unsafe_allow_html=True)
def login_screen():
    st.markdown(r'''<div class="rpm-brand"><span class="rpm-logo" aria-hidden="true"><svg viewBox="0 0 48 48" width="34" height="34"><rect x="3" y="3" width="42" height="42" rx="12" fill="#E6F7F7"/><path d="M9 25h7l3-8 5 16 4-11 3 6h8" fill="none" stroke="#087F8C" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><circle cx="38" cy="15" r="3" fill="#2F80ED"/></svg></span><span>Connected Care Intelligence Platform <small>v6.3</small></span></div>''', unsafe_allow_html=True)
    st.subheader('Secure Demo Sign In')
    st.info('Portfolio Demonstration Environment — all patients, credentials, measurements and workflows are synthetic. Demo authentication illustrates RBAC concepts and is not production healthcare security.')
    u=st.text_input('Username'); pw=st.text_input('Password',type='password')
    if st.button('Sign in',type='primary'):
        acct=DEMO_ACCOUNTS.get(u)
        if acct and pw==acct['password']:
            st.session_state.auth_user=u; st.session_state.selected_menu='1 · Today / Care Plan' if u=='Patient' else ('9 · Integration Hub / API' if u=='Integrations' else '4 · Clinical Command Center & Action Queue'); st.rerun()
        else: st.error('Invalid demo username or password.')
if not st.session_state.get('auth_user'): login_screen(); st.stop()
CURRENT_USER=st.session_state.auth_user; CURRENT_ROLE=DEMO_ACCOUNTS[CURRENT_USER]['role']
st.markdown(r'''<div class="rpm-brand"><span class="rpm-logo" aria-hidden="true"><svg viewBox="0 0 48 48" width="34" height="34"><rect x="3" y="3" width="42" height="42" rx="12" fill="#E6F7F7"/><path d="M9 25h7l3-8 5 16 4-11 3 6h8" fill="none" stroke="#087F8C" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><circle cx="38" cy="15" r="3" fill="#2F80ED"/></svg></span><span>Connected Care Intelligence Platform <small>v6.3</small></span></div>''', unsafe_allow_html=True)
st.markdown(f'''<div class="top-context"><span class="crumb">Connected Care Intelligence</span><span class="top-user">{CURRENT_USER} · {CURRENT_ROLE}</span></div>''', unsafe_allow_html=True)
_top_search=st.text_input('Global search',placeholder='Search patients, MRN, care path, alerts, cohorts or keywords…',label_visibility='collapsed',key='global_shell_search')
st.info('Portfolio prototype only. It does not diagnose, treat, or provide medical advice. ECG classifications are device-reported inputs; clinical decisions remain human-in-the-loop.')

@st.cache_data(show_spinner=False)
def build_research_data(n_participants=240, days=90):
    rng=random.Random(4060)
    cohort_map={
        'Lung Transplant':'Lung Transplant Home Spirometry',
        'COPD / Pulmonary':'COPD Remote Pulmonary Monitoring',
        'Pulmonary Home Rehab':'Pulmonary Home Rehabilitation',
        'Pneumonitis':'Pneumonitis Recovery Monitoring',
        'Respiratory Infection - Adult':'Post-Respiratory Infection Recovery',
        'Cardiology':'Cardiac Rhythm / 6L ECG',
        'Heart Failure':'Heart Failure Post-Discharge',
        'Coronary Artery Disease (CAD)':'CAD / Cardiac Recovery',
        'Hypertension':'Hypertension Monitoring',
        'Diabetes / CGM':'Diabetes / CGM Monitoring',
        'Chronic Kidney Disease':'CKD / AKI Transition Monitoring',
        'Post-Surgical Recovery':'Post-Surgical Recovery'
    }
    plans=list(cohort_map)
    rows=[]
    for i in range(1,n_participants+1):
        rid=f'RSP-{i:04d}'; operational_pid=f'ENT-{i:04d}'; plan=plans[(i-1)%len(plans)]; age=28+(i*7)%58; cohort=cohort_map[plan]
        base_fev1=round(1.5+(i%24)*0.075,2); base_spo2=94+(i%5); base_hr=62+(i%25); adherence=max(0.48,min(.99,.72+(i%20)/100+rng.uniform(-.08,.08)))
        trajectory=['Stable','Improving','Declining','Intermittent'][i%4]
        for d in range(0,days,3):
            if rng.random()>adherence: continue
            date=(datetime.now().date()-timedelta(days=days-1-d)).isoformat(); frac=d/max(days-1,1)
            drift={'Stable':0,'Improving':.10,'Declining':-.18,'Intermittent':-.04}[trajectory]*frac
            fev1=round(max(.7,base_fev1*(1+drift)+rng.uniform(-.08,.08)),2) if plan in SPIROMETRY_PLANS else None
            fvc=round(fev1/(.68+rng.uniform(.02,.12)),2) if fev1 else None
            ratio=round(100*fev1/fvc,1) if fvc else None; pef=round(230+(i%120)+rng.uniform(-25,25)) if fev1 else None
            quality=rng.choices(['A / acceptable','B / usable','Review quality'],[.72,.20,.08])[0] if fev1 else None
            spo2=max(86,min(100,round(base_spo2+(drift*10 if fev1 else 0)+rng.uniform(-1.5,1.5))))
            hr=max(45,min(145,round(base_hr+rng.uniform(-8,8))))
            ecg=None
            if plan in ['Cardiology','Heart Failure','Coronary Artery Disease (CAD)'] and d%6==0:
                ecg=rng.choices(['Normal Sinus Rhythm','Atrial Fibrillation','Tachycardia','Bradycardia','Unclassified'],[.66,.10,.08,.06,.10])[0]
            symptoms=max(0,min(5,round((1 if trajectory=='Stable' else 2)+(2*frac if trajectory=='Declining' else 0)+rng.uniform(-1,1))))
            alert=(spo2<92) or (fev1 and fev1<base_fev1*.85) or (ecg in ['Atrial Fibrillation','Tachycardia','Bradycardia']) or symptoms>=4
            intervention=alert and rng.random()<.88; outcome=rng.choices(['Stable at home','Earlier clinic review','Medication reviewed','Diagnostic testing','ED evaluation'],[.63,.16,.10,.08,.03])[0] if intervention else 'No intervention'
            systolic=round(118+(i%22)+rng.uniform(-8,8)) if plan in ['Heart Failure','Cardiology','Coronary Artery Disease (CAD)','Hypertension','CKD'] else None
            diastolic=round(70+(i%14)+rng.uniform(-5,5)) if systolic else None
            weight=round(145+(i%65)+rng.uniform(-2.5,2.5),1) if plan in ['Heart Failure','CKD','Post-Surgical Recovery'] else None
            glucose=round(95+(i%55)+rng.uniform(-15,20)) if plan=='Diabetes / CGM' else None
            rows.append({'Research Participant ID':rid,'Operational Link':operational_pid,'Care Path':plan,'Cohort':cohort,'Age Band':f'{(age//10)*10}s','Study Day':d+1,'Observation Date':date,'Trajectory':trajectory,'SpO2':spo2,'Heart Rate':hr,'Systolic BP':systolic,'Diastolic BP':diastolic,'Weight lb':weight,'Glucose mg/dL':glucose,'FEV1 L':fev1,'FVC L':fvc,'FEV1/FVC %':ratio,'PEF L/min':pef,'FEV1 % Personal Baseline':round(100*fev1/base_fev1,1) if fev1 else None,'Spirometry Quality':quality,'ECG Device Classification':ecg,'Symptom Burden (0-5)':symptoms,'Alert':alert,'Intervention':intervention,'Outcome':outcome,'Data Source':'Synthetic RPM research cohort'})
    return pd.DataFrame(rows)

def research_df(): return build_research_data()

def research_xlsx(df, title='RPM Research Export'):
    out=io.BytesIO()
    with pd.ExcelWriter(out,engine='openpyxl') as w:
        pd.DataFrame([{'Report':title,'Generated':datetime.now().strftime('%Y-%m-%d %H:%M'),'Scope':'100% synthetic/de-identified portfolio data','Important':'Associations are exploratory; not validated clinical evidence.'}]).to_excel(w,index=False,sheet_name='Report Summary')
        df.to_excel(w,index=False,sheet_name='Longitudinal Observations')
        df[['Research Participant ID','Care Path','Cohort','Age Band','Trajectory']].drop_duplicates().to_excel(w,index=False,sheet_name='Participants')
        df[df['FEV1 L'].notna()].to_excel(w,index=False,sheet_name='Spirometry')
        df[df['ECG Device Classification'].notna()].to_excel(w,index=False,sheet_name='ECG')
        df[['Research Participant ID','Observation Date','Symptom Burden (0-5)','Alert','Intervention','Outcome']].to_excel(w,index=False,sheet_name='Interventions Outcomes')
    return out.getvalue()

def export_bar(df,prefix):
    c1,c2=st.columns(2)
    c1.download_button('Download CSV',df.to_csv(index=False).encode(),file_name=f'{prefix}.csv',mime='text/csv',use_container_width=True)
    c2.download_button('Download Excel',research_xlsx(df,prefix),file_name=f'{prefix}.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',use_container_width=True)
    st.caption('CSV and Excel files can be imported directly into Google Sheets. Direct Google Workspace write-back would require authenticated OAuth/API integration and is not simulated here.')

def research_filters(df,key):
    a,b,c=st.columns(3); plans=a.multiselect('Care paths',sorted(df['Care Path'].unique()),key=key+'p'); cohorts=b.multiselect('Cohorts',sorted(df['Cohort'].unique()),key=key+'c'); traj=c.multiselect('Trajectories',sorted(df['Trajectory'].unique()),key=key+'t')
    x=df.copy()
    if plans: x=x[x['Care Path'].isin(plans)]
    if cohorts: x=x[x['Cohort'].isin(cohorts)]
    if traj: x=x[x['Trajectory'].isin(traj)]
    return x

def metric_card(label,value,helptext=''):
    st.metric(label,value,help=helptext or None)

patient_menu=['1 · Today / Care Plan','2 · Patient Home & Daily Check-In','3 · Communication Center','3A · Education Center']
clinical_menu=['4 · Clinical Command Center & Action Queue','4A · Education & Questionnaire Library','4B · RPM Fit & Transition Queue','5 · Patient 360 & Trends','6 · Clinician Interventions','7 · Care Coordination']
integration_menu=['8 · ECG & Spirometry Documents','9 · Integration Hub / API','10 · Mock EHR','11 · Patient Identity & Duplicate Prevention','12 · Data Lineage & Audit']
ai_menu=['13 · AI Agent Center','14 · Care Pathway Engine','15 · Architecture & Product']
research_menu=['16 · Research Analytics Overview','16A · Cohort Catalog','17 · Cohort Explorer','18 · Spirometry Research','19 · 6L ECG Research','20 · Reports & Exports','21 · Research Analytics Guide']
if CURRENT_USER=='Admin': ai_menu.append('15A · Logins & Roles')
if 'selected_menu' not in st.session_state:
    st.session_state.selected_menu=patient_menu[0]

st.sidebar.markdown('''<div class="side-brand"><span class="side-mark"><svg viewBox="0 0 32 32" width="24" height="24"><rect width="32" height="32" rx="9" fill="#DFF8F5"/><path d="M5 17h5l2-6 4 12 3-8 2 4h6" fill="none" stroke="#087F8C" stroke-width="2.2" stroke-linecap="round"/></svg></span><span><b>RPM Connected Care</b><small>Intelligence Platform</small></span></div>''',unsafe_allow_html=True)
st.sidebar.markdown('<div class="nav-hint"><b>Navigate the full platform</b><br>Capabilities stay visible and grouped by workflow.</div>',unsafe_allow_html=True)

NAV_ICONS={
 'PATIENT EXPERIENCE':'<svg viewBox="0 0 24 24"><path d="M12 21s-7-4.6-7-10a4 4 0 0 1 7-2.7A4 4 0 0 1 19 11c0 5.4-7 10-7 10Z"/><path d="M9 12h2l1-2 2 4 1-2h2"/></svg>',
 'CONNECTED CARE':'<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M7 12h3l2-4 3 8 2-4h2"/></svg>',
 'PLATFORM & INTEGRATION':'<svg viewBox="0 0 24 24"><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.3 10.9 15.7 7.1M8.3 13.1l7.4 3.8"/></svg>',
 'AI & CONFIGURATION':'<svg viewBox="0 0 24 24"><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/><circle cx="12" cy="12" r="4"/></svg>',
 'RESEARCH ANALYTICS':'<svg viewBox="0 0 24 24"><path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4A2 2 0 0 0 19 18l-5-9V3"/><path d="M7.5 15h9"/></svg>'
}
NAV_SHORT={
 'Clinical Command Center & Action Queue':'Command Center',
 'Patient Home & Daily Check-In':'Daily Check-In',
 'RPM Fit & Transition Queue':'RPM Fit & Transition',
 'Patient 360 & Trends':'Patient 360',
 'Patient Identity & Duplicate Prevention':'Identity & MPI',
 'Research Analytics Overview':'Research Overview',
 'Architecture & Product':'Architecture & Product Story',
}
def nav_group(title, items):
    icon=NAV_ICONS.get(title,'')
    st.sidebar.markdown(f'<div class="nav-section"><span class="nav-section-icon">{icon}</span><span class="nav-section-title">{title}</span><span class="nav-section-rule"></span></div>',unsafe_allow_html=True)
    for item in items:
        active=st.session_state.selected_menu==item
        clean=item.split(' · ',1)[1] if ' · ' in item else item
        label=NAV_SHORT.get(clean,clean)
        if st.sidebar.button(label,key='nav_'+item,use_container_width=True,type='primary' if active else 'secondary'):
            st.session_state.selected_menu=item
            st.rerun()

if CURRENT_USER=='Patient': nav_group('PATIENT EXPERIENCE',patient_menu)
elif CURRENT_USER=='Integrations': nav_group('PLATFORM & INTEGRATION',integration_menu)
elif CURRENT_USER=='Researcher': nav_group('RESEARCH ANALYTICS',research_menu)
elif CURRENT_USER in ['Clinician','Provider']:
    nav_group('CONNECTED CARE',clinical_menu); nav_group('PLATFORM & INTEGRATION',[x for x in integration_menu if x.startswith(('8 ·','10 ·','12 ·'))]); nav_group('RESEARCH ANALYTICS',research_menu)
elif CURRENT_USER=='RPM Admin':
    nav_group('PATIENT EXPERIENCE',patient_menu); nav_group('CONNECTED CARE',clinical_menu); nav_group('PLATFORM & INTEGRATION',integration_menu); nav_group('AI & CONFIGURATION',['14 · Care Pathway Engine','15 · Architecture & Product']); nav_group('RESEARCH ANALYTICS',research_menu)
else:
    nav_group('PATIENT EXPERIENCE',patient_menu); nav_group('CONNECTED CARE',clinical_menu); nav_group('PLATFORM & INTEGRATION',integration_menu); nav_group('AI & CONFIGURATION',ai_menu); nav_group('RESEARCH ANALYTICS',research_menu)
st.sidebar.divider(); st.sidebar.markdown(f'<span class="role-chip">Signed in as: {CURRENT_USER}<br>{CURRENT_ROLE}</span>',unsafe_allow_html=True)
if st.sidebar.button('Sign out',use_container_width=True): st.session_state.auth_user=None; st.rerun()
menu=st.session_state.selected_menu

def journey_strip(active='Monitor', related=None):
    steps=['Identify','Enroll','Prepare','Activate','Monitor','Intervene','Learn']
    active_set={active} if isinstance(active,str) else set(active)
    related_set=set(related or [])
    html='<div class="journey">'
    for i,label in enumerate(steps,1):
        cls='journey-step active' if label in active_set else ('journey-step related' if label in related_set else 'journey-step')
        html+=f'<div class="{cls}"><b>{i}</b>{label}</div>'
    html+='</div>'
    st.markdown(html,unsafe_allow_html=True)

def stage_context(stage, note):
    st.markdown(f'<div class="stage-context"><span class="stage-dot"></span><span><strong>{stage}</strong> · {note}</span></div>',unsafe_allow_html=True)

STAGE_BY_PREFIX={
 '1 ·':('Monitor','Patient monitoring tasks, education and daily care-plan engagement.'),
 '2 ·':('Monitor','Capture today’s readings, questionnaires and patient-reported information.'),
 '3 ·':('Intervene','Patient-care-team communication supporting follow-up and intervention.'),
 '3A ·':('Monitor','Patient education that supports safe participation and adherence.'),
 '4 ·':('Monitor','Clinical surveillance, prioritization and action queue for active RPM patients.'),
 '4A ·':('Intervene','Assign education or questionnaires as part of the care-team response.'),
 '4B ·':('Identify → Enroll → Prepare → Activate','Transition workflow from candidate identification through enrollment, kit readiness and activation.'),
 '5 ·':('Monitor','Longitudinal Patient 360 review of measurements, devices, symptoms and results.'),
 '6 ·':('Intervene','Document human outreach, escalation and closed-loop clinical actions.'),
 '7 ·':('Intervene','Coordinate services and operational follow-through around the patient.'),
 '8 ·':('Monitor','Review ECG/spirometry result documents generated during monitoring.'),
 '9 ·':('Monitor','Observe data movement from connected devices into normalized clinical interfaces.'),
 '10 ·':('Monitor','Verify RPM data and documents represented in the mock EHR.'),
 '11 ·':('Identify','Resolve patient identity before enrollment, monitoring and research linkage.'),
 '12 ·':('Monitor','Trace data, access and workflow events across the monitoring lifecycle.'),
 '13 ·':('Monitor → Intervene','AI-assisted prioritization supports human review; it does not replace clinical judgment.'),
 '14 ·':('Enroll → Monitor','Configure synthetic care-path tasks and escalation logic used after enrollment.'),
 '15 ·':('End-to-End','Product architecture connects every stage of the RPM operating model.'),
 '15A ·':('Platform Administration','Role and access demonstration supporting the full lifecycle.'),
 '16 ·':('Learn','De-identified longitudinal RPM data becomes population-level research insight.'),
 '16A ·':('Learn','Understand the purpose, population and signals represented by each research cohort.'),
 '17 ·':('Learn','Explore governed cohorts and analytical subgroups without exposing operational MRNs.'),
 '18 ·':('Learn','Study longitudinal home-spirometry patterns, quality and related clinical context.'),
 '19 ·':('Learn','Study device-reported 6L ECG patterns, quality, follow-up and subsequent actions.'),
 '20 ·':('Learn','Turn governed research datasets into interpretable reports and exports.'),
 '21 ·':('Learn','Explain what research outputs mean and how evidence can inform future care improvement.')}
for _prefix,(_stage,_note) in STAGE_BY_PREFIX.items():
    if menu.startswith(_prefix):
        stage_context(_stage,_note)
        break

def page_hero(kicker,title,body):
    stage=None
    for _p,(_s,_n) in STAGE_BY_PREFIX.items():
        if menu.startswith(_p): stage=_s; break
    badge=f'<span class="hero-stage">{stage}</span>' if stage else ''
    st.markdown(f'<div class="hero"><div class="hero-top"><div class="hero-kicker">{kicker}</div>{badge}</div><h1>{title}</h1><p>{body}</p></div>',unsafe_allow_html=True)

if menu.startswith('1 ·'):
    page_hero('PATIENT EXPERIENCE','Today / Care Plan','A focused daily plan showing what is due, what is complete, and what needs attention.')
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
    page_hero('PATIENT EXPERIENCE','Patient Home & Daily Check-In','A simple daily workflow for connected readings, questionnaires, requested samples, and care-team communication.')
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

    st.subheader(f"{p['care_plan']} Daily Questionnaire")
    answers={}
    for key,q in questionnaire_for(p['care_plan']): answers[key]=st.radio(q,['No','Yes'],horizontal=True,key=f'q_{pid}_{key}',index=1 if key=='meds' else 0)
    if st.button('Save Daily Questionnaire',key='save_q_'+pid):
        target=latest_for(pid)
        if target:
            target['questionnaire']=answers; target['sob']=answers.get('sob')=='Yes'; target['chest']=answers.get('chest')=='Yes'; target['dizzy']=answers.get('dizzy')=='Yes'; target['meds']=answers.get('meds')=='Yes'; log(target['event_id'],'Daily questionnaire submitted'); st.success('Daily questionnaire saved to the latest patient event.')
        else: st.warning('Save today’s readings first, then save the questionnaire.')

    st.subheader('Patient Samples')
    st.caption('Optional patient-generated media. Samples use their own save action and are routed to the clinical review queue.')
    audio_sample=st.audio_input('Record cough / breathing audio (optional)')
    image_sample=st.camera_input('Take a patient photo / symptom image (optional)')
    sample_note=st.text_input('Sample note (optional)',placeholder='Example: cough sample after morning questionnaire')
    if st.button('Save Patient Sample',key='save_sample_'+pid):
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
    page_hero('CONNECTED CARE','Clinical Command Center','Prioritize the work that matters, understand why a patient needs attention, and move from signal to human action.')
    active_count=sum(1 for p in PATIENTS.values() if p.get('lifecycle_status','Active Monitoring')=='Active Monitoring')
    research_count=research_df()['Research Participant ID'].nunique()
    k1,k2,k3,k4=st.columns(4)
    k1.metric('Active monitoring',active_count)
    k2.metric('Research participants',research_count)
    k3.metric('Discharge candidates',len(DISCHARGE_CANDIDATES))
    k4.metric('Data capture','94%')
    st.markdown('<div class="insight-card"><div class="section-eyebrow">Clinical intelligence</div><strong>Start with exceptions, not rows.</strong> This workspace separates clinical, engagement, and technical signals, then keeps the clinician or RPM team member in control of the next action.</div>',unsafe_allow_html=True)
    st.markdown('<div class="workspace-tabs"><span class="active">Patients needing attention</span><span>Recent results</span><span>Discharge candidates</span><span>Device issues</span></div>',unsafe_allow_html=True)
    aq=[]
    for _pid,_p in PATIENTS.items():
        if _p.get('lifecycle_status','Active Monitoring') != 'Active Monitoring': continue
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
        aq_search=f1.text_input('Search action queue',key='aq_search',placeholder='Patient, reason, care plan, clinician…')
        aq_plan=f2.multiselect('Filter care plan',sorted(aqdf['Care Plan'].unique()),key='aq_plan')
        aq_pri=f3.multiselect('Filter priority',['🔴 HIGH','🟡 MEDIUM','🟢 LOW'],key='aq_pri')
        if aq_search: aqdf=aqdf[aqdf.astype(str).apply(lambda r:r.str.contains(aq_search,case=False,na=False).any(),axis=1)]
        if aq_plan: aqdf=aqdf[aqdf['Care Plan'].isin(aq_plan)]
        if aq_pri: aqdf=aqdf[aqdf['Priority'].isin(aq_pri)]
        aqdf=aqdf.sort_values('_rank').drop(columns=['_rank'])
        st.dataframe(aqdf,hide_index=True,use_container_width=True)
    st.divider()
    st.write('Population view for clinicians: alerts, assigned clinician, connectivity, device status, and patient communications.')
    with st.expander('Create Patient / Add New Patient'):
        patient_creation_panel('Clinical Dashboard','clinical')
    rows=[]
    for pid,p in PATIENTS.items():
        if p.get('lifecycle_status','Active Monitoring') != 'Active Monitoring': continue
        e=latest_for(pid); devs=st.session_state.devices.get(pid,[]); problems=sum((not d['connected']) or (not d['wifi']) or d['battery']<30 for d in devs); unread=sum(m['patient_id']==pid and m['sender']=='Patient' and not m.get('read',False) for m in st.session_state.messages); new_samples=sum(m['patient_id']==pid and not m.get('reviewed',False) for m in st.session_state.patient_samples)
        if e: pri,_,_=assess(e); spo=e['spo2']; hr=e['ecg_hr']; ast=alert_status(e)
        else: pri='AWAITING DATA'; spo='—'; hr='—'; ast='No RPM reading yet'
        rows.append({'Priority':priority_badge(pri),'Patient':p['name'],'MRN':p['mrn'],'Assigned clinician':p['clinician'],'Care Plan':p['care_plan'],'SpO₂':spo,'HR':hr,'Alert status':ast,'Device issues':problems,'Unread chat':unread,'New samples':new_samples,'_pid':pid,'_rank':priority_rank(pri)})
    popdf=pd.DataFrame(rows)
    st.markdown('**Population filters**')
    f1,f2,f3,f4=st.columns(4)
    pop_search=f1.text_input('Global search',key='pop_search',placeholder='Last name, MRN, care plan…')
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
        st.session_state['patient360_return_menu']='4 · Clinical Command Center & Action Queue'
        st.session_state['patient360_opened_from_population']=True
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
        st.subheader('Patient Samples — Clinical Review')
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

elif menu.startswith('4B ·'):
    st.header('RPM Fit, Enrollment & Kit Transition')
    st.caption('Synthetic discharge-candidate workflow: identify potential RPM fit, complete human enrollment review, configure only the devices required by the selected care path, fulfill the kit, and activate monitoring.')
    st.info('A high Fit Score never auto-enrolls a patient. Clinical stability, medical necessity, consent, device/digital readiness and human confirmation remain required.')
    rows=[]
    for r in DISCHARGE_CANDIDATES:
        score=fit_score(r); bucket=fit_bucket(r); wf=transition_state(r['mrn'])
        rows.append({'Fit':'● '+bucket,'Score':score,'Patient':r['patient'],'MRN':r['mrn'],'Expected discharge':r['discharge'],'Suggested care plan':r['care_plan'],'Enrollment':wf['enrollment_status'],'Kit':wf['kit_status'],'Activation':wf['activation_status'],'Why flagged':r['reason']})
    df=pd.DataFrame(rows); q=st.text_input('Search transition queue',placeholder='Patient, MRN, care plan, status, discharge timing…')
    if q: df=df[df.astype(str).apply(lambda x:x.str.contains(q,case=False,na=False)).any(axis=1)]
    order={'● RPM FIT':0,'● REVIEW / ENABLE':1,'● NOT CURRENTLY FIT':2}; df['_order']=df['Fit'].map(order); df=df.sort_values(['_order','Score'],ascending=[True,False]).drop(columns='_order')
    def _fit_style(v):
        if 'RPM FIT' in str(v) and 'NOT' not in str(v): return 'background-color:#E8F7EE;color:#176B3A;font-weight:800'
        if 'REVIEW / ENABLE' in str(v): return 'background-color:#FFF6DB;color:#8A5A00;font-weight:800'
        if 'NOT CURRENTLY FIT' in str(v): return 'background-color:#F2F4F7;color:#475467;font-weight:800'
        return ''
    st.subheader('Transition candidates')
    st.caption('The rationale is intentionally shown in full on each candidate card so users never need to double-click a table cell.')
    visible_mrns=set(df['MRN'].tolist())
    visible_candidates=[r for r in DISCHARGE_CANDIDATES if r['mrn'] in visible_mrns]
    for rcard in visible_candidates:
        sc=fit_score(rcard); bk=fit_bucket(rcard); wfcard=transition_state(rcard['mrn'])
        pill='fit-green' if bk=='RPM FIT' else ('fit-amber' if bk=='REVIEW / ENABLE' else 'fit-slate')
        st.markdown(f'''<div class="rpm-fit-card"><div class="rpm-fit-card-top"><div><div class="rpm-fit-name">{rcard['patient']}</div><div class="rpm-fit-meta">{rcard['mrn']} · {rcard['care_plan']}</div></div><span class="fit-pill {pill}">{bk}</span></div><div class="fit-grid"><div class="fit-kv">Fit score<b>{sc} / 13</b></div><div class="fit-kv">Expected discharge<b>{rcard['discharge']}</b></div><div class="fit-kv">Enrollment<b>{wfcard['enrollment_status']}</b></div><div class="fit-kv">Activation<b>{wfcard['activation_status']}</b></div></div><div class="rpm-fit-reason"><b>Why flagged</b><br>{rcard['reason']}</div></div>''',unsafe_allow_html=True)
    st.subheader('Enrollment, kit fulfillment & activation')
    chosen=st.selectbox('Select a transition candidate to work',range(len(DISCHARGE_CANDIDATES)),format_func=lambda i:f"{DISCHARGE_CANDIDATES[i]['patient']} · {DISCHARGE_CANDIDATES[i]['mrn']} · {DISCHARGE_CANDIDATES[i]['care_plan']}")
    r=DISCHARGE_CANDIDATES[chosen]; wf=transition_state(r['mrn']); score=fit_score(r); bucket=fit_bucket(r)
    with st.container(border=True):
        st.markdown('#### Why this patient was flagged')
        st.write(r['reason'])
        c1,c2,c3=st.columns(3); c1.metric('RPM Fit Segment',bucket); c2.metric('Fit Score',f'{score} / 13'); c3.metric('Expected discharge',r['discharge'])
        st.caption('Fit factors: condition fit · measurable physiologic signal · transition need · active management need · willingness/consent · support · connectivity/device readiness · RPM-team capacity. Human review remains required.')
    a,b,c,d=st.columns(4); a.metric('Fit segment',bucket); b.metric('Fit score',f'{score}/13'); c.metric('Discharge',r['discharge']); d.metric('Enrollment',wf['enrollment_status'])
    st.markdown('#### Care-path kit configuration')
    st.caption('Portfolio defaults are configurable. ECG and spirometry are included only when appropriate to the selected pathway/order—not in every RPM kit.')
    devices=st.multiselect('Devices / supplies for this patient',kit_for(r['care_plan']),default=kit_for(r['care_plan']),key='kit_'+r['mrn'])
    method=st.radio('Fulfillment method',['Ship to home','Provide during acute-care discharge'],horizontal=True,index=0 if wf['delivery_method']=='Ship to home' else 1,key='delivery_'+r['mrn']); wf['delivery_method']=method
    if method=='Ship to home': st.info('Demo ship-to address will be verified before fulfillment: 200 Transition Home Way, Austin, TX 78701.')
    enrollment_options=['Candidate','Under review','Patient contacted','Consent obtained','Ready to enroll','Enrolled','Deferred','Declined','Not eligible']
    wf['enrollment_status']=st.selectbox('Enrollment status',enrollment_options,index=enrollment_options.index(wf['enrollment_status']) if wf['enrollment_status'] in enrollment_options else 0,key='enroll_status_'+r['mrn'])
    kit_options=['Not configured','Configured','Order created','Packed','Shipped','In transit','Delivered','Patient confirmed receipt','Prepared for discharge','Given at discharge','Device missing / issue','Replacement requested']
    wf['kit_status']=st.selectbox('Kit fulfillment status',kit_options,index=kit_options.index(wf['kit_status']) if wf['kit_status'] in kit_options else 0,key='kit_status_'+r['mrn'])
    activation_options=['Not started','Setup pending','Setup started','Devices paired','Training completed','Test reading received','Active monitoring','Needs technical support']
    wf['activation_status']=st.selectbox('Activation status',activation_options,index=activation_options.index(wf['activation_status']) if wf['activation_status'] in activation_options else 0,key='activation_'+r['mrn'])
    c1,c2=st.columns(2)
    with c1:
        if st.button('Save kit / fulfillment',type='primary',use_container_width=True):
            st.session_state.kit_orders.append({'mrn':r['mrn'],'patient':r['patient'],'care_plan':r['care_plan'],'devices':devices,'method':method,'kit_status':wf['kit_status'],'time':datetime.now().isoformat()}); st.success('Kit configuration and fulfillment status saved to the transition workflow.')
    with c2:
        if st.button('Enroll in RPM & add to My Patients',use_container_width=True,disabled=(bucket=='NOT CURRENTLY FIT' or wf['enrollment_status'] not in ['Ready to enroll','Enrolled'])):
            pid=enroll_candidate(r); st.success(f"{r['patient']} is now in the shared RPM patient registry as {PATIENTS[pid]['mrn']}. Patient 360 will show the patient immediately; trends begin after the first device reading.")
    if wf.get('patient_id'): st.success(f"Active RPM registry link: {PATIENTS[wf['patient_id']]['name']} · {PATIENTS[wf['patient_id']]['mrn']} · {PATIENTS[wf['patient_id']]['care_plan']}")
    st.markdown('#### Transition journey')
    journey_strip(['Identify','Enroll','Prepare','Activate'])
    st.write('Candidate → Under review → Consent obtained → Ready to enroll → Enrolled → Kit configured → Shipped / Given at discharge → Patient received kit → Devices paired → Training completed → Test reading received → Active monitoring')
    st.subheader('Illustrative RPM Fit Score')
    st.markdown('**Maximum 13 points.** Condition fit (0–3) + measurable physiologic signal (0–2) + transition/readmission need (0–2) + active management need (0–2) + willingness/consent (0–1) + ability/caregiver support (0–1) + connectivity/device readiness (0–1) + RPM team capacity (0–1).')
    st.caption('Prototype segmentation: 9–13 RPM FIT; 6–8 REVIEW / ENABLE; 0–5 NOT CURRENTLY FIT. Synthetic design assumptions; validation and governance are required before production use.')

elif menu.startswith('5 ·'):
    nav_left,nav_right=st.columns([1,5],vertical_alignment='center')
    if st.session_state.get('patient360_opened_from_population'):
        if nav_left.button('← Back to Command Center',key='back_to_command_center',use_container_width=True):
            st.session_state.selected_menu=st.session_state.get('patient360_return_menu','4 · Clinical Command Center & Action Queue')
            st.session_state['patient360_opened_from_population']=False
            st.rerun()
        nav_right.caption('Opened from Clinical Command Center · use Back to return to your filtered patient queue.')
    st.header('Patient 360 & Trends')
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
        weight_unit=trend_chart(pid,'weight','Weight Trend','lb','weight_min','weight_max','lb',compact_unit_selector=True)
        trend_chart(pid,'rr','Respiratory Rate Trend','breaths/min','rr_min','rr_max')
        temp_unit=trend_chart(pid,'skin_temp','Skin Temperature Trend','°C','temp_min','temp_max','°C',compact_unit_selector=True)
        trend_chart(pid,'glucose','Glucose (CGM) Trend','mg/dL','glucose_min','glucose_max')
        if p['care_plan'] in SPIROMETRY_PLANS:
          with st.container(border=True):
            sh,sb=st.columns([5,1],vertical_alignment='center'); sh.markdown(f'<div class="trend-head">{_trend_icon("rr")}<span>Spirometry Trend</span></div>',unsafe_allow_html=True)
            _sp=[x for x in patient_events(pid) if x.get('fev1') is not None]
            if _sp:
                _df=pd.DataFrame([{'Date/Time':x['timestamp'][:16].replace('T',' '),'FEV1 (L)':round(x['fev1'],2),'FVC (L)':round(x['fvc'],2),'FEV1/FVC':round(x['fev1']/x['fvc'],2),'PEF (L/min)':round(x['pef'],0),'FEV1 % personal baseline':round(x['fev1_pct_baseline'],0)} for x in reversed(_sp)])
                st.line_chart(pd.DataFrame([{'Date':x['timestamp'][:10],'FEV1 (L)':x['fev1'],'FVC (L)':x['fvc']} for x in _sp]).set_index('Date'))
                st.dataframe(_df,hide_index=True,use_container_width=True)
                sp_ids=[x['event_id'] for x in reversed(_sp)]
                sp_sel=st.selectbox('Select a spirometry result',sp_ids,format_func=lambda eid: next(x['timestamp'][:16].replace('T',' ')+' · '+eid for x in _sp if x['event_id']==eid),key='sp_hist_'+pid)
                latest_sp=next(x for x in _sp if x['event_id']==sp_sel)
                v1,v2=st.columns([1,1])
                if v1.button('View selected result',key='spiro_pdf_'+pid,use_container_width=True): st.session_state['show_spiro_pdf_'+pid]=not st.session_state.get('show_spiro_pdf_'+pid,False)
                _pdf=spirometry_pdf_bytes(latest_sp)
                v2.download_button('Download PDF',_pdf,file_name=f"{latest_sp['event_id']}_spirometry.pdf",mime='application/pdf',key='dl_spiro_'+pid,use_container_width=True)
                if st.session_state.get('show_spiro_pdf_'+pid,False): show_pdf_inline(_pdf)
                st.caption('Synthetic home-spirometry values. The alert engine compares FEV1 with the patient’s synthetic personal baseline; this is a portfolio rule, not a diagnostic criterion.')
        with st.container(border=True):
          st.markdown(f'<div class="trend-head">{_trend_icon("ecg")}<span>ECG Trend & Result History</span></div>',unsafe_allow_html=True)
          _ecgs=list(reversed(patient_events(pid)))
          _edf=pd.DataFrame([{'Date/Time':x['timestamp'][:16].replace('T',' '),'Heart Rate':x['ecg_hr'],'Device Classification':x['ecg'],'Source':x.get('source','Device'),'Document':'Available' if x.get('pdf_ok',True) else 'Held'} for x in _ecgs])
          if not _edf.empty:
              _plot=pd.DataFrame([{'Date':x['timestamp'][:10],'Heart Rate (bpm)':x['ecg_hr']} for x in reversed(_ecgs)]).set_index('Date')
              st.line_chart(_plot)
              st.dataframe(_edf,hide_index=True,use_container_width=True)
              ecg_ids=[x['event_id'] for x in _ecgs]
              ecg_sel=st.selectbox('Select an ECG result',ecg_ids,format_func=lambda eid: next(x['timestamp'][:16].replace('T',' ')+' · '+x['ecg']+' · '+eid for x in _ecgs if x['event_id']==eid),key='ecg_hist_'+pid)
              selected_ecg=next(x for x in _ecgs if x['event_id']==ecg_sel)
              e1,e2=st.columns([1,1])
              if e1.button('View selected result',key='ecg_pdf_trend_'+pid,use_container_width=True): st.session_state['show_ecg_pdf_'+pid]=not st.session_state.get('show_ecg_pdf_'+pid,False)
              _epdf=ecg_pdf_bytes(selected_ecg,selected_ecg.get('pdf_ok',True))
              e2.download_button('Download PDF',_epdf,file_name=f"{selected_ecg['event_id']}_ecg.pdf",mime='application/pdf',key='dl_ecg_'+pid,use_container_width=True)
              if st.session_state.get('show_ecg_pdf_'+pid,False): show_pdf_inline(_epdf)
        st.subheader('Patient Samples')
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
    st.header('Care Coordination')
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
    st.header('ECG & Spirometry Documents')
    st.caption('Patient-level document repository. ECG and spirometry reports are shown independently so every available historical result remains discoverable.')
    pid=st.selectbox('Patient',list(PATIENTS),format_func=lambda x:f"{PATIENTS[x]['name']} · {PATIENTS[x]['mrn']} · {PATIENTS[x]['care_plan']}",key='docs_patient')
    es=patient_events(pid)
    ecg_docs=list(reversed(es))
    spiro_docs=[e for e in reversed(es) if e.get('fev1') is not None]
    d1,d2,d3=st.columns(3)
    d1.metric('ECG reports',len(ecg_docs)); d2.metric('Spirometry reports',len(spiro_docs)); d3.metric('Care plan',PATIENTS[pid]['care_plan'])
    ecg_tab,spiro_tab=st.tabs([f'ECG Reports ({len(ecg_docs)})',f'Spirometry Reports ({len(spiro_docs)})'])
    with ecg_tab:
        if not ecg_docs: st.info('No ECG results are available for this patient.')
        for i,e in enumerate(ecg_docs):
            with st.expander(f"{e['timestamp'][:16].replace('T',' ')} · {e['ecg']} · {e['event_id']}",expanded=(i==0)):
                a,b=st.columns(2)
                pdf=ecg_pdf_bytes(e,e.get('pdf_ok',True))
                if a.button('View ECG result',key='docs_view_ecg_'+e['event_id'],use_container_width=True):
                    st.session_state['docs_show_ecg']=None if st.session_state.get('docs_show_ecg')==e['event_id'] else e['event_id']
                b.download_button('Download ECG PDF',pdf,file_name=f"{e['event_id']}_{PATIENTS[pid]['mrn']}_ECG.pdf",mime='application/pdf',key='docs_dl_ecg_'+e['event_id'],use_container_width=True)
                checks={'Patient name on every page':True,'MRN on every page':e.get('pdf_ok',True),'DOB on every page':True,'ECG timestamp':True,'Patient association':True}
                st.dataframe(pd.DataFrame([{'Check':k,'Result':'PASS' if v else 'FAIL'} for k,v in checks.items()]),hide_index=True,use_container_width=True)
                if st.session_state.get('docs_show_ecg')==e['event_id']: show_pdf_inline(pdf)
                st.success('DOCUMENT VALIDATION PASSED — eligible for downstream transmission.') if e.get('pdf_ok',True) else st.error('DOCUMENT VALIDATION FAILED — held; mock EHR Media filing blocked.')
    with spiro_tab:
        if not spiro_docs:
            st.info('No spirometry results are available for this patient. Spirometry appears only when the care pathway/order includes home spirometry and a result has been received.')
        for i,e in enumerate(spiro_docs):
            with st.expander(f"{e['timestamp'][:16].replace('T',' ')} · FEV1 {e['fev1']:.2f} L · {e['event_id']}",expanded=(i==0)):
                st.write(f"**FEV1:** {e['fev1']:.2f} L  |  **FVC:** {e['fvc']:.2f} L  |  **FEV1/FVC:** {e['fev1_fvc']:.1f}%  |  **PEF:** {e['pef']:.0f} L/min  |  **FEV1 % personal baseline:** {e['fev1_pct_baseline']:.0f}%")
                a,b=st.columns(2)
                pdf=spirometry_pdf_bytes(e)
                if a.button('View spirometry result',key='docs_view_sp_'+e['event_id'],use_container_width=True):
                    st.session_state['docs_show_sp']=None if st.session_state.get('docs_show_sp')==e['event_id'] else e['event_id']
                b.download_button('Download Spirometry PDF',pdf,file_name=f"{e['event_id']}_{PATIENTS[pid]['mrn']}_Spirometry.pdf",mime='application/pdf',key='docs_dl_sp_'+e['event_id'],use_container_width=True)
                st.caption(f"Session quality: {e.get('spirometry_quality','Synthetic session')} · Result retained as a separate longitudinal document.")
                if st.session_state.get('docs_show_sp')==e['event_id']: show_pdf_inline(pdf)

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
    st.divider(); st.subheader('Video-call simulation')
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
    with st.expander('Create Patient / Add New Patient'):
        patient_creation_panel('Mock EHR','ehr')
    reg=pd.DataFrame([{'Patient':p['name'],'MRN':p['mrn'],'Lifecycle':p.get('lifecycle_status','Active Monitoring'),'Care Plan':p['care_plan'],'Research Link':p.get('research_id','—')} for p in PATIENTS.values()])
    a,b,c=st.columns(3); a.metric('Enterprise registry',f'{len(reg):,}'); b.metric('Active RPM',f"{(reg['Lifecycle']=='Active Monitoring').sum():,}"); c.metric('Research-linked',f"{(reg['Research Link']!='—').sum():,}")
    with st.expander('Browse enterprise patient registry',expanded=False):
        rq=st.text_input('Search enterprise registry',key='ehr_registry_search',placeholder='Patient, MRN, lifecycle, care plan…'); view=reg
        if rq: view=view[view.astype(str).apply(lambda r:r.str.contains(rq,case=False,na=False).any(),axis=1)]
        st.dataframe(view,hide_index=True,use_container_width=True,height=360)
    pid=patient_picker('Open patient record','ehr_patient','Search enterprise patient by name, MRN, care plan, or clinician'); es=patient_events(pid); t1,t2,t3=st.tabs(['Flowsheets','Media','Care-team communications'])
    with t1: st.dataframe(pd.DataFrame([{'Date/Time':e['timestamp'][:16].replace('T',' '),'SpO₂':e['spo2'],'Heart Rate':e['ecg_hr'],'Weight':e['weight'],'BP':f"{e['sys']}/{e['dia']}",'ECG device result':e['ecg'],'FEV1 (L)':e.get('fev1'),'FVC (L)':e.get('fvc'),'FEV1/FVC %':round(e.get('fev1_fvc'),1) if e.get('fev1_fvc') else None,'PEF L/min':e.get('pef')} for e in es]),hide_index=True,use_container_width=True)
    with t2:
        st.subheader('RPM Documents & Patient Samples')
        ps=[m for m in st.session_state.patient_samples if m['patient_id']==pid]
        for m in ps:
            st.write(f"🎙️📷 {m['sample_id']} · {m['type']} · {m['timestamp'][:16].replace('T',' ')} · {m['note']}")
            st.download_button(f"Open / download {m['sample_id']}",m['bytes'],file_name=m['filename'],mime=m['mime'],key='media'+m['sample_id'])
        for e in [x for x in es if x['pdf_ok']]: st.write(f"{e['event_id']}.pdf · Remote ECG · Source: RPM Vendor · Status: FILED"); st.download_button('Download ECG PDF',ecg_pdf_bytes(e,True),file_name=f"{e['event_id']}.pdf",mime='application/pdf',key='ehr'+e['event_id'])
        for e in [x for x in es if x.get('fev1') is not None]: st.write(f"{e['event_id']}_spirometry.pdf · Home Spirometry · Status: FILED"); st.download_button('Download Spirometry PDF',spirometry_pdf_bytes(e),file_name=f"{e['event_id']}_spirometry.pdf",mime='application/pdf',key='ehrsp'+e['event_id'])
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
    page_hero('PRODUCT STORY','Architecture & Product Story','One enterprise patient ecosystem, multiple lifecycle-specific experiences, and a governed research layer.')
    journey_strip('Learn')
    st.info('V6.0 uses a unified synthetic enterprise patient model. Lifecycle status determines whether a person appears in transition, active monitoring, historical EHR, or research views. Research analytics is derived from governed longitudinal data and uses de-identified Research Participant IDs by default.'); st.code('''ACUTE CARE / DISCHARGE PLANNING
  RPM Fit Screening → Human Eligibility Review → Consent / Care Path Selection
                    │
                    ▼
        KIT CONFIGURATION & FULFILLMENT
  Care-path devices → Ship Home / Give at Discharge → Receipt → Pairing → Training
                    │
                    ▼
             ACTIVE RPM MONITORING
  KardiaMobile 6L (when ordered) + Spirometry (pulmonary paths) + Vitals + CGM + Questionnaire\n                    │ Bluetooth\n                    ▼\n              Patient Tablet\n                    │\n                    ▼\n             Vendor RPM Cloud\n          ┌─────────┴─────────┐\n          ▼                   ▼\n Clinical Dashboard        ECG PDF\n          │                   │\n          ▼                   ▼\n AI Alert / Trend Layer   Document Validation\n          │                   │\n          ▼                   ▼\n Clinician Outreach      Cloverleaf → OnBase\n          │                   │\n          ▼                   ▼\n RPM Integration API     Mock EHR Media\n          │\n          ▼\n FHIR/LOINC Mapping → Mock EHR Flowsheet\n\nCLOSED LOOP: Fit → Enrollment → Kit → Activation → Monitoring → Alert → Human review → Call/Chat → Outcome → EHR → Audit trail

UNIFIED DATA & RESEARCH ARCHITECTURE
Enterprise Patient Registry / MPI
  ├─ Candidate lifecycle → RPM Fit / Transition Queue
  ├─ Active Monitoring lifecycle → Clinical Command Center / Patient 360
  ├─ Completed lifecycle → longitudinal EHR / historical record
  └─ Governed research eligibility
          ↓
     De-identification / pseudonymization
          ↓
 Research Participant ID (MRN/name suppressed by default)
          ↓
 Longitudinal Research Dataset → Cohorts → Data Quality → Analysis → Reports
          ↓
 Hypothesis → clinical/research review → prospective validation
          ↓
 Governed care-path improvement + ongoing outcome/safety monitoring

KEY PRINCIPLE: one enterprise patient ecosystem, multiple role- and lifecycle-specific views. Operational MRN ≠ Research Participant ID.''')
    st.write('**MVP epics:** validated patient registration + MPI duplicate prevention · care-plan enrollment duration/review · care-plan-specific daily + ad-hoc questionnaires · bite-sized patient education completion · patient-generated audio/image samples · home spirometry + PDF · timestamped device ingestion · longitudinal trends · clinical command center · AI workflow prioritization · clinician intervention · ECG document integrity · EHR transformation · lineage/audit.')
    st.write('**Guardrails:** synthetic data only; no autonomous diagnosis; device classifications treated as source inputs; failed documents held; clinician remains decision-maker.')
    st.write('**KPIs:** alert precision, time-to-review, time-to-patient-contact, intervention completion, false-positive rate, data completeness, document validation pass rate, EHR delivery success, clinician override rate.')



elif menu.startswith('16 ·'):
    page_hero('RESEARCH & INSIGHTS','Research Analytics Center','Explore de-identified longitudinal RPM data, understand cohort patterns, and generate questions for governed clinical research.')
    st.info('V5.0 research records are derived from the same unified synthetic enterprise population. Operational identity is linked internally for traceability, while this workspace exposes Research Participant IDs by default. A de-identified, synthetic research workspace that connects longitudinal RPM measurements, symptoms, adherence, alerts, interventions and outcomes. It supports hypothesis generation and operational learning—not diagnosis, treatment, or causal claims.')
    df=research_df(); parts=df['Research Participant ID'].nunique(); obs=len(df); spi=df['FEV1 L'].notna().sum(); ecg=df['ECG Device Classification'].notna().sum(); alerts=int(df['Alert'].sum())
    cohort_n=df['Cohort'].nunique(); cols=st.columns(6); cols[0].metric('Participants',f'{parts:,}'); cols[1].metric('Research cohorts',f'{cohort_n:,}'); cols[2].metric('Observations',f'{obs:,}'); cols[3].metric('Spirometry sessions',f'{spi:,}'); cols[4].metric('6L ECG recordings',f'{ecg:,}'); cols[5].metric('Flagged observations',f'{alerts:,}')
    st.subheader('Research population at a glance')
    pop=df.groupby(['Cohort','Care Path'])['Research Participant ID'].nunique().reset_index(name='Participants').sort_values('Participants'); fig=go.Figure(go.Bar(y=pop['Cohort'],x=pop['Participants'],text=pop['Participants'],orientation='h')); fig.update_layout(height=520,xaxis_title='Participants',yaxis_title='',margin=dict(l=20,r=20,t=20,b=20)); st.plotly_chart(fig,use_container_width=True); st.caption('Each research cohort has a defined purpose and operational care-path source. Open Cohort Catalog for signals, example questions and intended users.')
    st.subheader('What this center is designed to answer')
    st.markdown('''**Pulmonary:** How do FEV₁/FVC/PEF trajectories, symptoms, SpO₂, adherence and technical quality change over time?  
**Cardiac:** What is the distribution and longitudinal burden of device-reported ECG classifications, and what follows an actionable recording?  
**Workflow:** How quickly are alerts reviewed and acted on, and where is operational friction occurring?  
**Outcomes & safety:** Are concerning trends followed by timely human review, and are there missing-data, device, document or escalation gaps that need investigation?''')
    export_bar(df,'rpm_research_overview_data')

elif menu.startswith('16A ·'):
    st.header('Research Cohort Catalog')
    st.caption('Cohorts represent a research purpose/population, while Care Path identifies the operational RPM pathway and Trajectory is an analytical subgroup. Keeping these concepts separate supports clearer, reproducible research questions.')
    catalog=pd.DataFrame([
      ['Lung Transplant Home Spirometry','Lung Transplant','Spirometry + SpO₂ + symptoms','FEV₁ trajectory, home-test quality, symptom relationships','Pulmonary researchers / transplant clinicians'],
      ['COPD Remote Pulmonary Monitoring','COPD / Pulmonary','Spirometry + SpO₂ + symptoms','Exacerbation-associated patterns, adherence, lung-function change','Pulmonary researchers / clinicians'],
      ['Pulmonary Home Rehabilitation','Pulmonary Home Rehab','Spirometry + SpO₂ + HR','Functional recovery and physiologic trajectory during home rehab','Pulmonary rehab / research teams'],
      ['Pneumonitis Recovery Monitoring','Pneumonitis','Spirometry + SpO₂ + symptoms','Recovery trajectory and symptom/physiology relationships','Pulmonary / oncology research teams'],
      ['Post-Respiratory Infection Recovery','Adult Respiratory Infection','SpO₂ + symptoms + HR','Post-acute respiratory recovery and persistent symptom patterns','Clinical research / population health'],
      ['Cardiac Rhythm / 6L ECG','Cardiology','6L ECG + HR + symptoms','Device-reported rhythm burden, quality and follow-up actions','Cardiology / electrophysiology research'],
      ['Heart Failure Post-Discharge','Heart Failure','Weight + BP + HR + SpO₂','Post-discharge multi-signal trends, alerts and interventions','HF research / transition teams'],
      ['CAD / Cardiac Recovery','Coronary Artery Disease (CAD)','6L ECG + BP + HR + symptoms','Cardiac recovery patterns and rhythm-related follow-up','Cardiology research'],
      ['Hypertension Monitoring','Hypertension','BP + HR','Home BP patterns, adherence and intervention workflows','Hypertension / outcomes research'],
      ['Diabetes / CGM Monitoring','Diabetes / CGM','Glucose + engagement','Longitudinal glucose patterns and monitoring adherence','Diabetes research'],
      ['CKD / AKI Transition Monitoring','CKD','BP + weight + symptoms','Post-acute fluid/BP monitoring patterns and escalation','Nephrology / transition research'],
      ['Post-Surgical Recovery','Post-Surgical Recovery','Weight + symptoms + engagement','Recovery, symptom burden and post-discharge engagement','Surgical outcomes research']
    ],columns=['Research Cohort','Operational Care Path','Primary Signals','Example Research Purpose','Primary Users'])
    counts=research_df().groupby('Cohort')['Research Participant ID'].nunique().rename('Participants')
    obs=research_df().groupby('Cohort').size().rename('Observations')
    catalog=catalog.merge(counts,left_on='Research Cohort',right_index=True,how='left').merge(obs,left_on='Research Cohort',right_index=True,how='left')
    st.dataframe(catalog,hide_index=True,use_container_width=True,height=500)
    st.info('Analysis subgroups such as Stable, Improving, Declining, Intermittent, high/low adherence, intervention/no intervention, and data-quality strata can be applied inside a cohort without redefining the cohort itself.')
    export_bar(research_df(),'rpm_research_cohort_catalog_source_data')

elif menu.startswith('17 ·'):
    st.header('Cohort Explorer')
    st.caption('Build transparent research cohorts without exposing operational MRNs. Research Participant IDs are used by default.')
    df=research_filters(research_df(),'cohort_'); st.write(f"**{df['Research Participant ID'].nunique()} participants · {len(df):,} longitudinal observations**")
    st.dataframe(df[['Research Participant ID','Care Path','Cohort','Age Band','Observation Date','Trajectory','SpO2','Heart Rate','Systolic BP','Diastolic BP','Weight lb','Glucose mg/dL','FEV1 L','FEV1/FVC %','ECG Device Classification','Symptom Burden (0-5)','Alert','Intervention','Outcome']],hide_index=True,use_container_width=True,height=430)
    export_bar(df,'rpm_filtered_research_cohort')

elif menu.startswith('18 ·'):
    st.header('Spirometry Research')
    st.caption('Longitudinal home-spirometry analysis for synthetic pulmonary cohorts. Quality and missingness are shown alongside physiologic trends so technically weak sessions are not treated as equally reliable evidence.')
    df=research_filters(research_df()[research_df()['FEV1 L'].notna()].copy(),'spi_');
    a,b,c,d=st.columns(4); a.metric('Participants',df['Research Participant ID'].nunique()); b.metric('Sessions',len(df)); c.metric('Median FEV₁',f"{df['FEV1 L'].median():.2f} L"); d.metric('Quality-review sessions',f"{(df['Spirometry Quality']=='Review quality').mean()*100:.1f}%")
    trend=df.groupby('Study Day',as_index=False)['FEV1 % Personal Baseline'].mean(); fig=go.Figure(go.Scatter(x=trend['Study Day'],y=trend['FEV1 % Personal Baseline'],mode='lines+markers',name='Mean % baseline')); fig.update_layout(height=360,xaxis_title='Study day',yaxis_title='FEV₁ % personal baseline',margin=dict(l=20,r=20,t=20,b=20)); st.plotly_chart(fig,use_container_width=True)
    st.subheader('Trajectory by participant')
    rid=st.selectbox('Research Participant ID',sorted(df['Research Participant ID'].unique()),key='spi_rid'); one=df[df['Research Participant ID']==rid]; fig2=go.Figure(); fig2.add_trace(go.Scatter(x=one['Observation Date'],y=one['FEV1 L'],mode='lines+markers',name='FEV₁')); fig2.add_trace(go.Scatter(x=one['Observation Date'],y=one['FVC L'],mode='lines+markers',name='FVC')); fig2.update_layout(height=330,yaxis_title='Liters',margin=dict(l=20,r=20,t=20,b=20)); st.plotly_chart(fig2,use_container_width=True)
    st.dataframe(one[['Observation Date','FEV1 L','FVC L','FEV1/FVC %','PEF L/min','FEV1 % Personal Baseline','Spirometry Quality','SpO2','Symptom Burden (0-5)','Alert','Intervention','Outcome']],hide_index=True,use_container_width=True)
    st.info('Research use: examine longitudinal lung-function trajectory, home-test adherence/quality, symptom and SpO₂ relationships, and what happened after concerning changes. This prototype does not infer diagnosis or treatment effect.')
    export_bar(df,'spirometry_research_dataset')

elif menu.startswith('19 ·'):
    st.header('6L ECG Research')
    st.caption('Analysis of synthetic device-reported 6-lead ECG classifications and downstream human workflow. The portfolio does not independently interpret ECG waveforms.')
    df=research_df(); df=df[df['ECG Device Classification'].notna()].copy(); df=research_filters(df,'ecg_')
    dist=df['ECG Device Classification'].value_counts().reset_index(); dist.columns=['Classification','Recordings']; fig=go.Figure(go.Bar(x=dist['Classification'],y=dist['Recordings'],text=dist['Recordings'])); fig.update_layout(height=350,xaxis_title='',yaxis_title='Recordings',margin=dict(l=20,r=20,t=20,b=20)); st.plotly_chart(fig,use_container_width=True)
    a,b,c,d=st.columns(4); a.metric('Participants',df['Research Participant ID'].nunique()); b.metric('Recordings',len(df)); c.metric('Unclassified',f"{(df['ECG Device Classification']=='Unclassified').mean()*100:.1f}%"); d.metric('Alert-linked',f"{df['Alert'].mean()*100:.1f}%")
    st.dataframe(df[['Research Participant ID','Care Path','Observation Date','Heart Rate','ECG Device Classification','Symptom Burden (0-5)','Alert','Intervention','Outcome']],hide_index=True,use_container_width=True,height=380)
    st.info('Research use: quantify recording burden and device-reported categories, study unclassified/quality workflow, relate recordings to symptoms and human interventions, and identify questions for prospective validation.')
    export_bar(df,'ecg_research_dataset')

elif menu.startswith('20 ·'):
    st.header('Reports & Exports')
    st.caption('A reporting workbench: each report states the question, intended audience, interpretation and limitation before presenting the data.')
    df=research_df()
    reports={
      'Longitudinal Lung Function':'How do FEV₁ and FEV₁ % personal baseline change over time in pulmonary cohorts?',
      'Spirometry Quality & Adherence':'Are home tests being completed consistently, and what proportion needs technical-quality review?',
      'ECG Classification & Event Burden':'What device-reported ECG categories occur, how often, and what follows them?',
      'Symptoms + Device Signals':'How do symptom burden and physiologic measurements move together over time?',
      'Alert-to-Intervention':'What proportion of flagged observations receive a documented human intervention?',
      'Care-Path Comparison':'How do engagement, alerts and interventions differ across synthetic care pathways?',
      'Data Quality & Missingness':'Where are missing or technically questionable data creating research/clinical blind spots?',
      'Clinical Efficiency':'How efficiently does the simulated RPM workflow convert signals into human review and documented action?',
      'Patient Safety':'Are concerning signals, poor-quality data and unresolved workflow exceptions visible and followed up?',
      'Patient Outcomes':'What longitudinal outcomes are observed after enrollment/intervention, without claiming causality?'}
    report=st.selectbox('Report',list(reports)); st.markdown(f'### {report}'); st.write(reports[report])
    if report=='Longitudinal Lung Function':
        x=df[df['FEV1 L'].notna()].groupby('Study Day',as_index=False)['FEV1 % Personal Baseline'].mean(); fig=go.Figure(go.Scatter(x=x['Study Day'],y=x['FEV1 % Personal Baseline'],mode='lines+markers')); fig.update_layout(yaxis_title='Mean FEV₁ % personal baseline',xaxis_title='Study day',height=360); st.plotly_chart(fig,use_container_width=True); out=df[df['FEV1 L'].notna()]
    elif report=='ECG Classification & Event Burden':
        x=df[df['ECG Device Classification'].notna()]['ECG Device Classification'].value_counts().reset_index(); x.columns=['Classification','Recordings']; fig=go.Figure(go.Bar(x=x['Classification'],y=x['Recordings'])); st.plotly_chart(fig,use_container_width=True); out=df[df['ECG Device Classification'].notna()]
    else:
        summary=df.groupby('Care Path').agg(Participants=('Research Participant ID','nunique'),Observations=('Research Participant ID','size'),Alert_Rate=('Alert','mean'),Intervention_Rate=('Intervention','mean'),Mean_SpO2=('SpO2','mean')).reset_index(); summary['Alert Rate %']=(summary.pop('Alert_Rate')*100).round(1); summary['Intervention Rate %']=(summary.pop('Intervention_Rate')*100).round(1); summary['Mean_SpO2']=summary['Mean_SpO2'].round(1); st.dataframe(summary,hide_index=True,use_container_width=True); out=df
    st.warning('Interpretation guardrail: these are descriptive/exploratory synthetic results. Differences can reflect cohort mix, missingness or simulated assumptions; they do not establish that RPM caused an outcome.')
    export_bar(out,'research_report_'+re.sub(r'[^a-z0-9]+','_',report.lower()).strip('_'))
    st.divider(); st.subheader('Research Question Builder')
    q1,q2,q3=st.columns(3); pop=q1.selectbox('Population',['All']+sorted(df['Care Path'].unique())); measure=q2.selectbox('Primary measure',['FEV₁ % Personal Baseline','SpO2','Heart Rate','Symptom Burden (0-5)','ECG Device Classification']); outcome=q3.selectbox('Outcome/context',['Intervention','Outcome','Alert'])
    qdf=df if pop=='All' else df[df['Care Path']==pop]; st.success(f'Question: In {pop} participants, how does {measure} relate longitudinally to {outcome}?  Cohort: {qdf["Research Participant ID"].nunique()} participants / {len(qdf):,} observations.')
    st.caption('This builder defines an exploratory cohort/question. Formal statistical inference, protocol approval and validated endpoints would be separate research activities.')

elif menu.startswith('21 ·'):
    page_hero('RESEARCH & INSIGHTS','Research Analytics Guide','Understand what each output means, why it matters, and how research can support safer and more efficient care without overstating causality.')
    st.info('This page explains the Research Analytics Center in plain language so clinicians, physicians, researchers, product teams and operational leaders can understand what each output depicts and how it may support safer, more efficient care.')
    guide=[
      ('Research Overview','Population-level orientation: cohort size, observations, device-result volume and flagged observations.','Researchers / program leaders','Shows whether there is enough longitudinal data to ask a question and where activity is concentrated.'),
      ('Cohort Explorer','Filters de-identified participants into a reproducible analysis population.','Researchers / analysts','Supports subgroup analysis while keeping operational MRNs out of the research view by default.'),
      ('Spirometry Research','FEV₁, FVC, FEV₁/FVC, PEF, personal-baseline change, quality, symptoms and interventions over time.','Pulmonary researchers / clinicians','Helps study trajectory, adherence, technical quality and whether concerning changes precede review or outcomes.'),
      ('6L ECG Research','Device-reported ECG classifications, heart rate, symptoms, alerts and human follow-up.','Cardiac researchers / clinicians','Helps quantify event burden, unclassified recordings and workflow after potentially actionable device results.'),
      ('Reports & Exports','Reusable report definitions, graphs and downloadable analysis-ready datasets.','Research / quality / leadership','Turns longitudinal observations into understandable evidence packages while preserving the underlying rows for independent analysis.')]
    st.dataframe(pd.DataFrame(guide,columns=['Output','What it depicts','Primary users','How it can help']),hide_index=True,use_container_width=True)
    st.subheader('How to measure clinical efficiency')
    st.markdown('''**Time to review:** alert timestamp → first clinician review.  
**Time to patient contact:** alert timestamp → successful outreach.  
**Actionable-alert rate:** alerts resulting in clinically meaningful review/action ÷ total alerts.  
**Documentation completion:** interventions documented within the defined service window ÷ interventions requiring documentation.  
**Automation/data-ingestion success:** successfully received/mapped readings ÷ expected transmissions.  
**Workload balancing:** alerts/participants per RPM clinician, plus time spent on technical vs clinical work.  
Use medians and percentiles, not only averages; stratify by care path and priority; include balancing measures so speed does not come at the expense of safety.''')
    st.subheader('How to measure patient outcomes')
    st.markdown('''**Engagement/adherence:** completed expected readings/tasks ÷ expected readings/tasks.  
**Physiologic trajectory:** within-patient change from baseline (for example FEV₁ % personal baseline), analyzed with technical quality and clinical context.  
**Symptom trajectory:** repeated patient-reported symptom burden over time.  
**Follow-through:** completed recommended follow-up ÷ recommended follow-up.  
**Utilization/outcomes:** where a study legitimately has those endpoints, examine post-discharge clinic/ED/hospital events with an appropriate comparison design.  
Outcome improvement requires a valid study design; a dashboard trend alone cannot prove RPM caused the change.''')
    st.subheader('How to measure patient safety')
    st.markdown('''**Critical-alert response:** urgent/high-priority alerts reviewed within the organization-defined window ÷ such alerts.  
**Unresolved-alert backlog:** open alerts beyond their expected review window.  
**Data-quality risk:** missing, poor-quality or unclassified device results requiring repeat/review.  
**Device/connectivity risk:** failed transmissions, low battery, pairing failures and replacement delays.  
**Document integrity:** PDFs passing patient-identifier/document-routing validation ÷ generated reports.  
**Escalation closure:** escalations with documented disposition ÷ escalations opened.  
Safety metrics should trigger human review and quality improvement; they are not autonomous treatment rules.''')
    st.subheader('From research signal to better care')
    st.code('''Reliable longitudinal data → reproducible cohort → descriptive analysis → hypothesis → clinical/research review → approved study / validation → evidence → governed pathway change → prospective monitoring of benefit + safety''')
    st.warning('All V6.0 research participants, measurements, associations, thresholds and outcomes are synthetic. The center demonstrates product and analytics design, not validated clinical evidence.')

elif menu.startswith('15A ·') and CURRENT_USER=='Admin':
    st.header('Logins & Roles')
    st.caption('Admin-only portfolio view. Demo passwords are intentionally simple and are not a production authentication pattern.')
    st.info('Production healthcare applications should use enterprise identity/SSO, MFA, server-side authorization, secure secret storage, least-privilege access and auditable access controls.')
    h=st.columns([1.1,1.5,1.8,3.4]); h[0].markdown('**Username**'); h[1].markdown('**Role**'); h[2].markdown('**Demo password**'); h[3].markdown('**Access / functionality**')
    for username,acct in DEMO_ACCOUNTS.items():
        c1,c2,c3,c4=st.columns([1.1,1.5,1.8,3.4],vertical_alignment='center'); c1.write(username); c2.write(acct['role']); key='reveal_'+username.replace(' ','_')
        if key not in st.session_state: st.session_state[key]=False
        pc,eye=c3.columns([4,1]); pc.code(acct['password'] if st.session_state[key] else '••••••••••••',language=None)
        if eye.button('◌',key='eye_'+username,help='Show/hide demo password'): st.session_state[key]=not st.session_state[key]; st.rerun()
        c4.write(acct['description'])

elif menu.startswith('11 ·'):
    st.header('Patient Identity & Duplicate Prevention')
    st.write('V6.0 uses one shared synthetic enterprise patient registry. Operational, transition, EHR and research workspaces are lifecycle-specific views of that registry—not separate patient universes. Research views use a governed Research Participant ID and suppress operational MRN/name by default.')
    st.subheader('Demo matching logic')
    st.markdown('''**1. Exact/high-confidence match:** normalized legal name + date of birth + phone → creation is blocked and the existing MRN is returned.  
**2. Possible match:** normalized legal name + date of birth → creation is blocked for identity review.  
**3. No match:** a new synthetic MRN is generated and the patient is written once to the shared registry.  
**4. Source is audited:** the audit trail records whether creation started from the Clinical Dashboard or Mock EHR.''')
    st.info('Production systems typically use an Enterprise Master Patient Index (EMPI/MPI), stronger identity attributes, configurable matching rules, role-based access, merge/unmerge governance, and human review for ambiguous matches. This portfolio prototype intentionally uses a simple deterministic rule.')
    st.subheader('Shared patient registry')
    st.dataframe(pd.DataFrame([{'Patient':p['name'],'MRN':p['mrn'],'DOB':p['dob'],'Phone':p.get('phone',''),'Lifecycle':p.get('lifecycle_status','Active Monitoring'),'Care Plan':p['care_plan'],'Assigned clinician':p['clinician'],'Research Participant ID':p.get('research_id','—')} for p in PATIENTS.values()]),hide_index=True,use_container_width=True)
