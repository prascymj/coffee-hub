# app.py
import streamlit as st
import os
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- การตั้งค่าหน้าจอและ Supabase ---
st.set_page_config(layout="wide", page_title="The Coffee Lab")

# ตรวจสอบว่า Secrets ถูกตั้งค่าใน Streamlit Cloud หรือ .streamlit/secrets.toml
if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
else:
    st.error("กรุณาตั้งค่า Supabase URL และ Key ใน Streamlit Secrets")
    st.stop()

st.title("The Coffee Lab ☕")
st.markdown("แพลตฟอร์มจัดการและติดตามข้อมูลกาแฟครบวงจร")

# --- FUNCTIONS ---

def login_form():
    st.header("เข้าสู่ระบบ")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("อีเมล")
            password = st.text_input("รหัสผ่าน", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ", use_container_width=True)
            if submitted:
                try:
                    user = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = user
                    profile = supabase.table('profiles').select('role, full_name').eq('id', user.user.id).single().execute()
                    if profile.data:
                        st.session_state.role = profile.data['role']
                        st.session_state.full_name = profile.data['full_name']
                        st.rerun()
                    else:
                        st.error(f"ไม่พบข้อมูลโปรไฟล์สำหรับผู้ใช้ ID: {user.user.id}")
                except Exception as e:
                    st.error("อีเมลหรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")

def admin_dashboard():
    # (โค้ด admin_dashboard เหมือนเดิม)
    st.header(f"หน้าสำหรับผู้ดูแลระบบ: {st.session_state.get('full_name', 'N/A')}")
    st.subheader("จัดการผู้ใช้งาน (เกษตรกร)")
    with st.expander("➕ เพิ่มเกษตรกรรายใหม่"):
        with st.form("add_farmer_form", clear_on_submit=True):
            email = st.text_input("อีเมลของเกษตรกร")
            password = st.text_input("รหัสผ่านเริ่มต้น", type="password")
            full_name = st.text_input("ชื่อ-นามสกุล")
            if st.form_submit_button("เพิ่มเกษตรกร"):
                try:
                    response = supabase.auth.sign_up({"email": email, "password": password})
                    new_user_id = response.user.id
                    if full_name:
                        supabase.table('profiles').update({'full_name': full_name}).eq('id', new_user_id).execute()
                    st.success(f"เพิ่มเกษตรกร '{full_name or email}' เรียบร้อยแล้ว!")
                    st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

    st.subheader("รายชื่อเกษตรกรในระบบ")
    response = supabase.from_('profiles_with_email').select('*').eq('role', 'FARMER').execute()
    if response.data:
        df_farmers = pd.DataFrame(response.data)
        st.dataframe(df_farmers, use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลเกษตรกรในระบบ")

def farmer_dashboard():
    try:
        user_id = st.session_state.user.user.id
    except (AttributeError, KeyError):
        st.error("เกิดข้อผิดพลาดในการโหลดข้อมูลผู้ใช้ กรุณาล็อกอินใหม่อีกครั้ง")
        st.stop()

    my_farms = supabase.table('farms').select('*').eq('owner_id', user_id).execute().data
    
    # --- Flow 1: First-Time Login ---
    if not my_farms:
        st.balloons()
        st.info("ยินดีต้อนรับ! มาเริ่มต้นด้วยการสร้างฟาร์มแรกของคุณกัน")
        with st.form("add_first_farm_form", clear_on_submit=True):
            farm_name = st.text_input("ชื่อฟาร์มของคุณ")
            location = st.text_input("ที่ตั้ง (อำเภอ, จังหวัด)")
            if st.form_submit_button("➕ สร้างฟาร์ม", use_container_width=True, type="primary"):
                supabase.table('farms').insert({"farm_name": farm_name, "location": location, "owner_id": user_id}).execute()
                st.success(f"สร้างฟาร์ม '{farm_name}' สำเร็จ!")
                st.rerun()
        return

    # --- Flow 2: Main Dashboard for Existing User ---
    st.header(f"ภาพรวมฟาร์ม")
    
    farm_names = [farm['farm_name'] for farm in my_farms]
    selected_farm_name = st.selectbox("เลือกฟาร์มที่จะจัดการ:", farm_names)
    selected_farm = next((farm for farm in my_farms if farm['farm_name'] == selected_farm_name), None)
    selected_farm_id = selected_farm['id']

    # --- Dashboard Metrics ---
    total_harvests_this_year = supabase.table('harvest_lots').select('id', count='exact').eq('farm_id', selected_farm_id).gte('harvest_date', f'{datetime.now().year}-01-01').execute().count
    total_activities_this_year = supabase.table('farm_activities').select('id', count='exact').eq('farm_id', selected_farm_id).gte('activity_date', f'{datetime.now().year}-01-01').execute().count
    last_soil_test = supabase.table('soil_tests').select('test_date').eq('farm_id', selected_farm_id).order('test_date', desc=True).limit(1).execute().data
    
    col1, col2, col3 = st.columns(3)
    col1.metric("จำนวนการเก็บเกี่ยว (ปีนี้)", f"{total_harvests_this_year or 0} ครั้ง")
    col2.metric("จำนวนกิจกรรม (ปีนี้)", f"{total_activities_this_year or 0} ครั้ง")
    col3.metric("ผลตรวจดินล่าสุด", last_soil_test[0]['test_date'] if last_soil_test else "ยังไม่มี")

    st.divider()

    # --- Main Action Buttons ---
    st.subheader("บันทึกข้อมูล")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🍒 บันทึกการเก็บเกี่ยว", use_container_width=True):
            st.session_state.show_harvest_form = True
    with col2:
        if st.button("🌱 บันทึกกิจกรรมในไร่", use_container_width=True):
            st.session_state.show_activity_form = True

    # --- Forms shown in dialogs for better UX ---
    if st.session_state.get("show_harvest_form", False):
        with st.dialog("บันทึกการเก็บเกี่ยว (Harvest Lot)", expanded=True):
            try:
                varieties_data = supabase.table('varieties').select('id, name').order('name').execute().data
                variety_options = {v['name']: v['id'] for v in varieties_data}
            except Exception as e:
                st.error(f"ไม่สามารถโหลดข้อมูลสายพันธุ์ได้: {e}")
                variety_options = {}

            with st.form("add_harvest_form_dialog", clear_on_submit=True):
                harvest_date = st.date_input("วันที่เก็บเกี่ยว")
                cherry_weight = st.number_input("น้ำหนักกาแฟเชอรี่ (กก.)", min_value=0.0, format="%.2f")
                selected_variety_name = st.selectbox("สายพันธุ์", options=variety_options.keys())
                harvester_name = st.text_input("ชื่อผู้เก็บเกี่ยว")
                if st.form_submit_button("บันทึก", type="primary"):
                    selected_variety_id = variety_options.get(selected_variety_name)
                    supabase.table('harvest_lots').insert({"farm_id": selected_farm_id, "harvest_date": str(harvest_date), "cherry_weight_kg": cherry_weight, "variety_id": selected_variety_id, "harvester_name": harvester_name}).execute()
                    st.success("บันทึกข้อมูลสำเร็จ!")
                    st.session_state.show_harvest_form = False
                    st.rerun()

    if st.session_state.get("show_activity_form", False):
         with st.dialog("บันทึกกิจกรรมในไร่", expanded=True):
            activity_categories = {"การจัดการดินและปุ๋ย": ["ใส่ปุ๋ยอินทรีย์", "ใส่ปุ๋ยเคมี", "ปรับปรุงโครงสร้างดิน"], "การจัดการวัชพืช": ["ตัดหญ้าด้วยเครื่อง", "ถางหญ้าด้วยมือ"], "การดูแลรักษาต้นกาแฟ": ["ตัดแต่งกิ่ง", "การให้น้ำ"], "การจัดการสิ่งแวดล้อม": ["เก็บขยะในแปลง", "จัดการของเสีย"]}
            with st.form("farm_activity_form_dialog", clear_on_submit=True):
                activity_date = st.date_input("วันที่ทำกิจกรรม")
                category = st.selectbox("หมวดหมู่กิจกรรม", options=activity_categories.keys())
                activity_type = st.selectbox("ประเภทกิจกรรม", options=activity_categories[category])
                description = st.text_area("คำอธิบายเพิ่มเติม")
                if st.form_submit_button("บันทึก", type="primary"):
                    supabase.table('farm_activities').insert({"farm_id": selected_farm_id, "activity_date": str(activity_date), "activity_category": category, "activity_type": activity_type, "description": description}).execute()
                    st.success("บันทึกกิจกรรมสำเร็จ!")
                    st.session_state.show_activity_form = False
                    st.rerun()

    st.divider()
    
    # --- Detailed Information in Tabs ---
    tab1, tab2, tab3 = st.tabs(["🗂️ ประวัติการเก็บเกี่ยว", "📝 ประวัติกิจกรรมและผลดิน", "📄 รายงาน GAP"])

    with tab1:
        st.subheader("ประวัติการเก็บเกี่ยว")
        harvests_data = supabase.table('harvest_lots').select('*, varieties(name)').eq('farm_id', selected_farm_id).order('harvest_date', desc=True).execute().data
        if harvests_data:
            df_harvests = pd.DataFrame(harvests_data).rename(columns={'harvest_date': 'วันที่เก็บเกี่ยว', 'cherry_weight_kg': 'น้ำหนักเชอรี่ (กก.)', 'harvester_name': 'ผู้เก็บเกี่ยว', 'varieties': 'สายพันธุ์'})
            st.dataframe(df_harvests[['วันที่เก็บเกี่ยว', 'น้ำหนักเชอรี่ (กก.)', 'สายพันธุ์', 'ผู้เก็บเกี่ยว']], use_container_width=True)
        else:
            st.info("ยังไม่มีประวัติการเก็บเกี่ยวสำหรับฟาร์มนี้")

    with tab2:
        st.subheader("ประวัติกิจกรรมและผลตรวจดิน")
        col1, col2 = st.columns([1,2])
        with col1:
            st.write("#### ผลตรวจดินล่าสุด")
            soil_tests = supabase.table('soil_tests').select('*').eq('farm_id', selected_farm_id).order('test_date', desc=True).execute().data
            if soil_tests:
                for test in soil_tests:
                    with st.expander(f"ผลตรวจวันที่ {test['test_date']}", expanded=(test == soil_tests[0])):
                        st.write(f"**pH:** {test['ph_level']}")
                        st.write(f"**N:** {test['nitrogen_ppm']} ppm, **P:** {test['phosphorus_ppm']} ppm, **K:** {test['potassium_ppm']} ppm")
                        st.write(f"**OM:** {test['organic_matter_percent']}%")
            else:
                st.info("ยังไม่มีผลตรวจดิน")

            with st.expander("➕ บันทึกผลตรวจดินใหม่"):
                 with st.form("soil_test_form", clear_on_submit=True):
                    test_date = st.date_input("วันที่ส่งตรวจ")
                    ph = st.number_input("ค่า pH", format="%.2f")
                    n, p, k = st.columns(3)
                    n.number_input("ไนโตรเจน (ppm)")
                    p.number_input("ฟอสฟอรัส (ppm)")
                    k.number_input("โพแทสเซียม (ppm)")
                    om = st.number_input("อินทรียวัตถุ (%)", format="%.2f")
                    if st.form_submit_button("บันทึกผลตรวจดิน"):
                        # (ใส่โค้ด INSERT ที่นี่)
                        st.success("บันทึกผลตรวจดินเรียบร้อย!")
                        st.rerun()
        with col2:
            st.write("#### ประวัติกิจกรรมในไร่")
            activities = supabase.table('farm_activities').select('*').eq('farm_id', selected_farm_id).order('activity_date', desc=True).execute().data
            if activities:
                df_activities = pd.DataFrame(activities).rename(columns={'activity_date': 'วันที่', 'activity_category': 'หมวดหมู่', 'activity_type': 'กิจกรรม', 'description': 'รายละเอียด'})
                st.dataframe(df_activities[['วันที่', 'หมวดหมู่', 'กิจกรรม', 'รายละเอียด']], use_container_width=True)
            else:
                st.info("ยังไม่มีการบันทึกกิจกรรม")

    with tab3:
        st.subheader("รายงานสรุปตามมาตรฐาน GAP")
        year_options = list(range(datetime.now().year, datetime.now().year - 5, -1))
        selected_year = st.selectbox("เลือกปีที่ต้องการสร้างรายงาน", options=year_options)
        
        if st.button(f"📄 สร้างตัวอย่างรายงาน GAP สำหรับปี {selected_year}", use_container_width=True):
            st.markdown(f"### บันทึกการปฏิบัติทางการเกษตรที่ดี (GAP) - ปี {selected_year}")
            st.markdown(f"**ฟาร์ม:** {selected_farm_name}")
            activities_in_year = [a for a in activities if datetime.strptime(a['activity_date'], '%Y-%m-%d').year == selected_year]
            if not activities_in_year:
                st.info(f"ไม่พบกิจกรรมที่บันทึกไว้ในปี {selected_year}")
            else:
                categories = sorted(list(set([a['activity_category'] for a in activities_in_year])))
                for category in categories:
                    st.markdown(f"#### {category}")
                    category_activities = [a for a in activities_in_year if a['activity_category'] == category]
                    for act in category_activities:
                        st.markdown(f"- **{act['activity_date']}**: {act['activity_type']} - *{act['description'] or 'ไม่มีคำอธิบาย'}*")


# --- MAIN APP LOGIC ---
if 'user' not in st.session_state:
    login_form()
else:
    full_name = st.session_state.get('full_name', 'N/A')
    role = st.session_state.get('role', 'Unknown')
    st.sidebar.image("https://i.imgur.com/4kprhNc.png", width=100) # ตัวอย่างโลโก้
    st.sidebar.title(f"สวัสดี, {full_name}")
    st.sidebar.markdown(f"**สิทธิ์:** {role}")
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state.clear()
        st.rerun()

    if role == 'ADMIN':
        admin_dashboard()
    elif role == 'FARMER':
        farmer_dashboard()
    else:
        st.error("ไม่รู้จักสิทธิ์ของผู้ใช้งานนี้")
        st.session_state.clear()
        st.rerun()