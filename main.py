import streamlit as st
import pandas as pd
import re
import os
from io import StringIO
import base64

# Set page config
st.set_page_config(
    page_title="GD&T Tolerance Extractor",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #003366;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .stDataFrame {
        background-color: #f8f9fa;
    }
    .success-message {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .error-message {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .info-box {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'results_data' not in st.session_state:
    st.session_state.results_data = []
if 'filename' not in st.session_state:
    st.session_state.filename = ""


def extract_tolerance_table(text):
    """Extract tolerance values and datums from STEP/text file"""
    lines = text.splitlines()
    # Build a dictionary mapping entity IDs to their lines
    line_dict = {
        re.match(r"(#\d+)\s*=", line).group(1): line.strip()
        for line in lines if re.match(r"(#\d+)\s*=", line)
    }

    # Regex patterns for tolerance, datum, and shape aspect entities
    tol_pattern = re.compile(
        r"(#\d+)\s*=\s*(CYLINDRICITY|FLATNESS|STRAIGHTNESS|ROUNDNESS)_TOLERANCE"
        r"\(\s*'([^']*)'\s*,\s*''\s*,\s*(#\d+)", re.IGNORECASE
    )
    datum_pattern = re.compile(
        r"#\d+\s*=\s*DATUM_FEATURE\(\s*'[^']*?\((\w)\)'", re.IGNORECASE
    )
    shape_aspect_pattern = re.compile(
        r"#\d+\s*=\s*SHAPE_ASPECT\('([^']*?)\((\w)?'?,.*?#(\d+)\)"
    )

    tol_results = []  # List of tolerance results
    datum_results = {}  # Mapping of datum letters to locations
    face_to_plane = {}  # Mapping of face IDs to surface types

    # Build datum letter to face ID and feature name mapping
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

    # Map face IDs to shape descriptions (Plane1, Plane2, Boss1, etc.)
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
        face_to_plane[plane_id] = location
        if datum_letter:
            datum_results[datum_letter] = location

    # Extract tolerances and associate with datums and locations
    for tol_id, tol_type, tol_name, ref_id in tol_pattern.findall(text):
        definition = line_dict.get(ref_id, "")
        value_match = re.search(
            r"(?:LENGTH_MEASURE|VALUE_REPRESENTATION_ITEM)\s*\(\s*([\d.]+)", definition
        )
        value = f"±{value_match.group(1)}" if value_match else "N/A"
        label = "Circularity" if tol_type.upper() == "ROUNDNESS" else tol_type.capitalize()

        # Find the last # reference in the tolerance line for datum mapping
        tol_line = next((l for l in lines if tol_id in l), "")
        ref_ids = re.findall(r"#(\d+)", tol_line)
        datum_ref_id = ref_ids[-1] if ref_ids else ref_id

        # Map datum_ref_id to datum letter and location
        datum_letter = ""
        location = ""
        for letter, faceid in datum_letter_to_faceid.items():
            if faceid == datum_ref_id:
                datum_letter = letter
                location = faceid_to_name.get(
                    faceid, face_to_plane.get(faceid, ""))
                break

        if not datum_letter:
            # Fallback to previous logic if not found
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

    # GD&T symbol mapping for output
    gdnt_symbols = {
        "Straightness": "─",
        "Flatness": "☐",
        "Circularity": "○",
        "Cylindricity": "⌀"
    }

    # Helper to map feature name to surface type (for Location column)
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
        else:
            return feature_name

    # Helper to map feature name and type to Surface (for Surface column)
    def get_likely_location(label, feature_name):
        fname = feature_name.lower()
        if "plane1" in fname or "top" in fname:
            return "top face (facing +Z)"
        elif "plane2" in fname or "bottom" in fname:
            return "bottom face (facing -Z)"
        elif "boss1" in fname or "cylindrical" in fname or "side" in fname:
            return "curved side of the cylinder"
        elif "cone" in fname or "conical" in fname:
            return "conical side"
        elif "face" in fname:
            return "planar face"
        else:
            return feature_name

    # Parse DIRECTION and AXIS2_PLACEMENT_3D for axis orientation
    direction_map = {}  # Maps DIRECTION entity IDs to vectors
    axis_map = {}       # Maps AXIS2_PLACEMENT_3D IDs to direction IDs
    plane_map = {}      # Maps PLANE IDs to AXIS2_PLACEMENT_3D IDs

    for line in lines:
        # Parse DIRECTION entity
        dir_match = re.match(
            r"#(\d+)=DIRECTION\('[^']*',\(([^)]*)\)\);", line)
        if dir_match:
            dir_id, vec = dir_match.groups()
            vec = tuple(float(x) for x in vec.split(","))
            direction_map[dir_id] = vec

        # Parse AXIS2_PLACEMENT_3D entity
        axis_match = re.match(
            r"#(\d+)=AXIS2_PLACEMENT_3D\('[^']*',#(\d+),#(\d+),#(\d+)\);", line)
        if axis_match:
            axis_id, pt_id, dir1_id, dir2_id = axis_match.groups()
            axis_map[axis_id] = (dir1_id, dir2_id)

        # Parse PLANE entity
        plane_match = re.match(r"#(\d+)=PLANE\('[^']*',#(\d+)\);", line)
        if plane_match:
            plane_id, axis_id = plane_match.groups()
            plane_map[plane_id] = axis_id

    # Helper to get axis orientation from plane_id
    def get_axis_orientation(plane_id):
        axis_id = plane_map.get(plane_id)
        if not axis_id:
            return "unknown axis"
        dir_ids = axis_map.get(axis_id)
        if not dir_ids:
            return "unknown axis"
        dir_vec = direction_map.get(dir_ids[0])
        if not dir_vec:
            return "unknown axis"
        axis_labels = ["X", "Y", "Z"]
        axis_vectors = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
        dot_products = [abs(sum(a*b for a, b in zip(dir_vec, axis)))
                        for axis in axis_vectors]
        max_idx = dot_products.index(max(dot_products))
        sign = '+' if dir_vec[max_idx] >= 0 else '-'
        return f"facing {sign}{axis_labels[max_idx]}"

    # Build table rows for results
    table_rows = []
    for label, value, datum, loc in tol_results:
        symbol = gdnt_symbols.get(label, "")
        type_with_symbol = f"{symbol} {label}" if symbol else label
        location_str = get_surface_type(loc)
        surface = get_likely_location(label, loc)

        # If planar face, try to get axis orientation
        axis_info = ""
        for pid in plane_map:
            if location_str.startswith("top face") or location_str.startswith("bottom face"):
                axis_info = get_axis_orientation(pid)
                break
        if axis_info and axis_info != "unknown axis":
            surface = f"{location_str} ({axis_info})"

        table_rows.append({
            "Type": type_with_symbol,
            "Value": value,
            "Datum": datum,
            "Location": location_str,
            "Surface": surface
        })

    # Add datums
    for d_letter in datum_letter_to_faceid:
        faceid = datum_letter_to_faceid[d_letter]
        feature_name = faceid_to_name.get(faceid, "")
        location_str = get_surface_type(feature_name)
        surface = get_likely_location('Datum', feature_name)

        # If planar face, try to get axis orientation
        axis_info = ""
        for pid in plane_map:
            if location_str.startswith("top face") or location_str.startswith("bottom face"):
                axis_info = get_axis_orientation(pid)
                break
        if axis_info and axis_info != "unknown axis":
            surface = f"{location_str} ({axis_info})"

        table_rows.append({
            "Type": "Datum",
            "Value": d_letter,
            "Datum": d_letter,
            "Location": location_str,
            "Surface": surface
        })

    return table_rows


def create_download_link(df, filename, file_format):
    """Create a download link for the dataframe"""
    if file_format == "CSV":
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv">Download CSV file</a>'
    elif file_format == "Excel":
        # Use BytesIO for Excel
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='GD&T Tolerances')
        output.seek(0)
        b64 = base64.b64encode(output.read()).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}.xlsx">Download Excel file</a>'
    else:  # TXT
        txt = df.to_string(index=False)
        b64 = base64.b64encode(txt.encode()).decode()
        href = f'<a href="data:file/txt;base64,{b64}" download="{filename}.txt">Download TXT file</a>'

    return href

# Main App Layout


def main():
    # Header with logos (placeholder for now)
    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        st.markdown("**📐 GD&T**")

    with col2:
        st.markdown(
            '<h1 class="main-header">GD&T Tolerance Value Extractor</h1>', unsafe_allow_html=True)

    with col3:
        st.markdown("**🔧 CAD**")

    # Sidebar for controls
    st.sidebar.header("📋 Controls")

    # File upload
    uploaded_file = st.sidebar.file_uploader(
        "Upload STEP or Text File",
        type=['step', 'stp', 'txt'],
        help="Select a STEP or text file containing GD&T tolerance data"
    )

    # Process file
    if uploaded_file is not None:
        try:
            # Read file content
            if uploaded_file.type == "text/plain":
                content = str(uploaded_file.read(), "utf-8")
            else:
                content = str(uploaded_file.read(), "utf-8", errors='ignore')

            # Store filename
            st.session_state.filename = uploaded_file.name

            # Extract tolerance data
            st.session_state.results_data = extract_tolerance_table(content)

            # Show success message
            st.sidebar.success(f"✅ File loaded: {uploaded_file.name}")

        except Exception as e:
            st.sidebar.error(f"❌ Error reading file: {str(e)}")
            st.session_state.results_data = []

    # Export options
    if st.session_state.results_data:
        st.sidebar.header("💾 Export Options")

        export_format = st.sidebar.selectbox(
            "Select Export Format",
            ["CSV", "Excel", "TXT"],
            help="Choose the format for exporting results"
        )

        # Create DataFrame
        df = pd.DataFrame(st.session_state.results_data)

        # Generate download link
        if st.sidebar.button("📥 Generate Download Link"):
            filename = os.path.splitext(st.session_state.filename)[
                0] if st.session_state.filename else "gdt_results"
            download_link = create_download_link(df, filename, export_format)
            st.sidebar.markdown(download_link, unsafe_allow_html=True)

    # Clear results
    if st.sidebar.button("🗑️ Clear Results"):
        st.session_state.results_data = []
        st.session_state.filename = ""
        st.sidebar.success("Results cleared!")

    # Main content area
    st.markdown("---")

    # Display current file
    if st.session_state.filename:
        st.markdown(f"**📁 Current File:** {st.session_state.filename}")

    # Display results
    if st.session_state.results_data:
        st.header("📊 Extracted GD&T Tolerance Data")

        # Create DataFrame and display
        df = pd.DataFrame(st.session_state.results_data)

        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Entries", len(df))
        with col2:
            tolerances = df[df['Type'] != 'Datum']
            st.metric("Tolerances", len(tolerances))
        with col3:
            datums = df[df['Type'] == 'Datum']
            st.metric("Datums", len(datums))

        # Display table
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Type": st.column_config.TextColumn("Type", width="medium"),
                "Value": st.column_config.TextColumn("Value", width="small"),
                "Datum": st.column_config.TextColumn("Datum", width="small"),
                "Location": st.column_config.TextColumn("Location", width="medium"),
                "Surface": st.column_config.TextColumn("Surface", width="large")
            }
        )

        # Display summary by type
        st.subheader("📈 Summary by Type")
        type_summary = df.groupby('Type').size().reset_index(name='Count')
        st.bar_chart(type_summary.set_index('Type'))

    else:
        # Instructions when no file is loaded
        st.markdown("""
        <div class="info-box">
            <h3>📋 How to use this application:</h3>
            <ol>
                <li>Upload a STEP (.step, .stp) or text file containing GD&T tolerance data using the sidebar</li>
                <li>The application will automatically extract tolerance values, datums, and surface information</li>
                <li>Review the extracted data in the table below</li>
                <li>Export the results in CSV, Excel, or TXT format</li>
            </ol>
            <p><strong>Note:</strong> The application supports various tolerance types including Straightness, Flatness, Circularity, and Cylindricity.</p>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
