import streamlit as st
import pandas as pd
import re
import os
from io import StringIO, BytesIO
import base64
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json

# Set page config
st.set_page_config(
    page_title="GD&T Tolerance Extractor",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for modern styling
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global styles */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Header styling */
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 1rem;
        letter-spacing: -0.02em;
    }
    
    .subtitle {
        text-align: center;
        color: #6b7280;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* Card styling */
    .metric-card {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    
    .info-card {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border-radius: 12px;
        padding: 1.5rem;
        border-left: 4px solid #3b82f6;
        box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
    }
    
    .success-card {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border-radius: 12px;
        padding: 1rem;
        border-left: 4px solid #22c55e;
        color: #166534;
        margin: 1rem 0;
    }
    
    .error-card {
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border-radius: 12px;
        padding: 1rem;
        border-left: 4px solid #ef4444;
        color: #991b1b;
        margin: 1rem 0;
    }
    
    /* Table styling */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        border: none;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.1);
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px -2px rgba(0, 0, 0, 0.2);
    }
    
    /* File uploader styling */
    .stFileUploader > div {
        border-radius: 12px;
        border: 2px dashed #cbd5e1;
        background: #f8fafc;
        transition: all 0.3s ease;
    }
    
    .stFileUploader > div:hover {
        border-color: #667eea;
        background: #f0f4ff;
    }
    
    /* Metric styling */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 4px;
    }
    
    /* Selectbox styling */
    .stSelectbox > div > div {
        border-radius: 8px;
        border: 1px solid #cbd5e1;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
    }
    
    /* Animation for loading */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    .loading {
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state with more features
if 'results_data' not in st.session_state:
    st.session_state.results_data = []
if 'filename' not in st.session_state:
    st.session_state.filename = ""
if 'processing_history' not in st.session_state:
    st.session_state.processing_history = []
if 'filter_settings' not in st.session_state:
    st.session_state.filter_settings = {
        'type_filter': 'All',
        'datum_filter': 'All',
        'location_filter': 'All'
    }
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}


