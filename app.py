"""Legit88 web page (Streamlit).

Run it locally with:   streamlit run app.py
Streamlit turns this Python file into a web page: each `st.something` draws an element.
"""

import csv
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from legit88.config import get_secret
from legit88.verdict import analyse

EVENTS_FILE = Path(__file__).parent / "data" / "events.csv"
SAMPLES_DIR = Path(__file__).parent / "tests" / "samples"

COLORS = {"red": "🔴", "orange": "🟠", "green": "🟢", "info": "ℹ️"}
BOXES = {"red": st.error, "orange": st.warning, "green": st.success}


def log_event(kind: str, value: str = ""):
    """Save an anonymous event (an analysis, a click) to measure traction. No personal data."""
    EVENTS_FILE.parent.mkdir(exist_ok=True)
    new = not EVENTS_FILE.exists()
    with open(EVENTS_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if new:
            writer.writerow(["time_utc", "event", "value"])
        writer.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), kind, value])


st.set_page_config(page_title="Legit88 — Is this farm job legit?", page_icon="🌾", layout="centered")

st.title("🌾 Legit88")
st.subheader("Is this farm job legit, and will it count toward your 88 days?")
st.caption("Paste a job ad from Facebook, Gumtree or WhatsApp, or upload a screenshot. "
           "We check it against official Australian records in about 30 seconds.")

# --- Demo examples (handy for the pitch) ---
def load_example():
    """Runs only when the menu changes, so it never overwrites what the user types afterwards."""
    choice = st.session_state["example"]
    if choice != "—":
        st.session_state["ad_text"] = (SAMPLES_DIR / f"{choice.replace(' ', '_')}.txt").read_text(encoding="utf-8")


samples = sorted(SAMPLES_DIR.glob("*.txt"))
if samples:
    st.selectbox("Or try an example ad (fictional)", ["—"] + [s.stem.replace("_", " ") for s in samples],
                 key="example", on_change=load_example)

text = st.text_area("Job ad", key="ad_text", height=220, placeholder="Paste the ad here…")
image = st.file_uploader("…or a screenshot", type=["png", "jpg", "jpeg"])

if not get_secret("OPENROUTER_API_KEY"):
    st.info("Demo mode: no AI key set, so the ad is read with simple rules. Screenshots need the AI key.")

if st.button("Check this ad", type="primary", disabled=not (text or image)):
    with st.spinner("Reading the ad and checking official records…"):
        report = analyse(text=text, image_bytes=image.getvalue() if image else None,
                         image_type=image.type if image else "image/png")
    log_event("analysis", report.verdict)
    st.session_state["image_unread"] = bool(image and not text and report.ad.extracted_by == "rules")
    # Streamlit re-runs the whole file on every click: we keep the report in memory
    # (session_state) so it stays on screen when the user clicks another button.
    st.session_state["report"] = report

report = st.session_state.get("report")
if report:
    if report.ad.ai_failed:
        st.info("The AI reader was unavailable, so a simpler reader was used. Double-check the details below.")
    if st.session_state.get("image_unread"):
        st.warning("We could not read the screenshot (the AI reader is unavailable), so this result is incomplete. "
                   "Please paste the text of the ad instead.")
    BOXES[report.verdict](f"{COLORS[report.verdict]} **{report.headline}**")

    st.markdown("### What we found")
    for f in report.findings:
        st.markdown(f"{COLORS[f.level]} **{f.title}**  \n{f.detail}")

    if report.questions:
        st.markdown("### Questions to ask the employer before you go")
        for q in report.questions:
            st.markdown(f"- {q}")

    with st.expander("What we read in the ad"):
        st.json({k: v for k, v in vars(report.ad).items() if v not in (None, [], False)})

    st.caption("Legit88 reports risk signals from public records; it does not accuse anyone. "
               "Always confirm with the employer and official sources (Fair Work, Home Affairs).")

    # --- Fake door: measures if people would pay (risky assumption n°3) ---
    st.divider()
    st.markdown("**Want unlimited checks and a saved report for your visa file?**")
    if st.button("Get the 88-day pass — A$9.99"):
        log_event("pass_click")
        st.success("Thanks! The pass is coming soon. We'll let you know.")
