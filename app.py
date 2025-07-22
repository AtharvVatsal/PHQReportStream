import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
import xlsxwriter

# ==============================
# OPTIONAL AI LAYER (DistilBERT)
# ==============================
try:
    from transformers import AutoTokenizer, AutoModelForQuestionAnswering, pipeline
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False

# -------------------------------------------------
# Streamlit config
# -------------------------------------------------
st.set_page_config(page_title="IRBn ReportStream v3 (AI+Regex)", layout="wide")
st.title("📋 IRBn ReportStream v3 — Styled Excel Report (Regex + DistilBERT)")
st.markdown("Paste one WhatsApp report at a time (or multiple separated by a delimiter). Click **Extract & Add** to include it in today's structured report.")

# -------------------------------------------------
# STRICT COLUMN ORDER (exact template wording)
# -------------------------------------------------
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
    "Issue for AP&T / PHQ"
]

COLUMN_WIDTHS = {
    "S. No": 6,
    "Name of IRBn/Bn": 25,
    "Reserves Deployed (District / Strength / Duration / In-Charge)": 70,
    "Districts where force deployed": 25,
    "Stay Arrangement / Bathrooms (Quality)": 30,
    "Messing Arrangements": 25,
    "CO's last Interaction with SP": 35,
    "Disciplinary Issues": 25,
    "Reserves Detained": 25,
    "Training": 25,
    "Welfare Initiative in Last 24 Hrs": 30,
    "Reserves Available in Bn": 25,
    "Issue for AP&T / PHQ": 25,
}

DELIMITERS = ["\n---\n", "\n#####\n", "\n===\n"]

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def is_numeric_zero(val: str) -> bool:
    try:
        return float(str(val).strip()) == 0.0
    except Exception:
        return False

def normalize(val: str) -> str:
    if val is None:
        return "Nil"
    v = str(val).strip()
    if v == "":
        return "Nil"
    if v.lower() in {"none", "nil", "no", "no issue", "n/a", "na", "not applicable", "-", "--", "nil."}:
        return "Nil"
    return v

def choose_best(regex_val: str, ai_val: str) -> str:
    r = normalize(regex_val)
    a = normalize(ai_val)
    return r if r != "Nil" else a

# -------------------------------------------------
# STRICT TEMPLATE PARSER (preferred path)
# -------------------------------------------------
SECTION_MAP = {
    "1": "Reserves Deployed (District / Strength / Duration / In-Charge)",
    "2": "Districts where force deployed",
    "3": "Stay Arrangement / Bathrooms (Quality)",
    "4": "Messing Arrangements",
    "5": "CO's last Interaction with SP",
    "6": "Disciplinary Issues",
    "7": "Reserves Detained",
    "8": "Training",
    "9": "Welfare Initiative in Last 24 Hrs",
    "10": "Reserves Available in Bn",
    "11": "Issue for AP&T / PHQ",
}

NAME_REGEX = re.compile(r"(?im)^\s*Name of IRBn/Bn\s*:\s*(.*)")
SECTION_REGEX = re.compile(
    r"(?ms)^\s*(?P<num>\d{1,2})\.\s*(?P<label>[^:\n]+):\s*(?P<body>.*?)(?=^\s*\d{1,2}\.\s|\Z)",
    re.MULTILINE | re.DOTALL
)

def parse_standard_template(text: str) -> dict:
    res = {c: "Nil" for c in COLUMNS}
    m = NAME_REGEX.search(text)
    if m:
        res["Name of IRBn/Bn"] = normalize(m.group(1))

    for sec in SECTION_REGEX.finditer(text):
        num = sec.group("num").strip()
        key = SECTION_MAP.get(num)
        if key:
            body = normalize(" ".join(sec.group("body").splitlines()).strip())
            res[key] = body

    for k, v in res.items():
        if is_numeric_zero(v):
            res[k] = "0"
    return res

# -------------------------------------------------
# Legacy regex fallback (when format is messy)
# -------------------------------------------------
def extract_section(text: str, start_labels, stop_labels=None) -> str:
    if stop_labels is None:
        stop_labels = []
    start_pattern = r"(?im)^(?:" + "|".join([re.escape(s) for s in start_labels]) + r")[\s:.-]*"
    m = re.search(start_pattern, text)
    if not m:
        return "Nil"
    remainder = text[m.end():]

    stops = [r"(?m)^\d+\.\s", r"(?m)^\*\s", r"(?m)^-\s"]
    if stop_labels:
        stops.append(r"(?im)^(?:" + "|".join([re.escape(s) for s in stop_labels]) + r")[\s:.-]*")

    stop_pos = None
    for sr in stops:
        sm = re.search(sr, remainder)
        if sm:
            pos = sm.start()
            if stop_pos is None or pos < stop_pos:
                stop_pos = pos
    block = remainder[:stop_pos] if stop_pos is not None else remainder
    return normalize(" ".join(block.splitlines()).strip())

