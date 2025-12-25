import src.pdf_parser as parser
import pandas as pd
import os

def debug_load():
    INPUT_DIR = "input_data"
    print(f"Loading data from {INPUT_DIR}...")
    df = parser.load_all_data(INPUT_DIR)
    
    if df.empty:
        print("DataFrame is EMPTY!")
        return

    print(f"Loaded {len(df)} rows.")
    print("\nData distribution by Year and Month:")
    summary = df.groupby(["Year", "Month"]).size().reset_index(name="Count")
    print(summary)
    
    latest_year = df["Year"].max()
    latest_month = df[df["Year"] == latest_year]["Month"].max()
    print(f"\nLatest Data Point: {latest_year}-{latest_month}")
    
    # Check if 'shisanhyou_202509.pdf' is in the Source
    print("\nFiles processed (subset):")
    print(df["Source"].unique())

if __name__ == "__main__":
    debug_load()
