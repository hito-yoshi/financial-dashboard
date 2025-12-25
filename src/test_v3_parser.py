import re

def test_v3_parsing():
    filenames = [
        "shisanhyou_202509.pdf",
        "shisanhyou_202506.pdf",
        "shisanhyou_202404.pdf",
        "202509.pdf",
        "2025_9.pdf",
        "trial_2025_12.pdf"
    ]
    
    print("--- Testing V3 Robust Parsing ---")
    for filename in filenames:
        # year extraction
        year_match = re.search(r'(20\d{2})', filename)
        year = int(year_match.group(1)) if year_match else 2025
        
        # month extraction
        remaining = filename.replace(str(year), "", 1)
        month_match = re.search(r'(0[1-9]|1[0-2]|[1-9])', remaining)
        month = int(month_match.group(1)) if month_match else 1
        
        print(f"File: {filename:30} -> Year: {year}, Month: {month}")

if __name__ == "__main__":
    test_v3_parsing()
