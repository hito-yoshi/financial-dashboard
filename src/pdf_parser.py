import pdfplumber
import pandas as pd
import os
import re

# New parsing trace for UI visibility
PARSING_TRACE = []

# Translation dictionary matching generate_dummy.py keys to Japanese strict names
# Based on User Image
TRANSLATION_MAP = {
    "Sales": "売上高",
    "Advances Received": "前受金",
    "EC Sales": "EC売上高",
    
    "Material Cost": "素材費",
    "Purchases": "仕入高",
    "EC Purchases": "EC仕入高",
    "EC Materials": "EC資材",
    "EC Fees": "EC手数料",
    "EC Ads": "EC広告費",
    "EC Shipping": "EC送料",
    "EC Outsourcing": "EC内職",
    "EC Other": "ECその他",
    
    "Outsource Coding": "外注コーディング費",
    "Outsource Design": "外注デザイン費",
    "Printing": "印刷費",
    "Other Outsourcing": "その他外注費",
    
    "Director Comp": "役員報酬",
    "Salaries": "給与手当",
    "Bonuses": "賞与",
    "Legal Welfare": "法定福利費",
    "Welfare": "福利厚生費",
    "Travel": "旅費交通費",
    "Comm": "通信費",
    "Entertainment": "交際費",
    "Meetings": "会議費",
    "Rent": "地代家賃",
    "Insurance": "保険料",
    "Utilities": "水道光熱費",
    "Fuel": "燃料費",
    "Supplies": "消耗品費",
    "Taxes Public": "租税公課",
    "Freight": "運賃",
    "Consumption Tax": "消費税",
    "Office Supplies": "事務用品費",
    "Ad Expenses": "広告宣伝費",
    "Payment Fees": "支払手数料",
    "Dues": "諸会費",
    "Books": "新聞図書費",
    "Misc": "雑費"
}

def parse_pdf(filepath):
    """
    Parses a single PDF file and returns a structured dictionary or DataFrame.
    Supports both "Dummy" format (4 columns) and "Real Trial Balance" format (~8 columns).
    """
    data = []
    filename = os.path.basename(filepath)
    # --- Definitive Robust Filename Parsing ---
    # 1. Search for YYYYMM (6 digits starting with 20)
    yyyymm_match = re.search(r'(20\d{2})(0[1-9]|1[0-2])', filename)
    if yyyymm_match:
        year = int(yyyymm_match.group(1))
        month = int(yyyymm_match.group(2))
    else:
        # 2. Search for Year (4 digits starting with 20)
        year_match = re.search(r'(20\d{2})', filename)
        year = int(year_match.group(1)) if year_match else 2025
        
        # 3. Search for Month in the digits that aren't the year
        # Get all digit groups
        all_digit_groups = re.findall(r'\d+', filename)
        month = 1
        for d in all_digit_groups:
            # If it's the year we found, skip it
            if d == str(year):
                continue
            # If it's a valid month, use it
            if 1 <= int(d) <= 12:
                month = int(d)
                break
    
    PARSING_TRACE.append(f"Parsing: {filename} -> Result: {year}-{month}")
    print(f"[DEBUG_PARSER] Filename: {filename} -> Parsed: {year}-{month}")

    
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            
            # --- STRATEGY 1: TABLE EXTRACTION (Real PDF) ---
            if tables:
                for table in tables:
                    for row in table:
                        # Clean None
                        row = [str(x).strip() if x is not None else "" for x in row]
                        
                        # Skip empty rows or headers
                        if not any(row) or "Account Item" in row or "勘 定 科 目" in row:
                            continue
                            
                        # REAL FORMAT (approx 8 cols)
                        # Debug showed: [None, None, Name, Prev, Debit, Credit, Curr, Ratio]
                        if len(row) >= 6:
                            # Try to find name in first few columns
                            name = ""
                            # Priority: Row[2] (Primary), then others for totals
                            if row[2] and str(row[2]).strip():
                                name = str(row[2])
                            else:
                                # Join all non-numeric cells to find labels like 【 流動資産 】
                                labels = []
                                for cell in row[:3]: # Only search first few cols for labels
                                    # Check if cell is effectively a number (including negative signs like )
                                    if cell:
                                        s_cell = str(cell).replace(",","").replace(".","").replace("-","").replace("","").replace("△","").replace("▲","")
                                        if not s_cell.isdigit():
                                            labels.append(str(cell))
                                name = " ".join(labels)
                            
                            name = name.replace("\n", "").replace(" ", "")
                            
                            # Normalize Full-width to Half-width (e.g., ＥＣ -> EC)
                            name = name.translate(str.maketrans('０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ', '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'))
                            
                            # Final Filter: Reject if it looks like a number (after normalization and cleaning)
                            # This handles cases where garbage was joined
                            check_name = name.replace(",","").replace("","").replace("△","").replace("▲","")
                            if any(c.isdigit() for c in check_name) and len(check_name) > 3 and "売上" not in check_name: 
                                # Heuristic: If it has digits and no known keywords, and looks like a number artifact
                                # Further refinement: if it is mostly digits
                                digit_count = sum(c.isdigit() for c in check_name)
                                if digit_count / len(check_name) > 0.5:
                                    continue

                            if not name: continue

                            # Special Handling for Operating Profit
                            if "営業損益金額" in name or "営業利益" in name:
                                name = "営業利益"

                            try:
                                # Parsing Helper
                                def parse_curr(s):
                                    if not s: return None # Distinguish empty from 0
                                    s = str(s)
                                    # Replace special minus char () and others
                                    s = s.replace('', '-').replace('△', '-').replace('▲', '-')
                                    s = s.replace(',', '').replace('%', '')
                                    try:
                                        return float(s)
                                    except ValueError:
                                        return None

                                # Extract all numbers in the row
                                numbers = []
                                for cell in row:
                                    val = parse_curr(cell)
                                    if val is not None:
                                        numbers.append(val)
                                
                                # Logic: [Prev, (Debit, Credit...), Current, Ratio]
                                # curr_bal (Current Balance) is the YTD total.
                                # prev_bal (Previous Balance) is the total up to last month.
                                if len(numbers) >= 3:
                                    prev_bal = numbers[0]
                                    curr_bal = numbers[-2] # The one before ratio
                                    
                                    # Calculate Flow (Monthly change)
                                    # For April (Month 4 = start of fiscal year), 
                                    # the "previous balance" in PDF might be from prior FY,
                                    # so we use Cumulative as Current for FY start month.
                                    if month == 4:
                                        flow_val = curr_bal  # First month of FY: Current = Cumulative
                                    else:
                                        flow_val = curr_bal - prev_bal
                                    
                                    data.append({
                                        "Year": year,
                                        "Month": month,
                                        "Item": name, 
                                        "Current": flow_val,     # Monthly Flow
                                        "Cumulative": curr_bal,  # YTD Total
                                        "Previous": 0,           # To be populated in load_all_data
                                        "Source": filename,
                                        "Type": "Real"
                                    })
                            except (IndexError, ValueError):
                                continue

            # --- STRATEGY 2: TEXT EXTRACTION (Dummy PDF) ---
            # If no tables found, or mixed content (Dummy PDF usually returns empty tables), try text
            if not tables:
                text = page.extract_text()
                if not text: continue
                
                lines = text.split('\n')
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            # Helper to check if string is a number
                            def is_num(s): return re.match(r'^-?[\d,]+(\.\d+)?%?$', s)
                            
                            # Find indices of numbers from the end
                            num_indices = [i for i, p in enumerate(parts) if is_num(p)]
                            
                            if len(num_indices) >= 2:
                                # Dummy Format: [Item Name] [Current] [Previous] [YoY]
                                # Current is -3, Previous is -2
                                
                                if len(parts) >= 3 and is_num(parts[-3]):
                                    raw_item_name = " ".join(parts[:-3]).strip()
                                    curr_val = float(parts[-3].replace(',', ''))
                                    prev_val = float(parts[-2].replace(',', ''))
                                    
                                    clean_name = raw_item_name.strip()
                                    jp_name = TRANSLATION_MAP.get(clean_name, raw_item_name)
                                    
                                    data.append({
                                        "Year": year,
                                        "Month": month,
                                        "Item": jp_name,
                                        "Current": curr_val,
                                        "Cumulative": curr_val, # To be recomputed in load_all_data
                                        "Previous": 0,
                                        "Source": filename,
                                        "Type": "Dummy"
                                    })
                        except Exception:
                            continue

    return pd.DataFrame(data)

