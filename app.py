import streamlit as st
import os
from pinecone import Pinecone
from openai import OpenAI
from dotenv import load_dotenv
from fpdf import FPDF

# --- INITIALIZATION ---
load_dotenv()
st.set_page_config(page_title="OmniMind Intelligence", page_icon="🕵️", layout="wide", initial_sidebar_state="expanded")

# --- THE CLEAN STYLE ---
st.markdown("""
    <style>
    /* Resetting the header visibility to ensure the arrow can exist */
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; visibility: visible !important; }
    
    /* Making the sidebar arrow BRIGHT BLUE so it stands out against the black */
    button[kind="headerNoContext"] { 
        background-color: #007BFF !important; 
        color: white !important; 
        border-radius: 5px !important;
    }

    .stApp { background-color: #0B0E11 !important; }
    [data-testid="stChatMessage"] div { color: #FFFFFF !important; }
    div[data-testid="stBottomBlockContainer"] { background-color: #0B0E11 !important; }
    [data-testid="stChatInput"] { background-color: #161B22 !important; border: 1px solid #2D3339 !important; border-radius: 12px !important; }
    [data-testid="stSidebar"] { background-color: #101418 !important; border-right: 1px solid #2D3339; }
    
    .evidence-chip { background-color: #161B22; color: #007BFF !important; border: 1px solid #007BFF; padding: 4px 12px; border-radius: 16px; font-size: 12px; font-weight: bold; display: inline-block; margin-bottom: 5px; }
    div.stButton > button { background-color: #007BFF !important; color: white !important; font-weight: bold !important; }
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
    pdf.cell(200, 15, txt="OMNIMIND FORENSIC CASE FILE", ln=True, align='C')
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
    st.markdown("<h2 style='color: white;'>OmniMind <span style='color:#007BFF'>AI</span></h2>", unsafe_allow_html=True)
    history_count = len(st.session_state.messages) // 2
    st.markdown(f"<p style='color: #8B949E; font-size: 12px;'>Case History: {history_count} exchanges</p>", unsafe_allow_html=True)
    
    if st.button("+ Start New Case"):
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    if st.session_state.messages:
        pdf_report = create_pdf(st.session_state.messages)
        st.download_button(label="📥 DOWNLOAD CASE REPORT", data=pdf_report, file_name="OmniMind_Report.pdf", mime="application/pdf", use_container_width=True)

# --- MAIN INTERFACE ---
# Emergency fallback: If sidebar is closed, this button is easy to see
col1, col2 = st.columns([8, 2])
with col1:
    st.markdown("<h1 style='color:white; margin-top:0px;'>ENRON FORENSIC ARCHIVE</h1>", unsafe_allow_html=True)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "evidence" in message:
            for doc in message["evidence"]:
                with st.expander(f"🔍 View Email Source: {doc['id']}"):
                    st.write(doc['text'])

# --- CHAT LOGIC ---
if prompt := st.chat_input("Ask OmniMind anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    query_vector = pc.inference.embed(model="multilingual-e5-large", inputs=[prompt], parameters={"input_type": "query"})
    results = index.query(vector=query_vector[0].values, top_k=5, include_metadata=True)
    
    evidence_context = ""
    evidence_list = []
    for m in results['matches']:
        text = m['metadata'].get('text', '')
        evidence_context += f"Source {m['id']}: {text}\n\n"
        evidence_list.append({"id": m['id'], "text": text})

    chat_memory = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-6:]]
    messages_for_ai = [
        {"role": "system", "content": f"You are a lead investigator. Use this evidence and history. Evidence:\n{evidence_context}"},
        *chat_memory
    ]

    with st.spinner("Searching..."):
        response = client.chat.completions.create(model="google/gemini-2.0-flash-001", messages=messages_for_ai)
        st.session_state.messages.append({"role": "assistant", "content": response.choices[0].message.content, "evidence": evidence_list})
        st.rerun()
