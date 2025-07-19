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

def extract_fields_v3_5(text):
    def find(patterns, join_lines=False, fallback="Nil"):
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE | re.DOTALL)
            if match:
                val = match.group(1).strip()
                if join_lines:
                    val = ' '.join(val.splitlines()).strip()
                return normalize(val)
        return fallback

    # Custom multi-part extraction for reserves
    reserves_deployed = re.findall(r"(?i)(\d+\s*(?:officials|police personnel).*?)(?:\n|\))", text)
    incharges = re.findall(r"(?i)incharge.*?:?\s*([A-Z][a-z]+.*?)(?:\n|$)", text)
    durations = re.findall(r"(?:w\.e\.f\.|upto|till)\s*(\d{1,2}[./-]\d{1,2}[./-]?\d{2,4})", text)
    districts = re.findall(r"(?i)district(?:\s+of)?\s*([A-Z][a-z]+)", text)
    reserves_summary = ", ".join(reserves_deployed) + ", In-charge(s): " + ", ".join(incharges) + ", Duration(s): " + ", ".join(durations)
    districts_summary = ", ".join(sorted(set(districts))) if districts else "Nil"

    return {
        "Name of IRBn/Bn": find([
            r"Bn(?: No\.? and location)?\s*[:\-]\s*(.*)",
            r"^\s*(\d..*?IRBn.*?)\n",
            r"Bn\s*:\s*(.*?IRBn.*?)\n"
        ]),

        "Reserves Deployed (Distt/Strength/Duration/In-Charge)": normalize(reserves_summary),

        "Districts where force deployed": normalize(districts_summary),

        "Stay Arrangement/Bathrooms (Quality)": find([
            r"Stay arrangements.*?:\s*(.*?)(?:\n\s*\d|\n3)",
            r"Stay arrangements/bathrooms.*?:\s*(.*?)\n",
            r"bathrooms.*?:\s*(.*?)\n"
        ], join_lines=True),

        "Messing Arrangements": find([
            r"Messing arrangements.*?:\s*(.*?)\n",
            r"Mess arrangements.*?:\s*(.*?)\n"
        ], join_lines=True),

        "CO's last Interaction with SP": find([
            r"(?:Date on which|On)\s.*?(spoke.*?\d{1,2}(?:st|nd|rd|th)?\s*[A-Za-z]+|\d{1,2}[./-]\d{1,2}[./-]\d{4}).*?",
            r"personally.*?\s*(visited|spoke.*?)\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4})"
        ], join_lines=True),

        "Disciplinary Issues": find([
            r"disciplinary.*?:\s*(.*?)\n",
            r"indiscipline.*?:\s*(.*?)\n"
        ]),

        "Reserves Detained": find([
            r"detained.*?:\s*(.*?)\n",
            r"beyond duty.*?:\s*(.*?)\n"
        ]),

        "Training": find([
            r"Training.*?:\s*(.*?)(?:\n|$)",
            r"undergoing.*?:\s*(.*?)\n"
        ], join_lines=True),

        "Welfare Initiative in Last 24 Hrs": find([
            r"welfare.*?24\s*hrs.*?:\s*(.*?)\n",
            r"CSR.*?:\s*(.*?)\n"
        ], join_lines=True),

        "Reserves Available in Bn": find([
            r"Reserves.*?available.*?:\s*(.*?)\n",
            r"available.*?:\s*(.*?)\n"
        ]),

        "Issue for AP&T/PHQ": find([
            r"requires.*?(?:attention|AP&T|PHQ).*?:\s*(.*?)\n",
            r"Issue.*?PHQ.*?:\s*(.*?)\n",
            r"important issue.*?:\s*(.*?)\n"
        ])
    }

with st.form("input_form"):
    input_text = st.text_area("📨 Paste WhatsApp Report Text Below", height=350)
    submitted = st.form_submit_button("➕ Extract & Add to Report")

    if submitted:
        if input_text.strip():
            entry = extract_fields_v3_5(input_text)
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
            worksheet.set_column('D:D', 25)
            worksheet.set_column('E:E', 30)
            worksheet.set_column('F:F', 25)
            worksheet.set_column('G:G', 35)
            worksheet.set_column('H:M', 25)

        output.seek(0)
        return output

    st.download_button("📥 Download Styled Excel Report", data=styled_excel(df), file_name="IRBn_Consolidated_Report.xlsx")

    if st.button("🔁 Reset Table for New Day"):
        st.session_state['report_data'] = []
        st.success("✅ Table reset for a new report cycle.")
