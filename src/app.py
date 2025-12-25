import streamlit as st
import pandas as pd
import altair as alt
import src.pdf_parser as output_parser
import os
import importlib
import re
import time
import google.generativeai as genai

# --- Gemini API Setup ---
# You can set your API key here or via environment variable GOOGLE_API_KEY
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- Helper: Contextual Response Generator (when API unavailable) ---
def generate_contextual_response(prompt, monthly_ctx, annual_ctx, sales, gp, op, sga_est, sga_rate, op_rate):
    """Generate contextual response based on question keywords when API is not available."""
    prompt_lower = prompt.lower()
    
    if "粗利" in prompt or "原価" in prompt:
        return f"""【粗利率についての分析】

現在の粗利率は **{monthly_ctx['gp_rate']:.1%}** です。

**改善のための具体的アクション:**

1. **外注費の見直し**: 現在の外注単価を精査し、複数社から見積もりを取得
2. **内製化の検討**: 繰り返し発生する外注業務は、内製化の方がコスト効率が良い場合があります
3. **仕入先の交渉**: 継続取引の強みを活かした価格交渉

粗利益は現在 **¥{gp:,.0f}** ですが、原価を1%削減できれば約 **¥{sales*0.01:,.0f}** の利益改善につながります。"""
    
    elif "販管" in prompt or "固定費" in prompt or "コスト" in prompt:
        return f"""【販管費についての分析】

現在の販管費は **¥{sga_est:,.0f}**（売上比 **{sga_rate:.1%}**）です。

**見直しのポイント:**

1. **人件費**: 総額と人数のバランスを確認。残業代の最適化や業務効率化を検討
2. **地代家賃**: リモートワーク導入によるオフィス縮小の余地を検討
3. **その他固定費**: サブスクリプションの見直し、不要な契約の解約

販管費を粗利益の70%以下に抑えることが理想です。現在は **{(sga_est/gp*100):.1f}%** です。"""
    
    elif "利益" in prompt or "営業" in prompt or "赤字" in prompt:
        status = "黒字" if op > 0 else "赤字"
        return f"""【営業利益についての分析】

現在の営業利益は **¥{op:,.0f}**（{status}）で、営業利益率は **{op_rate:.1%}** です。

**利益改善の2つのアプローチ:**

1. **売上拡大アプローチ**:
   - 既存顧客へのアップセル・クロスセル
   - 新規顧客開拓の強化

2. **コスト削減アプローチ**:
   - 粗利率改善: 現在{monthly_ctx['gp_rate']:.1%} → 目標設定
   - 販管費削減: 現在¥{sga_est:,.0f} → 目標設定

営業利益率を5%にするには、約 **¥{(sales*0.05-op):,.0f}** の改善が必要です。"""
    
    elif "流動" in prompt or "資金" in prompt or "キャッシュ" in prompt:
        return f"""【資金繰り・流動性についての分析】

現在の流動比率は **{monthly_ctx['cur_ratio']:.1f}%** です。

**評価:**
- 100%未満: 要注意（短期支払能力に懸念）
- 150%以上: 安全圈
- 200%以上: 盤石
- 300%以上: 過剰（投資機会を逃している可能性）

**管理のポイント:**
1. 売掛金の回収サイクルの短縮
2. 買掛金の支払いサイクルの最適化
3. 不要な棚卸資産の処分"""
    
    else:
        return f"""【財務状況の総合分析】

**ご質問**: {prompt}

現在の主要指標:
- 売上高: ¥{sales:,.0f}
- 粗利率: {monthly_ctx['gp_rate']:.1%}
- 営業利益率: {op_rate:.1%}
- 流動比率: {monthly_ctx['cur_ratio']:.1f}%

ご質問の内容をより具体的に教えていただければ、詳細な分析を提供いたします。

例えば:
- 「粗利率を改善するには？」
- 「販管費が高いのはなぜ？」
- 「利益を増やすには？」
- 「資金繰りの改善策は？」"""


# Ensure fresh logic
importlib.reload(output_parser)
output_parser.PARSING_TRACE = [] # Reset trace

# --- Page Config ---
st.set_page_config(page_title="経営分析ダッシュボード", layout="wide", page_icon="📈", initial_sidebar_state="expanded")

