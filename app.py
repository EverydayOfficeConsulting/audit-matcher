import streamlit as st
import pandas as pd
import zipfile
import re
from pdf2image import convert_from_bytes
import pytesseract
import io
from PIL import Image
from difflib import SequenceMatcher

def similar(a, b):
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

st.set_page_config(page_title="EOCO Audit Matcher", layout="wide")

st.title("📂 EOCO Audit Matcher v2.2")
st.write("Enhanced Deep-Scan for better receipt matching.")

col1, col2 = st.columns(2)
with col1:
    csv_file = st.file_uploader("1. Upload Transaction CSV", type="csv")
with col2:
    zip_file = st.file_uploader("2. Upload Receipts ZIP", type="zip")

if csv_file and zip_file:
    df = pd.read_csv(csv_file)
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    potential_cols = df.columns.tolist()
    default_amt = next((c for c in potential_cols if any(x in c for x in ['amt', 'amount', 'total'])), potential_cols[0])
    selected_amt_col = st.selectbox("Confirm the Amount column:", potential_cols, index=potential_cols.index(default_amt))

    if st.button("🚀 Run Deep-Scan Matching"):
        matches = []
        unmatched_pdfs = []
        
        with zipfile.ZipFile(zip_file, 'r') as z:
            pdf_files = [f for f in z.namelist() if f.lower().endswith('.pdf')]
            my_bar = st.progress(0)

            for i, filename in enumerate(pdf_files):
                with z.open(filename) as f:
                    try:
                        images = convert_from_bytes(f.read())
                        full_text = ""
                        for img in images:
                            # Use custom config to tell Tesseract to look for digits/currency patterns
                            full_text += pytesseract.image_to_string(img, config='--psm 11')
                        
                        # CLEANING: Remove spaces between digits and decimals (e.g., "150 . 00" -> "150.00")
                        cleaned_text = re.sub(r'(\d)\s+\.\s+(\d)', r'\1.\2', full_text)
                        # Remove common OCR errors (S instead of 5, O instead of 0) in number-like contexts
                        # (Keeping it simple for now to avoid breaking genuine text)
                        
                        # Find all patterns that look like currency (1.00, 1,000.00, etc)
                        found_amounts = re.findall(r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", cleaned_text)
                        
                        # Clean found amounts (remove commas) and convert to float
                        parsed_amounts = []
                        for a in found_amounts:
                            try:
                                val = float(a.replace(',', ''))
                                if val > 0: parsed_amounts.append(val)
                            except: continue

                        found_match = False
                        for amt_val in set(parsed_amounts):
                            # Try an exact match
                            row_match = df[df[selected_amt_col].astype(float) == amt_val]
                            
                            if not row_match.empty:
                                for _, row in row_match.iterrows():
                                    csv_vendor = str(row.get('vendor', row.get('description', 'Unknown'))).upper()
                                    name_score = similar(csv_vendor, cleaned_text)
                                    
                                    matches.append({
                                        "Receipt": filename,
                                        "Amount Found": f"${amt_val:.2f}",
                                        "CSV Transaction": csv_vendor,
                                        "Date": row.get('date', 'N/A'),
                                        "Confidence": f"{int(name_score * 100)}%"
                                    })
                                found_match = True
                        
                        if not found_match:
                            unmatched_pdfs.append(filename)
                            
                    except Exception as e:
                        st.warning(f"Skipped {filename}: {e}")
                
                my_bar.progress((i + 1) / len(pdf_files))

        if matches:
            st.success(f"Matched {len(matches)} items!")
            st.table(pd.DataFrame(matches))
        else:
            st.error("No matches found. This is often due to low-resolution PDFs or unusual CSV formats.")
            
        if unmatched_pdfs:
            with st.expander("View Unmatched Files"):
                st.write(unmatched_pdfs)
