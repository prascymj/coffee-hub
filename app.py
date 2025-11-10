# app.py
import streamlit as st
import os
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- การตั้งค่าหน้าจอและ Supabase ---
st.set_page_config(layout="wide")

# ไม่ต้องใช้ os และ dotenv สำหรับการเชื่อมต่ออีกต่อไป
# ตรวจสอบว่า Secrets ถูกตั้งค่าใน Streamlit Cloud หรือ .streamlit/secrets.toml
if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
else:
    st.error("กรุณาตั้งค่า Supabase URL และ Key ใน Streamlit Secrets")
    st.stop()


st.title("ยินดีต้อนรับสู่ The Coffee Lab ☕")

# --- FUNCTIONS ---

def login_form():
    st.header("เข้าสู่ระบบ")
    with st.form("login_form"):
        email = st.text_input("อีเมล")
        password = st.text_input("รหัสผ่าน", type="password")
        submitted = st.form_submit_button("เข้าสู่ระบบ")
        if submitted:
            try:
                user = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = user
                profile = supabase.table('profiles').select('role', 'full_name').eq('id', user.user.id).single().execute()
                if profile.data:
                    st.session_state.role = profile.data['role']
                    st.session_state.full_name = profile.data['full_name']
                    st.rerun()
                else:
                    st.error(f"ไม่พบข้อมูลโปรไฟล์สำหรับผู้ใช้ ID: {user.user.id}")
            except Exception as e:
                st.error("อีเมลหรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")
                st.error(f"Debug info: {e}")

