import streamlit as st
import pandas as pd
import zipfile
import re
from pdf2image import convert_from_bytes
import pytesseract
import io

st.set_page_config(page_title="EOCO Audit Matcher", layout="wide")

st.title("📂 EOCO Audit Matcher")
st.write("Upload your transaction CSV and a ZIP of receipts to find matches.")

# 1. File Uploads
col1, col2 = st.columns(2)
with col1:
    csv_file = st.file_uploader("Upload Transaction CSV", type="csv")
with col2:
    zip_file = st.file_uploader("Upload Receipts ZIP", type="zip")

if csv_file and zip_file:
    df = pd.read_csv(csv_file)
    st.write("### 📋 Transaction Preview", df.head())

    if st.button("🚀 Start Matching Process"):
        matches = []
        
        # 2. Open the ZIP and Process PDFs
        with zipfile.ZipFile(zip_file, 'r') as z:
            pdf_files = [f for f in z.namelist() if f.endswith('.pdf')]
            
            progress_bar = st.progress(0)
            
            for i, filename in enumerate(pdf_files):
                # Extract PDF content
                with z.open(filename) as f:
                    pdf_bytes = f.read()
                    # Convert PDF to Image for OCR
                    images = convert_from_bytes(pdf_bytes)
                    text = ""
                    for img in images:
                        text += pytesseract.image_to_string(img)
                
                # 3. Simple Matching Logic (Looking for $$$ amounts)
                # This finds numbers like 123.45 in the OCR text
                found_amounts = re.findall(r"\d+\.\d{2}", text)
                
                # Check each amount against the CSV
                for amount in found_amounts:
                    # Look for rows where the 'Amount' column matches
                    # (Note: You'll need to ensure your CSV column is named 'Amount')
                    val = float(amount)
                    match_row = df[df['Amount'] == val]
                    
                    if not match_row.empty:
                        matches.append({
                            "File": filename,
                            "Matched Amount": val,
                            "CSV Vendor": match_row.iloc[0].get('Vendor', 'Unknown'),
                            "Status": "✅ Match Found"
                        })

                progress_bar.progress((i + 1) / len(pdf_files))

        # 4. Display Results
        if matches:
            results_df = pd.DataFrame(matches)
            st.success("Matching Complete!")
            st.write("### 📊 Matching Results", results_df)
            
            # Download link for the report
            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Match Report", csv, "eoco_match_report.csv", "text/csv")
        else:
            st.warning("No matches found. Check if the amounts in the PDFs are clear.")