def find_first(patterns, text, join_lines=False, fallback="Nil"):
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
        if m:
            val = m.group(1).strip()
            if join_lines:
                val = " ".join(val.splitlines()).strip()
            return normalize(val)
    return fallback

def extract_regex_fields(raw: str) -> dict:
    text = raw.replace("\r", "")
    name = find_first([
        r"Name of IRBn/Bn\s*:\s*(.*)",
        r"Bn\s*[:\-]\s*(\d+.*?(?:IRBn|HPAP).*?)(?:\n|$)",
        r"^\s*(\d+.*?(?:IRBn|HPAP).*?)(?:\n|$)",
        r"Bn\s+No\.?\s*and\s*Location\s*[:\-]\s*(.*?)(?:\n|$)"
    ], text)

    reserves = extract_section(text,
        start_labels=["1. Reserves", "1. Reserves Deployed", "Reserves Deployed"],
        stop_labels=["2.", "Stay arrangements", "Stay Arrangement", "Disciplinary", "Training"]
    )

    districts = re.findall(r"(?i)(?:dist(?:rict)?|distt)\s*[:\-]?\s*([A-Za-z &/()-]+)", text)
    ps_pp = re.findall(r"(?i)(?:PS|PP)\s*[:\-]?\s*([A-Za-z &/()-]+)", text)
    def split_clean(lst):
        out = []
        for item in lst:
            for p in re.split(r"[,/;]", item):
                p = p.strip()
                if p and p.lower() != 'nil' and len(p) > 1:
                    out.append(p)
        return out
    all_districts = sorted(set(split_clean(districts + ps_pp))) or ["Nil"]

    stay = extract_section(text,
        start_labels=["Stay arrangements", "Stay Arrangement", "Stay"],
        stop_labels=["Mess", "Messing", "Disciplinary", "Training"]
    )

    messing = extract_section(text,
        start_labels=["Messing arrangements", "Mess arrangements", "Mess"],
        stop_labels=["CO's last Interaction", "Interaction", "Disciplinary", "Training"]
    )

    interaction = find_first([
        r"(?:interaction|spoke|talked|visited).*?(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
    ], text, join_lines=True)

    disciplinary = extract_section(text,
        start_labels=["Disciplinary Issues", "Disciplinary issue", "Indiscipline"],
        stop_labels=["Reserves Detained", "Training", "Welfare", "Issue for AP&T"]
    )

    detained = find_first([
        r"Reserves\s*detained\s*[:\-]\s*(.*?)(?:\n|$)",
        r"detained.*?:\s*(.*?)(?:\n|$)",
        r"beyond duty.*?:\s*(.*?)(?:\n|$)"
    ], text)

    training = extract_section(text,
        start_labels=["Training", "Experience sharing"],
        stop_labels=["Welfare", "Reserves Available", "Issue for AP&T"]
    )

    welfare = extract_section(text,
        start_labels=["Welfare", "CSR", "Initiative"],
        stop_labels=["Reserves Available", "Issue for AP&T"]
    )

    reserves_available = find_first([
        r"Reserves.*?available.*?:\s*(.*?)(?:\n|$)",
        r"available.*?:\s*(.*?)(?:\n|$)"
    ], text)

    issue_phq = extract_section(text,
        start_labels=["Issue for AP&T / PHQ", "Issue for AP&T/PHQ", "Issue for AP&T", "Issues for PHQ", "Issue for PHQ"],
        stop_labels=[]
    )

    out = {
        "Name of IRBn/Bn": name,
        "Reserves Deployed (District / Strength / Duration / In-Charge)": reserves,
        "Districts where force deployed": ", ".join(all_districts),
        "Stay Arrangement / Bathrooms (Quality)": stay,
        "Messing Arrangements": messing,
        "CO's last Interaction with SP": interaction,
        "Disciplinary Issues": disciplinary,
        "Reserves Detained": detained,
        "Training": training,
        "Welfare Initiative in Last 24 Hrs": welfare,
        "Reserves Available in Bn": reserves_available,
        "Issue for AP&T / PHQ": issue_phq
    }
    for k, v in out.items():
        if is_numeric_zero(v):
            out[k] = "0"
    return out

# -------------------------------------------------
# AI Extraction (QA)
# -------------------------------------------------
AI_QUESTIONS = {
    "Name of IRBn/Bn": "What is the name of the battalion or IRBn?",
    "Reserves Deployed (District / Strength / Duration / In-Charge)": "Describe the reserves deployed including district, strength, duration and in-charge?",
    "Districts where force deployed": "List the districts where the force is deployed?",
    "Stay Arrangement / Bathrooms (Quality)": "Describe the stay arrangement and bathroom quality?",
    "Messing Arrangements": "Describe the messing or food arrangements?",
    "CO's last Interaction with SP": "When did the CO last interact with the SP? Give the date.",
    "Disciplinary Issues": "Mention any disciplinary issues?",
    "Reserves Detained": "Were any reserves detained or held beyond duty? State details.",
    "Training": "Was there any training or experience sharing? Describe.",
    "Welfare Initiative in Last 24 Hrs": "What welfare initiatives were taken in the last 24 hours?",
    "Reserves Available in Bn": "How many reserves are available in the battalion?",
    "Issue for AP&T / PHQ": "List issues for AP&T or PHQ."
}

