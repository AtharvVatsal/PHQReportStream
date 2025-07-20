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
