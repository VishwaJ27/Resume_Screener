import os
import sys
import tempfile
import streamlit as st
import pandas as pd

sys.path.append(".")
from src.parser    import parse_resume
from src.extractor import extract_all
from src.matcher   import match_multiple_resumes
from src.skill_gap import run_gap_analysis_all


#  Page Config

st.set_page_config(
    page_title = "Resume Screener",
    layout     = "wide",
    initial_sidebar_state = "expanded"
)


#  Global Styles

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

[data-testid="stAppViewContainer"] { background: #0d0f12; color: #e2e8f0; }
[data-testid="stSidebar"]          { background: #111318; border-right: 1px solid #1e2230; }

#MainMenu, footer, header { visibility: hidden; }

.page-header   { padding: 2.5rem 0 1.5rem; border-bottom: 1px solid #1e2230; margin-bottom: 2rem; }
.page-title    { font-size: 1.75rem; font-weight: 600; letter-spacing: -0.02em; color: #f1f5f9; margin: 0; }
.page-subtitle { font-size: 0.875rem; color: #64748b; margin-top: 0.35rem; }

.sidebar-label  { font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
                  letter-spacing: 0.1em; color: #475569; margin-bottom: 0.4rem; }
.section-label  { font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
                  letter-spacing: 0.12em; color: #475569; padding-bottom: 0.5rem;
                  border-bottom: 1px solid #1e2230; margin: 2rem 0 1rem; }

.stat-card  { background: #13161d; border: 1px solid #1e2230; border-radius: 8px;
              padding: 1.1rem 1.25rem; }
.stat-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em;
              color: #475569; margin-bottom: 0.4rem; }
.stat-value { font-size: 1.5rem; font-weight: 600; color: #f1f5f9;
              font-family: 'DM Mono', monospace; }
.stat-value.high   { color: #34d399; }
.stat-value.medium { color: #fbbf24; }
.stat-value.low    { color: #f87171; }

.tag         { font-size: 0.72rem; padding: 0.2rem 0.65rem; border-radius: 4px;
               font-family: 'DM Mono', monospace; }
.tag-matched { background: #0a2a1a; color: #4ade80; border: 1px solid #14532d; }
.tag-missing { background: #2a0f0f; color: #fca5a5; border: 1px solid #7f1d1d; }
.tag-extra   { background: #0f1e35; color: #93c5fd; border: 1px solid #1e3a5f; }

.tag-row     { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem; }
.thin-hr     { border: none; border-top: 1px solid #1e2230; margin: 1.25rem 0; }

.feedback-box { background: #0d1117; border-left: 3px solid #2e3650;
                border-radius: 0 6px 6px 0; padding: 0.9rem 1.1rem;
                font-size: 0.85rem; color: #94a3b8; line-height: 1.8;
                margin-top: 0.75rem; white-space: pre-line; }

[data-testid="stButton"] > button {
    background: #1a3a5c; color: #e2e8f0; border: 1px solid #2e5f8a;
    border-radius: 7px; font-family: 'DM Sans', sans-serif; font-weight: 500;
    font-size: 0.875rem; width: 100%; padding: 0.55rem 1.25rem;
    transition: background 0.2s;
}
[data-testid="stButton"] > button:hover { background: #1e4a73; border-color: #3b7ab5; }

[data-testid="stFileUploader"] { background: #13161d; border: 1px dashed #2e3650; border-radius: 8px; }

textarea {
    background: #13161d !important; border: 1px solid #1e2230 !important;
    color: #cbd5e1 !important; font-family: 'DM Mono', monospace !important;
    font-size: 0.8rem !important; border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)


#  Helpers

def score_tier(pct: float) -> str:
    if pct >= 70: return "high"
    if pct >= 45: return "medium"
    return "low"

def render_tags(skills: list, css_class: str):
    if not skills:
        st.markdown('<span style="color:#475569;font-size:0.8rem;">None found</span>',
                    unsafe_allow_html=True)
        return
    tags = "".join([f'<span class="tag {css_class}">{s}</span>' for s in skills])
    st.markdown(f'<div class="tag-row">{tags}</div>', unsafe_allow_html=True)


#  Sidebar

with st.sidebar:
    st.markdown('<p class="sidebar-label">Resumes</p>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        " ", type=["pdf", "docx"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="sidebar-label">Job Description</p>', unsafe_allow_html=True)
    jd_text = st.text_area(
        " ", height=280,
        placeholder="Paste the full job description here...",
        label_visibility="collapsed"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("Run Analysis")

    if uploaded_files:
        st.markdown(
            f'<p style="font-size:0.75rem;color:#475569;margin-top:0.5rem;">'
            f'{len(uploaded_files)} file(s) ready</p>',
            unsafe_allow_html=True
        )


#  Page Header

st.markdown("""
<div class="page-header">
    <p class="page-title">Resume Screener</p>
    <p class="page-subtitle">Semantic matching and skill gap analysis for candidate screening</p>
</div>
""", unsafe_allow_html=True)


#  Empty State

if not run_btn:
    st.markdown("""
    <div style="color:#475569; font-size:0.9rem; line-height:2.2; margin-top:2rem;">
        <p style="color:#64748b; font-size:0.72rem; text-transform:uppercase;
                  letter-spacing:0.1em; margin-bottom:1rem;">How it works</p>
        <p>1 &nbsp;&nbsp; Upload one or more resumes as PDF or DOCX from the sidebar.</p>
        <p>2 &nbsp;&nbsp; Paste the full job description into the text area.</p>
        <p>3 &nbsp;&nbsp; Click <strong style="color:#94a3b8;">Run Analysis</strong>
                          to rank candidates and view their skill gap reports.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


#  Validation

if not uploaded_files:
    st.error("Upload at least one resume before running.")
    st.stop()

if not jd_text.strip():
    st.error("Paste a job description before running.")
    st.stop()


#  Pipeline

with st.spinner("Parsing resumes..."):
    parsed_list    = []
    extracted_list = []

    for uploaded in uploaded_files:
        suffix = os.path.splitext(uploaded.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name

        parsed = parse_resume(tmp_path)
        parsed["filename"] = uploaded.name
        os.unlink(tmp_path)

        if parsed.get("error"):
            st.warning(f"Could not parse {uploaded.name}: {parsed['error']}")
            continue
        parsed_list.append(parsed)

if not parsed_list:
    st.error("No resumes could be parsed. Check file formats and try again.")
    st.stop()

with st.spinner("Extracting skills and experience..."):
    for parsed in parsed_list:
        info             = extract_all(parsed["text"])
        info["text"]     = parsed["text"]
        info["filename"] = parsed["filename"]
        extracted_list.append(info)

with st.spinner("Running semantic matching..."):
    ranked = match_multiple_resumes(extracted_list, jd_text)

with st.spinner("Analysing skill gaps..."):
    reports = run_gap_analysis_all(ranked, jd_text)


#  Summary Stats

top       = reports[0]
avg_score = round(sum(r["match_score"] for r in reports) / len(reports), 1)
top_tier  = score_tier(top["match_score"])

st.markdown('<p class="section-label">Summary</p>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)

for col, label, value, tier in [
    (c1, "Candidates",        str(len(reports)),                    ""),
    (c2, "Top Match",         f"{top['match_score']}%",             top_tier),
    (c3, "Average Score",     f"{avg_score}%",                      ""),
    (c4, "JD Skills Detected",str(len(reports[0].get("jd_skills",[]))),""),
]:
    with col:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">{label}</div>
            <div class="stat-value {tier}">{value}</div>
        </div>""", unsafe_allow_html=True)


#  Ranking Table

st.markdown('<p class="section-label">Ranking</p>', unsafe_allow_html=True)

table_rows = []
for r in reports:
    verdict = "Strong" if r["match_score"] >= 70 else ("Moderate" if r["match_score"] >= 45 else "Weak")
    table_rows.append({
        "Rank":           r["rank"],
        "Name":           r["name"],
        "Email":          r["email"],
        "Match Score":    f"{r['match_score']}%",
        "Skill Coverage": f"{r['coverage']}%",
        "Missing Skills": r["missing_count"],
        "Verdict":        verdict
    })

st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)


#  Candidate Detail Cards

st.markdown('<p class="section-label">Candidate Reports</p>', unsafe_allow_html=True)

for r in reports:
    tier = score_tier(r["match_score"])

    with st.expander(f"{r['rank']}.  {r['name']}  —  {r['match_score']}%", expanded=(r["rank"] == 1)):

        col_a, col_b, col_c = st.columns([1, 1, 2])

        with col_a:
            st.markdown(f"""
            <div class="stat-card" style="margin-bottom:0.75rem;">
                <div class="stat-label">Match Score</div>
                <div class="stat-value {tier}">{r['match_score']}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Skill Coverage</div>
                <div class="stat-value">{r['coverage']}%</div>
            </div>""", unsafe_allow_html=True)

        with col_b:
            st.markdown(f"""
            <div class="stat-card" style="margin-bottom:0.75rem;">
                <div class="stat-label">Matched Skills</div>
                <div class="stat-value high">{r['matched_count']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Missing Skills</div>
                <div class="stat-value low">{r['missing_count']}</div>
            </div>""", unsafe_allow_html=True)

        with col_c:
            st.markdown(f"""
            <div class="stat-card" style="height:100%;box-sizing:border-box;">
                <div class="stat-label">Contact</div>
                <div style="color:#94a3b8;font-size:0.85rem;font-family:'DM Mono',monospace;margin-top:0.35rem;">
                    {r['email']}
                </div>
                <div style="color:#475569;font-size:0.8rem;margin-top:0.6rem;">
                    Experience: {r.get('experience_years', 'Not mentioned')}
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<hr class="thin-hr">', unsafe_allow_html=True)

        t1, t2, t3 = st.columns(3)

        for col, heading, skills, css in [
            (t1, "Matched Skills", r["matched_skills"],    "tag-matched"),
            (t2, "Missing Skills", r["missing_skills"],    "tag-missing"),
            (t3, "Bonus Skills",   r["extra_skills"][:8],  "tag-extra"),
        ]:
            with col:
                st.markdown(
                    f'<p style="font-size:0.72rem;text-transform:uppercase;'
                    f'letter-spacing:0.1em;color:#475569;">{heading}</p>',
                    unsafe_allow_html=True
                )
                render_tags(skills, css)

        st.markdown(
            f'<div class="feedback-box">{r["feedback"]}</div>',
            unsafe_allow_html=True
        )