def extract_tolerance_table(text):
    """Extract tolerance values and datums from STEP/text file with enhanced error handling"""
    try:
        lines = text.splitlines()
        # Build a dictionary mapping entity IDs to their lines
        line_dict = {
            re.match(r"(#\d+)\s*=", line).group(1): line.strip()
            for line in lines if re.match(r"(#\d+)\s*=", line)
        }

        # Enhanced regex patterns for better tolerance extraction
        tol_pattern = re.compile(
            r"(#\d+)\s*=\s*(CYLINDRICITY|FLATNESS|STRAIGHTNESS|ROUNDNESS|CONCENTRICITY|SYMMETRY|PERPENDICULARITY|PARALLELISM|ANGULARITY|POSITION|PROFILE_OF_LINE|PROFILE_OF_SURFACE|CIRCULAR_RUNOUT|TOTAL_RUNOUT)_TOLERANCE"
            r"\(\s*'([^']*)'\s*,\s*''\s*,\s*(#\d+)", re.IGNORECASE
        )
        datum_pattern = re.compile(
            r"#\d+\s*=\s*DATUM_FEATURE\(\s*'[^']*?\((\w)\)'", re.IGNORECASE
        )
        shape_aspect_pattern = re.compile(
            r"#\d+\s*=\s*SHAPE_ASPECT\('([^']*?)\((\w)?'?,.*?#(\d+)\)"
        )

        tol_results = []
        datum_results = {}
        face_to_plane = {}

        # Enhanced datum and shape aspect parsing
        datum_letter_to_faceid = {}
        faceid_to_name = {}

        # Find all DATUM and SHAPE_ASPECT lines
        for line in lines:
            # Parse DATUM entity
            m = re.match(
                r"#\d+=DATUM\('([^']*)',\$,#\d+,\.F\.,'([A-Z])'\);", line)
            if m:
                feature, letter = m.groups()
                # Find corresponding SHAPE_ASPECT for this feature
                for sa_line in lines:
                    sa_m = re.match(
                        r"#(\d+)=SHAPE_ASPECT\('([^']*)','',#\d+,\.T\.\);", sa_line)
                    if sa_m and feature in sa_m.group(2):
                        faceid = sa_m.group(1)
                        datum_letter_to_faceid[letter] = faceid
                        faceid_to_name[faceid] = feature

            # Parse SHAPE_ASPECT entity
            sa_m = re.match(
                r"#(\d+)=SHAPE_ASPECT\('([^']*)','',#\d+,\.T\.\);", line)
            if sa_m:
                faceid, feature = sa_m.groups()
                faceid_to_name[faceid] = feature

        # Enhanced shape mapping
        for match in shape_aspect_pattern.finditer(text):
            shape_name, datum_letter, plane_id = match.groups()
            shape_name = shape_name.lower()
            location = ""
            if "plane1" in shape_name:
                location = "Plane1"
            elif "plane2" in shape_name:
                location = "Plane2"
            elif "boss1" in shape_name:
                location = "Boss1"
            elif "top" in shape_name:
                location = "top face"
            elif "bottom" in shape_name:
                location = "bottom face"
            elif "cylindrical" in shape_name or "side" in shape_name:
                location = "cylindrical side"
            elif "hole" in shape_name:
                location = "hole"
            elif "slot" in shape_name:
                location = "slot"
            face_to_plane[plane_id] = location
            if datum_letter:
                datum_results[datum_letter] = location

        # Enhanced tolerance extraction
        for tol_id, tol_type, tol_name, ref_id in tol_pattern.findall(text):
            definition = line_dict.get(ref_id, "")
            value_match = re.search(
                r"(?:LENGTH_MEASURE|VALUE_REPRESENTATION_ITEM)\s*\(\s*([\d.]+)", definition
            )
            value = f"±{value_match.group(1)}" if value_match else "N/A"

            # Enhanced label mapping
            label_map = {
                "ROUNDNESS": "Circularity",
                "CYLINDRICITY": "Cylindricity",
                "FLATNESS": "Flatness",
                "STRAIGHTNESS": "Straightness",
                "CONCENTRICITY": "Concentricity",
                "SYMMETRY": "Symmetry",
                "PERPENDICULARITY": "Perpendicularity",
                "PARALLELISM": "Parallelism",
                "ANGULARITY": "Angularity",
                "POSITION": "Position",
                "PROFILE_OF_LINE": "Profile of Line",
                "PROFILE_OF_SURFACE": "Profile of Surface",
                "CIRCULAR_RUNOUT": "Circular Runout",
                "TOTAL_RUNOUT": "Total Runout"
            }
            label = label_map.get(tol_type.upper(), tol_type.capitalize())

            # Enhanced datum mapping
            tol_line = next((l for l in lines if tol_id in l), "")
            ref_ids = re.findall(r"#(\d+)", tol_line)
            datum_ref_id = ref_ids[-1] if ref_ids else ref_id

            datum_letter = ""
            location = ""
            for letter, faceid in datum_letter_to_faceid.items():
                if faceid == datum_ref_id:
                    datum_letter = letter
                    location = faceid_to_name.get(
                        faceid, face_to_plane.get(faceid, ""))
                    break

            if not datum_letter:
                tol_name_lower = tol_name.lower()
                for d_letter in datum_results:
                    if f"({d_letter.lower()})" in tol_name_lower:
                        datum_letter = d_letter
                        break
                if datum_letter and datum_letter in datum_letter_to_faceid:
                    faceid = datum_letter_to_faceid[datum_letter]
                    location = faceid_to_name.get(
                        faceid, face_to_plane.get(faceid, ""))
                else:
                    for key, val in face_to_plane.items():
                        if key in ref_id or key in tol_name:
                            location = val
                            break

            tol_results.append((label, value, datum_letter, location))

        # Enhanced GD&T symbol mapping
        gdnt_symbols = {
            "Straightness": "─",
            "Flatness": "□",
            "Circularity": "○",
            "Cylindricity": "⌀",
            "Concentricity": "◎",
            "Symmetry": "⌖",
            "Perpendicularity": "⊥",
            "Parallelism": "∥",
            "Angularity": "∠",
            "Position": "⊕",
            "Profile of Line": "⌒",
            "Profile of Surface": "⌓",
            "Circular Runout": "↗",
            "Total Runout": "↗↗"
        }

        # Enhanced surface type mapping
        def get_surface_type(feature_name):
            fname = feature_name.lower()
            if "plane1" in fname or "top" in fname:
                return "top face"
            elif "plane2" in fname or "bottom" in fname:
                return "bottom face"
            elif "boss1" in fname or "cylindrical" in fname or "side" in fname:
                return "cylindrical side"
            elif "cone" in fname or "conical" in fname:
                return "conical side"
            elif "hole" in fname:
                return "hole"
            elif "slot" in fname:
                return "slot"
            else:
                return feature_name

        def get_likely_location(label, feature_name):
            fname = feature_name.lower()
            if "plane1" in fname or "top" in fname:
                return "top face"
            elif "plane2" in fname or "bottom" in fname:
                return "bottom face"
            elif "boss1" in fname or "cylindrical" in fname or "side" in fname:
                return "curved side of the cylinder"
            elif "cone" in fname or "conical" in fname:
                return "conical side"
            elif "hole" in fname:
                return "hole surface"
            elif "slot" in fname:
                return "slot surface"
            elif "face" in fname:
                return "planar face"
            else:
                return feature_name

        # Build enhanced table rows
        table_rows = []
        for label, value, datum, loc in tol_results:
            symbol = gdnt_symbols.get(label, "")
            type_with_symbol = f"{symbol} {label}" if symbol else label
            location_str = get_surface_type(loc)
            surface = get_likely_location(label, loc)

            # Extract numeric value for analysis
            numeric_value = None
            if value != "N/A":
                numeric_match = re.search(r"±?(\d+\.?\d*)", value)
                if numeric_match:
                    numeric_value = float(numeric_match.group(1))

            table_rows.append({
                "Type": type_with_symbol,
                "Value": value,
                "Numeric_Value": numeric_value,
                "Datum": datum,
                "Location": location_str,
                "Surface": surface,
                "Category": "Tolerance"
            })

        # Enhanced datum entries
        for d_letter in datum_letter_to_faceid:
            faceid = datum_letter_to_faceid[d_letter]
            feature_name = faceid_to_name.get(faceid, "")
            location_str = get_surface_type(feature_name)
            surface = get_likely_location('Datum', feature_name)

            table_rows.append({
                "Type": "📍 Datum",
                "Value": d_letter,
                "Numeric_Value": None,
                "Datum": d_letter,
                "Location": location_str,
                "Surface": surface,
                "Category": "Datum"
            })

        return table_rows

    except Exception as e:
        st.error(f"Error parsing file: {str(e)}")
        return []


