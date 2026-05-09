import streamlit as st
import os
from pinecone import Pinecone
from openai import OpenAI
from dotenv import load_dotenv
import re
from fpdf import FPDF

# --- PAGE CONFIG ---
load_dotenv()
st.set_page_config(page_title="OmniMind Intelligence", page_icon="🕵️", layout="wide")

# --- STYLE VAULT ---
st.markdown("""
    <style>
    header, footer, .stAppHeader, [data-testid="stHeader"] { background-color: transparent !important; visibility: hidden; }
    .stApp { background-color: #0B0E11 !important; }
    [data-testid="stChatMessage"] div { color: #FFFFFF !important; }
    div[data-testid="stBottomBlockContainer"] { background-color: #0B0E11 !important; }
    [data-testid="stChatInput"] { background-color: #161B22 !important; border: 1px solid #2D3339 !important; border-radius: 12px !important; }
    
    [data-testid="stSidebar"] { background-color: #101418 !important; border-right: 1px solid #2D3339; }
    .chip-label { color: #8B949E; font-size: 11px; margin-top: 20px; font-weight: bold; text-transform: uppercase; }
    .evidence-chip { background-color: #161B22; color: #007BFF !important; border: 1px solid #007BFF; padding: 4px 12px; border-radius: 16px; font-size: 12px; font-weight: bold; display: inline-block; }
    
    div.stButton > button {
        background-color: #007BFF !important;
        color: white !important;
        border: none !important;
        width: 100% !important;
        border-radius: 8px !important;
        font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BACKEND ---
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
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(200, 5, txt="Proprietary Investigation: Enron Archive Subset", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "SECTION I: ANALYTICAL DIALOGUE", ln=True)
    pdf.ln(2)
    
    for msg in history:
        role = "INVESTIGATOR" if msg["role"] == "user" else "OMNIMIND AI"
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, f"[{role}]:", ln=True)
        pdf.set_font("Arial", size=9)
        content = msg["content"].encode('latin-1', 'ignore').decode('latin-1')
        pdf.multi_cell(0, 5, txt=content)
        pdf.ln(4)

    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "SECTION II: VERIFIED SOURCE MATERIAL", ln=True)
    pdf.ln(5)

    seen_ids = set()
    for msg in history:
        if "evidence" in msg:
            for doc in msg["evidence"]:
                if doc['id'] not in seen_ids:
                    pdf.set_font("Arial", 'B', 10)
                    pdf.set_text_color(0, 123, 255)
                    pdf.cell(0, 7, f"DOC ID: {doc['id']} | SENDER: {doc['sender']}", ln=True)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Arial", size=8)
                    clean_text = doc['text'].encode('latin-1', 'ignore').decode('latin-1')
                    pdf.multi_cell(0, 4, txt=clean_text[:1000] + "..." if len(clean_text) > 1000 else clean_text)
                    pdf.ln(5)
                    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                    pdf.ln(5)
                    seen_ids.add(doc['id'])

    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color: white; margin-bottom:0;'>OmniMind <span style='color:#007BFF'>AI</span></h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8B949E; font-size: 11px; margin-bottom:20px;'>Forensic Intelligence Unit</p>", unsafe_allow_html=True)
    
    if st.button("+ Start New Case"):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    if st.session_state.messages:
        pdf_report = create_pdf(st.session_state.messages)
        st.download_button(
            label="📥 DOWNLOAD CASE REPORT",
            data=pdf_report,
            file_name="OmniMind_Forensic_Report.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# --- MAIN INTERFACE ---
st.markdown("<h1 style='color:white; margin-top:40px; font-weight:800;'>ENRON FORENSIC ARCHIVE</h1>", unsafe_allow_html=True)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "evidence" in message:
            st.markdown('<div class="chip-label">VERIFIED EVIDENCE SOURCES:</div>', unsafe_allow_html=True)
            for doc in message["evidence"]:
                st.markdown(f'<div class="evidence-chip">🔍 {doc["id"]}</div>', unsafe_allow_html=True)
                with st.expander(f"Review Email: {doc['id']}"):
                    st.write(f"**Identified Sender:** {doc['sender']}")
                    st.write("---")
                    st.write(doc['text'])

# --- LOGIC ---
if prompt := st.chat_input("Ask OmniMind anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    user_query = st.session_state.messages[-1]["content"]
    with st.spinner("Analyzing Archive..."):
        query_vector = pc.inference.embed(model="multilingual-e5-large", inputs=[user_query], parameters={"input_type": "query"})
        results = index.query(vector=query_vector[0].values, top_k=10, include_metadata=True)
        evidence_context = ""
        evidence_list = []
        for m in results['matches']:
            full_text = m['metadata'].get('text', '')
            sender_match = re.search(r"(?:From|Sent by|Author):\s*([^\n\r]+)", full_text, re.IGNORECASE)
            found_sender = sender_match.group(1).strip() if sender_match else "External Source"
            evidence_context += f"Doc {m['id']} (Sender: {found_sender}): {full_text}\n\n"
            evidence_list.append({"id": m['id'], "sender": found_sender, "text": full_text})

        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[
                {"role": "system", "content": "You are a lead forensic investigator. Provide detailed analysis based on the evidence."},
                {"role": "user", "content": f"Evidence:\n{evidence_context}\n\nQuestion: {user_query}"}
            ]
        )
        answer = response.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": answer, "evidence": evidence_list})
        st.rerun()
