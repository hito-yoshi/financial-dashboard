import src.pdf_parser as parser
import pandas as pd

def test():
    # Test Dummy
    print("--- Testing Dummy PDF ---")
    df_dummy = parser.parse_pdf("input_data/2025_09_trial_balance.pdf")
    print(df_dummy.head() if not df_dummy.empty else "Dummy PDF: Empty DataFrame")
    
    # Test Real
    print("\n--- Testing Real PDF ---")
    try:
        df_real = parser.parse_pdf("raw_files/shisanhyou_202509.pdf")
        if not df_real.empty:
            print(f"Real PDF: {len(df_real)} rows")
            print("Unique Items:")
            print(df_real["Item"].unique())
        else:
            print("Real PDF: Empty DataFrame")
    except Exception as e:
        print(f"Real PDF missing or error: {e}")

if __name__ == "__main__":
    test()
