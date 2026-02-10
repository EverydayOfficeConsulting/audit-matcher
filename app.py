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
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

st.set_page_config(page_title="EOCO Audit Matcher", layout="wide")

st.title("📂 EOCO Audit Matcher v2.1")
st.write("Flexible matching engine for messy CSVs.")

col1, col2 = st.columns(2)
with col1:
    csv_file = st.file_uploader("1. Upload Transaction CSV", type="csv")
with col2:
    zip_file = st.file_uploader("2. Upload Receipts ZIP", type="zip")

if csv_file and zip_file:
    df = pd.read_csv(csv_file)
    # Clean up column names: remove spaces and make lowercase
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    st.write("### 📋 CSV Preview")
    st.dataframe(df.head())

    # DYNAMIC COLUMN PICKER
    # This helps the user if the app can't guess the right column
    potential_cols = df.columns.tolist()
    default_amt = next((c for c in potential_cols if 'amt' in c or 'amount' in c or 'total' in c), potential_cols[0])
    
    selected_amt_col = st.selectbox("Which column contains the Dollar Amount?", potential_cols, index=potential_cols.index(default_amt))

    if st.button("🚀 Run Matching Engine"):
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
                        
                        clean_text = full_text.replace('\n', ' ').upper()
                        found_amounts = re.findall(r"\d+\.\d{2}", full_text)
                        
                        found_match = False
                        for amt_str in set(found_amounts):
                            amt_val = float(amt_str)
                            
                            # Use the user-selected column for matching
                            row_match = df[df[selected_amt_col] == amt_val]
                            
                            if not row_match.empty:
                                for _, row in row_match.iterrows():
                                    # Try to find a vendor or description column
                                    csv_vendor = str(row.get('vendor', row.get('description', row.get('memo', 'Unknown')))).upper()
                                    name_score = similar(csv_vendor, clean_text)
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
            res_df = pd.DataFrame(matches).sort_values(by="Match Confidence", ascending=False)
            st.table(res_df)
            
            csv_report = res_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Audit Report", csv_report, "audit_report.csv")
        
        if unmatched_pdfs:
            with st.expander("⚠️ Unmatched Receipts"):
                st.write(unmatched_pdfs)
