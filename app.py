import streamlit as st
import pandas as pd
import zipfile
import base64
from io import BytesIO
from pypdf import PdfWriter, PdfReader

st.set_page_config(page_title="EOCO Review Station", layout="wide")

st.title("📑 EOCO Review Station")
st.write("Manual matching with intelligent search and compilation.")

# Session State Initialization
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
        
        # UI Layout
        left_col, right_col = st.columns([1, 1.2])
        
        # LEFT: Transaction Details
        with left_col:
            st.header(f"Transaction {st.session_state.current_idx + 1} of {len(df)}")
            row = df.iloc[st.session_state.current_idx]
            
            # Display transaction details prominently
            vendor_name = row.get('vendor', row.get('description', 'N/A'))
            st.info(f"""
            **Vendor:** {vendor_name}  
            **Date:** {row.get('date', 'N/A')}  
            **Amount:** ${row.get('amount', row.get('total', 0.0))}
            """)
            
            # Searchable Dropdown Logic
            search_query = st.text_input("🔍 Search Receipts:", value="", help="Type vendor name or file name to filter...")
            filtered_pdfs = [p for p in pdf_names if search_query.lower() in p.lower()]
            
            selected_pdf = st.selectbox("Select Match:", ["None"] + filtered_pdfs)
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Match & Next"):
                    if selected_pdf != "None":
                        st.session_state.matches[st.session_state.current_idx] = selected_pdf
                    if st.session_state.current_idx < len(df) - 1:
                        st.session_state.current_idx += 1
                        st.rerun()
            with col_b:
                if st.button("➡️ Skip"):
                    if st.session_state.current_idx < len(df) - 1:
                        st.session_state.current_idx += 1
                        st.rerun()
            
            st.write(f"**Total Matches Made:** {len(st.session_state.matches)}")
            if st.button("🔄 Reset All Progress"):
                st.session_state.current_idx = 0
                st.session_state.matches = {}
                st.rerun()

        # RIGHT: PDF Preview
        with right_col:
            if selected_pdf != "None":
                with z.open(selected_pdf) as f:
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                    # Iframe for smooth browser preview
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#toolbar=0" width="100%" height="700" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
            else:
                st.warning("Use the search or select a PDF to preview it here.")

    # 2. FINAL COMPILATION
    st.divider()
    if st.button("🎁 Compile & Export Final Audit PDF"):
        if not st.session_state.matches:
            st.error("You haven't matched any transactions yet.")
        else:
            with st.spinner("Merging PDFs into audit-ready package..."):
                merger = PdfWriter()
                with zipfile.ZipFile(zip_file, 'r') as z:
                    for idx, pdf_name in sorted(st.session_state.matches.items()):
                        with z.open(pdf_name) as f:
                            merger.append(PdfReader(f))
                
                output = BytesIO()
                merger.write(output)
                st.success(f"Successfully compiled {len(st.session_state.matches)} receipts!")
                st.download_button(
                    label="📥 Download Audit Package",
                    data=output.getvalue(),
                    file_name="EOCO_Audit_Report.pdf",
                    mime="application/pdf"
                )
