# 📚 StudyBuddy AI

Upload your study notes (PDF or TXT) and get:
- a short **summary**
- **key points** and **key terms**
- an interactive **multiple-choice quiz** with scoring

Built with **Streamlit** and **Google Gemini Flash**.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
Paste your Gemini API key in the sidebar (get one free at https://aistudio.google.com/apikey).

## Deploy on Streamlit Community Cloud
1. Push these files to a public GitHub repo.
2. Go to https://share.streamlit.io and create a new app from the repo (main file: `app.py`).
3. In **Advanced settings → Secrets** add:
   ```
   GEMINI_API_KEY = "your-key-here"
   ```

## Notes
- Scanned (image-only) PDFs are not supported.
- Very long notes are trimmed to the first 30,000 characters.
- The model name can be changed in the sidebar.