def analyze_tolerances(df):
    """Perform statistical analysis on tolerance data"""
    analysis = {}

    # Filter only tolerance entries (not datums)
    tolerance_df = df[df['Category'] == 'Tolerance'].copy()

    if not tolerance_df.empty:
        # Basic statistics
        numeric_values = tolerance_df['Numeric_Value'].dropna()
        if not numeric_values.empty:
            analysis['mean_tolerance'] = numeric_values.mean()
            analysis['std_tolerance'] = numeric_values.std()
            analysis['min_tolerance'] = numeric_values.min()
            analysis['max_tolerance'] = numeric_values.max()
            analysis['median_tolerance'] = numeric_values.median()

        # Count by type
        analysis['type_counts'] = tolerance_df['Type'].value_counts().to_dict()

        # Count by location
        analysis['location_counts'] = tolerance_df['Location'].value_counts().to_dict()

        # Datum usage
        datum_usage = tolerance_df['Datum'].value_counts()
        analysis['datum_usage'] = datum_usage.to_dict()

        # Tightest and loosest tolerances
        if not numeric_values.empty:
            tightest_idx = numeric_values.idxmin()
            loosest_idx = numeric_values.idxmax()
            analysis['tightest_tolerance'] = {
                'value': numeric_values.loc[tightest_idx],
                'type': tolerance_df.loc[tightest_idx, 'Type'],
                'location': tolerance_df.loc[tightest_idx, 'Location']
            }
            analysis['loosest_tolerance'] = {
                'value': numeric_values.loc[loosest_idx],
                'type': tolerance_df.loc[loosest_idx, 'Type'],
                'location': tolerance_df.loc[loosest_idx, 'Location']
            }

    return analysis


