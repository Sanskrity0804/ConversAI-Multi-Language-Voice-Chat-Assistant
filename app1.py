import streamlit as st
import speech_recognition as sr
import pyttsx3
from gtts import gTTS
import os
import tempfile
import json
from deep_translator import GoogleTranslator
import google.generativeai as genai

# ---------------- Gemini Configuration ----------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

# ---------------- TTS Engine ----------------
engine = pyttsx3.init()

# ---------------- Language Dictionary ----------------
LANGUAGES = {
    "English": "en",
    "Hindi": "hi",
    "Bengali": "bn",
    "Gujarati": "gu",
    "Tamil": "ta",
    "Telugu": "te",
    "Marathi": "mr",
    "Punjabi": "pa",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Urdu": "ur"
}

# ---------------- User Management ----------------
USERS_FILE = "users.json"
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

def register_user(email, password):
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    if email in users:
        return False
    users[email] = password
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)
    return True

def login_user(email, password):
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    if email in users and users[email] == password:
        return True
    return False

# ---------------- Session State ----------------
if "history" not in st.session_state:
    st.session_state.history = []
if "current_q" not in st.session_state:
    st.session_state.current_q = ""
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- Sidebar ----------------
st.sidebar.header("⚙️ Settings")

# Login/Register Form
st.sidebar.subheader("👤 User Login/Register")
auth_mode = st.sidebar.radio("Mode", ["Login", "Register"])
email = st.sidebar.text_input("Email", key="email")
password = st.sidebar.text_input("Password", type="password", key="pwd")

if st.sidebar.button("Submit"):
    if auth_mode == "Register":
        if register_user(email, password):
            st.sidebar.success("✅ Registered successfully! Please login.")
        else:
            st.sidebar.error("❌ User already exists.")
    else:
        if login_user(email, password):
            st.session_state.user = email
            st.sidebar.success(f"Logged in as {email}")
        else:
            st.sidebar.error("❌ Invalid credentials.")

if st.session_state.user:
    st.sidebar.info(f"Logged in: {st.session_state.user}")

# Language Selection
question_lang = st.sidebar.selectbox("🌍 Question Language", list(LANGUAGES.keys()), index=0)
answer_lang = st.sidebar.selectbox("🗣️ Answer Language", list(LANGUAGES.keys()), index=0)

# Extra Features
voice_enabled = st.sidebar.checkbox("🔊 Voice Answer")
summarize_mode = st.sidebar.checkbox("📝 Summarize Mode")

# Clear chat
if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state.history = []
    st.sidebar.success("Chat cleared!")

# ---------------- Functions ----------------
def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("🎙️ Listening...")
        audio = recognizer.listen(source)
        try:
            return recognizer.recognize_google(audio, language=LANGUAGES[question_lang])
        except sr.UnknownValueError:
            return "❌ Could not understand audio"
        except sr.RequestError:
            return "⚠️ Speech recognition service error"

def text_to_speech(text, lang_code):
    try:
        tts = gTTS(text=text, lang=lang_code)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_file = fp.name
            tts.save(temp_file)
        st.audio(temp_file, format="audio/mp3")
        os.remove(temp_file)
    except Exception as e:
        st.error(f"gTTS Error: {e}")

def ask_gemini(prompt):
    response = model.generate_content(prompt)
    return response.text

# ---------------- UI ----------------
st.title("🎙️ ConversAI: Multi-Language Voice & Chat Assistant")

# Chat Input with Mic + Send buttons parallel to input
input_col1, input_col2, input_col3 = st.columns([6,1,1])
with input_col1:
    user_q = st.text_input("🔍 Ask something…", value=st.session_state.current_q, key="input_box")
with input_col2:
    send_btn = st.button("➤")  # Send button
with input_col3:
    mic_btn = st.button("🎙️")  # Mic button

# Handle mic input
if mic_btn:
    user_q = speech_to_text()
    st.session_state.current_q = user_q
    send_btn = True

# ---------------- Process Query ----------------
if send_btn and user_q:
    # Translate question to English for Gemini
    translated_q = GoogleTranslator(source=LANGUAGES[question_lang], target="en").translate(user_q)

    # Get AI response
    response = ask_gemini(translated_q)

    # Summarize mode
    if summarize_mode:
        response = ask_gemini("Summarize this in points:\n" + response)

    # Translate to answer language
    final_response = GoogleTranslator(source="en", target=LANGUAGES[answer_lang]).translate(response)

    # Save chat history (latest first)
    st.session_state.history.insert(0, ("You", user_q))
    st.session_state.history.insert(0, ("Assistant", final_response))

    # Voice answer
    if voice_enabled:
        text_to_speech(final_response, LANGUAGES[answer_lang])

    # Clear input box
    st.session_state.current_q = ""

# ---------------- Show Chat History ----------------
st.markdown("📖 Chat History")
for role, text in st.session_state.history:
    if role == "You":
        st.markdown(f"**👤 {role}:** {text}")
    else:
        st.markdown(f"**🤖 {role}:** {text}")
