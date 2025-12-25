import sys
import os
import pandas as pd

# Add src to path to import pdf_parser
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pdf_parser

def verify_data_loading():
    input_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "input_data")
    print(f"Loading data from: {input_dir}")
    
    if not os.path.exists(input_dir):
        print("Error: input_data directory not found.")
        return

    df = pdf_parser.load_all_data(input_dir)
    
    if df.empty:
        print("Error: No data loaded.")
        return

    print(f"Loaded {len(df)} rows.")
    print("Columns:", df.columns.tolist())
    
    # Check for 2025 and 2024 data
    years = df["Year"].unique()
    print(f"Years found: {years}")
    
    if 2024 not in years or 2025 not in years:
        print("Warning: Expected 2024 and 2025 data for YoY check. Found:", years)
    
    # Verify YoY Logic for a specific month/item
    # Pick September 2025 (since we saw shisanhyou_202509.pdf and 202409)
    target_month = 9
    target_year = 2025
    
    month_df = df[(df["Year"] == target_year) & (df["Month"] == target_month)]
    if month_df.empty:
        print(f"No data for {target_year}-{target_month}")
        return

    # Pick an item, e.g., "売上高"
    item_name = "売上高"
    row = month_df[month_df["Item"] == item_name]
    
    if row.empty:
        print(f"Item {item_name} not found in {target_year}-{target_month}")
        # Try finding any item
        item_name = month_df.iloc[0]["Item"]
        row = month_df[month_df["Item"] == item_name]
        print(f"Using item: {item_name}")

    curr_val = row.iloc[0]["Current"]
    prev_curr_col_val = row.iloc[0]["Prev_Current"]
    
    print(f"Item: {item_name}")
    print(f"{target_year}-{target_month} Current: {curr_val}")
    print(f"{target_year}-{target_month} Prev_Current (from col): {prev_curr_col_val}")
    
    # Check actual 2024 value
    prev_row = df[(df["Year"] == target_year - 1) & (df["Month"] == target_month) & (df["Item"] == item_name)]
    if not prev_row.empty:
        actual_prev = prev_row.iloc[0]["Current"]
        print(f"{target_year-1}-{target_month} Actual Current: {actual_prev}")
        
        if abs(prev_curr_col_val - actual_prev) < 0.001:
            print("SUCCESS: Prev_Current matches actual 2024 data.")
        else:
            print("FAILURE: Prev_Current does NOT match actual 2024 data.")
    else:
        print(f"Warning: Could not find actual 2024 data for {item_name} to compare.")

if __name__ == "__main__":
    verify_data_loading()