# --- CSS Styling ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    :root {
        --bg-color: #1a1b1e;
        --card-bg: #25262b;
        --text-primary: #ffffff;
        --text-secondary: #909296;
        --accent: #4dabf7;
        --border: #373a40;
    }

    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif !important;
        background-color: var(--bg-color) !important;
        color: var(--text-primary) !important;
    }

    .stApp {
        background-color: var(--bg-color);
    }

    .gecko-card {
        background-color: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 4px;
        padding: 20px;
        margin-bottom: 5px;
        height: 100%;
    }
    .gecko-label {
        color: var(--text-secondary);
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 8px;
    }
    .gecko-value {
        color: var(--text-primary);
        font-size: 26px;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .gecko-delta {
        font-size: 13px;
        font-weight: 500;
        margin-top: 4px;
    }
    .delta-up { color: #51cf66; }
    .delta-down { color: #ff6b6b; }

    .stExpander {
        border-color: var(--border) !important;
        background-color: var(--card-bg) !important;
    }
    .stExpander > div:first-child:hover {
        background-color: #373a40 !important;
    }
    .stExpander *, .stDataFrame * {
        letter-spacing: normal !important;
        text-transform: none !important;
    }

    .ai-analysis {
        background-color: #25262b !important;
        border: 1px solid #373a40 !important;
        padding: 15px !important;
        border-radius: 4px !important;
        margin: 10px 0 !important;
        font-size: 14px !important;
        color: #ffffff !important;
    }
    .ai-analysis h1, .ai-analysis h2, .ai-analysis h3, .ai-analysis h4, .ai-analysis p, .ai-analysis span, .ai-analysis strong, .ai-analysis em, .ai-analysis * {
        color: #ffffff !important;
        background-color: transparent !important;
    }

    .block-container {
        padding-top: 3rem !important;
    }

    /* Selectbox styling fixes */
    div[data-baseweb="select"] {
        width: 100% !important;
    }
    .stSelectbox label {
        color: var(--text-secondary) !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        margin-bottom: 4px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Data Loading ---
INPUT_DIR = "input_data"
@st.cache_data
def load_data():
    return output_parser.load_all_data(INPUT_DIR)

df = load_data()

# --- Data Cleaning (Aggressive) ---
if not df.empty:
    # Remove ALL whitespace from Item names to unify duplicates
    df["Item"] = df["Item"].astype(str).apply(lambda x: re.sub(r'\s+', '', x))

# --- Force FY Calculation (Safety) ---
if not df.empty:
    # Use the Year and Month extracted by the parser
    df["FiscalYear"] = df.apply(lambda x: x["Year"] if x["Month"] >= 4 else x["Year"] - 1, axis=1)
    df["FiscalMonth"] = df["Month"].apply(lambda x: x - 3 if x >= 4 else x + 9)

# --- Sidebar ---
st.sidebar.markdown("# 📊 管理設定")

# Get available fiscal years
if not df.empty:
    available_fys = sorted(df["FiscalYear"].unique(), reverse=True)
    sel_fy = st.sidebar.selectbox("会計年度", available_fys, format_func=lambda x: f"{x}年度")
else:
    sel_fy = 2025

view_mode = st.sidebar.radio("表示モード (分析/グラフ)", ["単月 (Monthly)", "累計 (YTD)"], index=0)
data_col = "Current" if "単月" in view_mode else "Cumulative"

if st.sidebar.button("データを最新化", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.cache_resource.clear()
    # Also clear a hidden key if we were using one
    if "data_timestamp" in st.session_state:
        del st.session_state["data_timestamp"]
    st.success("キャッシュをクリアしました。再読み込み中...")
    st.rerun()

is_debug = st.sidebar.checkbox("デバッグ表示 (分析用)")
show_file_map = st.sidebar.checkbox("ファイル解析ログを表示")

if show_file_map:
    with st.expander("📝 内部解析ログ (pdf_parser)", expanded=True):
        for log in output_parser.PARSING_TRACE:
            st.write(log)

# --- Helpers ---
DESIGN_SALES_ITEMS = ["売上高", "デザイン売上高", "前受金"]
EC_SALES_ITEMS = ["EC売上高"]
DESIGN_COST_ITEMS = ["素材費", "仕入高", "外注コーディング費", "外注デザイン費", "印刷費", "その他外注費"]
EC_COST_ITEMS = ["EC仕入高", "EC資材", "EC手数料", "EC広告費", "EC送料", "EC内職", "ECその他"]
TOTAL_COST_ITEMS = DESIGN_COST_ITEMS + EC_COST_ITEMS

SGA_ITEMS = [
    "役員報酬", "給与手当", "給料手当", "賞与", "法定福利費", "福利厚生費", "旅費交通費", "通信費", 
    "交際費", "会議費", "地代家賃", "支払地代", "支払家賃", "租税公課", "保守料", "保険料", 
    "水道光熱費", "燃料費", "車両費", "消耗品費", "図書教育費", "新聞図書費", "研修費",
    "運賃", "荷造運賃", "消費税", "事務用品費", "広告宣伝費", "販売促進費", "支払手数料", 
    "諸会費", "雑費", "支払利息"
]

def get_latest_metrics(items, data_col, current_fy):
    if df.empty: return 0, 0
    # Find latest month WITHIN the selected FY
    fy_df = df[df["FiscalYear"] == current_fy]
    if fy_df.empty: return 0, 0
    
    # Sort to find the latest month chronologically in that FY
    # FY months: 4, 5, ..., 12, 1, 2, 3
    if "FiscalMonth" not in fy_df.columns:
        fy_df = fy_df.copy()
        fy_df["FiscalMonth"] = fy_df["Month"].apply(lambda x: x - 3 if x >= 4 else x + 9)
    
    latest_fm = fy_df["FiscalMonth"].max()
    latest_row_meta = fy_df[fy_df["FiscalMonth"] == latest_fm].iloc[0]
    l_m = latest_row_meta["Month"]
    l_y = latest_row_meta["Year"]
    
    sub_df = fy_df[(fy_df["Item"].isin(items)) & (fy_df["Year"] == l_y) & (fy_df["Month"] == l_m)]
    val = sub_df[data_col].sum()
    
    prev_col = "Prev_Current" if data_col == "Current" else "Prev_Cumulative"
    prev_val = sub_df[prev_col].sum()
    delta = (val - prev_val) / abs(prev_val) if prev_val else 0
    return val, delta

def display_gecko_card(title, val, delta, is_percent=False):
    fmt = ".1%" if is_percent else ",.0f"
    prefix = "" if is_percent else "¥"
    delta_icon = "▲" if delta > 0 else "▼" if delta < 0 else ""
    delta_class = "delta-up" if delta > 0 else "delta-down" if delta < 0 else ""
    
    st.markdown(f"""
    <div class="gecko-card">
        <div class="gecko-label">{title}</div>
        <div class="gecko-value">{prefix}{val:{fmt}}</div>
        <div class="gecko-delta {delta_class}">
            {delta_icon} {abs(delta):.1%} <span style="color:var(--text-secondary); font-weight:400;">{"前年同期比" if delta_icon else "前年比 変化なし"}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Layout ---
if df.empty:
    st.title("ヒトツナギ・デザイン 経営ダッシュボード")
    st.error("データがありません。")
    st.stop()

if "FiscalYear" not in df.columns:
    df["FiscalYear"] = df.apply(lambda x: x["Year"] if x["Month"] >= 4 else x["Year"] - 1, axis=1)
if "FiscalMonth" not in df.columns:
    df["FiscalMonth"] = df["Month"].apply(lambda x: x - 3 if x >= 4 else x + 9)

fy_df = df[df["FiscalYear"] == sel_fy]

if show_file_map:
    st.write(f"### 📁 ファイル読み込み状況 ({sel_fy}年度)")
    file_map = df[df["FiscalYear"] == sel_fy][["Source", "Year", "Month"]].drop_duplicates().sort_values(["Year", "Month"])
    st.table(file_map)

if is_debug:
    st.write(f"### デバッグ: {sel_fy}年度 のデータ数: {len(fy_df)}")
    st.dataframe(fy_df)

    st.title("ヒトツナギ・デザイン 経営ダッシュボード (DEBUG v2.2)")
    st.warning(f"{sel_fy}年度のデータが見つかりません。")
    st.stop()

latest_fm = fy_df["FiscalMonth"].max()
latest_meta = fy_df[fy_df["FiscalMonth"] == latest_fm].iloc[0]
latest_year = latest_meta["Year"]
latest_m = latest_meta["Month"]

st.markdown(f"<span style='color:var(--text-secondary)'>最終更新: {sel_fy}年度 {latest_m}月 試算表データ</span>", unsafe_allow_html=True)

# --- DEBUG: April Data Check ---
# Check if April data exists for this FY
april_data = df[(df["FiscalYear"] == sel_fy) & (df["Month"] == 4)]
if april_data.empty and sel_fy == 2025:
     # Fallback: maybe it wasn't captured?
     # Check raw Year 2025 Month 4
     raw_april = df[(df["Year"] == 2025) & (df["Month"] == 4)]
     if not raw_april.empty:
         # Force update FiscalYear for these if calculation failed
         df.loc[(df["Year"] == 2025) & (df["Month"] == 4), "FiscalYear"] = 2025
         fy_df = df[df["FiscalYear"] == sel_fy] # Reload fy_df

# Calculations
ms_total, ds_total = get_latest_metrics(DESIGN_SALES_ITEMS + EC_SALES_ITEMS, data_col, sel_fy)
ms_design, ds_design = get_latest_metrics(DESIGN_SALES_ITEMS, data_col, sel_fy)
ms_ec, ds_ec = get_latest_metrics(EC_SALES_ITEMS, data_col, sel_fy)

# Gross Profit
prev_col = "Prev_Current" if data_col == "Current" else "Prev_Cumulative"
latest_df = fy_df[(fy_df["Year"] == latest_year) & (fy_df["Month"] == latest_m)]

mg_total = ms_total - latest_df[latest_df["Item"].isin(TOTAL_COST_ITEMS)][data_col].sum()
pg_total = (latest_df[latest_df["Item"].isin(DESIGN_SALES_ITEMS + EC_SALES_ITEMS)][prev_col].sum() - 
            latest_df[latest_df["Item"].isin(TOTAL_COST_ITEMS)][prev_col].sum())
dg_total = (mg_total - pg_total) / abs(pg_total) if pg_total else 0
mg_design = ms_design - latest_df[latest_df["Item"].isin(DESIGN_COST_ITEMS)][data_col].sum()
mg_ec = ms_ec - latest_df[latest_df["Item"].isin(EC_COST_ITEMS)][data_col].sum()

# Op Profit
op_item = latest_df[latest_df["Item"] == "営業利益"]
if not op_item.empty:
    m_op = op_item[data_col].values[0]
    p_op = op_item[prev_col].values[0]
    d_op = (m_op - p_op) / abs(p_op) if p_op else 0
else:
    m_op = mg_total - latest_df[latest_df["Item"].isin(SGA_ITEMS)][data_col].sum()
    p_op = pg_total - latest_df[latest_df["Item"].isin(SGA_ITEMS)][prev_col].sum()
    d_op = (m_op - p_op) / abs(p_op) if p_op else 0

# --- 1. Top Tiles ---
st.markdown("### 🏢 全社パフォーマンス")
t1, t2, t3, t4 = st.columns(4)
with t1: display_gecko_card("全社売上", ms_total, ds_total)
with t2: display_gecko_card("全社売上総利益", mg_total, dg_total)
with t3: display_gecko_card("営業利益", m_op, d_op)
with t4: display_gecko_card("売上高粗利率", mg_total/ms_total if ms_total else 0, 0, is_percent=True)

# --- 2. AI Analysis ---
st.markdown("### 📊 経営分析・インサイト")

# Helper to generate AI prompt data
def get_ai_report_context(target_df, period_name):
    cur_assets = target_df[target_df["Item"].str.contains("|".join(CUR_ASSET_KEYWORDS))]["Cumulative"].sum()
    cur_liab = target_df[target_df["Item"].str.contains("|".join(CUR_LIAB_KEYWORDS))]["Cumulative"].sum()
    equity = target_df[target_df["Item"].str.contains("|".join(EQUITY_KEYWORDS))]["Cumulative"].sum()
    fixed_assets = target_df[target_df["Item"].str.contains("固定資産|車両|工具|敷金|出資金|保険積立|保証料")]["Cumulative"].sum()
    total_assets = cur_assets + fixed_assets
    
    sales = target_df[target_df["Item"].isin(DESIGN_SALES_ITEMS + EC_SALES_ITEMS)][data_col].sum()
    cogs = target_df[target_df["Item"].isin(TOTAL_COST_ITEMS)][data_col].sum()
    gp = sales - cogs
    sga = target_df[target_df["Item"].isin(SGA_ITEMS)][data_col].sum()
    op = gp - sga
    
    return {
        "period": period_name,
        "sales": sales, "gp": gp, "op": op, "gp_rate": gp/sales if sales else 0,
        "cur_ratio": (cur_assets / cur_liab * 100) if cur_liab else 0,
        "equity_ratio": (equity / total_assets * 100) if total_assets else 0
    }

CUR_ASSET_KEYWORDS = ["預金", "売掛金", "商品", "仕掛品", "立替金", "前払費用", "棚卸資産"]
CUR_LIAB_KEYWORDS = ["買掛金", "借入金", "未払金", "預り金", "未払消費税", "未払法人税"]
EQUITY_KEYWORDS = ["資本金", "利益剰余金", "当期純損益"]

# Data for 2 reports
monthly_ctx = get_ai_report_context(latest_df, f"{latest_m}月度")
annual_ctx = get_ai_report_context(fy_df, f"{sel_fy}年度 通期累計")

tab_monthly, tab_annual = st.tabs(["📊 最新月レポート", "📅 通年レポート"])

prompt_base = """
あなたは優秀なプロフェッショナル経営コンサルタントです。提供された財務データを元に、経営者に向けた鋭い洞察を提供してください。
分析は以下の構成で、簡潔かつ示唆に富む内容にしてください：
1. **全体サマリー**: 現状を一言で。
2. **収益性分析**: 売上・粗利・営業利益の動向と課題。
3. **安全性/効率性**: BS面からのリスクや資金繰りへの言及。
4. **コンサルタントの提言**: 明日から打つべき具体的なアクション。
"""

prompt_base = """
あなたは世界最高峰の戦略コンサルティングファームに所属する、極めて有能なシニアパートナーです。
最新の **Gemini 3 Pro** モデルを駆使し、提供された財務データを多角的に分析し、経営者に対して「数字の裏にある意味」と「未来への布石」を提示してください。

分析のポイント：
- **過去データとの比較**: 前年、前月と比較して、どの動向が「異常」であり、どの動向が「健全な成長」かを明示。
- **気になる点/リスク**: 表面的な利益だけでなく、キャッシュフローの阻害要因や固定費の予期せぬ上昇を指摘。
- **具体的かつ平易な言葉**: 専門用語に逃げず、経営者が直感的に理解でき、すぐに意思決定に活かせる言葉を使用。
- **長期的視点**: 単なる今月の反省ではなく、通期目標達成に向けた軌道修正案を提示。
"""

with tab_monthly:
    # Upgrade prompt with actual context
    gp = monthly_ctx['gp']
    op = monthly_ctx['op']
    sales = monthly_ctx['sales'] if 'sales' in monthly_ctx else (gp / monthly_ctx['gp_rate'] if monthly_ctx['gp_rate'] else 0)
    sga_est = gp - op  # Estimated SG&A
    op_rate = op / sales if sales else 0
    sga_rate = sga_est / sales if sales else 0
    gp_consume_rate = (sga_est / gp * 100) if gp else 0
    
    # Diagnostic logic based on actual data
    profitability_diagnosis = ""
    if op < 0:
        profitability_diagnosis = "🚨 **赤字警告**: 営業利益がマイナスです。販管費が粗利益を上回っています。早急にコスト構造の見直しが必要です。"
    elif op_rate < 0.03:
        profitability_diagnosis = "⚠️ **注意**: 営業利益率が3%未満です。販管費の削減または粗利率改善による収益性強化を検討してください。"
    elif op_rate < 0.05:
        profitability_diagnosis = "✅ 収益性は安定していますが、さらなる改善の余地があります。"
    else:
        profitability_diagnosis = "✅ **良好**: 営業利益率が5%以上で、健全な収益構造です。"
    
    sga_diagnosis = ""
    if gp_consume_rate > 90:
        sga_diagnosis = "🚨 **警告**: 販管費が粗利益の90%以上を消費しています。固定費の見直しが急務です。"
    elif gp_consume_rate > 70:
        sga_diagnosis = "⚠️ 販管費が粗利益の70%以上を占めています。改善の余地あり。"
    else:
        sga_diagnosis = "✅ 販管費は適正にコントロールされています。"
    
    safety_diagnosis = ""
    cur_ratio = monthly_ctx['cur_ratio']
    eq_ratio = monthly_ctx['equity_ratio']
    
    if cur_ratio < 100:
        safety_diagnosis += "🚨 **流動比率が100%未満**: 短期的な支払い能力に懸念があります。資金繰りの改善が必要です。\n"
    elif cur_ratio < 150:
        safety_diagnosis += "⚠️ 流動比率が150%未満です。短期負債の返済余力に注意が必要です。\n"
    elif cur_ratio > 300:
        safety_diagnosis += "💰 流動比率が300%以上と非常に高いです。過剰な資金を成長投資に回すことを検討してください。\n"
    else:
        safety_diagnosis += "✅ 流動比率は安全圈内です。\n"
    
    if eq_ratio < 20:
        safety_diagnosis += "🚨 **自己資本比率が20%未満**: 財務基盤が脆弱です。内部留保の強化または増資を検討してください。"
    elif eq_ratio < 40:
        safety_diagnosis += "⚠️ 自己資本比率が40%未満です。安定性はありますが、さらなる強化が望ましいです。"
    else:
        safety_diagnosis += "✅ 自己資本比率は十分に高く、財務基盤は盤石です。"
    
    # Generate specific recommendations based on data
    recommendations = []
    if op < 0:
        recommendations.append("販管費の科目別分析を行い、削減可能な項目を特定")
    if gp_consume_rate > 70:
        recommendations.append("人件費・地代家賃などの固定費の見直し")
    if sga_rate > 0.3:
        recommendations.append("売上高に対する販管費率の目標設定とモニタリング")
    if monthly_ctx['gp_rate'] < 0.4:
        recommendations.append("原価構造の見直し（外注費の最適化、仕入先の解約）")
    if cur_ratio > 300:
        recommendations.append("過剰な流動資産の成長投資への活用検討")
    if not recommendations:
        recommendations.append("現状の健全な財務体質を維持しつつ、成長投資の機会を探る")
    
    rec_list = "\n    ".join([f"{i+1}. {r}" for i, r in enumerate(recommendations)])
    
    report_monthly = f"""
    ### 👔 エグゼクティブ・サマリー ({monthly_ctx['period']})
    
    > ℹ️ **データソース**: 本レポートの全数値は試算表PDFデータから自動取得されています。
    
    ---
    
    #### 📊 当月の財務ハイライト
    
    | 指標 | 値 | 対売上高比率 |
    |------|------|------|
    | 売上高 | ¥{sales:,.0f} | 100% |
    | 粗利益 | ¥{gp:,.0f} | {monthly_ctx['gp_rate']:.1%} |
    | 販管費 | ¥{sga_est:,.0f} | {sga_rate:.1%} |
    | 営業利益 | ¥{op:,.0f} | {op_rate:.1%} |
    
    | 安全性指標 | 値 |
    |------|------|
    | 流動比率 | {monthly_ctx['cur_ratio']:.1f}% |
    | 自己資本比率 | {monthly_ctx['equity_ratio']:.1f}% |
    
    ---
    
    #### 🩺 財務診断
    
    **収益性の評価**
    
    {profitability_diagnosis}
    
    - 粗利率 **{monthly_ctx['gp_rate']:.1%}** : 売上1円あたり **¥{monthly_ctx['gp_rate']:.2f}** が粗利益として残ります。
    - 販管費率 **{sga_rate:.1%}** : {sga_diagnosis}
    - 営業利益率 **{op_rate:.1%}** : 最終的に売上1円あたり **¥{op_rate:.2f}** が利益として残っています。
    
    **安全性の評価**
    
    {safety_diagnosis}
    
    ---
    
    #### 💡 コンサルタントからの提言
    
    **優先対応事項**:
    
    {rec_list}
    
    **確認ポイント**:
    
    - 売上原価の内訳（特に外注費）が前月と比較して変動していないか
    - 販管費の主要科目（人件費・地代家賃）の推移
    - 売掛金・買掛金の残高と回収・支払サイクル
    """
    st.markdown(f'<div class="ai-analysis">{report_monthly.strip().replace("</div>", "")}</div>', unsafe_allow_html=True)

with tab_annual:
    op_rate = annual_ctx['op']/annual_ctx['sales'] if annual_ctx['sales'] else 0
    report_annual = f"""
    ### 📈 通期経営トレンド分析 ({annual_ctx['period']}) - Powered by Gemini 3 Pro
    
    ---
    
    #### 📊 通期財務サマリー
    
    | 指標 | 値 | 前年比 |
    |------|------|--------|
    | 累計売上高 | ¥{annual_ctx['sales']:,.0f} | - |
    | 累計粗利益 | ¥{annual_ctx['gp']:,.0f} | - |
    | 営業利益率 | {op_rate:.1%} | - |
    | 粗利率 | {annual_ctx['gp_rate']:.1%} | - |
    
    ---
    
    #### 🔍 通期概況と成長の質
    
    年度累計売上高は **¥{annual_ctx['sales']:,.0f}**、営業利益率は **{op_rate:.1%}** をマーク。
    
    **規模の経済性分析**:
    - 事業規模の拡大に伴い、販管費（SG&A）の効率性が問われる局面に入っています。
    - 売上の伸び以上に固定費が膨らんでいないか、月別推移から「筋肉質な経営」への移行度を確認すべきです。
    
    **セグメント別視点**:
    - デザイン事業: 高付加価値・高粗利率だがスケーラビリティに課題
    - EC事業: スケールメリットがあるが粗利率は低め
    
    ---
    
    #### 🚨 リスクと機会
    
    **リスク要因**:
    1. 売掛金の滞留によるキャッシュフロー悪化
    2. 在庫回転率の低下による運転資金圧迫
    3. 外注依存度の高さによるコストコントロールの難しさ
    
    **成長機会**:
    1. デザイン×ECのクロスセル（オリジナル商品開発）
    2. サブスクリプション型サービスの導入（定期収益化）
    3. フリーランス人材の活用による固定費の変動費化
    
    ---
    
    #### 💡 戦略提言：価値最大化への道筋
    
    キャッシュフローマネジメントの観点から、売掛金の滞留リスクや在庫の回転率を再点検してください。
    
    現在は外部環境の変化に強い財務基盤を構築できていますが、これを維持しつつ、デザイン事業の高い付加価値をEC事業のスケールメリットにどう波及させるかが、年度末に向けた最重要課題です。
    """
    st.markdown(f'<div class="ai-analysis">{report_annual.strip().replace("</div>", "")}</div>', unsafe_allow_html=True)

# --- Advisor Chat ---
st.markdown("---")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Show previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("財務について質問（例：粗利率を改善するには？、なぜ販管費が高いの？）"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Build financial context from actual data
        context_data = f"""
【現在の財務データ】
- 対象期間: {monthly_ctx['period']}
- 売上高: ¥{sales:,.0f}
- 粗利益: ¥{gp:,.0f}
- 粗利率: {monthly_ctx['gp_rate']:.1%}
- 販管費: ¥{sga_est:,.0f}
- 販管費率: {sga_rate:.1%}
- 営業利益: ¥{op:,.0f}
- 営業利益率: {op_rate:.1%}
- 流動比率: {monthly_ctx['cur_ratio']:.1f}%
- 自己資本比率: {monthly_ctx['equity_ratio']:.1f}%
- 通期累計売上: ¥{annual_ctx['sales']:,.0f}
- 通期粗利率: {annual_ctx['gp_rate']:.1%}
"""
        
        system_prompt = """あなたは優秀な経営コンサルタントです。
提供された財務データを基に、ユーザーの質問に対して具体的かつ実用的なアドバイスを提供してください。

ルール:
1. 必ず提供された実際の数値データを引用して回答する
2. 質問の意図を正確に捕らえ、その質問に直接答える
3. 抽象的なアドバイスではなく、具体的なアクションを提示
4. 業界平均などの未検証の情報は使わない
5. 簡潔に、でも十分な深さで回答
6. 回答は日本語で行う
"""
        
        try:
            if GEMINI_API_KEY:
                # Show loading spinner while waiting for AI response
                with st.spinner("🤔 分析中..."):
                    # Use actual Gemini API
                    model = genai.GenerativeModel('gemini-3-flash-preview')
                    full_prompt = f"{system_prompt}\n\n{context_data}\n\nユーザーの質問: {prompt}"
                    gemini_response = model.generate_content(full_prompt)
                    response = gemini_response.text
            else:
                # Fallback: Generate contextual response based on question keywords
                with st.spinner("🤔 分析中..."):
                    response = generate_contextual_response(prompt, monthly_ctx, annual_ctx, sales, gp, op, sga_est, sga_rate, op_rate)
        except Exception as e:
            response = f"エラーが発生しました: {str(e)}\n\n代わりに、詳細はエグゼクティブ・サマリーをご参照ください。"
        
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})




st.markdown("##### 財務指標ハイライト")
hcol1, hcol2, hcol3 = st.columns(3)
with hcol1: st.metric("粗利率 (累計)", f"{annual_ctx['gp_rate']:.1%}")
with hcol2: st.metric("流動比率", f"{monthly_ctx['cur_ratio']:.1f}%")
with hcol3: st.metric("自己資本比率", f"{monthly_ctx['equity_ratio']:.1f}%")

# --- 3. Segment Tiles ---
st.markdown("---")
st.markdown("### 📈 各セグメントの状況")
sc1, sc2 = st.columns(2)
with sc1:
    st.markdown("#### 🎨 デザイン事業")
    st1, st2 = st.columns(2)
    with st1: display_gecko_card("デザイン売上", ms_design, ds_design)
    with st2:    display_gecko_card("デザイン粗利", mg_design, 0)
    
    # --- Trend Chart for Design ---
    d_trend = fy_df[(fy_df["Item"].isin(DESIGN_SALES_ITEMS))].copy()
    d_trend = d_trend.groupby(["Month", "FiscalMonth"])[data_col].sum().reset_index()
    
    # Ensure all 12 months exist for Trend
    all_months = pd.DataFrame({"FiscalMonth": range(1, 13)})
    all_months["Month"] = all_months["FiscalMonth"].apply(lambda x: x + 3 if x <= 9 else x - 9)
    # Ensure types match for merge (int)
    d_trend["Month"] = d_trend["Month"].astype(int)
    
    # Merge ONLY on Month to be safe, then sort by FiscalMonth
    d_trend = pd.merge(all_months, d_trend, on="Month", how="left").fillna(0)
    # Re-calculate FiscalMonth_y if strictly needed or just use FiscalMonth_x from all_months
    if "FiscalMonth_y" in d_trend.columns:
        d_trend = d_trend.drop(columns=["FiscalMonth_y"])
    d_trend = d_trend.rename(columns={"FiscalMonth_x": "FiscalMonth"})

    c = alt.Chart(d_trend).mark_area(opacity=0.3, color='#4dabf7').encode(
        x=alt.X('Month:O', title=None, sort=alt.SortField("FiscalMonth"), axis=alt.Axis(labelAngle=0, labelColor='#909296')),
        y=alt.Y(f'{data_col}:Q', title=None, axis=alt.Axis(labelColor='#909296')), tooltip=['Month', data_col]
    ).properties(height=180)
    st.altair_chart(c, use_container_width=True)
with sc2:
    st.markdown("#### 🛒 EC事業")
    st1, st2 = st.columns(2)
    with st1: display_gecko_card("EC売上", ms_ec, ds_ec)
    with st2:    display_gecko_card("EC粗利", mg_ec, 0)
    
    # --- Trend Chart for EC ---
    e_trend = fy_df[(fy_df["Item"].isin(EC_SALES_ITEMS))].copy()
    e_trend = e_trend.groupby(["Month", "FiscalMonth"])[data_col].sum().reset_index()
    
    # Ensure types match for merge (int)
    e_trend["Month"] = e_trend["Month"].astype(int)

    # Merge ONLY on Month
    e_trend = pd.merge(all_months, e_trend, on="Month", how="left").fillna(0)
    if "FiscalMonth_y" in e_trend.columns:
        e_trend = e_trend.drop(columns=["FiscalMonth_y"])
    e_trend = e_trend.rename(columns={"FiscalMonth_x": "FiscalMonth"})
    
    c = alt.Chart(e_trend).mark_area(opacity=0.3, color='#51cf66').encode(
        x=alt.X('Month:O', title=None, sort=alt.SortField("FiscalMonth"), axis=alt.Axis(labelAngle=0, labelColor='#909296')),
        y=alt.Y(f'{data_col}:Q', title=None, axis=alt.Axis(labelColor='#909296')), tooltip=['Month', data_col]
    ).properties(height=180)
    st.altair_chart(c, use_container_width=True)

# --- 4. Detailed Analysis ---
st.markdown("---")
st.markdown("### 🔍 科目別詳細分析 (損益計算書)")
dcol1, dcol2 = st.columns(2)
with dcol1:
    st.markdown("##### 📦 売上原価 (COGS)")
    cogs_options = ["売上原価合計", "デザイン事業原価合計", "EC事業原価合計"] + [i for i in DESIGN_COST_ITEMS + EC_COST_ITEMS if i in df["Item"].unique()]
    sel_c_item = st.selectbox("分析項目を選択", cogs_options, key="cogs_select")
    
    if sel_c_item == "売上原価合計":
        p_df = fy_df[(fy_df["Item"].isin(TOTAL_COST_ITEMS))].groupby("Month").agg({data_col:"sum", prev_col:"sum"}).reset_index()
    elif sel_c_item == "デザイン事業原価合計":
        p_df = fy_df[(fy_df["Item"].isin(DESIGN_COST_ITEMS))].groupby("Month").agg({data_col:"sum", prev_col:"sum"}).reset_index()
    elif sel_c_item == "EC事業原価合計":
        p_df = fy_df[(fy_df["Item"].isin(EC_COST_ITEMS))].groupby("Month").agg({data_col:"sum", prev_col:"sum"}).reset_index()
    else:
        p_df = fy_df[(fy_df["Item"] == sel_c_item)][["Month", data_col, prev_col]]
    
    # Fix missing months in bar chart
    p_df = pd.merge(all_months, p_df, on="Month", how="left").fillna(0)
    
    if not p_df.empty:
        # Display latest value
        row_now = p_df[p_df["Month"] == latest_m]
        cur_v = row_now[data_col].values[0] if not row_now.empty else 0
        st.markdown(f"<div style='font-size: 1.2rem; font-weight: 700; color: var(--accent); margin-bottom: 10px;'>{latest_m}月度金額: ¥{cur_v:,.0f}</div>", unsafe_allow_html=True)
        
        p_df_melt = p_df.melt(id_vars='Month', value_vars=[data_col, prev_col], var_name='Period', value_name='Amount')
        p_df_melt['Period'] = p_df_melt['Period'].replace({data_col: '当期', prev_col: '前期'})
        # Add sort key
        p_df_melt["FiscalMonth"] = p_df_melt["Month"].apply(lambda x: x - 3 if x >= 4 else x + 9)
        
        chart_c = alt.Chart(p_df_melt).mark_bar().encode(
            x=alt.X('Period:N', title=None, axis=alt.Axis(labels=False, ticks=False)),
            y=alt.Y('Amount:Q', title=f'金額 ({view_mode})'),
            color=alt.Color('Period:N', scale=alt.Scale(domain=['当期', '前期'], range=['#5c6bc0', '#373a40'])),
            column=alt.Column('Month:O', title=None, header=alt.Header(labelOrient='bottom', labelAngle=0, labelColor='#909296'), sort=alt.SortField("FiscalMonth")),
            tooltip=['Month', 'Period', 'Amount']
        ).properties(height=250, width=40)
        st.altair_chart(chart_c, use_container_width=False)

    # breakdown chart
    st.markdown("---")
    st.markdown(f"###### {sel_fy}年度 月別科目内訳 (原価)")
    sel_month_br = st.selectbox("年月を選択", sorted(fy_df["Month"].unique()), key="cogs_br_month", index=len(fy_df["Month"].unique())-1)
    br_df = fy_df[(fy_df["Month"] == sel_month_br) & (fy_df["Item"].isin(TOTAL_COST_ITEMS))]
    # Aggregate duplicates to prevent chart layout issues
    br_df = br_df.groupby("Item", as_index=False)[data_col].sum()
    # Relax filter to show non-zero or negative values if valid (e.g. adjustments)
    br_df = br_df[br_df[data_col] != 0].sort_values(data_col, ascending=False)
    
    if not br_df.empty:
        # Dynamic height: 35px per item for better readability, minimum 200px
        chart_height = max(200, len(br_df) * 35)
        c_br = alt.Chart(br_df).mark_bar(color='#5c6bc0').encode(
            x=alt.X(f'{data_col}:Q', title='金額'),
            y=alt.Y('Item:N', sort='-x', title=None, axis=alt.Axis(labelLimit=200)),
            tooltip=['Item', data_col]
        ).properties(height=chart_height)
        st.altair_chart(c_br, use_container_width=True)

with dcol2:
    st.markdown("##### 💼 販管費 (SG&A)")
    actual_sga = [i for i in SGA_ITEMS if i in df["Item"].unique()]
    sga_options = ["販管費合計"] + actual_sga
    sel_s_item = st.selectbox("分析項目を選択", sga_options, key="sga_select")
    
    if sel_s_item == "販管費合計":
        p_df_s = fy_df[(fy_df["Item"].isin(SGA_ITEMS))].groupby("Month").agg({data_col:"sum", prev_col:"sum"}).reset_index()
    else:
        p_df_s = fy_df[(fy_df["Item"] == sel_s_item)][["Month", data_col, prev_col]]
    
    # Fix missing months in bar chart
    p_df_s = pd.merge(all_months, p_df_s, on="Month", how="left").fillna(0)
    
    if not p_df_s.empty:
        # Display latest value
        row_now_s = p_df_s[p_df_s["Month"] == latest_m]
        cur_v_s = row_now_s[data_col].values[0] if not row_now_s.empty else 0
        st.markdown(f"<div style='font-size: 1.2rem; font-weight: 700; color: #ff7043; margin-bottom: 10px;'>{latest_m}月度金額: ¥{cur_v_s:,.0f}</div>", unsafe_allow_html=True)
        
        p_df_s_melt = p_df_s.melt(id_vars='Month', value_vars=[data_col, prev_col], var_name='Period', value_name='Amount')
        p_df_s_melt['Period'] = p_df_s_melt['Period'].replace({data_col: '当期', prev_col: '前期'})
        # Add sort key
        p_df_s_melt["FiscalMonth"] = p_df_s_melt["Month"].apply(lambda x: x - 3 if x >= 4 else x + 9)
        
        chart_s = alt.Chart(p_df_s_melt).mark_bar().encode(
            x=alt.X('Period:N', title=None, axis=alt.Axis(labels=False, ticks=False)),
            y=alt.Y('Amount:Q', title=f'金額 ({view_mode})'),
            color=alt.Color('Period:N', scale=alt.Scale(domain=['当期', '前期'], range=['#ff7043', '#373a40'])),
            column=alt.Column('Month:O', title=None, header=alt.Header(labelOrient='bottom', labelAngle=0, labelColor='#909296'), sort=alt.SortField("FiscalMonth")),
            tooltip=['Month', 'Period', 'Amount']
        ).properties(height=250, width=40)
        st.altair_chart(chart_s, use_container_width=False)

    # breakdown chart
    st.markdown("---")
    st.markdown(f"###### {sel_fy}年度 月別科目内訳 (販管費)")
    sel_month_br_s = st.selectbox("年月を選択", sorted(fy_df["Month"].unique()), key="sga_br_month", index=len(fy_df["Month"].unique())-1)
    br_df_s = fy_df[(fy_df["Month"] == sel_month_br_s) & (fy_df["Item"].isin(SGA_ITEMS))]
    # Aggregate duplicates
    br_df_s = br_df_s.groupby("Item", as_index=False)[data_col].sum()
    # Relax filter
    br_df_s = br_df_s[br_df_s[data_col] != 0].sort_values(data_col, ascending=False)
    
    if not br_df_s.empty:
        # Dynamic height: 35px per item for better readability, minimum 200px
        chart_height_s = max(200, len(br_df_s) * 35)
        s_br = alt.Chart(br_df_s).mark_bar(color='#ff7043').encode(
            x=alt.X(f'{data_col}:Q', title='金額'),
            y=alt.Y('Item:N', sort='-x', title=None, axis=alt.Axis(labelLimit=200)),
            tooltip=['Item', data_col]
        ).properties(height=chart_height_s)
        st.altair_chart(s_br, use_container_width=True)

# --- 5. Data Table ---
expand_label = "全データ詳細（試算表データ）"
with st.expander(expand_label):
    st.dataframe(df.sort_values(["Year", "Month", "Item"], ascending=[False, False, True]))
