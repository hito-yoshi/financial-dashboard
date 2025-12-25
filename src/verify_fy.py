import src.pdf_parser as parser
import pandas as pd

def verify_fy_ordering():
    df = parser.load_all_data("input_data")
    if df.empty:
        print("Data is empty")
        return
    
    # Check FY 2025
    fy2025 = df[df["FiscalYear"] == 2025]
    print(f"FY 2025 months available: {sorted(fy2025['Month'].unique())}")
    
    # Check ordering
    fy2025_sorted = fy2025.sort_values("FiscalMonth")
    print(f"FY 2025 months in Fiscal Order: {fy2025_sorted['Month'].unique().tolist()}")
    
    # Check latest month logic for FY 2025
    latest_fm = fy2025["FiscalMonth"].max()
    latest_row = fy2025[fy2025["FiscalMonth"] == latest_fm].iloc[0]
    print(f"Latest Month in FY 2025: {latest_row['Year']}-{latest_row['Month']} (FiscalMonth {latest_fm})")

if __name__ == "__main__":
    verify_fy_ordering()
