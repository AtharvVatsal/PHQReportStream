# app_v3.py

import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
import xlsxwriter

st.set_page_config(page_title="IRBn ReportStream v3", layout="wide")
st.title("📋 IRBn ReportStream v3 — Styled Excel Report")
st.markdown("Paste one WhatsApp report at a time. Click **Extract & Add** to include it in today's structured report.")

# Initialize report data
if 'report_data' not in st.session_state:
    st.session_state['report_data'] = []

# Normalization helper
def normalize(value):
    if not value or value.lower().strip() in ["nil", "none", "no", "no issue", "no any complaint", "-", "n/a"]:
        return "Nil"
    return value.strip()

# Smart field extraction with multiple patterns
def extract_fields(text):
    def find(patterns, join_lines=False, fallback="Nil"):
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE | re.DOTALL)
            if match:
                val = match.group(1).strip()
                if join_lines:
                    val = ' '.join(val.splitlines()).strip()
                return normalize(val)
        return fallback

    # Normalize common NIL responses
    def normalize(val):
        if not val or val.strip().lower() in ["none", "nil", "no", "no issue", "n/a", "not applicable", "-", ""]:
            return "Nil"
        return val.strip()

    return {
        "Name of IRBn/Bn": find([
            r"Bn(?: No\.? and location)?\s*[:\-]\s*(.*)", 
            r"^\s*(\d..*?IRBn.*?)\n", 
            r"Bn\s*:\s*(.*?IRBn.*?)\n"
        ]),

        "Reserves Deployed (Distt/Strength/Duration/In-Charge)": find([
            r"(?:Detail[s]? of Bn Reserves(?: deployed)?\s*[:\-]?\s*)(.*?)(?:\n\s*\d+[\.\)]|2\.)", 
            r"(1\.\s*Detail.*?)(?:\n2\.|\n\n2)", 
            r"1\.\s*(.*?)\n\s*2[\.\)]"
        ], join_lines=True),

        "District Deployed": find([
            r"District[s]?\s*[:\-]?\s*(.*?)(?:\n|$)", 
            r"deployed at\s+(.*?)\n", 
            r"Deployed in\s+(.*?)\n", 
            r"location\s*[:\-]?\s*(.*)"
        ], join_lines=True),

        "Stay Arrangements / Bathrooms (Quality)": find([
            r"Stay arrangements.*?:\s*(.*?)(?:\n\s*\d|\n3)", 
            r"Stay arrangements/bathrooms.*?:\s*(.*)", 
            r"bathrooms.*?:\s*(.*?)\n"
        ], join_lines=True),

        "Messing Arrangements": find([
            r"Messing arrangements.*?:\s*(.*?)\n", 
            r"Mess arrangements.*?:\s*(.*?)\n"
        ], join_lines=True),

        "CO’s Last Interaction with SP": find([
            r"(?:CO.*?(spoke|interaction).*?)[:\-]?\s*(\d{1,2}[./\- ]\d{1,2}[./\- ]?\d{2,4})", 
            r"CO.*?on\s*(\d{1,2}[./\- ]\d{1,2}[./\- ]?\d{2,4})"
        ]),

        "Disciplinary Issues": find([
            r"disciplinary.*?:\s*(.*?)\n", 
            r"indiscipline.*?:\s*(.*?)\n"
        ]),

        "Reserves Detained": find([
            r"detained.*?:\s*(.*?)\n", 
            r"beyond duty.*?:\s*(.*?)\n"
        ]),

        "Training": find([
            r"Training.*?:\s*(.*?)\n", 
            r"undergoing.*?:\s*(.*?)\n"
        ]),

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
            r"Issue.*?PHQ.*?:\s*(.*?)\n"
        ])
    }


# Input form
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

# Show current records
if st.session_state['report_data']:
    st.markdown("### 📄 Today's Reports (Live View)")
    df = pd.DataFrame(st.session_state['report_data'])
    df.index = df.index + 1  # For 1-based S. No.

    st.dataframe(df, use_container_width=True)

    # Excel formatting
    def styled_excel(df):
        output = BytesIO()
        today_str = datetime.today().strftime("%d/%m/%Y")
        title = f"Consolidated Daily Status Report of All IRBn/Bns as on {today_str}"

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet("IRBn Report")
            writer.sheets["IRBn Report"] = worksheet

            # Formats
            title_format = workbook.add_format({'bold': True, 'font_size': 14})
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1})
            cell_format = workbook.add_format({'border': 1, 'text_wrap': True, 'valign': 'top'})

            # Write title
            worksheet.merge_range('A1:M1', title, title_format)

            # Write headers
            headers = ["S. No"] + list(df.columns)
            worksheet.write_row('A3', headers, header_format)

            # Write data
            for row_num, row_data in enumerate(df.itertuples(), start=3):
                worksheet.write(row_num, 0, row_num - 2, cell_format)  # S. No
                for col_num, val in enumerate(row_data[1:], start=1):
                    worksheet.write(row_num, col_num, val, cell_format)

            # Set column widths
            worksheet.set_column('A:A', 6)
            worksheet.set_column('B:B', 25)
            worksheet.set_column('C:C', 40)
            worksheet.set_column('D:D', 15)
            worksheet.set_column('E:E', 30)
            worksheet.set_column('F:F', 25)
            worksheet.set_column('G:G', 22)
            worksheet.set_column('H:M', 20)

        output.seek(0)
        return output

    st.download_button("📥 Download Styled Excel Report", data=styled_excel(df), file_name="IRBn_Consolidated_Report.xlsx")

    if st.button("🔁 Reset Table for New Day"):
        st.session_state['report_data'] = []
        st.success("✅ Table reset for a new report cycle.")
