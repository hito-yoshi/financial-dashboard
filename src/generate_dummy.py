# -*- coding: utf-8 -*-
import os
import random
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

def create_dummy_pdf(filename, year=2025, month=1):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, f"Monthly Trial Balance - Month {month}")
    c.setFont("Helvetica", 10)
    c.drawString(450, height - 50, f"{year} Fiscal Year")

    # Header
    y = height - 100
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Account Item")
    c.drawString(250, y, "Current")
    c.drawString(350, y, "Previous")
    c.drawString(450, y, "YoY")
    
    y -= 20
    c.line(50, y+15, 550, y+15)

    # Base Values from User's September Data (Month 9)
    # Ratios applied to other months to create trends
    
    # REVENUE (Monthly Flow)
    # "Sales" (Design) - Credit 6,561,460
    sales_design_base = 6561460 
    # "Advances" - Monthly 0
    advances_base = 0 
    # "EC Sales" - Credit 6,252,693
    sales_ec_base = 6252693
    
    # COST OF SALES (Monthly Flow - Debit)
    # Design Costs
    material_cost_base = 8820 # 素材費
    purchase_base = 314047 # 仕入高
    outsource_coding_base = 120400 # 外注コーディング費
    outsource_design_base = 643540 # 外注デザイン費
    print_cost_base = 43620 # 印刷費
    outsource_other_base = 411368 # その他外注費

    # EC Costs
    ec_purchase_base = 1894763 # EC仕入高
    ec_material_base = 117765 # EC資材
    ec_fees_base = 1754045 # EC手数料
    ec_ads_base = 604618 # EC広告費
    ec_shipping_base = 217688 # EC送料
    ec_homework_base = 562627 # EC内職
    ec_other_base = 54727 # ECその他

    # SGA (Monthly Flow - Debit)
    director_comp = 850000 # 役員報酬
    salaries = 2058400 # 給与手当
    bonuses = 0 # 賞与 (0 in Sep possibly)
    legal_welfare = 433055 # 法定福利費
    welfare = 21856 # 福利厚生費
    travel = 52750 # 旅費交通費
    comm = 143577 # 通信費
    entertainment = 0 # 交際費
    meetings = 15330 # 会議費
    rent = 183700 # 地代家賃
    insurance = 0 # 保険料
    utilities = 22263 # 水道光熱費
    fuel = 745 # 燃料費
    supplies = 490554 # 消耗品費
    taxes_public = 1703 # 租税公課
    freight = 26928 # 運賃
    consumption_tax = 776600 # 消費税
    office_supplies = 65846 # 事務用品費
    ad_expenses = 72458 # 広告宣伝費
    payment_fees = 119673 # 支払手数料
    dues = 0 # 諸会費
    books = 2320 # 新聞図書費
    misc = 1000 # 雑費

    # Define Full Structure (English Keys -> Mapped to Japanese in Parser)
    items_def = [
        ("Sales", sales_design_base), 
        ("Advances Received", advances_base),
        ("EC Sales", sales_ec_base),
        
        ("Material Cost", material_cost_base),
        ("Purchases", purchase_base),
        ("EC Purchases", ec_purchase_base),
        ("EC Materials", ec_material_base),
        ("EC Fees", ec_fees_base),
        ("EC Ads", ec_ads_base),
        ("EC Shipping", ec_shipping_base),
        ("EC Outsourcing", ec_homework_base),
        ("EC Other", ec_other_base),
        ("Outsource Coding", outsource_coding_base),
        ("Outsource Design", outsource_design_base),
        ("Printing", print_cost_base),
        ("Other Outsourcing", outsource_other_base),
        
        ("Director Comp", director_comp),
        ("Salaries", salaries),
        ("Bonuses", bonuses),
        ("Legal Welfare", legal_welfare),
        ("Welfare", welfare),
        ("Travel", travel),
        ("Comm", comm),
        ("Entertainment", entertainment),
        ("Meetings", meetings),
        ("Rent", rent),
        ("Insurance", insurance),
        ("Utilities", utilities),
        ("Fuel", fuel),
        ("Supplies", supplies),
        ("Taxes Public", taxes_public),
        ("Freight", freight),
        ("Consumption Tax", consumption_tax),
        ("Office Supplies", office_supplies),
        ("Ad Expenses", ad_expenses),
        ("Payment Fees", payment_fees),
        ("Dues", dues),
        ("Books", books),
        ("Misc", misc)
    ]

    c.setFont("Helvetica", 10)
    
    # Seasonality Factor (Example: Higher in later months)
    seasonality = 1.0 + (month - 9) * 0.02 # Center around month 9

    for item, current_base in items_def:
        # User provided Month 9 data. We verify logic:
        # If generating month 9, use Exact Base (with tiny noise to avoid 100.00% exact match looking fake if user cares, but user wants check so keep close)
        
        if month == 9:
            current = int(current_base)
            prev = int(current_base * 0.95) # Assume growth
        else:
            # Vary by month relative to Month 9
            factor = 1.0 + (month - 9) * 0.03
            current = int(current_base * factor * random.uniform(0.95, 1.05))
            prev = int(current * random.uniform(0.90, 0.98))

        if prev == 0:
            ratio = "-"
        else:
            ratio = f"{current/prev:.1%}"
        
        c.drawString(50, y, item)
        c.drawString(250, y, f"{current:,}")
        c.drawString(350, y, f"{prev:,}")
        c.drawString(450, y, ratio)
        y -= 20
        
        if y < 50: # New Page if needed
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - 50

    c.save()
    print(f"Created {filename}")

if __name__ == "__main__":
    os.makedirs("input_data", exist_ok=True)
    # Generate 2024 data (Full year for comparison)
    for i in range(1, 13):
        create_dummy_pdf(f"input_data/2024_{i:02d}_trial_balance.pdf", year=2024, month=i)
    # Generate 2025 data up to Month 8
    for i in range(1, 9):
        create_dummy_pdf(f"input_data/2025_{i:02d}_trial_balance.pdf", year=2025, month=i)
