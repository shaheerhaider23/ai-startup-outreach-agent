import streamlit as st
import sys
import os
import asyncio

# Add both root and backend/ so all import styles work on Streamlit Cloud
_root = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.join(_root, "backend")
if _root not in sys.path:
    sys.path.insert(0, _root)
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from backend.app.agents.icp_agent import analyze_icp
from backend.app.agents.prospect_agent import find_prospects
from backend.app.agents.email_agent import generate_email_draft

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Outreach Agent Studio",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
/* Import fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Hide default streamlit header */
#MainMenu, footer, header { visibility: hidden; }

/* Hero banner */
.hero {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 16px;
    padding: 40px 48px;
    margin-bottom: 32px;
    border: 1px solid rgba(255,255,255,0.08);
}
.hero h1 {
    font-size: 2.4rem;
    font-weight: 700;
    color: #ffffff;
    margin: 0 0 8px 0;
}
.hero p {
    font-size: 1.05rem;
    color: rgba(255,255,255,0.65);
    margin: 0;
}

/* Step badge */
.step-badge {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.4);
    border-radius: 50px;
    padding: 6px 16px;
    margin-bottom: 12px;
}
.step-badge .num {
    background: #6366f1;
    color: white;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 700;
}
.step-badge .label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #a5b4fc;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

/* Pill example buttons row */
.pill-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 16px;
}

/* Card */
.card {
    background: #1e1e2e;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 24px;
    margin-bottom: 16px;
}

/* ICP tag chips */
.chip {
    display: inline-block;
    background: rgba(99,102,241,0.18);
    color: #a5b4fc;
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.8rem;
    margin: 3px 3px 3px 0;
}
.chip-green {
    background: rgba(34,197,94,0.15);
    color: #86efac;
    border-color: rgba(34,197,94,0.3);
}
.chip-orange {
    background: rgba(249,115,22,0.15);
    color: #fdba74;
    border-color: rgba(249,115,22,0.3);
}

/* Prospect cards */
.prospect-card {
    background: linear-gradient(135deg, #1e1e2e, #16213e);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 10px;
    transition: border-color 0.2s;
}
.prospect-card:hover {
    border-color: rgba(99,102,241,0.6);
}
.prospect-card .company {
    font-size: 1.05rem;
    font-weight: 600;
    color: #e2e8f0;
}
.prospect-card .meta {
    font-size: 0.82rem;
    color: rgba(255,255,255,0.45);
    margin-top: 4px;
}
.score-badge {
    display: inline-block;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
}

/* Email card */
.email-card {
    background: #1a1a2e;
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 14px;
    padding: 28px;
}
.email-subject {
    font-size: 1.1rem;
    font-weight: 600;
    color: #c7d2fe;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}

/* Tone selector styled */
.tone-label {
    font-size: 0.85rem;
    font-weight: 500;
    color: rgba(255,255,255,0.6);
    margin-bottom: 6px;
}

/* Progress steps */
.progress-steps {
    display: flex;
    align-items: center;
    gap: 0;
    margin-bottom: 28px;
}
.ps-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    position: relative;
}
.ps-circle {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: rgba(255,255,255,0.08);
    border: 2px solid rgba(255,255,255,0.15);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    color: rgba(255,255,255,0.4);
    font-weight: 600;
    z-index: 1;
}
.ps-circle.active {
    background: #6366f1;
    border-color: #818cf8;
    color: white;
    box-shadow: 0 0 12px rgba(99,102,241,0.5);
}
.ps-circle.done {
    background: #22c55e;
    border-color: #4ade80;
    color: white;
}
.ps-label {
    font-size: 0.72rem;
    color: rgba(255,255,255,0.4);
    margin-top: 6px;
    text-align: center;
    font-weight: 500;
}
.ps-label.active { color: #a5b4fc; }
.ps-label.done   { color: #86efac; }
.ps-line {
    flex: 1;
    height: 2px;
    background: rgba(255,255,255,0.08);
    margin-top: -16px;
}
.ps-line.done { background: #22c55e; }

/* Override Streamlit button styles */
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.95rem;
    padding: 10px 28px;
    transition: opacity 0.2s, transform 0.1s;
}
div[data-testid="stButton"] > button:hover {
    opacity: 0.88;
    transform: translateY(-1px);
}

/* Divider */
.section-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.07);
    margin: 20px 0;
}
</style>
""", unsafe_allow_html=True)

# ── Session state init ─────────────────────────────────────────────
for key in ["input_idea", "icp", "leads", "idea", "email_draft", "selected_idx"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key in ("input_idea", "idea") else None

# ── Hero ───────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🚀 Outreach Agent Studio</h1>
    <p>Describe your startup idea · Discover perfect-fit prospects · Generate personalised outreach — in minutes.</p>
</div>
""", unsafe_allow_html=True)