def load_all_data(input_dir):
    all_data = []
    for f in os.listdir(input_dir):
        if f.endswith(".pdf"):
            try:
                df = parse_pdf(os.path.join(input_dir, f))
                if not df.empty:
                    all_data.append(df)
            except Exception as e:
                print(f"Error parsing {f}: {e}")
    
    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        
        # --- FIX: Recompute Cumulative for Dummy Data with Fiscal Year Logic ---
        # 1. Add Fiscal Year Column (Apr Start)
        full_df["FiscalYear"] = full_df.apply(lambda x: x["Year"] if x["Month"] >= 4 else x["Year"] - 1, axis=1)
        
        # 2. Sort to ensure cumsum works chronologically by FY
        # Fiscal Month Order: Apr=1, ..., Mar=12
        full_df["FiscalMonth"] = full_df["Month"].apply(lambda x: x - 3 if x >= 4 else x + 9)
        full_df = full_df.sort_values(["FiscalYear", "FiscalMonth"])
        
        # Identify Dummy rows
        dummy_mask = full_df["Type"] == "Dummy"
        if dummy_mask.any():
            # Group by FiscalYear and Item, then cumsum the Current values
            # Assign explicitly to the Cumulative column for these rows
            full_df.loc[dummy_mask, "Cumulative"] = full_df[dummy_mask].groupby(["FiscalYear", "Item"])["Current"].cumsum()
        
        # --- YoY MAPPING LOGIC ---
        # For each (Month, Item, CurrentYear), find (Month, Item, CurrentYear-1)
        # and populate the 'Previous' column for the CurrentYear items.
        
        indexed_df = full_df.set_index(["Year", "Month", "Item"])
        
        def get_prev_metrics(row):
            try:
                # Look for the same month and item in the previous year
                prev_row = indexed_df.loc[(row["Year"] - 1, row["Month"], row["Item"])]
                if isinstance(prev_row, pd.DataFrame):
                    prev_row = prev_row.iloc[0]
                return prev_row["Current"], prev_row["Cumulative"]
            except (KeyError, IndexError):
                return 0, 0

        # Create two new helper columns for comparison
        res = full_df.apply(get_prev_metrics, axis=1)
        full_df["Prev_Current"] = [x[0] for x in res]
        full_df["Prev_Cumulative"] = [x[1] for x in res]
        
        return full_df
    else:
        return pd.DataFrame()
