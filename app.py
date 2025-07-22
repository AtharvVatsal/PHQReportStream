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
st.set_page_config(page_title="IRBn ReportStream v3 FINAL", layout="wide")
st.title("📋 IRBn ReportStream v3 — FINAL (Strict Template + Smart Fallback + AI)")
st.caption("Build date: 22-Jul-2025")

# -------------------------------------------------
# Canonical column order (exact wording)
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

# If multiple reports are pasted together, split on these
DELIMITERS = ["\n---\n", "\n#####\n", "\n===\n"]

# -------------------------------------------------
# Helpers
# -------------------------------------------------

def is_zero(val):
    try:
        return float(str(val).strip()) == 0.0
    except Exception:
        return False


def normalize(val):
    if val is None:
        return "Nil"
    v = str(val).strip()
    if not v:
        return "Nil"
    if v.lower() in {"nil", "none", "no", "no issue", "n/a", "na", "not applicable", "--", "-"}:
        return "Nil"
    return v


def choose_best(regex_val, ai_val):
    r = normalize(regex_val)
    a = normalize(ai_val)
    return r if r != "Nil" else a

# -------------------------------------------------
# 1) STRICT parser (messages that follow the exact numbered template)
# -------------------------------------------------
SECTION_MAP_STRICT = {
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

NAME_PATTERNS = [
    r"^\s*Name of IRBn/Bn\s*:\s*<?([^>\n]+)>?",
    r"^\s*Name of Bn\s*:\s*<?([^>\n]+)>?",
    r"^\s*Bn\s*No\.?\s*and\s*Location\s*:\s*(.*)",
]

STRICT_SECTION_RE = re.compile(
    r"(?ms)^\s*(?P<num>\d{1,2})\.\s*(?P<label>[^:\n]+):\s*(?P<body>.*?)(?=^\s*\d{1,2}\.\s|\Z)",
    re.MULTILINE
)


def parse_strict(text: str) -> dict:
    out = {c: "Nil" for c in COLUMNS}
    # Name
    for pat in NAME_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            out["Name of IRBn/Bn"] = normalize(m.group(1))
            break
    # Sections
    for m in STRICT_SECTION_RE.finditer(text):
        num = m.group("num").strip()
        body = normalize(" ".join(m.group("body").splitlines()))
        key = SECTION_MAP_STRICT.get(num)
        if key:
            out[key] = body
    for k, v in out.items():
        if is_zero(v):
            out[k] = "0"
    return out

# -------------------------------------------------
# 2) SMART fuzzy parser (when numbers/labels are shuffled)
# -------------------------------------------------
# Keyword lists for fuzzy label → field mapping
FIELD_KEYWORDS = {
    "Reserves Deployed (District / Strength / Duration / In-Charge)": ["reserve", "deployed", "strength", "duration", "in-charge", "detail of bn reserves"],
    "Districts where force deployed": ["districts where force deployed", "district-wise", "distt", "district"],
    "Stay Arrangement / Bathrooms (Quality)": ["stay", "bathroom", "bathrooms", "quality"],
    "Messing Arrangements": ["messing", "mess facility", "mess"],
    "CO's last Interaction with SP": ["last spoke", "interaction", "spoke to", "personally last", "date on which co"],
    "Disciplinary Issues": ["disciplinary", "indiscipline"],
    "Reserves Detained": ["detained", "beyond duty"],
    "Training": ["training", "course", "undergoing"],
    "Welfare Initiative in Last 24 Hrs": ["welfare", "csr", "initiative"],
    "Reserves Available in Bn": ["available in the bn", "reserves (with strength) available", "reserves available"],
    "Issue for AP&T / PHQ": ["issue", "ap&t", "phq"],
}

# A generic numbered/bulleted section regex
GENERIC_SECTION_RE = re.compile(
    r"(?ms)^\s*(\d{1,2})\.\s*([^:\n]+):\s*(.*?)(?=^\s*\d{1,2}\.\s|\Z)",
    re.MULTILINE
)


def fuzzy_label_to_field(label: str) -> str | None:
    lab = label.lower()
    best_field = None
    best_hits = 0
    for field, keys in FIELD_KEYWORDS.items():
        hits = sum(1 for k in keys if k in lab)
        if hits > best_hits:
            best_hits = hits
            best_field = field
    # Require at least 1 keyword match
    return best_field if best_hits else None


def derive_districts(full_text: str) -> str:
    # Try explicit section first
    m = re.search(r"(?im)^\s*2\.\s*Districts where force deployed\s*:\s*(.*)$", full_text)
    if m:
        return normalize(m.group(1))
    # Else: scrape from anywhere: "Distt/District X" OR lines like "Shimla:" at start
    dists = set()
    for d in re.findall(r"(?:Distt\.?|District)\s*([A-Za-z][A-Za-z &/-]+)", full_text, flags=re.IGNORECASE):
        dists.add(d.strip())
    for d in re.findall(r"^\s*([A-Z][A-Za-z &/-]+)\s*:\s*\d", full_text, flags=re.MULTILINE):
        # common pattern "Shimla: 25..."
        dists.add(d.strip())
    return ", ".join(sorted(dists)) if dists else "Nil"


def parse_smart(text: str) -> dict:
    out = {c: "Nil" for c in COLUMNS}
    # Name
    for pat in NAME_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            out["Name of IRBn/Bn"] = normalize(m.group(1))
            break
    # Numbered sections, fuzzy match labels
    for num, label, body in GENERIC_SECTION_RE.findall(text):
        field = fuzzy_label_to_field(label)
        if field:
            val = normalize(" ".join(body.splitlines()))
            out[field] = val
    # If districts still Nil, derive heuristically
    if out["Districts where force deployed"] == "Nil":
        out["Districts where force deployed"] = derive_districts(text)
    for k, v in out.items():
        if is_zero(v):
            out[k] = "0"
    return out

# -------------------------------------------------
# 3) Legacy regex fallback from old script (for safety)
# -------------------------------------------------

# Reuse pieces of the old code for ultimate fallback
OLD_SECTION_STARTS = {
    "reserves": ["1. Reserves", "1. Reserves Deployed", "1. Detail of Bn Reserves", "1. Details of Bn Reserves", "1. Details of Bn Reserves Deployed"],
    "stay": ["3. Stay", "2. Stay", "Stay arrangements", "Stay Arrangement"],
    "mess": ["4. Messing", "3. Messing", "Messing arrangements", "Mess arrangements"],
    "disciplinary": ["6. Disciplinary", "5. Any disciplinary"],
    "detained": ["7. Reserves Detained", "6. Reserves detained"],
    "training": ["8. Training", "7. Training"],
    "welfare": ["9. Welfare", "8. Any Initiative of welfare"],
    "issue": ["11. Issue", "10. Any other issue"],
}


def extract_section(text: str, start_labels, stop_labels=None) -> str:
    if stop_labels is None:
        stop_labels = []
    start_pattern = r"(?im)^(?:" + "|".join([re.escape(s) for s in start_labels]) + r")[\s:.-]*"
    m = re.search(start_pattern, text)
    if not m:
        return "Nil"
    rem = text[m.end():]
    # generic stops
    stops = [r"(?m)^\d+\.\s", r"(?m)^\*\s", r"(?m)^-\s"]
    if stop_labels:
        stops.append(r"(?im)^(?:" + "|".join([re.escape(s) for s in stop_labels]) + r")[\s:.-]*")
    stop_pos = None
    for sr in stops:
        mm = re.search(sr, rem)
        if mm:
            pos = mm.start()
            if stop_pos is None or pos < stop_pos:
                stop_pos = pos
    block = rem[:stop_pos] if stop_pos is not None else rem
    return normalize(" ".join(block.splitlines()))


def extract_legacy(text: str) -> dict:
    name = normalize(next((re.search(p, text, flags=re.I|re.M).group(1) for p in NAME_PATTERNS if re.search(p, text, flags=re.I|re.M)), "Nil"))
    reserves = extract_section(text, OLD_SECTION_STARTS["reserves"], ["2.", "Stay", "Disciplinary", "Training"])
    districts = derive_districts(text)
    stay = extract_section(text, OLD_SECTION_STARTS["stay"], ["Mess", "Disciplinary", "Training"])
    mess = extract_section(text, OLD_SECTION_STARTS["mess"], ["Interaction", "Disciplinary", "Training"])
    interaction = normalize(next((m.group(1) for m in [re.search(r"(?:interaction|spoke).*?(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})", text, flags=re.I|re.S)] if m), "Nil"))
    disciplinary = extract_section(text, OLD_SECTION_STARTS["disciplinary"], ["Reserves Detained", "Training", "Welfare", "Issue"])
    detained = extract_section(text, OLD_SECTION_STARTS["detained"], ["Training", "Welfare", "Issue"])
    training = extract_section(text, OLD_SECTION_STARTS["training"], ["Welfare", "Issue"])
    welfare = extract_section(text, OLD_SECTION_STARTS["welfare"], ["Issue"])
    available = normalize(next((m.group(1) for m in [re.search(r"10\..*?:\s*(.*)", text, flags=re.I|re.S)] if m), "Nil"))
    issue = extract_section(text, OLD_SECTION_STARTS["issue"], [])
    out = {
        COLUMNS[0]: name,
        COLUMNS[1]: reserves,
        COLUMNS[2]: districts,
        COLUMNS[3]: stay,
        COLUMNS[4]: mess,
        COLUMNS[5]: interaction,
        COLUMNS[6]: disciplinary,
        COLUMNS[7]: detained,
        COLUMNS[8]: training,
        COLUMNS[9]: welfare,
        COLUMNS[10]: available,
        COLUMNS[11]: issue,
    }
    for k, v in out.items():
        if is_zero(v):
            out[k] = "0"
    return out

# -------------------------------------------------
# 4) AI QA layer (always-on but silent if model missing)
# -------------------------------------------------
AI_QUESTIONS = {
    COLUMNS[0]: "What is the name of the battalion or IRBn?",
    COLUMNS[1]: "Describe the reserves deployed including district, strength, duration and in-charge?",
    COLUMNS[2]: "List the districts where the force is deployed?",
    COLUMNS[3]: "Describe the stay arrangement and bathroom quality?",
    COLUMNS[4]: "Describe the messing or food arrangements?",
    COLUMNS[5]: "When did the CO last interact with the SP? Give the date.",
    COLUMNS[6]: "Mention any disciplinary issues?",
    COLUMNS[7]: "Were any reserves detained or held beyond duty? State details.",
    COLUMNS[8]: "Was there any training or experience sharing? Describe.",
    COLUMNS[9]: "What welfare initiatives were taken in the last 24 hours?",
    COLUMNS[10]: "How many reserves are available in the battalion?",
    COLUMNS[11]: "List issues for AP&T or PHQ.",
}

@st.cache_resource(show_spinner=False)
def load_qa():
    if not TRANSFORMERS_AVAILABLE:
        return None
    try:
        tok = AutoTokenizer.from_pretrained("distilbert-base-uncased-distilled-squad")
        mdl = AutoModelForQuestionAnswering.from_pretrained("distilbert-base-uncased-distilled-squad")
        return pipeline("question-answering", model=mdl, tokenizer=tok)
    except Exception:
        return None


def ai_extract(text: str, qa_pipe):
    if qa_pipe is None:
        return {k: "Nil" for k in COLUMNS}
    out = {}
    for field, q in AI_QUESTIONS.items():
        try:
            r = qa_pipe({"question": q, "context": text})
            ans = r.get("answer", "").strip()
        except Exception:
            ans = "Nil"
        out[field] = normalize(ans) if ans else "Nil"
    return out

# -------------------------------------------------
# 5) Master extractor
# -------------------------------------------------

def extract_fields(text: str, qa_pipe=None) -> dict:
    # 1. Strict
    strict = parse_strict(text)
    # Count how many fields filled (excluding name)
    filled = sum(1 for k, v in strict.items() if k != COLUMNS[0] and v != "Nil")
    if filled >= 6:  # good enough
        base = strict
    else:
        # 2. Smart fuzzy
        smart = parse_smart(text)
        filled2 = sum(1 for k, v in smart.items() if k != COLUMNS[0] and v != "Nil")
        if filled2 >= filled:
            base = smart
        else:
            # 3. Legacy
            base = extract_legacy(text)

    # AI overlay
    ai_out = ai_extract(text, qa_pipe)
    final = {col: choose_best(base.get(col, "Nil"), ai_out.get(col, "Nil")) for col in COLUMNS}
    return final

# -------------------------------------------------
# Excel writer
# -------------------------------------------------

def styled_excel(df: pd.DataFrame) -> BytesIO:
    output = BytesIO()
    today_str = datetime.today().strftime("%d/%m/%Y")
    title = f"Consolidated Daily Status Report of All IRBn/Bns as on {today_str}"

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        wb = writer.book
        ws = wb.add_worksheet("IRBn Report")
        writer.sheets["IRBn Report"] = ws

        title_fmt  = wb.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        header_fmt = wb.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'text_wrap': True,
                                    'align': 'center', 'valign': 'vcenter'})
        cell_fmt   = wb.add_format({'border': 1, 'text_wrap': True, 'valign': 'top'})

        headers = ["S. No"] + list(df.columns)
        last_col = xlsxwriter.utility.xl_col_to_name(len(headers) - 1)

        ws.merge_range(f"A1:{last_col}1", title, title_fmt)
        ws.set_row(0, 28)
        ws.write_row('A3', headers, header_fmt)
        ws.set_row(2, 22)

        start_row = 3
        for ridx, row in enumerate(df.itertuples(index=False), start=start_row):
            ws.write_number(ridx, 0, ridx - 2, cell_fmt)
            for cidx, val in enumerate(row, start=1):
                ws.write(ridx, cidx, val, cell_fmt)

        for col_idx, head in enumerate(headers):
            ws.set_column(col_idx, col_idx, COLUMN_WIDTHS.get(head, 25))

        ws.freeze_panes(start_row, 1)

    output.seek(0)
    return output