def admin_dashboard():
    st.header(f"หน้าสำหรับผู้ดูแลระบบ: {st.session_state.full_name}")
    st.subheader("จัดการผู้ใช้งาน (เกษตรกร)")
    with st.form("add_farmer_form", clear_on_submit=True):
        st.write("เพิ่มเกษตรกรรายใหม่")
        email = st.text_input("อีเมลของเกษตรกร")
        password = st.text_input("รหัสผ่านเริ่มต้น", type="password")
        full_name = st.text_input("ชื่อ-นามสกุล")
        submitted = st.form_submit_button("เพิ่มเกษตรกร")
        if submitted:
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
    st.header(f"หน้าสำหรับเกษตรกร: {st.session_state.full_name or 'N/A'}")
    
    try:
        user_id = st.session_state.user.user.id
    except (AttributeError, KeyError):
        st.error("เกิดข้อผิดพลาดในการโหลดข้อมูลผู้ใช้ กรุณาล็อกอินใหม่อีกครั้ง")
        st.stop()

    my_farms = supabase.table('farms').select('*').eq('owner_id', user_id).execute().data
    
    if not my_farms:
        st.info("คุณยังไม่มีฟาร์มในระบบ กรุณาเพิ่มฟาร์มของคุณเพื่อเริ่มต้นใช้งาน")
        with st.expander("➕ เพิ่มฟาร์มใหม่"):
            with st.form("add_farm_form", clear_on_submit=True):
                farm_name = st.text_input("ชื่อฟาร์ม")
                location = st.text_input("ที่ตั้ง/ตำบล")
                if st.form_submit_button("เพิ่มฟาร์ม"):
                    supabase.table('farms').insert({"farm_name": farm_name, "location": location, "owner_id": user_id}).execute()
                    st.success(f"เพิ่มฟาร์ม '{farm_name}' สำเร็จ!")
                    st.rerun()
        return # หยุดการทำงานของฟังก์ชันไว้แค่นี้ถ้ายังไม่มีฟาร์ม

    # --- เริ่มใช้ Tabs สำหรับจัดการส่วนต่างๆ ---
    tab1, tab2, tab3 = st.tabs(["🏡 จัดการฟาร์มและการเก็บเกี่ยว", "📝 การจัดการ GAP และกิจกรรม", "📄 ส่งออกเอกสาร GAP"])

    with tab1:
        st.subheader("🏡 จัดการฟาร์มและการเก็บเกี่ยว")
        farm_options = {farm['farm_name']: farm['id'] for farm in my_farms}
        selected_farm_name = st.selectbox("เลือกฟาร์มที่จะจัดการ", options=farm_options.keys())
        selected_farm_id = farm_options[selected_farm_name]

        col1, col2 = st.columns(2)
        with col1:
            st.write("#### บันทึกการเก็บเกี่ยว (Harvest Lot)")
            try:
                varieties_data = supabase.table('varieties').select('id, name').order('name').execute().data
                variety_options = {v['name']: v['id'] for v in varieties_data}
            except Exception as e:
                st.error(f"ไม่สามารถโหลดข้อมูลสายพันธุ์ได้: {e}")
                variety_options = {}

            with st.form("add_harvest_form", clear_on_submit=True):
                harvest_date = st.date_input("วันที่เก็บเกี่ยว")
                cherry_weight = st.number_input("น้ำหนักกาแฟเชอรี่ (กก.)", min_value=0.0, format="%.2f")
                selected_variety_name = st.selectbox("สายพันธุ์", options=variety_options.keys())
                harvester_name = st.text_input("ชื่อผู้เก็บเกี่ยว")
                if st.form_submit_button("บันทึกข้อมูล"):
                    selected_variety_id = variety_options.get(selected_variety_name)
                    supabase.table('harvest_lots').insert({
                        "farm_id": selected_farm_id,
                        "harvest_date": str(harvest_date),
                        "cherry_weight_kg": cherry_weight,
                        "variety_id": selected_variety_id,
                        "harvester_name": harvester_name
                    }).execute()
                    st.success("บันทึกข้อมูลการเก็บเกี่ยวเรียบร้อย!")
                    st.rerun()
        
        with col2:
            st.write("#### ประวัติการเก็บเกี่ยว")
            harvests_data = supabase.table('harvest_lots').select('*, varieties(name)').eq('farm_id', selected_farm_id).order('harvest_date', desc=True).execute().data
            if harvests_data:
                df_harvests = pd.DataFrame(harvests_data)
                st.dataframe(df_harvests, use_container_width=True)
            else:
                st.info("ยังไม่มีประวัติการเก็บเกี่ยวสำหรับฟาร์มนี้")

    with tab2:
        st.subheader("📝 การจัดการ GAP และกิจกรรม")
        
        # ส่วนแสดงผลตรวจดิน และเชื่อมโยงกิจกรรม
        st.write("#### ผลการตรวจวิเคราะห์ดิน")
        soil_tests = supabase.table('soil_tests').select('*').eq('farm_id', selected_farm_id).order('test_date', desc=True).execute().data
        if soil_tests:
            for test in soil_tests:
                with st.expander(f"ผลตรวจวันที่ {test['test_date']}"):
                    st.write(f"- **pH:** {test['ph_level']}")
                    st.write(f"- **Nitrogen (N):** {test['nitrogen_ppm']} ppm")
                    st.write(f"- **Phosphorus (P):** {test['phosphorus_ppm']} ppm")
                    st.write(f"- **Potassium (K):** {test['potassium_ppm']} ppm")
                    st.write(f"- **Organic Matter:** {test['organic_matter_percent']}%")
                    st.info(f"**คำแนะนำ:** {test['recommendations'] or 'ไม่มี'}")

        with st.expander("➕ บันทึกผลตรวจดินใหม่ / บันทึกกิจกรรมในไร่"):
            # นิยามหมวดหมู่และกิจกรรมย่อย
            activity_categories = {
                "การจัดการดินและปุ๋ย": ["ใส่ปุ๋ยอินทรีย์", "ใส่ปุ๋ยเคมี", "ปรับปรุงโครงสร้างดิน"],
                "การจัดการวัชพืช": ["ตัดหญ้าด้วยเครื่อง", "ถางหญ้าด้วยมือ"],
                "การดูแลรักษาต้นกาแฟ": ["ตัดแต่งกิ่ง", "การให้น้ำ"],
                "การจัดการสิ่งแวดล้อม": ["เก็บขยะในแปลง", "จัดการของเสีย"]
            }
            
            form_col1, form_col2 = st.columns(2)
            with form_col1:
                st.write("##### บันทึกกิจกรรมในไร่")
                with st.form("farm_activity_form", clear_on_submit=True):
                    activity_date = st.date_input("วันที่ทำกิจกรรม")
                    category = st.selectbox("หมวดหมู่กิจกรรม", options=activity_categories.keys())
                    activity_type = st.selectbox("ประเภทกิจกรรม", options=activity_categories[category])
                    description = st.text_area("คำอธิบายเพิ่มเติม")
                    if st.form_submit_button("บันทึกกิจกรรม"):
                        supabase.table('farm_activities').insert({
                            "farm_id": selected_farm_id,
                            "activity_date": str(activity_date),
                            "activity_category": category,
                            "activity_type": activity_type,
                            "description": description
                        }).execute()
                        st.success("บันทึกกิจกรรมเรียบร้อย!")
                        st.rerun()

            with form_col2:
                 st.write("##### บันทึกผลตรวจดิน")
                 with st.form("soil_test_form", clear_on_submit=True):
                    test_date = st.date_input("วันที่ส่งตรวจ")
                    ph = st.number_input("ค่า pH", format="%.2f")
                    n = st.number_input("ไนโตรเจน (ppm)")
                    p = st.number_input("ฟอสฟอรัส (ppm)")
                    k = st.number_input("โพแทสเซียม (ppm)")
                    om = st.number_input("อินทรียวัตถุ (%)", format="%.2f")
                    reco = st.text_area("คำแนะนำจากห้องปฏิบัติการ (ถ้ามี)")
                    if st.form_submit_button("บันทึกผลตรวจดิน"):
                        supabase.table('soil_tests').insert({
                            "farm_id": selected_farm_id, "test_date": str(test_date), "ph_level": ph,
                            "nitrogen_ppm": n, "phosphorus_ppm": p, "potassium_ppm": k,
                            "organic_matter_percent": om, "recommendations": reco
                        }).execute()
                        st.success("บันทึกผลตรวจดินเรียบร้อย!")
                        st.rerun()

        st.write("#### ประวัติกิจกรรมในไร่")
        activities = supabase.table('farm_activities').select('*').eq('farm_id', selected_farm_id).order('activity_date', desc=True).execute().data
        if activities:
            df_activities = pd.DataFrame(activities)
            st.dataframe(df_activities, use_container_width=True)
        else:
            st.info("ยังไม่มีการบันทึกกิจกรรมสำหรับฟาร์มนี้")


    with tab3:
        st.subheader("📄 ส่งออกเอกสาร GAP")
        st.warning("ฟังก์ชันส่งออกเป็น PDF ยังอยู่ในระหว่างการพัฒนา")
        
        year_options = list(range(datetime.now().year, datetime.now().year - 5, -1))
        selected_year = st.selectbox("เลือกปีที่ต้องการสร้างรายงาน", options=year_options)
        
        if st.button(f"สร้างตัวอย่างรายงาน GAP สำหรับปี {selected_year}"):
            st.write(f"### บันทึกการปฏิบัติทางการเกษตรที่ดี (GAP) - ปี {selected_year}")
            st.write(f"**ฟาร์ม:** {selected_farm_name}")

            # ดึงข้อมูลมาแสดงเป็นตัวอย่าง
            activities_in_year = [a for a in activities if datetime.strptime(a['activity_date'], '%Y-%m-%d').year == selected_year]
            
            if not activities_in_year:
                st.info(f"ไม่พบกิจกรรมที่บันทึกไว้ในปี {selected_year}")
            else:
                categories = sorted(list(set([a['activity_category'] for a in activities_in_year])))
                for category in categories:
                    st.write(f"#### {category}")
                    category_activities = [a for a in activities_in_year if a['activity_category'] == category]
                    for act in category_activities:
                        st.markdown(f"- **{act['activity_date']}**: {act['activity_type']} - *{act['description'] or 'ไม่มีคำอธิบาย'}*")


# --- MAIN APP LOGIC ---
if 'user' not in st.session_state:
    login_form()
else:
    # ใช้ .get() เพื่อป้องกัน Error หาก full_name หรือ role ไม่มีอยู่
    full_name = st.session_state.get('full_name', 'N/A')
    role = st.session_state.get('role', 'Unknown')

    st.sidebar.write(f"ล็อกอินในชื่อ: **{full_name}**")
    st.sidebar.write(f"สิทธิ์: **{role}**")
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state.clear()
        st.rerun()

    if role == 'ADMIN':
        admin_dashboard()
    elif role == 'FARMER':
        farmer_dashboard()
    else:
        st.error("ไม่รู้จักสิทธิ์ของผู้ใช้งานนี้")
        login_form()