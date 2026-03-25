import streamlit as st
import datetime
import math
import os
import sqlite3
import requests

import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
from streamlit_geolocation import streamlit_geolocation

import database
import pandas as pd
import plotly.graph_objects as go
from database import register_mother, verify_mother, get_all_mothers, update_location, get_mothers_with_risk_and_location, save_daily_log, create_alert, log_live_sms, get_active_alerts, get_all_logs, has_recent_high_risk_sms
from ai_engine import calculate_risk
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="MAATRI SURAKSHA AI", page_icon="🩺", layout="wide")

def init_session_state():
    """Initialize essential session state variables."""
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'role' not in st.session_state:
        st.session_state['role'] = None
    if 'otp_sent' not in st.session_state:
        st.session_state['otp_sent'] = False
        
    # Catch navigational query parameters
    query_params = st.query_params
    if 'nav' in query_params:
        target = query_params['nav']
        if target == "Geospatial Heatmap" and st.session_state.get('role') == 'ASHA Worker':
            st.session_state['asha_page'] = "Geospatial Heatmap"
            
            if 'focus' in query_params:
                st.session_state['map_focus_mother'] = query_params['focus']
                
            # Clear it so we don't get stuck in a loop on refresh
            st.query_params.clear()
    if 'temp_phone' not in st.session_state:
        st.session_state['temp_phone'] = ""
    if 'temp_role' not in st.session_state:
        st.session_state['temp_role'] = None
    if 'mother_page' not in st.session_state:
        st.session_state['mother_page'] = "Dashboard Overview"
    if 'language' not in st.session_state:
        st.session_state['language'] = "English"
    if 'transcription' not in st.session_state:
        st.session_state['transcription'] = ""
    if 'audio_processed' not in st.session_state:
        st.session_state['audio_processed'] = False
    if 'asha_page' not in st.session_state:
        st.session_state['asha_page'] = "Overview"

def apply_custom_css():
    """Apply professional healthcare-themed CSS styles."""
    st.markdown("""
        <style>
        /* Main background - Soft blush and cream feel */
        .stApp {
            background-color: #fcf9f9;
        }
        
        /* Hide main menu and footer for cleaner UI */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Emergency Badge */
        .emergency-badge {
            position: absolute;
            top: 15px;
            right: 25px;
            background-color: #dc3545;
            color: #ffffff;
            padding: 10px 18px;
            border-radius: 50px;
            font-weight: 700;
            font-family: 'Inter', sans-serif;
            font-size: 1.1rem;
            box-shadow: 0 4px 8px rgba(220, 53, 69, 0.3);
            z-index: 9999;
            display: flex;
            align-items: center;
            letter-spacing: 0.5px;
        }

        /* Title styling */
        .app-title {
            font-family: 'Inter', sans-serif;
            color: #0b5394;
            font-size: 2.8rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
            padding-bottom: 0px;
            margin-top: 2rem;
        }
        
        .app-subtitle {
            font-family: 'Inter', sans-serif;
            color: #3d85c6;
            font-size: 1.2rem;
            font-weight: 500;
            margin-top: 0px;
            margin-bottom: 2rem;
        }
        
        /* Footer styling */
        .custom-footer {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: #ffffff;
            color: #666666;
            text-align: center;
            padding: 8px 0;
            font-size: 0.8rem;
            border-top: 1px solid #e0e0e0;
            font-family: 'Inter', sans-serif;
            z-index: 999;
        }
        .footer-links {
            margin-top: 4px;
        }
        .footer-links a {
            color: #0b5394;
            text-decoration: none;
            margin: 0 10px;
        }
        .footer-links a:hover {
            text-decoration: underline;
        }
        
        /* Login Card Frame styling */
        div[data-testid="stForm"] {
            background-color: #ffffff;
            padding: 2.5rem 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            border-top: 5px solid #d47e8c;
        }
        
        /* Dashboard Cards */
        .health-card {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            margin-bottom: 1rem;
            border-left: 4px solid #d47e8c;
        }
        
        .risk-badge-low { background-color: #d4edda; color: #155724; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
        .risk-badge-medium { background-color: #fff3cd; color: #856404; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
        .risk-badge-high { background-color: #f8d7da; color: #721c24; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
        
        /* Button styling */
        div[data-testid="stFormSubmitButton"] > button {
            width: 100%;
            background-color: #d47e8c;
            color: white;
            font-weight: 600;
            font-size: 1.1rem;
            border-radius: 8px;
            padding: 0.6rem;
            border: none;
            transition: all 0.3s ease;
            margin-top: 1rem;
        }
        
        div[data-testid="stFormSubmitButton"] > button:hover {
            background-color: #b5606e;
            color: white;
            box-shadow: 0 4px 8px rgba(212, 126, 140, 0.2);
            border: none;
        }
        
        /* ASHA Dashboard Specific Styles */
        .asha-metric-box {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border: 1px solid #eaeaea;
        }
        .metric-title { font-size: 1rem; color: #555; text-transform: uppercase; font-weight: 600; margin-bottom: 5px; }
        .metric-value { font-size: 2.5rem; font-weight: 800; margin: 0; }
        .val-red { color: #dc3545; }
        .val-yellow { color: #ffc107; }
        .val-green { color: #28a745; }
        .val-blue { color: #0b5394; }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #ffffff !important;
            border-right: 1px solid #f0f0f0;
        }
        
        /* Input fields */
        .stTextInput input {
            border-radius: 6px;
        }
        </style>
    """, unsafe_allow_html=True)