# -------------------------------------------------
# Session state
# -------------------------------------------------
if 'report_data' not in st.session_state:
    st.session_state['report_data'] = []

# -------------------------------------------------
# Sidebar options
# -------------------------------------------------
st.sidebar.header("⚙️ Options")
use_ai = st.sidebar.checkbox("Enable AI assist (DistilBERT)", value=True,
                             help="Runs a QA model to verify/fill fields. Falls back silently if model not available.")
qa_pipe = load_qa() if use_ai else None
if use_ai and qa_pipe is None:
    st.sidebar.warning("QA model not loaded; continuing with regex/parsers only.")

batch_mode = st.sidebar.checkbox("Batch paste (split by delimiter)", value=False,
                                 help="Split input by --- or ##### or ===")

# -------------------------------------------------
# Input form
# -------------------------------------------------
with st.form("input_form"):
    text = st.text_area("📨 Paste WhatsApp Report Text Below", height=350)
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
            st.success(f"✅ Extracted and added {added} report(s).")
        else:
            st.warning("⚠️ Please paste a report before submitting.")

# -------------------------------------------------
# Display & download
# -------------------------------------------------
if st.session_state['report_data']:
    st.markdown("### 📄 Today's Reports (Live View)")
    df = pd.DataFrame(st.session_state['report_data'], columns=COLUMNS)
    df.index = df.index + 1
    st.dataframe(df, use_container_width=True)

    xls = styled_excel(df)
    st.download_button("📅 Download Styled Excel Report", data=xls, file_name="IRBn_Consolidated_Report.xlsx")

    if st.button("🔁 Reset Table for New Day"):
        st.session_state['report_data'] = []
        st.success("✅ Table reset for a new report cycle.")
else:
    st.info("No reports added yet.")
