import csv
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from engine import search

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "escalations.csv")
STAFF_CONTACT = "VIT Student Support Office"  # replace with the real contact if your team has one

SAMPLE_QUESTIONS = [
    "Where is the health centre?",
    "What time does the library open?",
    "How do I register for an event?",
    "I lost my ID card, what should I do?",
    "What are the timings?",
    "What is the B.Tech fee?",
]

WELCOME = (
    "Hi! I'm the VIT Campus Helpdesk Assistant. I answer only from approved FAQs and "
    "campus information, and I'll pass anything I can't answer to the student support staff. "
    "Try asking about the library, labs, hostels, events or campus procedures."
)

st.set_page_config(page_title="VIT Campus Helpdesk", page_icon="🎓")


def log_escalation(query):
    """Save an unanswered query to escalations.csv and return a ticket id."""
    now = datetime.now()
    ticket_id = "TKT-" + now.strftime("%Y%m%d-%H%M%S-%f")[:-3]
    is_new = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["ticket_id", "timestamp", "query", "status"])
        writer.writerow([ticket_id, now.strftime("%Y-%m-%d %H:%M:%S"), query, "Pending"])
    return ticket_id


def render_assistant(msg, idx):
    if "text" in msg:                      # plain text message (welcome)
        st.markdown(msg["text"])
        return

    r = msg["result"]

    if r["status"] == "no_match":
        st.markdown(
            "I couldn't find this in the approved campus information, so I've "
            "forwarded your question to the student support staff."
        )
        st.info(
            f"🎫 Ticket **{msg['ticket']}** created. Please contact the "
            f"**{STAFF_CONTACT}** and quote this ticket number."
        )
        return

    if r["answer"]:                        # an answer was found
        st.markdown(r["answer"])
        source_line = f"📄 **Source:** {r['source']} — *{r['title']}*"
        if r["source_url"]:
            source_line += f"  ([link]({r['source_url']}))"
        st.markdown(source_line)
        if not r["verified"]:
            st.warning(
                "This entry is project-team or sample data and is not marked as verified. "
                "Please confirm with the relevant office."
            )
        st.caption(f"Match score: {r['score']:.2f}")
    else:                                  # vague question, no single answer
        st.markdown(
            "Your question is a bit broad and could mean several things."
        )

    if r["status"] == "ambiguous":
        options = [s for s in r["suggestions"] if s != r["title"]]
        if options:
            st.markdown("**Did you mean one of these?**")
            for i, s in enumerate(options):
                if st.button(s, key=f"sug_{idx}_{i}"):
                    st.session_state.pending = s
                    st.rerun()


# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("🎓 VIT Campus Helpdesk")
    st.caption("Answers come only from the approved knowledge base.")
    st.subheader("Try asking")
    for i, q in enumerate(SAMPLE_QUESTIONS):
        if st.button(q, key=f"sample_{i}", use_container_width=True):
            st.session_state.pending = q
    st.divider()
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "text": WELCOME}]
        st.rerun()
    staff_view = st.checkbox("Staff view (escalated queries)")

# ---------------- Chat state ----------------
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "text": WELCOME}]

st.title("AI Campus Helpdesk Assistant")

query = st.chat_input("Ask about classrooms, labs, events, hostel, library...")
if st.session_state.get("pending"):
    query = st.session_state.pop("pending")

if query:
    st.session_state.messages.append({"role": "user", "text": query})
    result = search(query)
    msg = {"role": "assistant", "result": result}
    if result["status"] == "no_match":
        msg["ticket"] = log_escalation(query)
    st.session_state.messages.append(msg)

# ---------------- Render history ----------------
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["text"])
        else:
            render_assistant(msg, idx)

# ---------------- Staff view ----------------
if staff_view:
    st.divider()
    st.subheader("📋 Escalated queries (staff view)")
    if os.path.exists(LOG_PATH):
        st.dataframe(pd.read_csv(LOG_PATH), use_container_width=True)
    else:
        st.write("No escalated queries yet.")