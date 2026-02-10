import streamlit as st
import pandas as pd
import zipfile
import base64
from io import BytesIO
from pypdf import PdfWriter, PdfReader

st.set_page_config(page_title="EOCO Review Station", layout="wide")

st.title("📑 EOCO Review Station")
st.write("Visual verification and audit compilation.")

# Session State to track progress
if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0
if 'matches' not in st.session_state:
    st.session_state.matches = {}

# 1. File Uploads
col1, col2 = st.columns(2)
with col1:
    csv_file = st.file_uploader("Upload CSV", type="csv")
with col2:
    zip_file = st.file_uploader("Upload Receipts ZIP", type="zip")

if csv_file and zip_file:
    df = pd.read_csv(csv_file)
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    with zipfile.ZipFile(zip_file, 'r') as z:
        pdf_names = sorted([f for f in z.namelist() if f.lower().endswith('.pdf')])
        
        # UI Layout: 40% Control Panel / 60% PDF Preview
        left_col, right_col = st.columns([2, 3])
        
        # LEFT: Transaction Details & Controls
        with left_col:
            st.subheader(f"Transaction {st.session_state.current_idx + 1} of {len(df)}")
            row = df.iloc[st.session_state.current_idx]
            
            # Highlighted Transaction Data
            vendor_name = row.get('vendor', row.get('description', 'N/A'))
            st.info(f"""
            **Vendor:** {vendor_name}  
            **Date:** {row.get('date', 'N/A')}  
            **Amount:** ${row.get('amount', row.get('total', 0.0))}
            """)
            
            # Search & Filter Receipts
            search_query = st.text_input("🔍 Search Receipts:", placeholder="Type to filter files...")
            filtered_pdfs = [p for p in pdf_names if search_query.lower() in p.lower()]
            
            selected_pdf = st.selectbox("Select Receipt to View:", ["-- Select a File --"] + filtered_pdfs)
            
            st.divider()
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Match & Next", use_container_width=True):
                    if selected_pdf != "-- Select a File --":
                        st.session_state.matches[st.session_state.current_idx] = selected_pdf
                        if st.session_state.current_idx < len(df) - 1:
                            st.session_state.current_idx += 1
                            st.rerun()
                    else:
                        st.warning("Please select a PDF first.")
            with col_b:
                if st.button("➡️ Skip Transaction", use_container_width=True):
                    if st.session_state.current_idx < len(df) - 1:
                        st.session_state.current_idx += 1
                        st.rerun()
            
            st.write(f"📊 **Progress:** {len(st.session_state.matches)} matched")
            if st.button("🔄 Reset All Matches"):
                st.session_state.current_idx = 0
                st.session_state.matches = {}
                st.rerun()

        # RIGHT: Live PDF Viewer
        with right_col:
            if selected_pdf != "-- Select a File --":
                with z.open(selected_pdf) as f:
                    # Convert PDF bytes to a format the browser can display in an iframe
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
            else:
                st.info("The selected receipt will appear here for verification.")

    # 2. FINAL COMPILATION
    st.divider()
    if st.button("🎁 Export Combined Audit Package"):
        if not st.session_state.matches:
            st.error("No matches have been recorded yet.")
        else:
            with st.spinner("Generating PDF..."):
                merger = PdfWriter()
                with zipfile.ZipFile(zip_file, 'r') as z:
                    # Sort by index to keep the PDF in the same order as your CSV
                    for idx, pdf_name in sorted(st.session_state.matches.items()):
                        with z.open(pdf_name) as f:
                            merger.append(PdfReader(f))
                
                output = BytesIO()
                merger.write(output)
                st.download_button(
                    label="📥 Download Audit PDF",
                    data=output.getvalue(),
                    file_name="EOCO_Compiled_Receipts.pdf",
                    mime="application/pdf"
                )
