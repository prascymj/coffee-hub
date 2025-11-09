# app.py
import streamlit as st
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import pandas as pd

# โหลดค่าจาก .env
load_dotenv()

# ตั้งค่าการเชื่อมต่อ Supabase
#url: str = os.environ.get("SUPABASE_URL")
#key: str = os.environ.get("SUPABASE_KEY")
#supabase: Client = create_client(url, key)

# ไม่ต้องใช้ os และ dotenv สำหรับการเชื่อมต่ออีกต่อไป
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("ยินดีต้อนรับสู่ The Coffee Lab ☕")


# (ต่อจากโค้ดด้านบน)

# --- FUNCTIONS ---

# โค้ดที่ถูกต้องควรเป็นแบบนี้
def login_form():
    st.header("เข้าสู่ระบบ")
    with st.form("login_form"):
        email = st.text_input("อีเมล")
        password = st.text_input("รหัสผ่าน", type="password")
        submitted = st.form_submit_button("เข้าสู่ระบบ")

        if submitted:
            # ใช้ try-except เพื่อ "ดักจับ" ข้อผิดพลาดที่อาจเกิดขึ้น
            try:
                # พยายามล็อกอิน
                user = supabase.auth.sign_in_with_password({"email": email, "password": password})
                
                # โค้ดส่วนนี้จะทำงานก็ต่อเมื่อล็อกอินสำเร็จเท่านั้น
                st.session_state.user = user
                profile = supabase.table('profiles').select('role', 'full_name').eq('id', user.user.id).execute()
                
                # ตรวจสอบอีกชั้นว่าหา profile เจอหรือไม่
                if profile.data:
                    st.session_state.role = profile.data[0]['role']
                    st.session_state.full_name = profile.data[0]['full_name']
                    st.rerun()
                else:
                    st.error(f"ไม่พบข้อมูลโปรไฟล์สำหรับผู้ใช้ ID: {user.user.id}")

            except Exception as e:
                # ถ้าการล็อกอินล้มเหลว โค้ดจะกระโดดมาทำงานในบล็อก except นี้
                st.error("อีเมลหรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")
                st.error(f"Debug info: {e}") # แสดง error จริงๆ เพื่อช่วยเรา debug

def admin_dashboard():
    st.header(f"หน้าสำหรับผู้ดูแลระบบ: {st.session_state.full_name}")

    # =================== ส่วนเพิ่มเกษตรกร (เวอร์ชันอัปเดต) ===================
    st.subheader("จัดการผู้ใช้งาน (เกษตรกร)")
    with st.form("add_farmer_form", clear_on_submit=True):
        st.write("เพิ่มเกษตรกรรายใหม่")
        email = st.text_input("อีเมลของเกษตรกร")
        password = st.text_input("รหัสผ่านเริ่มต้น", type="password")
        full_name = st.text_input("ชื่อ-นามสกุล")
        submitted = st.form_submit_button("เพิ่มเกษตรกร")

        if submitted:
            try:
                # ขั้นตอนที่ 1: สร้าง User ในระบบ Authentication (Trigger จะทำงานตรงนี้)
                # เราจะส่งไปแค่ email กับ password เท่านั้น
                response = supabase.auth.sign_up({
                    "email": email,
                    "password": password,
                })
                new_user_id = response.user.id

                # ขั้นตอนที่ 2: อัปเดตโปรไฟล์ด้วยชื่อเต็ม (ถ้ามี)
                # เราจะไปอัปเดตแถวที่ Trigger เพิ่งสร้างให้โดยตรง
                if full_name:
                    supabase.table('profiles').update({'full_name': full_name}).eq('id', new_user_id).execute()

                st.success(f"เพิ่มเกษตรกร '{full_name or email}' เรียบร้อยแล้ว!")
                st.rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

    # =================== ส่วนแสดงรายชื่อ (เหมือนเดิม) ===================
    st.subheader("รายชื่อเกษตรกรในระบบ")
    response = supabase.from_('profiles_with_email').select('*').eq('role', 'FARMER').execute()
    
    # เพิ่มการตรวจสอบข้อมูลก่อนสร้าง DataFrame เพื่อป้องกัน Error
    if response.data:
        df_farmers = pd.DataFrame(response.data)
        st.dataframe(df_farmers)
    else:
        st.info("ยังไม่มีข้อมูลเกษตรกรในระบบ")