# ── Progress tracker ───────────────────────────────────────────────
has_icp   = st.session_state.icp   is not None
has_leads = st.session_state.leads is not None
has_email = st.session_state.email_draft is not None

def _ps(step):
    if step == 1:
        done   = has_icp
        active = not done
    elif step == 2:
        done   = has_leads
        active = has_icp and not done
    else:
        done   = has_email
        active = has_leads and not done

    circle_cls = "done" if done else ("active" if active else "")
    label_cls  = circle_cls
    icon       = "✓" if done else str(step)
    return circle_cls, label_cls, icon

labels = ["Idea & ICP", "Prospects", "Email Draft"]
step_data = [_ps(i+1) for i in range(3)]

ps_html = '<div class="progress-steps">'
for i, (cc, lc, icon) in enumerate(step_data):
    ps_html += f'<div class="ps-item"><div class="ps-circle {cc}">{icon}</div><div class="ps-label {lc}">{labels[i]}</div></div>'
    if i < 2:
        line_cls = "done" if step_data[i][0] == "done" else ""
        ps_html += f'<div class="ps-line {line_cls}"></div>'
ps_html += '</div>'
st.markdown(ps_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# STEP 1 — Idea input
# ══════════════════════════════════════════════════════════════════
st.markdown('<div class="step-badge"><span class="num">1</span><span class="label">Describe Your Idea</span></div>', unsafe_allow_html=True)

examples = {
    "🦷 Dental AI":         "A smart scheduling automation tool for busy dental clinics that uses machine learning to fill cancellations via SMS.",
    "🏭 Manufacturing ERP": "AI predictive maintenance software that integrates with existing ERPs to help manufacturing companies reduce downtime.",
    "🌍 Global Payroll":    "A B2B platform that automates international compliance and multi-currency payroll for remote, distributed tech startups.",
    "🛒 E-commerce AI":     "An AI-powered product recommendation engine for small Shopify stores that increases average order value.",
    "🏥 Health Tech":       "A telehealth triage chatbot that helps clinics pre-screen patients before appointments to reduce no-shows.",
}

st.markdown("**Quick examples — click to load:**")
ex_cols = st.columns(len(examples))
for col, (label, text) in zip(ex_cols, examples.items()):
    if col.button(label, key=f"ex_{label}"):
        st.session_state.input_idea = text
        st.rerun()

idea = st.text_area(
    "Your startup idea",
    value=st.session_state.input_idea or "",
    placeholder="e.g. An AI tool that automates cold outreach for B2B SaaS startups…",
    height=110,
    label_visibility="collapsed",
)

char_count = len(idea.strip().split()) if idea.strip() else 0
st.caption(f"{'✅' if char_count >= 10 else '📝'} {char_count} words — {'good to go!' if char_count >= 10 else 'aim for at least 10 words for best results.'}")

btn_col, _ = st.columns([1, 3])
with btn_col:
    analyze_clicked = st.button("🔍 Analyze & Find Customers", use_container_width=True)

if analyze_clicked:
    if not idea.strip():
        st.error("Please enter a startup idea first.")
    elif char_count < 5:
        st.warning("Your idea is very short — add more detail for better results.")
    else:
        st.session_state.idea = idea
        st.session_state.email_draft = None

        prog = st.progress(0, text="🧠 Building your Ideal Customer Profile…")
        icp = asyncio.run(analyze_icp(idea))
        st.session_state.icp = icp
        prog.progress(50, text="🔍 Searching for perfect-fit prospects…")

        prospects = asyncio.run(find_prospects(idea, icp, 5))
        st.session_state.leads = prospects if isinstance(prospects, list) else prospects.get("leads", [])
        st.session_state.selected_idx = 0
        prog.progress(100, text="✅ Done!")
        st.rerun()

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# STEP 2 — ICP + Prospects
# ══════════════════════════════════════════════════════════════════
if has_icp:
    icp = st.session_state.icp

    st.markdown('<div class="step-badge"><span class="num">2</span><span class="label">Your ICP & Prospects</span></div>', unsafe_allow_html=True)

    left, right = st.columns([1, 1.4], gap="large")

    # ── Left: ICP card ────────────────────────────────────────────
    with left:
        st.markdown("#### 🎯 Ideal Customer Profile")
        st.info(icp.get("summary", ""))

        ind_html  = "".join(f'<span class="chip">{i}</span>' for i in icp.get("industries", []))
        title_html = "".join(f'<span class="chip chip-orange">{t}</span>' for t in icp.get("buyer_titles", []))
        pain_html  = "".join(f'<span class="chip chip-green">{p}</span>' for p in icp.get("pain_points", []))

        st.markdown(f"**🏢 Industries**<br>{ind_html}", unsafe_allow_html=True)
        st.markdown(f"**👔 Buyer Titles**<br>{title_html}", unsafe_allow_html=True)
        st.markdown(f"**⚡ Key Pain Points**<br>{pain_html}", unsafe_allow_html=True)

    # ── Right: Prospect list ──────────────────────────────────────
    with right:
        if has_leads and st.session_state.leads:
            leads = st.session_state.leads
            st.markdown("#### 🏆 Top Prospects Found")

            # Render clickable prospect cards
            for i, lead in enumerate(leads):
                score = lead.get("lead_score", "—")
                is_selected = (st.session_state.selected_idx == i)
                border = "border-color: #6366f1;" if is_selected else ""
                website = lead.get("website", "") or ""
                web_link = f'<a href="{website}" target="_blank" style="color:#818cf8;font-size:0.78rem;">🔗 {website[:40]}</a>' if website and website not in ("Needs verification", "demo_fallback", "") else ""

                card_html = f"""
                <div class="prospect-card" style="{border}">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                            <div class="company">{lead.get('company_name','Unknown')}</div>
                            <div class="meta">🏢 {lead.get('industry','—')} &nbsp;|&nbsp; ⚡ {lead.get('pain_point','—')[:60]}…</div>
                            <div style="margin-top:6px;">{web_link}</div>
                        </div>
                        <div><span class="score-badge">⭐ {score}</span></div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                if st.button(f"Select →", key=f"sel_{i}", use_container_width=True):
                    st.session_state.selected_idx = i
                    st.session_state.email_draft = None
                    st.rerun()

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# STEP 3 — Email Draft
# ══════════════════════════════════════════════════════════════════
if has_leads and st.session_state.leads:
    leads      = st.session_state.leads
    sel_idx    = st.session_state.selected_idx or 0
    sel_lead   = leads[sel_idx]

    st.markdown('<div class="step-badge"><span class="num">3</span><span class="label">Craft Your Outreach Email</span></div>', unsafe_allow_html=True)

    e1, e2, e3 = st.columns([2, 1, 1], gap="medium")

    with e1:
        st.markdown(f"**Selected company:** `{sel_lead.get('company_name','—')}`")
        why_fit = sel_lead.get("why_fit", "")
        if why_fit:
            st.success(f"✅ **Why it fits:** {why_fit}")

    with e2:
        tone = st.selectbox(
            "📣 Email Tone",
            ["professional", "casual", "bold"],
            index=0,
        )

    with e3:
        st.markdown("<div style='margin-top:27px;'>", unsafe_allow_html=True)
        draft_clicked = st.button("✉️ Generate Email", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if draft_clicked:
        with st.spinner(f"Drafting personalised email for {sel_lead['company_name']}…"):
            email_draft = asyncio.run(generate_email_draft(st.session_state.idea, sel_lead, tone))
            st.session_state.email_draft = email_draft
        st.rerun()

    if has_email:
        draft = st.session_state.email_draft
        st.markdown("<br>", unsafe_allow_html=True)

        d1, d2 = st.columns([1.6, 1], gap="large")

        with d1:
            st.markdown("#### ✉️ Your AI-Generated Email")
            subject = draft.get("subject", "")
            body    = draft.get("email_body", "")
            cta     = draft.get("cta", "")

            st.markdown(f"""
            <div class="email-card">
                <div class="email-subject">📌 Subject: {subject}</div>
            </div>
            """, unsafe_allow_html=True)

            st.text_area("Email Body (copy-paste ready)", body, height=220, label_visibility="visible")

            if cta:
                st.info(f"**📣 Call to Action:** {cta}")

        with d2:
            st.markdown("#### 📊 Email Intelligence")
            reason = draft.get("personalization_reason", "")
            compliance = draft.get("compliance_footer", "")

            if reason:
                st.success(f"**Why this works:**\n\n{reason}")
            if compliance:
                st.caption(f"🛡️ Compliance: {compliance}")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**🔄 Try another tone:**")
            retry_cols = st.columns(3)
            for col, t in zip(retry_cols, ["professional", "casual", "bold"]):
                if col.button(t.capitalize(), key=f"tone_{t}"):
                    with st.spinner("Regenerating…"):
                        st.session_state.email_draft = asyncio.run(
                            generate_email_draft(st.session_state.idea, sel_lead, t)
                        )
                    st.rerun()
