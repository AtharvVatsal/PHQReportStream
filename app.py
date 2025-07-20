import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
import xlsxwriter

st.set_page_config(page_title="IRBn ReportStream v4", layout="wide")
st.title("📋 IRBn ReportStream v4 — Styled Excel Report")
st.markdown("Paste one WhatsApp report at a time. Click **Extract & Add** to include it in today's structured report.")

if 'report_data' not in st.session_state:
    st.session_state['report_data'] = []

def normalize(val):
    if not val or val.strip().lower() in ["none", "nil", "no", "no issue", "n/a", "not applicable", "-", ""]:
        return "Nil"
    return re.sub(r"\s+", " ", val.strip())

def extract_fields_fixed(text):
    def find(patterns, join_lines=False, fallback="Nil"):
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE | re.DOTALL)
            if match:
                val = match.group(1).strip()
                if join_lines:
                    val = ' '.join(val.splitlines()).strip()
                return normalize(val)
        return fallback

    name_of_battalion = find([
        r"Bn\s*[:\-]\s*(\d+.*?(?:IRBn|HPAP).*?)\n",
        r"^\s*(\d+.*?(?:IRBn|HPAP).*?)\n",
        r"Bn\s+No\.? and Location\s*[:\-]\s*(.*?)\n"
    ])

    reserves_clean = find([
        r"1\.\s*Details?.*?Reserves?.*?(?=\d\.\s|\Z)"
    ], join_lines=True)

    districts = ", ".join(sorted(set(re.findall(r"(?i)(?:(?:district|distt)\.?|district of)\s*([A-Z][a-z]+)", text))))
    if not districts:
        districts = find([r"Deployed at\s*([A-Z][a-z,&\s]+)"])

    stay = find([
        r"Stay arrangements.*?:\s*(.*?)(?:\n|$)",
        r"stay.*?(?:at|in)\s*(.*?)(?:\.|\n)"
    ], join_lines=True)

    bathrooms = find([
        r"bathrooms.*?:\s*(.*?)(?:\n|$)"
    ], join_lines=True)

    messing = find([
        r"Messing arrangements.*?:\s*(.*?)(?:\n|$)",
        r"mess.*?(?:at|in)\s*(.*?)(?:\.|\n)"
    ], join_lines=True)

    interaction = find([
        r"(?:spoke.*?SP.*?|visited.*?)\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        r"interaction.*?on\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        r"(?:spoke|talked).*?SP.*?(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})"
    ])

    training = find([r"training.*?:\s*(.*?)\n", r"experience.*?programme.*?\n(.*?)\n"], join_lines=True)
    welfare = find([r"welfare.*?:\s*(.*?)\n", r"initiative.*?:\s*(.*?)\n"], join_lines=True)
    reserves_available = find([r"Reserves.*?available.*?:\s*(.*?)\n", r"available.*?:\s*(.*?)\n"])
    issues_apt = find([r"issue.*?PHQ.*?:\s*(.*?)\n", r"requires.*?attention.*?:\s*(.*?)\n"])
    disciplinary = find([r"disciplinary issue.*?:\s*(.*?)\n", r"indiscipline.*?:\s*(.*?)\n"], join_lines=True)
    detained = find([r"detained.*?:\s*(.*?)\n", r"beyond duty.*?:\s*(.*?)\n", r"Reserves detained.*?(\d+.*?)\n"])

    return {
        "Name of IRBn/Bn": name_of_battalion,
        "Reserves Deployed (Distt/Strength/Duration/In-Charge)": reserves_clean,
        "Districts where force Deployed": normalize(districts),
        "Stay Arrangements/Bathroom (Quality)": f"{stay} - {bathrooms}" if bathrooms != "Nil" else stay,
        "Messing Arrangements": messing,
        "CO's Last Interaction with SP": interaction,
        "Disciplinary Issues": disciplinary,
        "Reserves Detained": detained,
        "Training": training,
        "Welfare Initiative in Last 24 Hrs": welfare,
        "Reserves Available In Bn": reserves_available,
        "Issues for AP&T/PHQ": issues_apt
    }

with st.form("input_form"):
    input_text = st.text_area("📨 Paste WhatsApp Report Text Below", height=350)
    submitted = st.form_submit_button("➕ Extract & Add to Report")

    if submitted:
        if input_text.strip():
            entry = extract_fields_fixed(input_text)
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
            worksheet.set_column('C:C', 80)
            worksheet.set_column('D:D', 30)
            worksheet.set_column('E:E', 30)
            worksheet.set_column('F:F', 25)
            worksheet.set_column('G:M', 30)

        output.seek(0)
        return output

    st.download_button("📅 Download Styled Excel Report", data=styled_excel(df), file_name="IRBn_Consolidated_Report.xlsx")

    if st.button("🔁 Reset Table for New Day"):
        st.session_state['report_data'] = []
        st.success("✅ Table reset for a new report cycle.")
