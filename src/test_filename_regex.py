import re

def test_filenames():
    filenames = [
        "shisanhyou_202509.pdf",
        "2025_09_trial_balance.pdf",
        "202509.pdf",
        "trial_2025_4.pdf"
    ]
    
    print("--- Testing Filename Parsing ---")
    
    for f in filenames:
        print(f"\nFile: {f}")
        # Current Logic (approximate reconstruction)
        digits = re.findall(r'\d+', f)
        print(f"Digits found: {digits}")
        
        year = 2025
        month = 1
        
        # Proposed Logic for YYYYMM
        # Check for 6-digit pattern starting with 20
        six_digit = re.search(r'(20\d{2})(0[1-9]|1[0-2])', f)
        if six_digit:
            print(f"Matched 6-digit: Year={six_digit.group(1)}, Month={six_digit.group(2)}")
        else:
            print("No 6-digit match")

if __name__ == "__main__":
    test_filenames()
