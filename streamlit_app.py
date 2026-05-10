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

st.set_page_config(page_title="Outreach Agent Studio", page_icon="🚀", layout="wide")

st.title("🚀 Outreach Agent Studio")
st.markdown("Turn raw ideas into targeted, compliant outreach in minutes.")

st.markdown("---")

if "input_idea" not in st.session_state:
    st.session_state.input_idea = ""

st.markdown("**Quick Examples:**")
cols = st.columns(3)
if cols[0].button("🦷 Dental AI"):
    st.session_state.input_idea = "A smart scheduling automation tool for busy dental clinics that uses machine learning to fill cancellations via SMS."
if cols[1].button("🏭 Manufacturing ERP"):
    st.session_state.input_idea = "AI predictive maintenance software that integrates with existing ERPs to help manufacturing companies reduce downtime."
if cols[2].button("🌍 Global Payroll"):
    st.session_state.input_idea = "A B2B platform that automates international compliance and multi-currency payroll for remote, distributed tech startups."

idea = st.text_area("Step 1: Describe your startup idea", value=st.session_state.input_idea, placeholder="e.g. An AI tool that automates cold outreach for B2B SaaS startups...", height=100)

if st.button("Analyze & Find Customers"):
    if not idea.strip():
        st.error("Please enter a startup idea.")
    else:
        with st.spinner("Analyzing startup idea and building ICP..."):
            icp = asyncio.run(analyze_icp(idea))
            st.session_state.icp = icp
            st.session_state.idea = idea
        
        with st.spinner("Searching for perfect-fit prospects..."):
            prospects = asyncio.run(find_prospects(idea, icp, 5))
            st.session_state.leads = prospects if isinstance(prospects, list) else prospects.get("leads", [])
            st.session_state.email_draft = None # Reset email draft on new search

col1, col2 = st.columns([1, 1.2])

with col1:
    if "icp" in st.session_state:
        st.subheader("Ideal Customer Profile")
        icp = st.session_state.icp
        st.info(f"**Summary:** {icp.get('summary', '')}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🏢 Industries**")
            for ind in icp.get('industries', []):
                st.caption(f"• {ind}")
        with c2:
            st.markdown("**👔 Buyer Titles**")
            for title in icp.get('buyer_titles', []):
                st.caption(f"• {title}")
                
        st.markdown("**⚡ Key Pain Points**")
        for pp in icp.get('pain_points', []):
            st.caption(f"- {pp}")

with col2:
    if "leads" in st.session_state and st.session_state.leads:
        st.subheader("Select a Prospect")
        leads = st.session_state.leads
        
        selected_idx = st.selectbox(
            "Target Company", 
            range(len(leads)), 
            format_func=lambda i: f"{leads[i]['company_name']} (Fit Score: {leads[i].get('lead_score', 'N/A')})"
        )
        selected_lead = leads[selected_idx]
        
        # ── Website display (clickable link or plain text) ───────
        website = selected_lead.get('website', '') or ''
        source_url = selected_lead.get('source_url', '') or ''
        source_type = selected_lead.get('source_type', 'web')
        
        if website and website not in ('Needs verification', 'demo_fallback', ''):
            st.markdown(f"**🌐 Website:** [{website}]({website})")
        elif website == 'Needs verification':
            st.markdown("**🌐 Website:** Needs verification")
        else:
            st.markdown("**🌐 Website:** N/A")
        
        st.markdown(f"**🏢 Industry:** {selected_lead.get('industry', 'N/A')}")
        st.markdown(f"**⚡ Pain Point:** {selected_lead.get('pain_point', 'N/A')}")
        
        why_fit = selected_lead.get('why_fit', '')
        if why_fit:
            st.markdown(f"**✅ Why it fits:** {why_fit}")
        
        if source_url and source_url not in ('demo_fallback', ''):
            st.markdown(f"**🔗 Evidence:** [{source_url}]({source_url})")
        
        st.caption(f"Source: {'🌍 Web Search' if source_type == 'web' else '🔶 Demo Fallback'}")
        
        st.markdown("---")
        tone = st.selectbox("Email Tone", ["professional", "casual", "bold"])
        
        if st.button("Draft AI Outreach"):
            with st.spinner(f"Drafting personalized email for {selected_lead['company_name']}..."):
                email_draft = asyncio.run(generate_email_draft(st.session_state.idea, selected_lead, tone))
                st.session_state.email_draft = email_draft

    if "email_draft" in st.session_state and st.session_state.email_draft:
        st.markdown("---")
        st.subheader("✉️ AI Email Draft")
        draft = st.session_state.email_draft
        
        st.markdown(f"**Subject:** {draft.get('subject', '')}")
        st.text_area("Message Body", draft.get('email_body', ''), height=200)
        
        st.markdown("**Call to Action**")
        st.info(draft.get('cta', ''))
        
        st.success(f"**Why this works:** {draft.get('personalization_reason', '')}")
        st.caption(f"Compliance: {draft.get('compliance_footer', '')}")