def send_sms_alert(mother_id):
    """
    Sends a live High-Risk SMS via Fast2SMS API.
    Retries once on failure. Logs status via database.
    """
    import sqlite3
    import database
    import time
    import requests
    import os
    
    # Get user details for formatting
    conn = sqlite3.connect("maatrisuraksha.db")
    c = conn.cursor()
    c.execute("SELECT name, village FROM users WHERE unique_id = ?", (mother_id,))
    row = c.fetchone()
    conn.close()
    
    name = row[0] if row else "Unknown"
    village = row[1] if row and len(row)>1 else "Unknown"
    
    # Needs to match user spec exactly for single-line format
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"ALERT: High Risk Pregnancy | ID:{mother_id} | Village:{village} | Immediate visit required."
    
    api_key = os.environ.get("FAST2SMS_API_KEY", "")
    asha_phone = database.get_asha_phone(village)
    
    if not asha_phone:
        api_status = "Failed: No ASHA mapped to village"
        database.log_live_sms(mother_id, "Unknown", message, api_status, timestamp)
        st.warning("⚠️ Live SMS skipped: No ASHA worker mapped to this village.")
        return
        
    if not api_key:
        api_status = "Failed: Missing API Credentials"
        database.log_live_sms(mother_id, asha_phone, message, api_status, timestamp)
        st.warning("⚠️ Live SMS skipped: Missing FAST2SMS_API_KEY in .env file.")
        return
        
    url = "https://www.fast2sms.com/dev/bulkV2"
    querystring = {
        "authorization": api_key,
        "message": message,
        "language": "english",
        "route": "q",
        "numbers": asha_phone
    }
    headers = {
        'cache-control': "no-cache"
    }

    print("\n" + "="*40)
    print("LIVE SMS INITIATED")
    print("="*40)
    print(message)
    print("="*40 + "\n")

    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = requests.request("GET", url, headers=headers, params=querystring, timeout=5)
            
            if response.status_code == 200:
                resp_json = response.json()
                if resp_json.get('return', True):
                    api_status = "Sent"
                    database.log_live_sms(mother_id, asha_phone, message, api_status, timestamp)
                    st.success(f"📩 Emergency SMS delivered to ASHA Worker ({asha_phone})")
                    return
                else:
                    api_status = f"Failed: API Error {resp_json.get('message')}"
                    print(f"SMS Attempt {attempt+1} API error: {resp_json.get('message')}")
            else:
                api_status = f"Failed: HTTP {response.status_code}"
                print(f"SMS Attempt {attempt+1} failed with status {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            api_status = f"Failed: Exception ({type(e).__name__})"
            print(f"SMS Attempt {attempt+1} exception: {e}")
            
        if attempt < max_retries - 1:
            time.sleep(2)  # Wait before retrying
            
    # If we exhaust retries
    database.log_live_sms(mother_id, asha_phone, message, api_status, timestamp)
    st.warning("⚠️ Could not deliver SMS alert. Please notify the ASHA worker manually.")

def login_page():
    """Render the centralized professional login page with logo and footer."""
    apply_custom_css()
    
    # Emergency Badge
    st.markdown("""
        <div class="emergency-badge">
            🚑 Emergency: 108
        </div>
    """, unsafe_allow_html=True)
    
    # Header Section with Logo and Title
    header_col1, header_col2 = st.columns([1, 4])
    with header_col1:
        # Load the generated logo
        try:
            st.image("logo.png", width=120)
        except Exception:
            st.markdown("🩺") # Fallback icon
    
    with header_col2:
        st.markdown("<h1 class='app-title'>MAATRI SURAKSHA AI</h1>", unsafe_allow_html=True)
        st.markdown("<p class='app-subtitle'>AI-Powered Rural Maternal Health Companion</p>", unsafe_allow_html=True)
    
    st.divider()
    
    # Grid column layout to perfectly center the form
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        if not st.session_state.get('otp_sent', False):
            st.markdown("<h3 style='text-align: center; color: #444; margin-bottom: 1.5rem;'>Secure Patient Portal</h3>", unsafe_allow_html=True)
            role = st.selectbox("👥 Select Role", ["Mother", "ASHA Worker"], key="role_selector")
            
            if role == "Mother":
                with st.form("login_form_mother"):
                    unique_id = st.text_input("🆔 Unique ID", placeholder="Enter your ASHA assigned ID (e.g. M-001)")
                    name = st.text_input("👤 Full Name", placeholder="Enter your registered name")
                    submit_button = st.form_submit_button("Login")
                    
                    if submit_button:
                        if not unique_id.strip() or not name.strip():
                            st.error("⚠️ Please enter both Unique ID and Name.")
                        else:
                            if verify_mother(unique_id.strip(), name.strip()):
                                st.session_state['logged_in'] = True
                                st.session_state['role'] = "Mother"
                                st.session_state['unique_id'] = unique_id.strip()
                                st.session_state['mother_name'] = name.strip()
                                st.rerun()
                            else:
                                st.error("❌ Invalid ID or Name. Please check and try again.")
            else:
                with st.form("login_form"):
                    phone = st.text_input("📱 Phone Number", placeholder="Enter your 10-digit mobile number")
                    password = st.text_input("🔒 Password", placeholder="Enter your 4-digit PIN", type="password")
                    submit_button = st.form_submit_button("Login")
                    
                    if submit_button:
                        if phone.strip() != "8184995387":
                            st.error("⚠️ Only the registered demo ASHA number (8184995387) is permitted for login.")
                        elif password != "1111":
                            st.error("❌ Incorrect password.")
                        else:
                            st.session_state['logged_in'] = True
                            st.session_state['role'] = "ASHA Worker"
                            st.rerun()

def mother_dashboard():
    """Render the comprehensive Mother's portal."""
    
    # Render Sidebar Navigation for Mother Dashboard
    with st.sidebar:
        st.header("🤰 Mother's Portal")
        st.markdown(f"**Language:** {st.session_state['language']}")
        st.divider()
        
        st.markdown("<p style='color: #888; font-size: 0.8rem; font-weight: bold;'>MAIN MENU</p>", unsafe_allow_html=True)
        
        # Navigation buttons layout
        nav_options = {
            "Dashboard Overview": "🏠",
            "Daily Health Log": "📝",
            "Voice Input (Symptoms)": "🎤",
            "Food & Nutrition": "🍎",
            "AI Food Planner": "🤖",
            "Mood Tracker": "😊",
            "AI Risk Panel": "📊",
            "Live Location & Map": "📍",
            "Emergency Help": "🚨"
        }
        
        for option, icon in nav_options.items():
            if st.button(f"{icon} {option}", use_container_width=True, type="secondary" if st.session_state['mother_page'] != option else "primary"):
                st.session_state['mother_page'] = option
                st.rerun()
                
        st.divider()
        st.selectbox("🌐 Language Toggle", ["English", "Hindi", "Marathi (Coming Soon)"], key="lang_toggle")
        
        if st.button("🔓 Logout", use_container_width=True):
            logout()

    # Right Content Area based on selected page
    page = st.session_state['mother_page']
    
    if page == "Dashboard Overview":
        st.title("🏠 Dashboard Overview")
        st.markdown("<p style='font-size: 1.2rem; color: #666;'>Namaste! Here is your daily health summary.</p>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
                <div class='health-card'>
                    <h4 style='margin-top:0'>Current Risk Level</h4>
                    <p style='margin-bottom:0'><span class='risk-badge-low'>🟢 Low Risk</span></p>
                    <p style='color:#666; font-size:0.9rem; margin-top:10px;'>Everything looks normal today.</p>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            current_time = datetime.datetime.now().strftime("%I:%M %p, %b %d")
            st.markdown(f"""
                <div class='health-card'>
                    <h4 style='margin-top:0'>Last Health Log</h4>
                    <p style='font-size: 1.3rem; font-weight: bold; margin-bottom:0'>{current_time}</p>
                    <p style='color:#666; font-size:0.9rem; margin-top:0px;'>Logged Automatically</p>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("""
            <div class='health-card' style='border-left: 4px solid #17a2b8;'>
                <h4 style='margin-top:0'>💡 AI Health Suggestion</h4>
                <p>Stay hydrated! Drink at least 8 glasses of water today to help with your mild headache.</p>
            </div>
        """, unsafe_allow_html=True)

    elif page == "Daily Health Log":
        st.title("📝 Daily Health Log")
        st.markdown("Please select any symptoms you are feeling today.")
        
        with st.form("health_log_form"):
            st.markdown("<div class='health-card'>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                h_headache = st.checkbox("🤕 Headache")
                h_swelling = st.checkbox("🦶 Swelling in hands/feet")
                h_dizziness = st.checkbox("💫 Dizziness")
            with c2:
                h_fetal = st.checkbox("👶 Reduced fetal movement")
                h_bleeding = st.checkbox("🩸 Bleeding or Spotting")
                
            other_symptoms = st.text_area("Any other symptoms?", placeholder="Type anything else you are worried about here...")
            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.form_submit_button("Submit Health Log"):
                # Aggregate symptoms
                symptom_list = []
                if h_headache: symptom_list.append("headache")
                if h_swelling: symptom_list.append("swelling")
                if h_dizziness: symptom_list.append("dizziness")
                if h_fetal: symptom_list.append("reduced fetal movement")
                if h_bleeding: symptom_list.append("bleeding")
                if other_symptoms: symptom_list.append(other_symptoms)
                
                # Fetch baseline mood/nutrition from session if available (mocked here for now)
                mood = "normal"
                nutrition = "good"
                
                # Call AI Engine
                ai_result = calculate_risk(symptom_list, mood, nutrition)
                
                # Save to Database
                mother_id = st.session_state.get('unique_id', 'Unknown')
                save_daily_log(mother_id, symptom_list, mood, nutrition, ai_result['risk_score'], ai_result['risk_level'], ai_result['timestamp'])
                
                if ai_result['escalation']:
                    create_alert(mother_id, ai_result['risk_level'], ai_result['timestamp'])
                    st.error(f"🚨 ALERT! Risk Level: {ai_result['risk_level'].upper()}. {ai_result['recommendation']}")
                    
                    # Live SMS verification
                    if ai_result['risk_level'] == "High":
                        if not has_recent_high_risk_sms(mother_id):
                            send_sms_alert(mother_id)
                            
                elif ai_result['risk_level'] == "Medium":
                    st.warning(f"⚠️ Risk Level: {ai_result['risk_level'].upper()}. {ai_result['recommendation']}")
                else:
                    st.success(f"✅ Log saved successfully! AI Analysis: Your risk remains LOW. {ai_result['recommendation']}")

    elif page == "Voice Input (Symptoms)":
        st.title("🎤 Voice Input")
        st.markdown("Find it hard to type? Just speak your symptoms to us.")
        
        st.markdown("<div class='health-card' style='text-align: center; padding: 2rem;'>", unsafe_allow_html=True)
        audio_data = st.audio_input("Record your symptoms here:")
        st.markdown("</div>", unsafe_allow_html=True)
        
        if audio_data is not None:
            if not st.session_state['audio_processed']:
                with st.spinner("Processing audio with AI..."):
                    import speech_recognition as sr
                    try:
                        r = sr.Recognizer()
                        with sr.AudioFile(audio_data) as source:
                            audio = r.record(source)
                        
                        text = r.recognize_google(audio)
                        st.session_state['transcription'] = text
                    except Exception as e:
                        print(f"Audio processing error: {e}")
                        st.error("Audio could not be understood. Please try again.")
                        st.session_state['transcription'] = "Error capturing voice. Please try again."
                        
                    st.session_state['audio_processed'] = True
                    st.rerun()
        else:
            if st.session_state['audio_processed']:
                st.session_state['transcription'] = ""
                st.session_state['audio_processed'] = False
                
        transcribed_text = st.text_area("Live Transcription", st.session_state['transcription'], height=100)
        
        if st.button("Send to AI Engine"):
            if not transcribed_text.strip():
                st.error("Please record audio first.")
            else:
                # Mock NLP extraction of symptoms from transcription
                extracted_symptoms = ["swelling"] if "swelling" in transcribed_text.lower() else []
                ai_result = calculate_risk(extracted_symptoms, "normal", "good")
                mother_id = st.session_state.get('unique_id', 'Unknown')
                save_daily_log(mother_id, extracted_symptoms, "normal", "good", ai_result['risk_score'], ai_result['risk_level'], ai_result['timestamp'])
                
                if ai_result['escalation']:
                    create_alert(mother_id, ai_result['risk_level'], ai_result['timestamp'])
                    st.error(f"🚨 Risk Level: {ai_result['risk_level'].upper()}. {ai_result['recommendation']}")
                    
                    # Live SMS verification
                    if ai_result['risk_level'] == "High":
                        if not has_recent_high_risk_sms(mother_id):
                            send_sms_alert(mother_id)
                else:
                    st.success(f"✅ Symptoms analyzed successfully. Risk Score: {ai_result['risk_score']}. {ai_result['recommendation']}")
                
                # Clear transcription after sending
                st.session_state['transcription'] = ""
                st.session_state['audio_processed'] = False

    elif page == "Food & Nutrition":
        st.title("🍎 Food & Nutrition")
        st.markdown("Keep track of your meals and hydration.")
        
        st.warning("👩‍⚕️ Reminder: Include ample iron-rich (spinach, beans) and protein-rich (eggs, lentils) foods for your baby's growth!")
        
        with st.form("food_log"):
            st.subheader("💧 Water Intake")
            water_glasses = st.slider("Glasses of water today:", 0, 15, 3)
            
            st.subheader("🍽️ Food Intake")
            st.text_area("What did you eat today?", placeholder="E.g., 2 rotis with dal and spinach...")
            
            if st.form_submit_button("Save Nutrition Log"):
                if water_glasses < 5:
                    st.error(f"⚠️ Warning: You only drank {water_glasses} glasses. Please drink at least 8-10 glasses for proper hydration!")
                else:
                    st.success(f"✅ Nutrition logged! Great job drinking {water_glasses} glasses of water.")

    elif page == "AI Food Planner":
        st.title("🤖 AI Food Planner")
        st.markdown("Personalized weekly nutrition schedule based on your Trimester 2 profile.")
        
        col_diet, col_day = st.columns(2)
        with col_diet:
            diet_type = st.radio("Select Diet Preference:", ["Vegetarian", "Non-Vegetarian"], horizontal=True)
        with col_day:
            days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            selected_day = st.selectbox("Select Day to View:", days_of_week)
            
        # Simulated varied data
        meal_plans = {
            "Monday": {
                "Vegetarian": ("Oatmeal & Almonds", "Dal, Roti, Spinach", "Khichdi & Mixed Veg"),
                "Non-Vegetarian": ("Boiled Eggs & Toast", "Chicken Curry & Rice", "Light Soup & Salad")
            },
            "Tuesday": {
                "Vegetarian": ("Poha & Peanut", "Rajma & Brown Rice", "Paneer Sabzi & Roti"),
                "Non-Vegetarian": ("Omelette & Roti", "Fish Curry & Quinoa", "Grilled Chicken Salad")
            },
            "Wednesday": {
                "Vegetarian": ("Idli & Sambar", "Chana Masala & Roti", "Veg Pulao with Raita"),
                "Non-Vegetarian": ("Egg Bhurji", "Mutton Stew", "Chicken Clear Soup")
            },
            "Thursday": {
                "Vegetarian": ("Upma & Veggies", "Kadhi Pakora & Rice", "Dalia (Cracked Wheat)"),
                "Non-Vegetarian": ("Boiled Eggs & Fruits", "Egg Curry & Rice", "Grilled Fish")
            },
            "Friday": {
                "Vegetarian": ("Besan Chilla", "Aloo Gobi & Roti", "Lentil Soup"),
                "Non-Vegetarian": ("Chicken Sausages", "Chicken Biryani (Light)", "Mutton Soup")
            },
            "Saturday": {
                "Vegetarian": ("Stuffed Paratha (Light)", "Mushroom Curry", "Vegetable Stew"),
                "Non-Vegetarian": ("Scrambled Eggs", "Fish Fry (shallow)", "Chicken Salad")
            },
            "Sunday": {
                "Vegetarian": ("Fruit Smoothie Bowl", "Special Paneer Biryani", "Light Tomato Soup"),
                "Non-Vegetarian": ("Egg Sandwich", "Sunday Special Chicken", "Clear Chicken Soup")
            }
        }
        
        m_meal, a_meal, e_meal = meal_plans[selected_day][diet_type]
        
        col_m, col_a, col_e = st.columns(3)
        
        with col_m:
            st.markdown(f"""
                <div class='health-card'>
                    <h5 style='color:#0b5394;'>🌅 Morning Routine</h5>
                    <ul style='color:#555; padding-left: 20px; font-size: 0.9rem;'>
                        <li>Warm water with lemon</li>
                        <li><b>{m_meal}</b></li>
                        <li>Prenatal Vitamins</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            
        with col_a:
            st.markdown(f"""
                <div class='health-card'>
                    <h5 style='color:#0b5394;'>☀️ Afternoon Lunch</h5>
                    <ul style='color:#555; padding-left: 20px; font-size: 0.9rem;'>
                        <li><b>{a_meal}</b></li>
                        <li>Fresh Greens (Iron focus)</li>
                        <li>Curd (Calcium)</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            
        with col_e:
            st.markdown(f"""
                <div class='health-card'>
                    <h5 style='color:#0b5394;'>🌙 Night Dinner</h5>
                    <ul style='color:#555; padding-left: 20px; font-size: 0.9rem;'>
                        <li><b>{e_meal}</b></li>
                        <li>Easily digestible side</li>
                        <li>Warm Milk before sleep</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

    elif page == "Mood Tracker":
        st.title("😊 Mood Tracker")
        st.markdown("How are you feeling mentally today?")
        
        mood = st.selectbox("Select Current Mood", ["Happy", "Normal", "Stressed", "Very Sad"])
        
        if mood == "Happy" or mood == "Normal":
            st.success("We are so glad you are feeling well! Keep up the positive energy.")
        elif mood == "Stressed":
            st.info("It's completely normal to feel stressed. Try taking 5 deep breaths, or listen to calming music.")
        else:
            st.error("We're sorry you're feeling down. Please don't hesitate to reach out to loved ones or call your ASHA worker if you need support.")

    elif page == "AI Risk Panel":
        st.title("📊 AI Risk Result Panel")
        
        st.markdown("Press the button below to simulate real-time sensor processing and see how the AI engine rapidly analyzes health metrics.")
        
        start_monitor = st.button("🔴 Start Live AI Risk Analysis", type="primary")
        
        dashboard_placeholder = st.empty()
        
        if start_monitor:
            import time
            import random
            
            # Simulate real-time streaming data for 15 frames
            for i in range(15):
                bp_level = random.randint(110, 150)
                swelling_level = random.randint(10, 60)
                fetal_level = random.randint(40, 90)
                stress_level = random.randint(30, 90)
                
                # Formula for simulation score logic
                deduction = ((bp_level - 120) * 0.4) + (swelling_level * 0.3) + ((80 - fetal_level) * 0.4) + (stress_level * 0.2)
                score = max(10, min(100, int(100 - deduction)))
                
                if score > 75:
                    status_title = "Low Risk"
                    status_color = "#28a745"
                    bg_color = "#f4faf6"
                    text_color = "#155724"
                elif score > 50:
                    status_title = "Medium Risk Alert"
                    status_color = "#ffc107"
                    bg_color = "#fffdf5"
                    text_color = "#856404"
                else:
                    status_title = "High Risk Alert"
                    status_color = "#dc3545"
                    bg_color = "#f8d7da"
                    text_color = "#721c24"

                fig = go.Figure(data=[
                    go.Bar(name='Threshold', x=['Blood Pressure', 'Swelling', 'Fetal Movement', 'Stress'], y=[120, 20, 80, 50], marker_color='#e0e0e0'),
                    go.Bar(name='Current Level', x=['Blood Pressure', 'Swelling', 'Fetal Movement', 'Stress'], 
                           y=[bp_level, swelling_level, fetal_level, stress_level], 
                           marker_color=[
                               '#dc3545' if bp_level > 120 else '#28a745',
                               '#dc3545' if swelling_level > 20 else '#28a745',
                               '#dc3545' if fetal_level < 80 else '#28a745',
                               '#dc3545' if stress_level > 50 else '#28a745'
                           ])
                ])
                fig.update_layout(barmode='group', title='Real-time Symptom Monitoring vs Safe Thresholds', template='plotly_white', height=350, margin=dict(l=20, r=20, t=40, b=20))
                
                with dashboard_placeholder.container():
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        st.markdown(f"""
                            <div class='health-card' style='border-left: 6px solid {status_color}; background-color: {bg_color}; height: 100%; transition: all 0.2s ease;'>
                                <h3 style='color: {text_color}; margin-top:0'>Status: {status_title}</h3>
                                <h1 style='font-size: 3rem; margin: 0; color: {text_color};'>Score: {score}/100</h1>
                                <hr>
                                <p><b>Monitoring:</b> Actively reading sensors... 🔄</p>
                                <p><b>Escalation Status:</b> Analyzing condition...</p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                    with c2:
                        st.plotly_chart(fig, use_container_width=True)
                
                time.sleep(0.3)  # Rapid UI refresh delay
            
            # Final steady state
            with dashboard_placeholder.container():
                fig = go.Figure(data=[
                    go.Bar(name='Threshold', x=['Blood Pressure', 'Swelling', 'Fetal Movement', 'Stress'], y=[120, 20, 80, 50], marker_color='#e0e0e0'),
                    go.Bar(name='Last Recorded Level', x=['Blood Pressure', 'Swelling', 'Fetal Movement', 'Stress'], y=[130, 45, 75, 65], marker_color=['#ffc107', '#dc3545', '#28a745', '#ffc107'])
                ])
                fig.update_layout(barmode='group', title='Final AI Assessment vs Safe Thresholds', template='plotly_white', height=350, margin=dict(l=20, r=20, t=40, b=20))
                c1, c2 = st.columns([1, 1])
                with c1:
                    st.markdown(f"""
                        <div class='health-card' style='border-left: 6px solid #ffc107; background-color: #fffdf5; height: 100%;'>
                            <h3 style='color: #856404; margin-top:0'>Final Assessment: Medium Risk Alert</h3>
                            <h1 style='font-size: 3rem; margin: 0;'>Score: 65/100</h1>
                            <hr>
                            <p><b>Recommendation:</b> Monitor swelling closely. Drink fluids.</p>
                            <p><b>Escalation Status:</b> <span style='color:green;'>Not Escalated</span> - Notified local ASHA worker.</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with c2:
                    st.plotly_chart(fig, use_container_width=True)
                    
        else:
            # Default state before clicking button
            with dashboard_placeholder.container():
                st.info("Click '🔴 Start Live AI Risk Analysis' above to simulate real-time vitals monitoring.")

    elif page == "Live Location & Map":
        st.title("📍 Live Location & Nearest PHC")
        st.markdown("Share your live location to see the nearest Primary Health Center (PHC).")
        
        # Capture GPS
        loc = streamlit_geolocation()
        
        if loc and loc.get('latitude') and loc.get('longitude'):
            lat = loc['latitude']
            lon = loc['longitude']
            
            st.success("Location captured successfully!")
            
            # Save to Database
            mother_id = st.session_state.get('unique_id', 'Unknown')
            if mother_id != 'Unknown':
                update_location(mother_id, lat, lon)
                
            # Database of Nearest PHCs (Mock for demonstration)
            phcs = [
                {"name": "Rampur Rural Health Center", "lat": lat + 0.015, "lon": lon + 0.020},
                {"name": "Sitapur PHC", "lat": lat - 0.025, "lon": lon + 0.010},
                {"name": "Kondapur CHC", "lat": lat + 0.005, "lon": lon - 0.018}
            ]
            
            # Calculate nearest
            nearest_phc = None
            min_dist = float('inf')
            for phc in phcs:
                dist = geodesic((lat, lon), (phc["lat"], phc["lon"])).km
                if dist < min_dist:
                    min_dist = dist
                    nearest_phc = phc
                    
            st.info(f"🏥 Your Nearest Health Center is **{nearest_phc['name']}** ({min_dist:.1f} km away)")
            
            # Check latest log to see if high risk
            import sqlite3
            conn = sqlite3.connect("maatrisuraksha.db")
            c = conn.cursor()
            c.execute("SELECT risk_level FROM daily_logs WHERE user_id=? ORDER BY date DESC LIMIT 1", (mother_id,))
            risk_row = c.fetchone()
            conn.close()
            
            is_high_risk = risk_row and risk_row[0] == "High"
            
            if is_high_risk:
                st.error("🚨 HIGH RISK ALERT: Please seek immediate medical attention or contact your ASHA worker.")
                phc_color = "red"
                phc_icon = "plus"
            else:
                phc_color = "green"
                phc_icon = "medkit"
            
            # Draw Map
            m = folium.Map(location=[lat, lon], zoom_start=13)
            
            # Mother's location
            folium.Marker(
                [lat, lon], 
                popup="Your Location", 
                icon=folium.Icon(color="blue", icon="user")
            ).add_to(m)
            
            # Nearest PHC
            folium.Marker(
                [nearest_phc["lat"], nearest_phc["lon"]], 
                popup=nearest_phc["name"], 
                icon=folium.Icon(color=phc_color, icon=phc_icon)
            ).add_to(m)
            
            if is_high_risk:
                # Add red overlay to visualize urgency zone
                folium.Circle(
                    radius=500,
                    location=[lat, lon],
                    color="red",
                    fill=True,
                ).add_to(m)
                
            st_folium(m, width=700, height=450)
            
        else:
            st.warning("Please allow location access to continue.")

    elif page == "Emergency Help":
        st.title("🚨 Emergency Help")
        st.error("⚠️ Press only in case of serious symptoms (Severe bleeding, extreme pain, unconsciousness).")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("🆘 TRIGGER EMERGENCY HELP NOW", type="primary", use_container_width=True):
                mother_id = st.session_state.get('unique_id', 'Unknown')
                if mother_id != 'Unknown':
                    create_alert(mother_id, "MANUAL_SOS", "High")
                    send_sms_alert(mother_id)
                    st.error("🚨 EMERGENCY INITIATED. Alert SMS sent to the registered ASHA worker.")
                else:
                    st.warning("⚠️ Could not identify your profile to send alert.")
    
def asha_worker_dashboard():
    """Render the comprehensive ASHA Worker monitoring portal."""
    
    # Render Sidebar Navigation for ASHA Worker
    with st.sidebar:
        st.header("👩‍⚕️ ASHA Portal")
        st.markdown(f"**District:** Rural Sector 4")
        st.divider()
        
        st.markdown("<p style='color: #888; font-size: 0.8rem; font-weight: bold;'>MONITORING MENU</p>", unsafe_allow_html=True)
        
        nav_options = {
            "Overview": "📊",
            "Geospatial Heatmap": "🌍",
            "Register Mother": "📝",
            "High Risk Alerts": "🚨",
            "All Mothers": "👩",
            "Risk Trends": "📈",
            "Search Mother": "🔍"
        }
        
        for option, icon in nav_options.items():
            if st.button(f"{icon} {option}", use_container_width=True, type="secondary" if st.session_state['asha_page'] != option else "primary"):
                st.session_state['asha_page'] = option
                st.rerun()
                
        st.divider()
        st.selectbox("🌐 Language Toggle", ["English", "Hindi"], key="lang_toggle_asha")
        
        if st.button("🔓 Logout", use_container_width=True):
            logout()

    page = st.session_state['asha_page']
    
    # Fetch real data
    try:
        logs_data = get_all_logs()
        alerts_data = get_active_alerts()
    except Exception as e:
        logs_data = []
        alerts_data = []
        st.error("Database connection error. Displaying empty datasets.")

    if page == "Overview":
        st.title("📊 System Overview")
        st.markdown("<p style='font-size: 1.1rem; color: #555;'>Real-time situational awareness of assigned mothers.</p>", unsafe_allow_html=True)
        
        # Calculate mock metrics from db rows if available, otherwise fallback to defaults
        total_mothers = max(124, len(logs_data)) if logs_data else 124
        active_alerts = len(alerts_data) if alerts_data else 3
        high_risk = active_alerts
        med_risk = 18
        low_risk = total_mothers - high_risk - med_risk

        st.markdown("<br>", unsafe_allow_html=True)
        m1, m2, m3, m4, m5 = st.columns(5)
        
        with m1:
            st.markdown(f"<div class='asha-metric-box'><p class='metric-title'>Total Mothers</p><p class='metric-value val-blue'>{total_mothers}</p></div>", unsafe_allow_html=True)
        with m2:
            st.markdown(f"<div class='asha-metric-box'><p class='metric-title'>Active Alerts</p><p class='metric-value val-red'>{active_alerts}</p></div>", unsafe_allow_html=True)
        with m3:
            st.markdown(f"<div class='asha-metric-box'><p class='metric-title' style='color:#dc3545'>High Risk</p><p class='metric-value val-red'>{high_risk}</p></div>", unsafe_allow_html=True)
        with m4:
            st.markdown(f"<div class='asha-metric-box'><p class='metric-title' style='color:#ffc107'>Medium Risk</p><p class='metric-value val-yellow'>{med_risk}</p></div>", unsafe_allow_html=True)
        with m5:
            st.markdown(f"<div class='asha-metric-box'><p class='metric-title' style='color:#28a745'>Low Risk</p><p class='metric-value val-green'>{low_risk}</p></div>", unsafe_allow_html=True)

        st.markdown("<br><hr><br>", unsafe_allow_html=True)
        st.subheader("📅 Recent System Activity")
        if logs_data:
            df_recent = pd.DataFrame(logs_data, columns=["Log ID", "Mother ID", "Symptoms", "Mood", "Nutrition", "Risk Score", "Risk Level", "Date"])
            st.dataframe(df_recent.head(5)[["Mother ID", "Risk Level", "Symptoms", "Date"]], use_container_width=True, hide_index=True)
        else:
            st.info("No recent logs found in database.")

    elif page == "Geospatial Heatmap":
        st.title("🌍 Geospatial Heatmap & Tracking")
        st.markdown("<p style='font-size: 1.1rem; color: #555;'>Live interactive map of all mothers showing risk levels and locations.</p>", unsafe_allow_html=True)
        
        with st.spinner("Fetching latest geospatial data..."):
            all_mothers_data = get_mothers_with_risk_and_location()
        
        if not all_mothers_data:
            st.info("No mothers found in the database. Please register mothers first.")
        else:
            # mother shape: u.unique_id(0), u.name(1), u.village(2), u.latitude(3), u.longitude(4), l.risk_level(5), l.risk_score(6), l.date(7)
            map_data = []
            for row in all_mothers_data:
                lat = row[3]
                lon = row[4]
                if lat and lon: # Only map if location exists
                    map_data.append({
                        "id": row[0],
                        "name": row[1],
                        "village": row[2] or "Unknown",
                        "lat": lat,
                        "lon": lon,
                        "risk_level": row[5] or "Low",
                        "risk_score": row[6] or 0,
                        "timestamp": row[7] or "Unknown"
                    })
                    
            if not map_data:
                st.warning("No mothers have shared their location yet.")
            else:
                # Calculate bounds
                high_risk_bounds = []
                all_bounds = []
                
                for md in map_data:
                    all_bounds.append([md["lat"], md["lon"]])
                    if md["risk_level"] == "High":
                        high_risk_bounds.append([md["lat"], md["lon"]])
                
                # Center map roughly
                avg_lat = sum([float(b[0]) for b in all_bounds]) / len(all_bounds)
                avg_lon = sum([float(b[1]) for b in all_bounds]) / len(all_bounds)
                
                # Initialize map
                m = folium.Map(location=[avg_lat, avg_lon], zoom_start=11)
                
                # Add markers
                for md in map_data:
                    if md["risk_level"] == "High":
                        color = "red"
                        radius = 12
                        fill_opacity = 0.8
                    elif md["risk_level"] == "Medium":
                        color = "orange"
                        radius = 10
                        fill_opacity = 0.6
                    else:
                        color = "green"
                        radius = 8
                        fill_opacity = 0.5
                        
                    html_popup = f"""
                    <div style="font-family: Arial; min-width: 150px;">
                        <h4>{md['id']} - {md['name']}</h4>
                        <b>Village:</b> {md['village']}<br>
                        <b>Risk Level:</b> <span style="color:{color}; font-weight:bold;">{md['risk_level']}</span><br>
                        <b>Risk Score:</b> {md['risk_score']}<br>
                        <b>Last Updated:</b> {md['timestamp']}
                    </div>
                    """
                    
                    folium.CircleMarker(
                        location=[md["lat"], md["lon"]],
                        radius=radius,
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity=fill_opacity,
                        tooltip=f"{md['id']} ({md['risk_level']})",
                        popup=folium.Popup(html_popup, max_width=300)
                    ).add_to(m)
                
                # Auto-zoom to high-risk clusters if they exist, else to all
                focus_mother_id = st.session_state.get('map_focus_mother')
                focus_bounds = []
                
                if focus_mother_id:
                    for md in map_data:
                        if md["id"] == focus_mother_id:
                            focus_bounds.append([md["lat"], md["lon"]])
                
                if focus_bounds:
                    # Zoom tightly to single mother
                    st.info(f"📍 Map is currently focused on Mother ID: {focus_mother_id}")
                    if st.button("Clear Focus", size="small"):
                        st.session_state['map_focus_mother'] = None
                        st.rerun()
                    m.fit_bounds([focus_bounds[0], focus_bounds[0]], max_zoom=15)
                elif high_risk_bounds:
                    m.fit_bounds(high_risk_bounds)
                else:
                    m.fit_bounds(all_bounds)
                    
                st_folium(m, width=800, height=500)

    elif page == "High Risk Alerts":
        st.title("🚨 High Risk Alerts")
        st.error("ACTION REQUIRED: Proceed to visit or contact these mothers immediately.")
        
        if not alerts_data:
            # Fallback mock data if DB is totally empty for demonstration
            df_alerts = pd.DataFrame([
                {"Mother ID": "M-8042", "Village": "Rampur", "Risk Level": "High", "Risk Score": 85, "Date": "2026-02-27 10:15 AM", "Alert Status": "Active"},
                {"Mother ID": "M-1029", "Village": "Sitapur", "Risk Level": "High", "Risk Score": 92, "Date": "2026-02-27 09:30 AM", "Alert Status": "Active"},
                {"Mother ID": "M-5531", "Village": "Rampur", "Risk Level": "High", "Risk Score": 78, "Date": "2026-02-27 08:45 AM", "Alert Status": "Active"}
            ])
        else:
            # Need to get Village and Risk Score which aren't in the generic alerts return
            import sqlite3
            conn = sqlite3.connect("maatrisuraksha.db")
            query = """
                SELECT a.id, a.user_id, a.risk_level, a.status, a.timestamp, u.village, 
                       (SELECT risk_score FROM daily_logs WHERE user_id = a.user_id ORDER BY date DESC LIMIT 1) as risk_score
                FROM alerts a
                JOIN users u ON a.user_id = u.unique_id
                WHERE a.status = 'Active'
            """
            df_alerts = pd.read_sql_query(query, conn)
            conn.close()
            
            if not df_alerts.empty:
                df_alerts.rename(columns={
                    "user_id": "Mother ID", 
                    "village": "Village",
                    "risk_level": "Risk Level",
                    "risk_score": "Risk Score",
                    "timestamp": "Date",
                    "status": "Alert Status"
                }, inplace=True)
                df_alerts = df_alerts[["Mother ID", "Village", "Risk Level", "Risk Score", "Date", "Alert Status"]]
            else:
                df_alerts = pd.DataFrame(columns=["Mother ID", "Village", "Risk Level", "Risk Score", "Date", "Alert Status"])
            
        # Sort by Risk Score descending (highest risk first)
        df_alerts = df_alerts.sort_values(by="Risk Score", ascending=False)
        
        # Add a column that contains the actual app URL to make LinkColumn work
        # To do this natively in streamlit without an actual external URL, we can use query parameters
        base_url = "http://localhost:8503/?nav=Geospatial+Heatmap&focus="
        df_alerts["View Map"] = base_url + df_alerts["Mother ID"]
        
        # Display table with Streamlit configuration
        st.dataframe(
            df_alerts,
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Village": st.column_config.TextColumn("Village"),
                "Risk Level": st.column_config.TextColumn("Risk Level"),
                "View Map": st.column_config.LinkColumn("View Map", 
                                                        display_text="📍 See Map",
                                                        help="Click to open full Geospatial Heatmap")
            }
        )
        
        # Add a manual button alternative to jump to heatmap
        if st.button("🌍 Open Full Geospatial Heatmap", type="primary"):
            st.session_state['asha_page'] = "Geospatial Heatmap"
            st.rerun()
        
        st.markdown("### Resolve Alerts")
        c1, c2 = st.columns([3, 1])
        with c1:
            resolve_id = st.selectbox("Select Mother ID to mark as resolved:", df_alerts["Mother ID"].tolist())
        with c2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✅ Mark as Resolved", type="primary", use_container_width=True):
                st.success(f"Alert for {resolve_id} marked as resolved. Database updated.")

    elif page == "All Mothers":
        st.title("👩 All Monitored Mothers")
        st.markdown("Complete directory of assigned cases.")
        
        import sqlite3
        conn = sqlite3.connect("maatrisuraksha.db")
        # Fetch latest log for each mother joined with user info
        query_all = """
            WITH LatestLogs AS (
                SELECT user_id, risk_level, risk_score, mood, date
                FROM daily_logs
                WHERE id IN (
                    SELECT MAX(id)
                    FROM daily_logs
                    GROUP BY user_id
                )
            )
            SELECT u.unique_id as 'Mother ID', 
                   COALESCE(l.risk_level, 'Low') as 'Risk Level', 
                   COALESCE(l.risk_score, 0) as 'Risk Score', 
                   COALESCE(l.mood, 'Unknown') as 'Mood',
                   COALESCE(l.date, 'No Logs') as 'Date',
                   u.village as 'Village'
            FROM users u
            LEFT JOIN LatestLogs l ON u.unique_id = l.user_id
            WHERE u.role = 'Mother'
        """
        df_all = pd.read_sql_query(query_all, conn)
        conn.close()
        
        if df_all.empty:
            st.info("No mothers registered yet.")
            df_all = pd.DataFrame(columns=["Mother ID", "Risk Level", "Risk Score", "Mood", "Date", "Village"])
            
        # Filters
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            risk_filter = st.selectbox("Filter by Risk Level:", ["Show All", "High", "Medium", "Low"])
        with col_f2:
            sort_order = st.radio("Sort Order:", ["Highest Risk First", "Lowest Risk First"], horizontal=True)
            
        # Apply filters
        if risk_filter != "Show All":
            df_all = df_all[df_all["Risk Level"] == risk_filter]
            
        # Apply sort
        ascending_sort = False if sort_order == "Highest Risk First" else True
        df_all = df_all.sort_values(by="Risk Score", ascending=ascending_sort)
        
        st.dataframe(df_all, use_container_width=True, hide_index=True)

    elif page == "Risk Trends":
        st.title("📈 Risk Score Trends")
        st.markdown("View historical risk data for a specific mother to identify deteriorating conditions.")
        
        mother_focus = st.text_input("Enter Mother ID (e.g., M-8042):", "M-8042")
        
        if st.button("Generate Trend Chart"):
            # Mock historical dates
            dates = pd.date_range(end=datetime.datetime.today(), periods=14).strftime("%b %d").tolist()
            # Mock trend: getting worse over two weeks
            scores = [15, 12, 18, 20, 25, 22, 35, 40, 45, 60, 65, 78, 82, 85]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dates, y=scores, mode='lines+markers', name='Risk Score', line=dict(color='#dc3545', width=3)))
            # Add safe threshold line
            fig.add_hline(y=50, line_dash="dash", line_color="orange", annotation_text="Medium Risk Threshold")
            fig.add_hline(y=75, line_dash="dash", line_color="red", annotation_text="High Risk Threshold")
            
            fig.update_layout(title=f'14-Day Risk Trend for {mother_focus}', xaxis_title='Date', yaxis_title='Risk Score (0-100)', template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)

    elif page == "Search Mother":
        st.title("🔍 Search Mother Record")
        search_id = st.text_input("Scan or Enter Mother ID:", placeholder="M-XXXX")
        
        if st.button("Fetch Records", type="primary"):
            if not search_id.strip():
                st.warning("Please enter an ID.")
            else:
                with st.spinner("Querying database..."):
                    import time
                    time.sleep(1)
                    st.success(f"Record found for {search_id}")
                    
                    st.markdown("""
                        <div class='health-card' style='border-left: 5px solid #0b5394;'>
                            <h4>📝 Most Recent Health Summary</h4>
                            <p><b>Last Checked:</b> Today, 10:15 AM</p>
                            <p><b>Current Risk Score:</b> 45 (Medium)</p>
                            <p><b>Reported Symptoms:</b> Mild headache, slight foot swelling.</p>
                            <p><b>AI Note:</b> Mother instructed to increase water intake to 10 glasses/day.</p>
                        </div>
                    """, unsafe_allow_html=True)

    elif page == "Register Mother":
        st.title("📝 Register New Mother")
        st.markdown("Create a new patient record with a Unique ID.")
        
        with st.form("register_mother_form"):
            new_id = st.text_input("🆔 Assign Unique ID *", placeholder="e.g. M-001 (Must be unique)")
            new_name = st.text_input("👤 Full Name *", placeholder="Mother's name")
            new_phone = st.text_input("📱 Phone Number", placeholder="10-digit mobile number")
            new_village = st.text_input("🏘️ Village *", placeholder="Village name")
            
            submit_register = st.form_submit_button("Register Mother", type="primary")
            
            if submit_register:
                if not new_id.strip() or not new_name.strip() or not new_village.strip():
                    st.error("⚠️ Please fill in all required fields marked with *.")
                else:
                    success = register_mother(new_id.strip(), new_name.strip(), new_phone.strip(), new_village.strip())
                    if success:
                        st.success(f"✅ Successfully registered {new_name.strip()} with ID {new_id.strip()}!")
                    else:
                        st.error(f"❌ ID '{new_id.strip()}' is already taken. Please assign a different Unique ID.")

def logout():
    """Clear session data and return to login."""
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.rerun()

def render_footer():
    """Render the permanent bottom footer."""
    st.markdown("""
        <div class="custom-footer">
            <div>&copy; 2026 MAATRI SURAKSHA AI. All Rights Reserved.</div>
            <div class="footer-links">
                <a href="#">Privacy Policy</a> | <a href="#">Terms of Service</a> | <a href="#">Help Center</a>
            </div>
        </div>
    """, unsafe_allow_html=True)

def main():
    init_session_state()
    
    if not st.session_state['logged_in']:
        login_page()
    else:
        # Session-Based Routing to Respective Dashboards
        if st.session_state['role'] == "Mother":
            mother_dashboard()
        elif st.session_state['role'] == "ASHA Worker":
            asha_worker_dashboard()
            
    # Always render footer at the very end
    render_footer()

if __name__ == "__main__":
    main()