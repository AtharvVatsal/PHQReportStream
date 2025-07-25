import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
import xlsxwriter

# AI LAYER (DistilBERT)
try:
    from transformers import AutoTokenizer, AutoModelForQuestionAnswering, pipeline
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False

st.set_page_config(page_title="IRBn ReportStream v3 FINAL", layout="wide")

st.markdown(
    """
    <style>
    .report-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .section-subtitle {
        font-size: 1.25rem;
        font-weight: 600;
        color: #34495e;
        margin-top: 1.5rem;
        margin-bottom: 0.25rem;
    }
    .footer-text {
        font-size: 0.85rem;
        color: #95a5a6;
        text-align: center;
        margin-top: 2rem;
    }
    .stButton>button {
        border-radius: 1rem;
        padding: 0.5rem 1rem;
    }
    .stDownloadButton>button {
        background-color: #1abc9c;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="report-title">📋 IRBn ReportStream v3 — FINAL<br><small>Strict Template + Smart Fallback + AI</small></div>', unsafe_allow_html=True)
st.caption("Build date: 22-Jul-2025")

# Add optional logo (replace 'logo.png' with your actual asset)
st.image("logo.png", width=120)

COLUMNS = [
    "Name of IRBn/Bn",
    "Reserves Deployed (District / Strength / Duration / In-Charge)",
    "Districts where force deployed",
    "Stay Arrangement / Bathrooms (Quality)",
    "Messing Arrangements",
    "CO's last Interaction with SP",
    "Disciplinary Issues",
    "Reserves Detained",
    "Training",
    "Welfare Initiative in Last 24 Hrs",
    "Reserves Available in Bn",
    "Issue for AP&T / PHQ",
]

COLUMN_WIDTHS = {
    "S. No": 6,
    "Name of IRBn/Bn": 28,
    "Reserves Deployed (District / Strength / Duration / In-Charge)": 72,
    "Districts where force deployed": 28,
    "Stay Arrangement / Bathrooms (Quality)": 32,
    "Messing Arrangements": 28,
    "CO's last Interaction with SP": 36,
    "Disciplinary Issues": 26,
    "Reserves Detained": 26,
    "Training": 26,
    "Welfare Initiative in Last 24 Hrs": 32,
    "Reserves Available in Bn": 28,
    "Issue for AP&T / PHQ": 28,
}

DELIMITERS = ["\n---\n", "\n#####\n", "\n===\n"]

# Sidebar with grouped controls

st.sidebar.markdown("<h3 class='section-subtitle'>⚙️ Settings</h3>", unsafe_allow_html=True)
with st.sidebar.expander("AI Assist", expanded=True):
    use_ai = st.checkbox(
        "Enable AI assist (DistilBERT)", value=True,
        help="Runs a QA model to verify/fill fields. Falls back if model not available."
    )
    qa_pipe = None
    if use_ai:
        from transformers import AutoTokenizer, AutoModelForQuestionAnswering, pipeline  # ensure import context
        qa_pipe = load_qa()
        if qa_pipe is None:
            st.warning("QA model not loaded; regex/parsers only.")

with st.sidebar.expander("Batch Mode", expanded=False):
    batch_mode = st.checkbox(
        "Batch paste (split by delimiters)", value=False,
        help="Split multiple reports by --- or ##### or ==="
    )

# Main input & extraction form
st.markdown("<div class='section-subtitle'>📨 Paste WhatsApp Report Text</div>", unsafe_allow_html=True)
col1, col2 = st.columns([2, 1])
with col1:
    with st.form("input_form", clear_on_submit=False):
        text = st.text_area("", height=300)
        submitted = st.form_submit_button("➕ Extract & Add to Report")
        if submitted:
            if text.strip():
                texts = [text]
                if batch_mode:
                    for d in DELIMITERS:
                        if d in text:
                            texts = [t.strip() for t in text.split(d) if t.strip()]
                            break
                added = 0
                for t in texts:
                    row = extract_fields(t, qa_pipe)
                    st.session_state['report_data'].append(row)
                    added += 1
                st.success(f"Extracted and added {added} report(s)! 🎉")
            else:
                st.warning("Please paste a report before submitting.")

# Display & download section
if st.session_state.get('report_data'):
    st.markdown("<div class='section-subtitle'>📄 Today's Reports (Live View)</div>", unsafe_allow_html=True)
    df = pd.DataFrame(st.session_state['report_data'], columns=COLUMNS)
    df.index += 1
    with st.expander("View Dataframe", expanded=True):
        st.dataframe(df, use_container_width=True)

    xls = styled_excel(df)
    st.download_button(
        "Download Styled Excel Report",
        data=xls,
        file_name="IRBn_Consolidated_Report.xlsx"
    )

    if st.button("🔄 Reset Table for New Day"):
        st.session_state['report_data'] = []
        st.success("Table reset for a new report cycle.")
else:
    st.info("No reports added yet.")

st.markdown('<div class="footer-text">Powered by IRBn ReportStream v3 • © 2025</div>', unsafe_allow_html=True)
