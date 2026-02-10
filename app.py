import streamlit as st
import pandas as pd
import zipfile
import base64
from io import BytesIO
from pypdf import PdfWriter, PdfReader

st.set_page_config(page_title="EOCO Review Station", layout="wide")

st.title("📑 EOCO Review Station")
st.write("Manual matching with automatic PDF compilation.")

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
        pdf_names = [f for f in z.namelist() if f.lower().endswith('.pdf')]
        
        # UI Layout
        left_col, right_col = st.columns([1, 1])
        
        # LEFT: Transaction Details
        with left_col:
            st.header(f"Transaction {st.session_state.current_idx + 1} of {len(df)}")
            row = df.iloc[st.session_state.current_idx]
            
            # Display transaction as a nice card
            st.info(f"""
            **Vendor:** {row.get('vendor', row.get('description', 'N/A'))}  
            **Date:** {row.get('date', 'N/A')}  
            **Amount:** ${row.get('amount', row.get('total', 0.0))}
            """)
            
            selected_pdf = st.selectbox("Select Matching Receipt:", ["None"] + pdf_names)
            
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
            
            if st.button("🔄 Reset Progress"):
                st.session_state.current_idx = 0
                st.session_state.matches = {}
                st.rerun()

        # RIGHT: PDF Preview
        with right_col:
            if selected_pdf != "None":
                with z.open(selected_pdf) as f:
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
            else:
                st.warning("Select a PDF from the dropdown to preview it here.")

    # 2. FINAL COMPILATION
    st.divider()
    if st.button("🎁 Generate Final Audit PDF"):
        if not st.session_state.matches:
            st.error("No matches made yet.")
        else:
            merger = PdfWriter()
            with zipfile.ZipFile(zip_file, 'r') as z:
                for idx, pdf_name in st.session_state.matches.items():
                    with z.open(pdf_name) as f:
                        merger.append(PdfReader(f))
            
            output = BytesIO()
            merger.write(output)
            st.success("Audit PDF Compiled Successfully!")
            st.download_button("📥 Download Combined Audit PDF", output.getvalue(), "EOCO_Audit_Package.pdf", "application/pdf")
