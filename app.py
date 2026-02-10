import streamlit as st
import pandas as pd
import zipfile
import re
from pdf2image import convert_from_bytes
import pytesseract
import io
from PIL import Image
from difflib import SequenceMatcher

# Helper function for fuzzy string matching
def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

st.set_page_config(page_title="EOCO Audit Matcher", layout="wide")

st.title("📂 EOCO Audit Matcher v2.0")
st.write("Advanced OCR matching with Fuzzy Vendor Verification.")

# File Uploads
col1, col2 = st.columns(2)
with col1:
    csv_file = st.file_uploader("1. Upload Transaction CSV", type="csv")
with col2:
    zip_file = st.file_uploader("2. Upload Receipts ZIP", type="zip")

if csv_file and zip_file:
    df = pd.read_csv(csv_file)
    df.columns = [c.lower() for c in df.columns]
    
    st.write("### 📋 CSV Preview")
    st.dataframe(df.head())

    if st.button("🚀 Run Matching Engine"):
        if 'amount' not in df.columns:
            st.error("Error: CSV must have an 'amount' column.")
        else:
            matches = []
            unmatched_pdfs = []
            
            with zipfile.ZipFile(zip_file, 'r') as z:
                pdf_files = [f for f in z.namelist() if f.lower().endswith('.pdf')]
                my_bar = st.progress(0, text="Reading receipts...")

                for i, filename in enumerate(pdf_files):
                    with z.open(filename) as f:
                        pdf_bytes = f.read()
                        try:
                            images = convert_from_bytes(pdf_bytes)
                            full_text = ""
                            for img in images:
                                full_text += pytesseract.image_to_string(img)
                            
                            # Clean up OCR text for better name matching
                            clean_text = full_text.replace('\n', ' ').upper()
                            
                            # Regex for amounts
                            found_amounts = re.findall(r"\d+\.\d{2}", full_text)
                            
                            found_match = False
                            for amt_str in set(found_amounts):
                                amt_val = float(amt_str)
                                row_match = df[df['amount'] == amt_val]
                                
                                if not row_match.empty:
                                    for _, row in row_match.iterrows():
                                        csv_vendor = str(row.get('vendor', row.get('description', ''))).upper()
                                        
                                        # Perform Fuzzy Match on Vendor Name
                                        name_score = similar(csv_vendor, clean_text)
                                        
                                        # If name score is high, it's a high-confidence match
                                        status = "✅ Confident Match" if name_score > 0.4 else "❓ Amount Match Only"
                                        
                                        matches.append({
                                            "Receipt": filename,
                                            "Amount": amt_val,
                                            "CSV Vendor": csv_vendor,
                                            "Match Confidence": f"{int(name_score * 100)}%",
                                            "Result": status
                                        })
                                    found_match = True
                            
                            if not found_match:
                                unmatched_pdfs.append(filename)
                                
                        except Exception as e:
                            st.warning(f"Error reading {filename}: {e}")
                    
                    my_bar.progress((i + 1) / len(pdf_files))

            st.divider()
            if matches:
                st.success(f"Processing complete. Found {len(matches)} matches.")
                res_df = pd.DataFrame(matches)
                
                # Sort by confidence so user sees best matches first
                res_df = res_df.sort_values(by="Match Confidence", ascending=False)
                st.table(res_df)
                
                csv_report = res_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Audit Report", csv_report, "audit_report.csv")
            
            if unmatched_pdfs:
                with st.expander("⚠️ Unmatched Receipts"):
                    st.write("Could not find any corresponding CSV amounts for:")
                    st.write(unmatched_pdfs)