def farmer_dashboard():
    st.header(f"หน้าสำหรับเกษตรกร: {st.session_state.full_name}")
    user_id = st.session_state.user.user.id

    # ส่วนจัดการฟาร์ม
    st.subheader("จัดการฟาร์มของคุณ")
    my_farms = supabase.table('farms').select('*').eq('owner_id', user_id).execute().data
    if not my_farms:
        st.info("คุณยังไม่มีฟาร์มในระบบ, กรุณาเพิ่มฟาร์มใหม่")
    with st.expander("เพิ่มฟาร์มใหม่"):
        with st.form("add_farm_form", clear_on_submit=True):
            farm_name = st.text_input("ชื่อฟาร์ม")
            location = st.text_input("ที่ตั้ง/ตำบล")
            if st.form_submit_button("เพิ่มฟาร์ม"):
                supabase.table('farms').insert({"farm_name": farm_name, "location": location, "owner_id": user_id}).execute()
                st.success(f"เพิ่มฟาร์ม '{farm_name}' สำเร็จ!")
                st.rerun()

    # ส่วนบันทึกการเก็บเกี่ยว (Harvest Lot)
    st.subheader("บันทึกการเก็บเกี่ยว")
    if my_farms:
        farm_options = {farm['farm_name']: farm['id'] for farm in my_farms}
        selected_farm_name = st.selectbox("เลือกฟาร์ม", options=farm_options.keys())

        with st.form("add_harvest_form", clear_on_submit=True):
            harvest_date = st.date_input("วันที่เก็บเกี่ยว")
            cherry_weight = st.number_input("น้ำหนักกาแฟเชอรี่ (กก.)", min_value=0.0, format="%.2f")
            variety = st.text_input("สายพันธุ์")
            harvester_name = st.text_input("ชื่อผู้เก็บเกี่ยว")
            if st.form_submit_button("บันทึกข้อมูล"):
                farm_id = farm_options[selected_farm_name]
                supabase.table('harvest_lots').insert({
                    "farm_id": farm_id,
                    "harvest_date": str(harvest_date),
                    "cherry_weight_kg": cherry_weight,
                    "variety": variety,
                    "harvester_name": harvester_name
                }).execute()
                st.success("บันทึกข้อมูลการเก็บเกี่ยวเรียบร้อย!")
    else:
        st.warning("กรุณาเพิ่มฟาร์มก่อนทำการบันทึกการเก็บเกี่ยว")

    # แสดงข้อมูลการเก็บเกี่ยวที่ผ่านมา
    st.subheader("ประวัติการเก็บเกี่ยว")
    farm_ids = [farm['id'] for farm in my_farms]
    if farm_ids:
        harvests_data = supabase.table('harvest_lots').select('*, farms(farm_name)').in_('farm_id', farm_ids).order('harvest_date', desc=True).execute().data
        df_harvests = pd.DataFrame(harvests_data)
        st.dataframe(df_harvests)

# --- MAIN APP LOGIC ---

# ตรวจสอบว่า user ล็อกอินหรือยัง
if 'user' not in st.session_state:
    login_form()
else:
    st.sidebar.write(f"ล็อกอินในชื่อ: **{st.session_state.full_name}**")
    st.sidebar.write(f"สิทธิ์: **{st.session_state.role}**")
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state.clear()
        st.rerun()

    # แสดง Dashboard ตาม Role
    if st.session_state.role == 'ADMIN':
        admin_dashboard()
    elif st.session_state.role == 'FARMER':
        farmer_dashboard()
    else:
        st.error("ไม่รู้จักสิทธิ์ของผู้ใช้งานนี้")