@st.cache_resource(show_spinner=False)
def load_qa_pipeline():
    if not TRANSFORMERS_AVAILABLE:
        return None
    try:
        tok = AutoTokenizer.from_pretrained("distilbert-base-uncased-distilled-squad")
        mdl = AutoModelForQuestionAnswering.from_pretrained("distilbert-base-uncased-distilled-squad")
        return pipeline("question-answering", model=mdl, tokenizer=tok)
    except Exception:
        return None

def ai_extract_fields(raw_text: str, qa_pipe) -> dict:
    if qa_pipe is None:
        return {k: "Nil" for k in COLUMNS}
    out = {}
    for field, q in AI_QUESTIONS.items():
        try:
            res = qa_pipe({"question": q, "context": raw_text})
            ans = res.get("answer", "").strip()
        except Exception:
            ans = "Nil"
        out[field] = ans if ans else "Nil"
    return out

# -------------------------------------------------
# Excel writer
# -------------------------------------------------
def styled_excel(df: pd.DataFrame) -> BytesIO:
    output = BytesIO()
    today_str = datetime.today().strftime("%d/%m/%Y")
    title = f"Consolidated Daily Status Report of All IRBn/Bns as on {today_str}"

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        ws = workbook.add_worksheet("IRBn Report")
        writer.sheets["IRBn Report"] = ws

        title_fmt  = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'text_wrap': True,
                                          'align': 'center', 'valign': 'vcenter'})
        cell_fmt   = workbook.add_format({'border': 1, 'text_wrap': True, 'valign': 'top'})

        headers = ["S. No"] + list(df.columns)
        last_col = xlsxwriter.utility.xl_col_to_name(len(headers) - 1)

        ws.merge_range(f"A1:{last_col}1", title, title_fmt)
        ws.set_row(0, 28)
        ws.write_row("A3", headers, header_fmt)
        ws.set_row(2, 22)

        start_row = 3
        for r, row in enumerate(df.itertuples(index=False), start=start_row):
            ws.write_number(r, 0, r - 2, cell_fmt)
            for c, val in enumerate(row, start=1):
                ws.write(r, c, val, cell_fmt)

        for i, head in enumerate(headers):
            ws.set_column(i, i, COLUMN_WIDTHS.get(head, 25))

        ws.freeze_panes(start_row, 1)

    output.seek(0)
    return output

# -------------------------------------------------
# Session state
# -------------------------------------------------
if "report_data" not in st.session_state:
    st.session_state["report_data"] = []

# -------------------------------------------------
# Sidebar
# -------------------------------------------------
st.sidebar.header("⚙️ Options")
use_ai = st.sidebar.checkbox("Enable AI assist (DistilBERT)", value=True)
qa_pipe = load_qa_pipeline() if use_ai else None
if use_ai and qa_pipe is None:
    st.sidebar.warning("Could not load the QA model. Falling back to regex only.")

batch_mode = st.sidebar.checkbox("Batch paste (split by delimiter)", value=False)

# -------------------------------------------------
# Input form
# -------------------------------------------------
with st.form("input_form"):
    input_text = st.text_area("📨 Paste WhatsApp Report Text Below", height=350)
    submitted = st.form_submit_button("➕ Extract & Add to Report")

    if submitted:
        if input_text.strip():
            texts = [input_text]
            if batch_mode:
                for delim in DELIMITERS:
                    if delim in input_text:
                        texts = [t.strip() for t in input_text.split(delim) if t.strip()]
                        break

            added = 0
            for t in texts:
                row = parse_standard_template(t)
                # if template not followed (all Nil except name), fallback to regex + AI
                if all(row.get(col, "Nil") == "Nil" for col in COLUMNS[1:]):
                    regex_out = extract_regex_fields(t)
                    ai_out = ai_extract_fields(t, qa_pipe)
                    row = {col: choose_best(regex_out.get(col, "Nil"), ai_out.get(col, "Nil")) for col in COLUMNS}
                st.session_state["report_data"].append(row)
                added += 1

            st.success(f"✅ Extracted and added {added} report(s).")
        else:
            st.warning("⚠️ Please paste a report before submitting.")

# -------------------------------------------------
# Display & Download
# -------------------------------------------------
if st.session_state["report_data"]:
    st.markdown("### 📄 Today's Reports (Live View)")
    df = pd.DataFrame(st.session_state["report_data"], columns=COLUMNS)
    df.index = df.index + 1
    st.dataframe(df, use_container_width=True)

    xls_bytes = styled_excel(df)
    st.download_button("📅 Download Styled Excel Report", data=xls_bytes, file_name="IRBn_Consolidated_Report.xlsx")

    if st.button("🔁 Reset Table for New Day"):
        st.session_state["report_data"] = []
        st.success("✅ Table reset for a new report cycle.")
else:
    st.info("No reports added yet.")
