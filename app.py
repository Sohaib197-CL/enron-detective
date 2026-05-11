import streamlit as st
import os
from pinecone import Pinecone
from openai import OpenAI
from dotenv import load_dotenv
from fpdf import FPDF

# --- INITIALIZATION ---
load_dotenv()

# CUSTOM LOGO LINK
ICON_URL = "https://raw.githubusercontent.com/Sohaib197-CL/enron-detective/main/logo.pys.png"

st.set_page_config(
    page_title="Enron Intelligence", 
    page_icon=ICON_URL, 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- STYLE VAULT ---
st.markdown("""
    <style>
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; visibility: visible !important; }
    button[kind="headerNoContext"] { background-color: #007BFF !important; color: white !important; border-radius: 5px !important; }
    .stApp { background-color: #0B0E11 !important; }
    [data-testid="stChatMessage"] div { color: #FFFFFF !important; }
    div[data-testid="stBottomBlockContainer"] { background-color: #0B0E11 !important; }
    [data-testid="stChatInput"] { background-color: #161B22 !important; border: 1px solid #2D3339 !important; border-radius: 12px !important; }
    [data-testid="stSidebar"] { background-color: #101418 !important; border-right: 1px solid #2D3339; }
    div.stButton > button { background-color: #007BFF !important; color: white !important; font-weight: bold !important; }
    .history-item { color: #8B949E; font-size: 13px; margin-bottom: 8px; border-left: 2px solid #007BFF; padding-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("enron-detective")
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- PDF GENERATOR ---
def create_pdf(history):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(0, 123, 255)
    pdf.cell(200, 15, txt="ENRON INVESTIGATION REPORT", ln=True, align='C')
    pdf.ln(10)
    for msg in history:
        role = "INVESTIGATOR" if msg["role"] == "user" else "AI"
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, f"[{role}]:", ln=True)
        pdf.set_font("Arial", size=9)
        content = msg["content"].encode('latin-1', 'ignore').decode('latin-1')
        pdf.multi_cell(0, 5, txt=content)
        pdf.ln(4)
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color: white;'>Enron <span style='color:#007BFF'>Intelligence</span></h2>", unsafe_allow_html=True)
    
    # REVERTED & UPDATED: New Chat Button
    if st.button("+ New Chat"):
        st.session_state.messages = []
        st.rerun()
    
    # Investigation Log (Visual History)
    user_questions = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
    if user_questions:
        st.markdown("<p style='color: white; font-size: 14px; font-weight: bold; margin-top: 20px;'>INVESTIGATION LOG</p>", unsafe_allow_html=True)
        for q in user_questions:
            st.markdown(f'<div class="history-item">{q[:25]}...</div>', unsafe_allow_html=True)
    
    st.markdown("---")

    # Tech Stack
    with st.expander("🛠️ Tech Stack Details"):
        st.write("**Model:** Gemini 2.0 Flash")
        st.write("**Database:** Pinecone Vector DB")
        st.write("**Frontend:** Streamlit")
        st.write("**Dataset:** Enron Email Archive")
    
    if st.session_state.messages:
        pdf_report = create_pdf(st.session_state.messages)
        st.download_button(label="📥 DOWNLOAD REPORT", data=pdf_report, file_name="Enron_Report.pdf", mime="application/pdf", use_container_width=True)

# --- MAIN INTERFACE ---
st.markdown("<h1 style='color:white; margin-top:0px;'>FORENSIC ARCHIVE</h1>", unsafe_allow_html=True)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "evidence" in message:
            for doc in message["evidence"]:
                with st.expander(f"🔍 View Email: {doc['id']}"):
                    st.write(doc['text'])

# --- CHAT LOGIC ---
if prompt := st.chat_input("Search the archive..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # RAG: Search Pinecone
    query_vector = pc.inference.embed(model="multilingual-e5-large", inputs=[prompt], parameters={"input_type": "query"})
    results = index.query(vector=query_vector[0].values, top_k=5, include_metadata=True)
    
    evidence_context = ""
    evidence_list = []
    for m in results['matches']:
        text = m['metadata'].get('text', '')
        evidence_context += f"Source {m['id']}: {text}\n\n"
        evidence_list.append({"id": m['id'], "text": text})

    # AI Memory
    chat_memory = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-6:]]
    messages_for_ai = [
        {"role": "system", "content": f"You are a forensic expert. Answer based on the provided evidence and history. Evidence:\n{evidence_context}"},
        *chat_memory
    ]

    with st.spinner("Analyzing Archive..."):
        response = client.chat.completions.create(model="google/gemini-2.0-flash-001", messages=messages_for_ai)
        st.session_state.messages.append({"role": "assistant", "content": response.choices[0].message.content, "evidence": evidence_list})
        st.rerun()