def create_download_link(df, filename, file_format):
    """Create a download link for the dataframe with enhanced formats"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if file_format == "CSV":
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}_{timestamp}.csv" class="download-link">📥 Download CSV</a>'
    elif file_format == "Excel":
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='GD&T Tolerances')
            # Add analysis sheet if available
            if hasattr(st.session_state, 'analysis_results') and st.session_state.analysis_results:
                analysis_df = pd.DataFrame([st.session_state.analysis_results])
                analysis_df.to_excel(writer, index=False,
                                     sheet_name='Analysis')
        output.seek(0)
        b64 = base64.b64encode(output.read()).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}_{timestamp}.xlsx" class="download-link">📥 Download Excel</a>'
    elif file_format == "JSON":
        json_data = df.to_json(orient='records', indent=2)
        b64 = base64.b64encode(json_data.encode()).decode()
        href = f'<a href="data:application/json;base64,{b64}" download="{filename}_{timestamp}.json" class="download-link">📥 Download JSON</a>'
    else:  # TXT
        txt = df.to_string(index=False)
        b64 = base64.b64encode(txt.encode()).decode()
        href = f'<a href="data:file/txt;base64,{b64}" download="{filename}_{timestamp}.txt" class="download-link">📥 Download TXT</a>'

    return href


def create_visualizations(df):
    """Create enhanced visualizations for the data"""
    if df.empty:
        return None, None, None

    # Filter tolerance data
    tolerance_df = df[df['Category'] == 'Tolerance'].copy()

    if tolerance_df.empty:
        return None, None, None

    # 1. Tolerance Distribution by Type
    type_counts = tolerance_df['Type'].value_counts()
    fig1 = px.pie(
        values=type_counts.values,
        names=type_counts.index,
        title="Distribution of Tolerance Types",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig1.update_traces(textposition='inside', textinfo='percent+label')
    fig1.update_layout(
        font=dict(size=12),
        showlegend=True,
        height=400
    )

    # 2. Tolerance Values Distribution
    numeric_df = tolerance_df.dropna(subset=['Numeric_Value'])
    if not numeric_df.empty:
        fig2 = px.histogram(
            numeric_df,
            x='Numeric_Value',
            nbins=20,
            title="Distribution of Tolerance Values",
            color_discrete_sequence=['#667eea']
        )
        fig2.update_layout(
            xaxis_title="Tolerance Value",
            yaxis_title="Count",
            height=400
        )
    else:
        fig2 = None

    # 3. Location vs Tolerance Type Heatmap
    if len(tolerance_df) > 1:
        heatmap_data = tolerance_df.groupby(
            ['Location', 'Type']).size().reset_index(name='Count')
        if not heatmap_data.empty:
            pivot_data = heatmap_data.pivot(
                index='Location', columns='Type', values='Count').fillna(0)
            fig3 = px.imshow(
                pivot_data,
                title="Tolerance Types by Location",
                color_continuous_scale='Blues',
                aspect='auto'
            )
            fig3.update_layout(height=400)
        else:
            fig3 = None
    else:
        fig3 = None

    return fig1, fig2, fig3


def main():
    # Enhanced header with logos and subtitle
    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        # st.markdown("""
        # <div style='text-align: center; padding: 1rem;'>
        #     <div style='font-size: 3rem; margin-bottom: 0.5rem;'>📐</div>
        #     <div style='color: #6b7280; font-size: 0.9rem; font-weight: 500;'>GD&T</div>
        # </div>
        # """, unsafe_allow_html=True)
        st.image('./assets/unisza.png', width=250, use_container_width='auto')

    with col2:
        st.markdown(
            '<h1 class="main-header">GD&T Tolerance Extractor</h1>', unsafe_allow_html=True)
        st.markdown(
            '<p class="subtitle">Advanced STEP File Analysis for Mechanical Engineering</p>', unsafe_allow_html=True)

    with col3:
        # st.markdown("""
        # <div style='text-align: center; padding: 1rem;'>
        #     <div style='font-size: 3rem; margin-bottom: 0.5rem;'>🔧</div>
        #     <div style='color: #6b7280; font-size: 0.9rem; font-weight: 500;'>CAD</div>
        # </div>
        # """, unsafe_allow_html=True)
        st.image('./assets/frit.png', width=250, use_container_width='auto')

    # Enhanced sidebar with tabs
    st.sidebar.header("🎛️ Control Panel")

    # Sidebar tabs
    tab1, tab2, tab3 = st.sidebar.tabs(["📁 Upload", "🔍 Filter", "📊 Export"])

    with tab1:
        # File upload with enhanced styling
        st.markdown("### File Upload")
        uploaded_file = st.file_uploader(
            "Select STEP or Text File",
            type=['step', 'stp', 'txt'],
            help="Upload a STEP file containing GD&T tolerance data"
        )

        # Processing options
        st.markdown("### Processing Options")
        auto_analyze = st.checkbox("Auto-analyze after upload", value=True)
        show_raw_data = st.checkbox("Show raw extraction data", value=False)

        # Process file
        if uploaded_file is not None:
            try:
                with st.spinner("Processing file..."):
                    if uploaded_file.type == "text/plain":
                        content = str(uploaded_file.read(), "utf-8")
                    else:
                        content = str(uploaded_file.read(),
                                      "utf-8", errors='ignore')

                    st.session_state.filename = uploaded_file.name
                    st.session_state.results_data = extract_tolerance_table(
                        content)

                    # Add to processing history
                    st.session_state.processing_history.append({
                        'filename': uploaded_file.name,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'entries': len(st.session_state.results_data)
                    })

                    # Auto-analyze if enabled
                    if auto_analyze and st.session_state.results_data:
                        df = pd.DataFrame(st.session_state.results_data)
                        st.session_state.analysis_results = analyze_tolerances(
                            df)

                st.success(f"✅ Successfully processed: {uploaded_file.name}")
                st.info(
                    f"📊 Extracted {len(st.session_state.results_data)} entries")

            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")
                st.session_state.results_data = []

        # Processing history
        if st.session_state.processing_history:
            st.markdown("### 📋 Processing History")
            for i, entry in enumerate(reversed(st.session_state.processing_history[-3:])):
                with st.expander(f"{entry['filename']} - {entry['timestamp']}"):
                    st.write(f"Entries extracted: {entry['entries']}")

    with tab2:
        # Enhanced filtering options
        st.markdown("### 🔍 Filter Options")
        if st.session_state.results_data:
            df = pd.DataFrame(st.session_state.results_data)

            # Type filter
            type_options = ['All'] + sorted(df['Type'].unique().tolist())
            st.session_state.filter_settings['type_filter'] = st.selectbox(
                "Filter by Type",
                type_options,
                index=type_options.index(
                    st.session_state.filter_settings['type_filter'])
                if st.session_state.filter_settings['type_filter'] in type_options else 0
            )

            # Location filter
            location_options = ['All'] + \
                sorted(df['Location'].unique().tolist())
            st.session_state.filter_settings['location_filter'] = st.selectbox(
                "Filter by Location",
                location_options,
                index=location_options.index(
                    st.session_state.filter_settings['location_filter'])
                if st.session_state.filter_settings['location_filter'] in location_options else 0
            )

            # Datum filter
            datum_options = ['All'] + \
                sorted([d for d in df['Datum'].unique() if d])
            st.session_state.filter_settings['datum_filter'] = st.selectbox(
                "Filter by Datum",
                datum_options,
                index=datum_options.index(
                    st.session_state.filter_settings['datum_filter'])
                if st.session_state.filter_settings['datum_filter'] in datum_options else 0
            )

            # Tolerance value range filter
            tolerance_df = df[df['Category'] == 'Tolerance'].copy()
            numeric_values = tolerance_df['Numeric_Value'].dropna()
            if not numeric_values.empty:
                st.markdown("### 📏 Tolerance Range")
                min_val, max_val = float(
                    numeric_values.min()), float(numeric_values.max())
                range_values = st.slider(
                    "Tolerance Value Range",
                    min_val, max_val, (min_val, max_val),