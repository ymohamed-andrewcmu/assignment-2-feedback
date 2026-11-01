from __future__ import annotations

import os
import uuid
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from demo import demo_feedback
from feedback import (
    ACTION_LABELS, BUSINESS_QUESTION, DEFAULT_MODEL, LABELS, MAX_COMMENT_LENGTH,
    REVIEW_LABEL, classify_comment, load_feedback, resolve_feedback, retry_feedback,
    save_feedback, summarize,
)

st.set_page_config(page_title="Campus Cup · Feedback", page_icon="☕", layout="wide")


def secret(name, default=""):
    try:
        return str(st.secrets.get(name, os.environ.get(name, default)))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return os.environ.get(name, default)


API_KEY = secret("GROQ_API_KEY")
MODEL = secret("GROQ_MODEL", DEFAULT_MODEL)
DB_PATH = Path(os.environ.get("FEEDBACK_DB_PATH", "data/feedback.sqlite3"))

st.markdown("""<style>
    .stApp { background: #faf8f4; }
    h1, h2, h3 { color: #203e35; }
    [data-testid="stSidebar"] { background: #edf1e9; }
    [data-testid="stMetric"] { background: white; border: 1px solid #dce4d8;
        border-radius: 14px; padding: 18px 20px; }
    .block-container { max-width: 1160px; padding-top: 2.5rem; }
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("☕ Campus Cup")
    st.caption("A little feedback. A better café.")
    page = st.radio("Choose a side", ["Leave feedback", "Owner dashboard", "Question & labels"])
    st.divider()
    st.caption("Fictional café · Public classroom demo")
    if API_KEY:
        st.caption("AI labeling configured · Groq")
    else:
        st.caption("AI setup pending · comments enter manual review")


def labels_table():
    st.table(pd.DataFrame([{"Label": key, "Definition": value} for key, value in LABELS.items()]))


def customer_page():
    st.caption("YOUR VISIT, IN YOUR WORDS")
    st.title("How was your Campus Cup visit?")
    st.write("Tell us what made your day—or what we could do better.")
    st.info("Public demo: feedback is visible on the owner dashboard. Please avoid names, contact details, or other personal information. Written comments are sent to Groq for AI labeling when configured.")
    if not API_KEY:
        st.warning("AI labeling is awaiting setup. You can still leave feedback; written comments will be saved for manual review.")
    st.session_state.setdefault("submission_id", str(uuid.uuid4()))
    with st.form("customer_feedback", clear_on_submit=True, border=True):
        st.subheader("Share your experience")
        st.write("Star rating (optional)")
        stars = st.feedback("stars", key="stars")
        comment = st.text_area("Your comment (optional)", max_chars=MAX_COMMENT_LENGTH,
                               placeholder="What went well? What should we improve?", height=150)
        st.caption("Choose a star rating, write a comment, or do both.")
        submit = st.form_submit_button("Send feedback", type="primary", use_container_width=True)
    if submit:
        rating = stars + 1 if stars is not None else None
        comment = comment.strip()
        if rating is None and not comment:
            st.error("Please add a star rating, a comment, or both.")
            return
        with st.spinner("Saving your feedback…"):
            classification = classify_comment(comment, API_KEY, MODEL) if comment else None
            try:
                save_feedback(DB_PATH, st.session_state.submission_id, rating, comment, classification)
            except Exception:
                st.error("Your feedback could not be saved. Please try again.")
                if comment:
                    st.text(comment)
                return
        st.session_state.submission_id = str(uuid.uuid4())
        st.success("Thank you! Your feedback has been saved.")
        if classification:
            st.write(f"**Label:** {classification.label}")
            if classification.label == REVIEW_LABEL:
                st.caption("An owner will review your comment before it contributes to improvement priorities.")
        else:
            st.caption("Your star rating was saved. There is no written comment to label.")


def owner_page():
    st.caption("LISTEN. PRIORITIZE. IMPROVE.")
    st.title("Owner dashboard")
    st.write(f"**{BUSINESS_QUESTION}**")
    scope_col, refresh_col = st.columns([3, 1])
    with scope_col:
        scope = st.radio("Data source", ["Live feedback", "Example dataset"], horizontal=True)
    with refresh_col:
        st.button("Refresh dashboard", use_container_width=True)
    is_example = scope == "Example dataset"
    if is_example:
        rows = demo_feedback()
        st.info("EXAMPLE DATA: fictional, hand-labeled comments to demonstrate the dashboard. These are separate from live submissions and were not labeled by the LLM.")
    else:
        try:
            rows = load_feedback(DB_PATH)
        except Exception:
            st.error("Feedback storage is temporarily unavailable. Please refresh to try again.")
            return
    stats = summarize(rows)
    c1, c2, c3 = st.columns(3)
    c1.metric("Feedback submissions", stats["submissions"])
    c2.metric("Average star rating", f"{stats['average_rating']:.1f} / 5" if stats["ratings"] else "—",
              help=f"Based on {stats['ratings']} submissions with a star rating; missing ratings are excluded.")
    c3.metric("Comments needing review", stats["review_count"])
    st.subheader("Where to focus first")
    if stats["priorities"]:
        names = ", ".join(stats["priorities"])
        wording = "each" if len(stats["priorities"]) > 1 else ""
        st.success(f"{'Joint priorities' if len(stats['priorities']) > 1 else 'First priority'}: **{names}** · {stats['priority_count']} improvement comments {wording}.")
    else:
        st.info("No labeled improvement requests yet. Collect feedback or resolve the review queue to identify a priority.")
    st.caption("Priority = the most frequent main improvement requested. Praise, rating-only submissions, and comments awaiting review are excluded. Ties are shown; this is a count-based starting point, not a measure of severity.")

    left, right = st.columns([1.25, 1])
    with left:
        st.subheader("Requested improvements")
        counts = pd.DataFrame({"Area": ACTION_LABELS,
                               "Comments": [stats["action_counts"][label] for label in ACTION_LABELS]})
        chart = alt.Chart(counts).mark_bar(color="#3f6d58", cornerRadiusEnd=4).encode(
            x=alt.X("Comments:Q", axis=alt.Axis(tickMinStep=1), scale=alt.Scale(domainMin=0)),
            y=alt.Y("Area:N", sort="-x", title=None), tooltip=["Area:N", "Comments:Q"],
        ).properties(height=260)
        st.altair_chart(chart, use_container_width=True)
    with right:
        st.subheader("Star ratings")
        ratings = pd.DataFrame({"Stars": list(range(1, 6)),
                                "Submissions": [sum(r.get("rating") == n for r in rows) for n in range(1, 6)]})
        chart = alt.Chart(ratings).mark_bar(color="#c68b42", cornerRadiusTopLeft=4,
                                          cornerRadiusTopRight=4).encode(
            x=alt.X("Stars:O", title="Star rating"),
            y=alt.Y("Submissions:Q", axis=alt.Axis(tickMinStep=1), scale=alt.Scale(domainMin=0)),
            tooltip=["Stars:O", "Submissions:Q"],
        ).properties(height=260)
        st.altair_chart(chart, use_container_width=True)

    st.subheader("Manual review queue")
    st.caption("Comments appear in full below. Low confidence (<75%), unclear feedback, invalid AI output, or service failures enter this queue. Model confidence is a heuristic, not a calibrated probability.")
    queue = [row for row in rows if row.get("label") == REVIEW_LABEL]
    if not queue:
        st.success("No comments are waiting for review.")
    for row in queue:
        with st.container(border=True):
            rating_text = f"{row['rating']} / 5 stars" if row["rating"] else "No star rating"
            st.caption(f"{row['created_at'][:16].replace('T', ' ')} UTC · {rating_text}")
            st.text(row["comment"])
            st.caption(row["reason"])
            if not is_example:
                selected = st.selectbox("Verified label", [x for x in LABELS if x != REVIEW_LABEL],
                                        index=None, placeholder="Choose after reading the full comment",
                                        key=f"label-{row['id']}")
                manual_col, retry_col = st.columns(2)
                if manual_col.button("Save verified label", key=f"resolve-{row['id']}",
                                     disabled=selected is None, use_container_width=True):
                    try:
                        resolve_feedback(DB_PATH, row["id"], selected)
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))
                if retry_col.button("Retry AI labeling", key=f"retry-{row['id']}",
                                    disabled=not API_KEY, use_container_width=True):
                    with st.spinner("Labeling comment…"):
                        result = classify_comment(row["comment"], API_KEY, MODEL)
                        try:
                            retry_feedback(DB_PATH, row["id"], result)
                        except ValueError as error:
                            st.error(str(error))
                            return
                    st.rerun()

    with st.expander("All feedback & export"):
        if rows:
            frame = pd.DataFrame(rows)
            columns = ["created_at", "rating", "comment", "label", "source", "reason"]
            st.dataframe(frame[columns], hide_index=True, use_container_width=True)
            st.download_button("Download feedback CSV", frame.to_csv(index=False).encode("utf-8"),
                               file_name="campus_cup_examples.csv" if is_example else "campus_cup_feedback.csv",
                               mime="text/csv")
        else:
            st.write("No live feedback yet. Leave feedback or select the example dataset to explore.")
    st.caption("Classroom storage: submissions are saved in SQLite on the app server and shared across visitors. Streamlit Cloud can reset local storage after a restart or redeployment. Export CSV to keep a copy. The owner dashboard is public for this assignment.")


def about_page():
    st.title("The question behind the labels")
    st.write("**Business:** Campus Cup, a fictional café serving students and staff.")
    st.subheader(BUSINESS_QUESTION)
    st.write("Each written comment receives exactly one label. We count the five improvement labels to identify the most frequently requested change.")
    labels_table()
    st.subheader("How labeling works")
    st.write("Written feedback is classified by a Groq-hosted LLM using a fixed prompt and validated JSON output. Low-confidence results and failures go to manual review. An owner can verify a label or retry the LLM. Ratings are optional and are not used to infer a comment's label.")
    st.write("Rating-only submissions are saved without a text label and contribute only to submission and rating statistics. Example data is fictional and hand-labeled, kept separate from live feedback.")
    st.caption(f"Configured model: {MODEL}. API keys are read from Streamlit secrets or environment variables and never displayed.")


if page == "Leave feedback":
    customer_page()
elif page == "Owner dashboard":
    owner_page()
else:
    about_page()
