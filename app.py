"""StudyBuddy AI - upload study notes (PDF or TXT) and get a summary,
key points and an interactive quiz, powered by Gemini Flash."""

import json
import re

import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader

DEFAULT_MODEL = "gemini-3.8-flash"
MAX_CHARS = 30000  # keep requests small and fast


# ---------- helpers (pure functions, easy to test) ----------
def extract_text(uploaded_file) -> str:
    """Read text from an uploaded PDF or TXT file."""
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        pages = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(pages).strip()
    return uploaded_file.read().decode("utf-8", errors="ignore").strip()


def clean_json(raw: str):
    """Parse JSON even if the model wrapped it in ```json fences."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    return json.loads(raw)


def summary_prompt(text: str) -> str:
    return f"""You are a helpful study assistant. Read the notes below and reply in Markdown with:
## Summary
(5-7 sentences, simple language)
## Key Points
(6-10 bullet points)
## Key Terms
(term - one-line meaning, 5-8 items)

NOTES:
{text}"""


def quiz_prompt(text: str, n: int) -> str:
    return f"""Create {n} multiple-choice questions from the notes below.
Return ONLY valid JSON, a list of objects with exactly these keys:
"question" (string), "options" (list of exactly 4 strings),
"answer" (integer 0-3, index of the correct option), "explanation" (string).

NOTES:
{text}"""


def validate_quiz(data) -> list:
    """Keep only well-formed questions."""
    good = []
    for q in data if isinstance(data, list) else []:
        try:
            if (
                isinstance(q["question"], str)
                and isinstance(q["options"], list)
                and len(q["options"]) == 4
                and isinstance(q["answer"], int)
                and 0 <= q["answer"] <= 3
            ):
                good.append(
                    {
                        "question": q["question"],
                        "options": [str(o) for o in q["options"]],
                        "answer": q["answer"],
                        "explanation": str(q.get("explanation", "")),
                    }
                )
        except (KeyError, TypeError):
            continue
    return good


def ask_gemini(client, model: str, prompt: str, as_json: bool = False) -> str:
    config = types.GenerateContentConfig(
        response_mime_type="application/json" if as_json else "text/plain",
        temperature=0.4,
    )
    response = client.models.generate_content(model=model, contents=prompt, config=config)
    return response.text or ""


# ---------- UI ----------
def main():
    st.set_page_config(page_title="StudyBuddy AI", page_icon="📚", layout="centered")
    st.title("📚 StudyBuddy AI")
    st.caption("Upload your notes and get a summary, key points and a quiz.")

    with st.sidebar:
        st.header("Settings")
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
        except Exception:
            api_key = ""
        if not api_key:
            api_key = st.text_input("Gemini API key", type="password")
        model = st.text_input("Model name", value=DEFAULT_MODEL)
        num_q = st.slider("Number of quiz questions", 3, 10, 5)

    uploaded = st.file_uploader("Upload notes (PDF or TXT)", type=["pdf", "txt"])

    if st.button("Generate study material", type="primary"):
        if not api_key:
            st.error("Please enter your Gemini API key in the sidebar.")
            st.stop()
        if not uploaded:
            st.error("Please upload a PDF or TXT file first.")
            st.stop()

        try:
            text = extract_text(uploaded)
        except Exception as e:
            st.error(f"Could not read the file: {e}")
            st.stop()
        if len(text) < 50:
            st.error("Not enough text found. Scanned PDFs (images) are not supported.")
            st.stop()
        if len(text) > MAX_CHARS:
            st.warning(f"Notes are long, using only the first {MAX_CHARS} characters.")
            text = text[:MAX_CHARS]

        try:
            client = genai.Client(api_key=api_key)
            with st.spinner("Reading your notes..."):
                st.session_state["summary"] = ask_gemini(client, model, summary_prompt(text))
            with st.spinner("Building your quiz..."):
                raw = ask_gemini(client, model, quiz_prompt(text, num_q), as_json=True)
                st.session_state["quiz"] = validate_quiz(clean_json(raw))
            st.session_state["submitted"] = False
        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.stop()

    if "summary" in st.session_state:
        st.markdown(st.session_state["summary"])

    quiz = st.session_state.get("quiz", [])
    if "summary" in st.session_state and not quiz:
        st.warning("The quiz could not be generated. Click the button again.")

    if quiz:
        st.divider()
        st.subheader("📝 Quiz")
        for i, q in enumerate(quiz):
            st.radio(
                f"{i + 1}. {q['question']}",
                q["options"],
                index=None,
                key=f"q{i}",
                disabled=st.session_state.get("submitted", False),
            )
        if st.button("Submit answers"):
            st.session_state["submitted"] = True
            st.rerun()

        if st.session_state.get("submitted"):
            score = 0
            for i, q in enumerate(quiz):
                picked = st.session_state.get(f"q{i}")
                correct = q["options"][q["answer"]]
                if picked == correct:
                    score += 1
                    st.success(f"Q{i + 1}: Correct ✅")
                else:
                    st.error(f"Q{i + 1}: Wrong ❌ - correct answer: {correct}")
                if q["explanation"]:
                    st.caption(q["explanation"])
            st.subheader(f"Your score: {score} / {len(quiz)}")


if __name__ == "__main__":
    main()
