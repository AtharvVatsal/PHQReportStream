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

def extract_fields(text):
    def normalize(val):
        if not val or str(val).strip().lower() in ["none", "nil", "no", "no issue", "n/a", "-", ""]:
            return "Nil"
        return str(val).strip()

    def clean_date(val):
        try:
            val = re.sub(r"[^\d./-]", "", val)
            return datetime.strptime(val, "%d.%m.%Y").strftime("%d.%m.%Y")
        except:
            try:
                return datetime.strptime(val, "%d/%m/%Y").strftime("%d.%m.%Y")
            except:
                return "Nil"

    def find(patterns, join=False):
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE | re.DOTALL)
            if match:
                result = match.group(1).strip()
                return ' '.join(result.splitlines()).strip() if join else result
        return "Nil"

    # Extract Bn Name
    name = find([
        r"(?:(?:Bn|Battalion)\s*[:\-])\s*(\d+.*?(?:IRBn|HPAP).*?)\n",
        r"^\s*(\d+.*?(?:IRBn|HPAP).*?)\n"
    ])

    # Extract reserves deployed - clean structured form
    reserves_block = find([r"1\..*?Reserves.*?(?=\n\d+\.|\n*Stay arrangements|\Z)"], join=True)
    reserves_clean = "Nil"
    if reserves_block and "reserve" in reserves_block.lower():
        entries = re.findall(r"(?i)(\d+).*?Reserve.*?\((\d+).*?\).*?at (.*?)(?:upto|till|w\.e\.f\.).*?(?:till|upto|w\.e\.f\.)\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}).*?(?:In[-\s]?charge[:\-]?\s*|Incharge[:\-]?\s*)([^.;\n]+)", reserves_block)
        if entries:
            formatted = []
            for e in entries:
                count, strength, location, till, officer = e
                dt = clean_date(till)
                formatted.append(f"{count} Reserves ({strength}) at {location} upto {dt}, In-Charge: {officer}")
            reserves_clean = "; ".join(formatted)
        else:
            # fallback: combine all lines starting with *
            fallback_lines = re.findall(r"^\*.*$", reserves_block, re.MULTILINE)
            reserves_clean = ' '.join(line.strip("*- ") for line in fallback_lines) if fallback_lines else "Nil"

    # Extract district(s)
    districts = sorted(set(re.findall(r"(?i)(?:(?:district|distt)\.?|district of)\s*([A-Z][a-z]+)", text) +
                          re.findall(r"(?i)(?:PS|PP)\s+([A-Z][a-z]+)", text)))
    districts_joined = ", ".join(districts) if districts else "Nil"

    # Stay & Messing Standardization
    stay = find([r"stay.*?:\s*(.*)", r"bathroom.*?:\s*(.*)"], join=True)
    stay = f"Staying at {stay}" if "pl" in stay.lower() else normalize(stay)

    mess = find([r"messing.*?:\s*(.*)", r"food.*?arranged.*?([^\.\n]*)"], join=True)
    mess = f"Mess at {mess}" if "pl" in mess.lower() and "mess" not in mess.lower() else normalize(mess)

    # Interaction with SP
    interaction_text = find([
        r"(?:spoke.*?SP.*?)(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        r"(?:interaction.*?on|visited.*?on)\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})"
    ])
    co_interaction = clean_date(interaction_text)

    return {
        "Name of IRBn/Bn": normalize(name),
        "Reserves Deployed (Distt/Strength/Duration/In-Charge)": normalize(reserves_clean),
        "Districts where force Deployed": normalize(districts_joined),
        "Stay Arrangements/Bathroom (Quality)": normalize(stay),
        "Messing Arrangements": normalize(mess),
        "CO's Last Interaction with SP": normalize(co_interaction),
        "Disciplinary Issues": find([r"discipline.*?:\s*(.*)", r"indiscipline.*?:\s*(.*)"]),
        "Reserves Detained": find([r"detained.*?:\s*(.*)", r"beyond.*?without.*?:\s*(.*)"]),
        "Training": find([r"training.*?:\s*(.*)", r"experience.*?:\s*(.*)"], join=True),
        "Welfare Initiative in Last 24 Hrs": find([r"welfare.*?:\s*(.*)", r"CSR.*?:\s*(.*)", r"initiative.*?:\s*(.*)"]),
        "Reserves Available in Bn": find([r"available.*?:\s*(.*)"]),
        "Issues for AP&T/PHQ": find([r"(?:issue|requires).*?(?:PHQ|AP&T).*?:\s*(.*)"])
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
