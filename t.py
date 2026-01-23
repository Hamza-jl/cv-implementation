import streamlit as st
from openai import OpenAI
import PyPDF2
from docx import Document
import fitz  # PyMuPDF
import io
import base64
import json
from docxtpl import DocxTemplate

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI CV Tailor Agent", page_icon="👔", layout="wide")

st.title("👔 AI CV Extraction & TECH-6 Form Builder")
st.markdown("Upload an old CV and your Company TECH-6 Template. The AI will extract the data and perfectly fill your document and tables.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Enter your OpenAI API Key:", type="password")
    model_choice = st.selectbox("Select OpenAI Model:", ["gpt-4o", "gpt-3.5-turbo"], index=0)
    use_vision = st.toggle("Use Vision for PDFs", value=True, help="Converts PDFs to images so the AI can read complex layouts flawlessly. Requires gpt-4o.")

# --- HELPER FUNCTIONS ---
def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    return "".join([page.extract_text() + "\n" for page in reader.pages if page.extract_text()])

def extract_text_from_docx(docx_file):
    doc = Document(docx_file)
    return '\n'.join([para.text for para in doc.paragraphs])

def pdf_to_base64_images(pdf_file):
    pdf_bytes = pdf_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    base64_images = [base64.b64encode(doc.load_page(i).get_pixmap(dpi=150).tobytes("png")).decode("utf-8") for i in range(len(doc))]
    pdf_file.seek(0)
    return base64_images

def tailor_cv_to_json(client, model, job_offer_text="", cv_text=None, cv_images=None):
    """Forces the AI to output JSON, and adapts if there is no job offer."""
    
    instruction = "You are an expert Executive Recruiter. Output ONLY valid JSON."
    
    # DYNAMIC LOGIC: Tailor to a job, or just extract data
    if job_offer_text.strip():
        action_prompt = f"Read the candidate's CV and carefully ADAPT it to fit this Job Offer:\n{job_offer_text}"
    else:
        action_prompt = "Read the candidate's CV and EXTRACT their information exactly as it is. Do not change the narrative, just clean up and standardize the formatting."

    task_prompt = f"""
    {action_prompt}
    
    You MUST return a JSON object with EXACTLY these keys:
    "name", "proposed_role", "date_of_birth", "nationality", "education", "certifications", 
    "total_experience_years", "experience_summary", "affiliations", "languages", 
    "contact_info", "current_date", "representative_name"
    
    CRITICAL INSTRUCTION FOR THE EXPERIENCE TABLE ("experience" key):
    You MUST return a JSON array under the key "experience". 
    Each item must have EXACTLY these keys:
    - "period": The dates they worked there.
    - "employer": The company and job title.
    - "country": The country where the job took place.
    - "summary": A clean, bulleted list of their tasks and achievements.

    CRITICAL INSTRUCTION FOR THE TASKS TABLE ("task_references" key):
    You MUST return a JSON array under the key "task_references".
    Each item must have EXACTLY these keys:
    - "specific_task": A specific task required for this role (deduced from the job offer or general profile).
    - "reference": The name of a past employer/project from their CV that proves they can do this task.
    
    Format the values cleanly. If information is missing from the old CV, output "Non spécifié".
    """

    messages = [{"role": "system", "content": instruction}]
    
    if cv_images:
        content_array = [{"type": "text", "text": task_prompt}]
        for b64_img in cv_images:
            content_array.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}})
        messages.append({"role": "user", "content": content_array})
    else:
        messages.append({"role": "user", "content": f"--- OLD CV ---\n{cv_text}\n\n{task_prompt}"})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        response_format={ "type": "json_object" } # Forces strict JSON output
    )
    
    return json.loads(response.choices[0].message.content)

def fill_word_template(template_file, context_dict):
    """Uses docxtpl to inject the JSON dictionary into the Word template tags."""
    doc = DocxTemplate(template_file)
    doc.render(context_dict)
    
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream

# --- MAIN APP FLOW ---
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("1. Old CV")
    old_cv_file = st.file_uploader("Upload Old CV", type=["pdf", "docx"], key="old")

with col2:
    st.subheader("2. Target Template")
    template_file = st.file_uploader("Upload Company DOCX Template", type=["docx"], key="template")
    st.caption("Ensure your template has the TECH-6 tags and the loops for tables.")

with col3:
    st.subheader("3. Job Offer (Optional)")
    job_offer = st.text_area("Paste job description here:", height=150, placeholder="Leave blank to just extract and format...")

if st.button("🚀 Generate Target CV", use_container_width=True):
    if not api_key or not old_cv_file or not template_file:
        st.error("⚠️ Please upload your Old CV, your Target Template, and provide your API key in the sidebar.")
    elif use_vision and model_choice != "gpt-4o":
        st.error("⚠️ Vision is only supported with the 'gpt-4o' model. Please change your model or disable Vision.")
    else:
        with st.spinner("Extracting, analyzing, and filling template tables..."):
            try:
                client = OpenAI(api_key=api_key)
                
                # 1. Extract Old CV (Vision vs Text)
                if old_cv_file.name.endswith('.pdf') and use_vision and model_choice == "gpt-4o":
                    st.info("👁️ Vision Enabled: Reading PDF layout...")
                    cv_images = pdf_to_base64_images(old_cv_file)
                    ai_data_dict = tailor_cv_to_json(client, model_choice, job_offer, cv_images=cv_images)
                else:
                    st.info("📄 Text Mode Enabled: Extracting raw text...")
                    raw_cv_text = extract_text_from_pdf(old_cv_file) if old_cv_file.name.endswith('.pdf') else extract_text_from_docx(old_cv_file)
                    ai_data_dict = tailor_cv_to_json(client, model_choice, job_offer, cv_text=raw_cv_text)
                
                # 2. Fill Template
                final_docx = fill_word_template(template_file, ai_data_dict)
                
                st.success("Target CV Successfully Generated!")
                
                # Expandable section to see the raw extracted JSON data
                with st.expander("👀 View Extracted Data (JSON)"):
                    st.json(ai_data_dict) 
                
                # 3. Download
                st.download_button(
                    label="📥 Download Filled Target CV",
                    data=final_docx,
                    file_name="Final_TECH6_CV.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary"
                )
            except Exception as e:
                st.error(f"An error occurred: {e}")