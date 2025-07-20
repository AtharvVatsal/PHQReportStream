import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
import xlsxwriter

st.set_page_config(page_title="IRBn ReportStream v3", layout="wide")
st.title("📋 IRBn ReportStream v3 — Styled Excel Report")
st.markdown("Paste one WhatsApp report at a time. Click **Extract & Add** to include it in today's structured report.")

if 'report_data' not in st.session_state:
    st.session_state['report_data'] = []

def normalize(val):
    if not val or val.strip().lower() in ["none", "nil", "no", "no issue", "n/a", "not applicable", "-", ""]:
        return "Nil"
    return val.strip()

def clean_line(line):
    return re.sub(r"^[-\*\d\.\)\s]+", "", line).strip()

def extract_fields(text):
    def block(pattern):
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""

    def line(pattern):
        m = re.search(pattern, text, re.IGNORECASE)
        return normalize(m.group(1)) if m else "Nil"

    def all_matches(pattern):
        return re.findall(pattern, text, re.IGNORECASE)

    name = line(r"Bn\s*[:\-]\s*(\d+.*?(?:IRBn|HPAP).*?)\n")
    if name == "Nil":
        name = line(r"^(\d+.*?(?:IRBn|HPAP).*?)\n")
    if name == "Nil":
        name = line(r"Bn\s+No\.? and Location\s*[:\-]\s*(.*?)\n")

    reserves_raw = block(r"1\..*?reserves.*?(?=\n\d+\.|\Z|Stay arrangement)".replace(" ", "\\s"))
    reserves_clean = "; ".join([clean_line(l) for l in reserves_raw.splitlines() if any(w in l.lower() for w in ["reserve", "official"])]) or "Nil"

    districts = set(all_matches(r"(?:(?:district|distt)\.?|district of)\s*([A-Z][a-z]+)"))
    districts |= set(all_matches(r"(?:PS|PP)\s+([A-Z][a-z]+)"))
    districts_joined = ", ".join(sorted(districts)) if districts else "Nil"

    stay = block(r"stay arrangements.*?:\s*(.*?)\n") or block(r"bathroom.*?:\s*(.*?)\n")
    stay = clean_line(stay)
    if stay and not stay.lower().startswith("mess") and "good" not in stay.lower():
        stay = f"{stay} - Good"
    stay = normalize(stay)

    mess = block(r"messing arrangements.*?:\s*(.*?)\n")
    mess = normalize(mess)
    if mess.lower().startswith("pl"):
        mess = f"Mess at {mess}"

    interaction = line(r"(?:spoke|interaction|talked).*?(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})")
    try:
        if interaction != "Nil":
            interaction = datetime.strptime(interaction.replace("-", "/").replace(".", "/"), "%d/%m/%Y").strftime("%d.%m.%Y")
    except:
        interaction = "Nil"

    disciplinary = line(r"disciplinary.*?:\s*(.*?)\n")
    if disciplinary == "Nil":
        disciplinary = line(r"indiscipline.*?:\s*(.*?)\n")

    detained = line(r"detained.*?:\s*(.*?)\n")
    if detained == "Nil":
        detained = line(r"beyond.*?without.*?:\s*(.*?)\n")

    training = line(r"training.*?:\s*(.*?)\n")

    welfare = line(r"welfare.*?:\s*(.*?)\n")
    if welfare == "Nil":
        welfare = line(r"CSR.*?:\s*(.*?)\n")
    if welfare == "Nil":
        welfare = line(r"initiative.*?:\s*(.*?)\n")

    reserves_avail = line(r"available.*?:\s*(.*?)\n")

    issue_ap = line(r"issue.*?(PHQ|AP&T).*?:\s*(.*?)\n")
    if issue_ap == "Nil":
        issue_ap = line(r"requires.*?attention.*?:\s*(.*?)\n")

    return {
        "Name of IRBn/Bn": name,
        "Reserves Deployed (Distt/Strength/Duration/In-Charge)": normalize(reserves_clean),
        "Districts where force Deployed": normalize(districts_joined),
        "Stay Arrangements/Bathroom (Quality)": normalize(stay),
        "Messing Arrangements": mess,
        "CO's Last Interaction with SP": interaction,
        "Disciplinary Issues": disciplinary,
        "Reserves Detained": detained,
        "Training": training,
        "Welfare Initiative in Last 24 Hrs": welfare,
        "Reserves Available in Bn": reserves_avail,
        "Issues for AP&T/PHQ": issue_ap,
    }

with st.form("input_form"):
    input_text = st.text_area("📨 Paste WhatsApp Report Text Below", height=350)
    submitted = st.form_submit_button("➕ Extract & Add to Report")

    if submitted:
        if input_text.strip():
            entry = extract_fields(input_text)
            st.session_state['report_data'].append(entry)
            st.success("✅ Report extracted and added.")
        else:
            st.warning("⚠️ Please paste a report before submitting.")

if st.session_state['report_data']:
    st.markdown("### 📄 Today's Reports (Live View)")
    df = pd.DataFrame(st.session_state['report_data'])
    df.index = df.index + 1

    st.dataframe(df, use_container_width=True)

    def styled_excel(df):
        output = BytesIO()
        today_str = datetime.today().strftime("%d/%m/%Y")
        title = f"Consolidated Daily Status Report of All IRBn/Bns as on {today_str}"

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet("IRBn Report")
            writer.sheets["IRBn Report"] = worksheet

            title_format = workbook.add_format({'bold': True, 'font_size': 14})
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1})
            cell_format = workbook.add_format({'border': 1, 'text_wrap': True, 'valign': 'top'})

            worksheet.merge_range('A1:M1', title, title_format)

            headers = ["S. No"] + list(df.columns)
            worksheet.write_row('A3', headers, header_format)

            for row_num, row_data in enumerate(df.itertuples(), start=3):
                worksheet.write(row_num, 0, row_num - 2, cell_format)
                for col_num, val in enumerate(row_data[1:], start=1):
                    worksheet.write(row_num, col_num, val, cell_format)

            worksheet.set_column('A:A', 6)
            worksheet.set_column('B:B', 25)
            worksheet.set_column('C:C', 70)
            worksheet.set_column('D:D', 30)
            worksheet.set_column('E:E', 30)
            worksheet.set_column('F:F', 25)
            worksheet.set_column('G:G', 35)
            worksheet.set_column('H:M', 25)

        output.seek(0)
        return output

    st.download_button("📅 Download Styled Excel Report", data=styled_excel(df), file_name="IRBn_Consolidated_Report.xlsx")

    if st.button("🔁 Reset Table for New Day"):
        st.session_state['report_data'] = []
        st.success("✅ Table reset for a new report cycle.")
