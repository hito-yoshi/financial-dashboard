import src.pdf_parser as parser
import pandas as pd

def debug_fy():
    print("Loading all data...")
    df = parser.load_all_data("input_data")
    if df.empty:
        print("DataFrame is empty!")
        return

    print(f"Total rows: {len(df)}")
    
    # Check column existence
    print(f"Columns: {df.columns.tolist()}")
    
    # Explicitly calculate FY if missing to compare
    df['Calc_FY'] = df.apply(lambda x: x['Year'] if x['Month'] >= 4 else x['Year'] - 1, axis=1)
    
    # Group by both Year/Month and result FY
    summary = df.groupby(['Year', 'Month', 'FiscalYear', 'Calc_FY']).size().reset_index(name='Count')
    print("\nFiscal Year Mapping Summary:")
    print(summary.to_string())
    
    print("\nUnique FiscalYears in DF:", df['FiscalYear'].unique())
    print("Unique Calc_FYs in DF:", df['Calc_FY'].unique())

if __name__ == "__main__":
    debug_fy()
