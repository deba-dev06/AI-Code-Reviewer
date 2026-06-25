"""
streamlit_app.py -- Streamlit Frontend for AI Code Reviewer
Premium-looking code editor with analysis result display.
"""

import streamlit as st
import requests
import json

# ---------------------------------------------
#  CONFIG
# ---------------------------------------------

FLASK_API = "http://localhost:5000/analyze"

st.set_page_config(
    page_title="AI Code Reviewer",
    page_icon="</>",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------
#  CUSTOM CSS
# ---------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* -- Global -- */
    .stApp {
        background: linear-gradient(160deg, #0f0c29 0%, #1a1a3e 40%, #24243e 100%);
        font-family: 'Inter', sans-serif;
    }
    .block-container { padding-top: 2rem; max-width: 1200px; }

    /* -- Header -- */
    .hero-title {
        text-align: center;
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        text-align: center;
        color: #a0aec0;
        font-size: 1.1rem;
        font-weight: 300;
        margin-bottom: 2rem;
    }

    /* -- Text Area (code editor) -- */
    .stTextArea textarea {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 14px !important;
        background: #1e1e2e !important;
        color: #cdd6f4 !important;
        border: 1px solid #45475a !important;
        border-radius: 12px !important;
        padding: 16px !important;
        line-height: 1.6 !important;
    }
    .stTextArea textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2) !important;
    }

    /* -- Button -- */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.7rem 2.5rem !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        letter-spacing: 0.3px;
        transition: all 0.3s ease !important;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4) !important;
    }

    /* -- Metric Cards -- */
    .metric-card {
        background: rgba(255,255,255,0.04);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        transition: transform 0.2s ease;
    }
    .metric-card:hover { transform: translateY(-4px); }
    .metric-label {
        color: #a0aec0;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
    }
    .metric-value.time { color: #667eea; }
    .metric-value.space { color: #764ba2; }
    .metric-value.errors-zero { color: #48bb78; }
    .metric-value.errors-some { color: #fc8181; }

    /* -- Optimality Badge -- */
    .optimality-card {
        background: rgba(255,255,255,0.04);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
    }
    .optimality-badge {
        display: inline-block;
        font-size: 1.4rem;
        font-weight: 700;
        padding: 0.5rem 1.5rem;
        border-radius: 50px;
        margin-top: 0.3rem;
    }
    .badge-optimal { background: rgba(72,187,120,0.15); color: #48bb78; border: 1px solid rgba(72,187,120,0.3); }
    .badge-near    { background: rgba(102,126,234,0.15); color: #667eea; border: 1px solid rgba(102,126,234,0.3); }
    .badge-moderate{ background: rgba(236,201,75,0.15); color: #ecc94b; border: 1px solid rgba(236,201,75,0.3); }
    .badge-improve { background: rgba(237,137,54,0.15); color: #ed8936; border: 1px solid rgba(237,137,54,0.3); }
    .badge-brute   { background: rgba(252,129,129,0.15); color: #fc8181; border: 1px solid rgba(252,129,129,0.3); }

    /* -- Details Box -- */
    .details-box {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        color: #cbd5e0;
        font-size: 0.95rem;
        line-height: 1.7;
        margin-top: 1rem;
    }

    /* -- Error Table -- */
    .error-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        border-radius: 12px;
        overflow: hidden;
        margin-top: 1rem;
    }
    .error-table th {
        background: rgba(252,129,129,0.12);
        color: #fc8181;
        padding: 12px 16px;
        text-align: left;
        font-weight: 600;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .error-table td {
        padding: 10px 16px;
        border-bottom: 1px solid rgba(255,255,255,0.04);
        color: #e2e8f0;
        font-size: 0.9rem;
    }
    .error-table tr:last-child td { border-bottom: none; }
    .error-table .line-num {
        font-family: 'JetBrains Mono', monospace;
        color: #fc8181;
        font-weight: 600;
        width: 80px;
    }

    /* -- Success banner -- */
    .success-banner {
        background: rgba(72,187,120,0.08);
        border: 1px solid rgba(72,187,120,0.2);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        color: #48bb78;
        font-size: 1.1rem;
        font-weight: 500;
    }

    /* -- Section Title -- */
    .section-title {
        color: #e2e8f0;
        font-size: 1.3rem;
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid rgba(102,126,234,0.3);
    }

    /* -- Hide Streamlit branding -- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------
#  HEADER
# ---------------------------------------------

st.markdown('<h1 class="hero-title">&lt;/&gt; AI Code Reviewer</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Paste your Python code below -- get instant complexity analysis, optimality rating, and error detection</p>', unsafe_allow_html=True)

# ---------------------------------------------
#  CODE INPUT
# ---------------------------------------------

sample_code = """def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
"""

code_input = st.text_area(
    "Paste your Python code here",
    value=sample_code.strip(),
    height=320,
    placeholder="# Write or paste your Python code here...",
    key="code_editor"
)

col_btn_l, col_btn, col_btn_r = st.columns([1, 1, 1])
with col_btn:
    analyze_clicked = st.button("Analyze Code", use_container_width=True)

# ---------------------------------------------
#  ANALYSIS
# ---------------------------------------------

if analyze_clicked and code_input.strip():
    with st.spinner("Analyzing your code..."):
        try:
            response = requests.post(
                FLASK_API,
                json={"code": code_input, "language": "python"},
                timeout=15
            )
            result = response.json()
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the Flask API. Make sure app.py is running on port 5000.")
            st.code("python app.py", language="bash")
            st.stop()
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

    if "error" in result:
        st.error(f"{result['error']}")
        st.stop()

    # If there are errors, only display the error report. Else display complexity analysis and optimality rating.
    if result['error_count'] > 0:
        st.markdown('<div class="section-title">Error Report</div>', unsafe_allow_html=True)
        
        # Display the number of errors
        st.markdown(f"""
        <div class="metric-card" style="margin-bottom: 1.5rem;">
            <div class="metric-label">Errors Found</div>
            <div class="metric-value errors-some">{result['error_count']}</div>
        </div>
        """, unsafe_allow_html=True)

        error_rows = ""
        for err in result["errors"]:
            error_rows += f"""
            <tr>
                <td class="line-num">Line {err['line']}</td>
                <td>{err['message']}</td>
            </tr>
            """
        st.markdown(f"""
        <table class="error-table">
            <thead>
                <tr>
                    <th>Line</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                {error_rows}
            </tbody>
        </table>
        """, unsafe_allow_html=True)

    else:
        # -- Metric Cards --
        st.markdown('<div class="section-title">Analysis Results</div>', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Time Complexity</div>
                <div class="metric-value time">{result['time_complexity']}</div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Space Complexity</div>
                <div class="metric-value space">{result['space_complexity']}</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Errors Found</div>
                <div class="metric-value errors-zero">0</div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Lines</div>
                <div class="metric-value" style="color: #a78bfa;">{result['total_lines']}</div>
            </div>
            """, unsafe_allow_html=True)

        # -- Optimality --
        st.markdown('<div class="section-title">Optimality Rating</div>', unsafe_allow_html=True)

        opt = result["optimality"]
        label = opt["label"]

        if "OPTIMAL" in label and "NEAR" not in label:
            badge_class = "badge-optimal"
        elif "NEAR" in label:
            badge_class = "badge-near"
        elif "MODERATE" in label:
            badge_class = "badge-moderate"
        elif "IMPROVED" in label:
            badge_class = "badge-improve"
        else:
            badge_class = "badge-brute"

        st.markdown(f"""
        <div class="optimality-card">
            <div class="optimality-badge {badge_class}">{label}</div>
            <div style="color: #a0aec0; margin-top: 0.8rem; font-size: 0.95rem;">{opt['description']}</div>
        </div>
        """, unsafe_allow_html=True)

        # -- Details --
        if result.get("complexity_details"):
            st.markdown(f"""
            <div class="details-box">
                <strong>Details:</strong> {result['complexity_details']}
            </div>
            """, unsafe_allow_html=True)

        # -- Errors (Clean State) --
        st.markdown('<div class="section-title">Error Report</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="success-banner">
            No errors detected -- your code looks clean!
        </div>
        """, unsafe_allow_html=True)

    # -- Raw JSON --
    with st.expander("Raw JSON Response"):
        st.json(result)

elif analyze_clicked:
    st.warning("Please paste some code before clicking Analyze.")

# ---------------------------------------------
#  FOOTER
# ---------------------------------------------

st.markdown("---")
st.markdown(
    '<p style="text-align:center; color:#4a5568; font-size:0.85rem;">'
    'AI Code Reviewer | Built with Flask & Streamlit | Powered by AST Analysis'
    '</p>',
    unsafe_allow_html=True
)
