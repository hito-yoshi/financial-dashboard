import sys
import os
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))
import pdf_parser

def inspect_items():
    input_dir = "input_data"
    df = pdf_parser.load_all_data(input_dir)
    if df.empty:
        print("No data found.")
        return
    
    unique_items = sorted(df["Item"].unique())
    print("--- Extracted Items ---")
    for item in unique_items:
        print(f"'{item}'")
        if "ke)" in item or "keyk" in item:
            print(f">>> FOUND SUSPICIOUS ITEM: {item}")

if __name__ == "__main__":
    inspect_items()
