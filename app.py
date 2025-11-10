# app.py
import streamlit as st
import os
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- การตั้งค่าหน้าจอและ Supabase ---
st.set_page_config(layout="wide", page_title="The Coffee Lab", initial_sidebar_state="expanded")

# --- Custom CSS เพื่อความสวยงาม ---
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 5rem;
        padding-right: 5rem;
    }
    /* Metric card styling */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    [data-testid="stMetricLabel"] {
        font-size: 16px;
        font-weight: 500;
        color: #555555;
    }
    [data-testid="stMetricValue"] {
        font-size: 36px;
        font-weight: 700;
    }
    /* Custom container for feedback */
    .feedback-card {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)


# --- การเชื่อมต่อ Supabase ---
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except KeyError:
    st.error("กรุณาตั้งค่า Supabase URL และ Key ใน Streamlit Secrets")
    st.stop()


# --- FUNCTIONS --- (Login and Admin Dashboard remain the same)

def login_form():
    st.title("The Coffee Lab ☕")
    st.markdown("แพลตฟอร์มจัดการและติดตามข้อมูลกาแฟครบวงจร")
    st.header("เข้าสู่ระบบ")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("อีเมล")
            password = st.text_input("รหัสผ่าน", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ", use_container_width=True, type="primary")
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
                except Exception:
                    st.error("อีเมลหรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")

def admin_dashboard():
    st.header(f"Admin Dashboard: {st.session_state.get('full_name', 'N/A')}")
    # ... (โค้ดส่วน Admin เหมือนเดิม) ...

def farmer_dashboard():
    try:
        user_id = st.session_state.user.user.id
    except (AttributeError, KeyError):
        st.error("เกิดข้อผิดพลาดในการโหลดข้อมูลผู้ใช้ กรุณาล็อกอินใหม่อีกครั้ง")
        st.stop()
    
    # --- Sidebar ---
    with st.sidebar:
        st.image("https://i.imgur.com/4kprhNc.png", width=70)
        st.title("Coffee Lab")
        st.markdown(f"**ผู้ใช้:** {st.session_state.get('full_name', 'N/A')}")
        
        page = st.radio("เมนู", ["Farmer Dashboard", "GAP Helper", "Data Hub"], label_visibility="collapsed")
        
        if st.button("ออกจากระบบ"):
            st.session_state.clear()
            st.rerun()

    # --- Header ---
    st.header("Farmer Dashboard")
    st.markdown("Your command center for farm and harvest management.")

    # --- Fetch Data ---
    my_farms = supabase.table('farms').select('*').eq('owner_id', user_id).execute().data
    
    # --- Metrics Cards ---
    # หมายเหตุ: ข้อมูล metric เป็นข้อมูลสมมติเพื่อการแสดงผล
    total_harvests = 2 
    total_weight = 450
    lots_in_processing = 1
    ready_for_processing = 1
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Harvest Lots", total_harvests)
    with col2:
        st.metric("Total Weight (kg)", total_weight)
    with col3:
        st.metric("Lots in Processing", lots_in_processing)
    with col4:
        st.metric("Ready for Processing", ready_for_processing)
    
    st.markdown("---")

    # --- Quality Feedback Card ---
    st.subheader("Quality Feedback")
    st.markdown("Here are the latest cupping results for your top-performing lots.")
    
    # สร้าง feedback card ด้วย st.container และ class ที่เรากำหนดใน CSS
    with st.container():
        st.markdown('<div class="feedback-card">', unsafe_allow_html=True)
        fb_col1, fb_col2 = st.columns([4, 1])
        with fb_col1:
            st.markdown("**Lot HL001** - Geisha")
        with fb_col2:
            st.markdown("<p style='text-align: right; font-size: 24px; font-weight: bold; color: #007bff;'>89.25</p>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: right; color: #555;'>Final Score</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")

    # --- Input Forms ---
    form_col1, form_col2 = st.columns(2)
    with form_col1:
        st.subheader("Register New Farm")
        with st.form("add_farm_form", clear_on_submit=True):
            farm_name = st.text_input("Farmer Name", label_visibility="collapsed", placeholder="Farmer Name")
            location = st.text_input("Farm Location / Plot", label_visibility="collapsed", placeholder="Farm Location / Plot")
            if st.form_submit_button("＋ Register Farm", use_container_width=True, type="primary"):
                supabase.table('farms').insert({"farm_name": farm_name, "location": location, "owner_id": user_id}).execute()
                st.success(f"เพิ่มฟาร์ม '{farm_name}' สำเร็จ!")
                st.rerun()
    
    with form_col2:
        st.subheader("Register New Harvest Lot")
        with st.form("add_harvest_form", clear_on_submit=True):
            if my_farms:
                farm_options = {farm['farm_name']: farm['id'] for farm in my_farms}
                selected_farm_name = st.selectbox("Select a farm...", options=farm_options.keys(), label_visibility="collapsed")
            else:
                st.selectbox("Select a farm...", options=["Please register a farm first"], disabled=True, label_visibility="collapsed")

            hc1, hc2 = st.columns(2)
            variety = hc1.text_input("Cherry Variety", label_visibility="collapsed", placeholder="Cherry Variety")
            weight = hc2.text_input("Weight (kg)", label_visibility="collapsed", placeholder="Weight (kg)")
            
            if st.form_submit_button("＋ Submit Lot", use_container_width=True, type="primary"):
                # (ใส่โค้ด INSERT harvest lot ที่นี่)
                st.success("บันทึกข้อมูลการเก็บเกี่ยวเรียบร้อย!")
                st.rerun()

    st.markdown("---")

    # --- Data Table with Filters ---
    st.subheader("Active Harvest Lots")
    
    filter_tabs = st.tabs(["All", "Ready for Processing", "Processing"])
    
    with filter_tabs[0]:
        # ดึงข้อมูลทั้งหมด
        harvests_data = supabase.table('harvest_lots').select('*, farms(farm_name), varieties(name)').eq('farms.owner_id', user_id).execute().data
        if harvests_data:
            df_harvests = pd.DataFrame(harvests_data)
            st.dataframe(df_harvests, use_container_width=True)
        else:
            st.info("ยังไม่มีประวัติการเก็บเกี่ยว")
    
    with filter_tabs[1]:
        st.info("Filter 'Ready for Processing' is under development.")

    with filter_tabs[2]:
        st.info("Filter 'Processing' is under development.")

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