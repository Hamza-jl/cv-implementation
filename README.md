# CV Implementation

Streamlit app that extracts information from an existing CV and fills a TECH-6 Word template. Supports both direct text extraction and GPT-4o vision for PDFs with complex layouts.

## What it does

Upload a CV (PDF or DOCX) and optionally a job offer. The app sends the document to GPT-4o, which extracts the candidate's information into a structured JSON (name, role, education, experience timeline, certifications, languages, etc.) and uses that to populate a TECH-6 `.docx` template via `docxtpl`.

If a job offer is provided, the agent adapts the experience narrative to match the role before filling the template. If not, it extracts and standardizes the existing content as-is.

Vision mode (enabled by default) converts each PDF page to an image before sending it to the model, which handles scanned documents and heavily formatted layouts much better than raw text extraction.

## Stack

- Python / Streamlit
- OpenAI GPT-4o
- PyMuPDF for PDF-to-image conversion
- PyPDF2 for text extraction fallback
- python-docx / docxtpl for Word output

## Setup

```
pip install streamlit openai PyPDF2 python-docx PyMuPDF docxtpl
```

Run:

```
streamlit run CV_implementation.py
```

Enter your OpenAI API key in the sidebar when the app loads. No `.env` required — the key is passed through the UI.
