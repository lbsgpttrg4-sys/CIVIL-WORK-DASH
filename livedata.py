import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import requests
import io

# --- CONFIGURATION ---
PRIMARY_COLOR = "#1E3A8A" # Dark professional blue
SECONDARY_COLOR = "#4B5563" # Muted text gray
BACKGROUND_COLOR = "#F0F2F6" # Very light background
CARD_COLOR = "#FFFFFF"
COLOR_SEQUENCE = ["#1E3A8A", "#636EF5", "#A3A7F4", "#C6C9F9", "#00A86B", "#FFD700", "#DC3545"] # Expanded sequence for charts

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Civil Works Dashboard",
    page_icon="🏛️",
    layout="wide"
)

# --- CUSTOM CSS (Professional Styling) ---
st.markdown(f"""
    <style>
    /* Global overrides for a clean look */
    .stApp {{
        background-color: {BACKGROUND_COLOR};
    }}
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 1rem;
    }}

    /* 1. Main Headers */
    .main-header {{
        font-size: 2.8rem;
        font-weight: 800;
        color: {PRIMARY_COLOR};
        text-align: center;
        margin-bottom: 0rem;
    }}
    .sub-header {{
        font-size: 1.2rem;
        color: {SECONDARY_COLOR};
        text-align: center;
        margin-bottom: 2rem;
    }}
    
    /* 2. Metric Cards (KPIs) - Targetting Streamlit's stMetric class */
    .stMetric {{
        background-color: {CARD_COLOR};
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    .stMetric label {{ /* Metric Title */
        font-size: 1.1rem;
        color: {SECONDARY_COLOR};
        font-weight: 600;
    }}
    .stMetric div[data-testid="stMetricValue"] {{ /* Metric Value */
        font-size: 2.5rem;
        color: {PRIMARY_COLOR};
        font-weight: 700;
    }}
    
    /* 3. Department Buttons */
    .stButton button {{
        width: 100%;
        height: 4rem; /* Increased height for prominence */
        font-weight: bold;
        border-radius: 10px;
        background-color: {PRIMARY_COLOR};
        color: white;
        border: none;
        transition: all 0.2s;
    }}
    .stButton button:hover {{
        background-color: #0F377A; /* Darker shade on hover */
    }}
    
    /* 4. Chart Headers (Used for st.subheader) */
    h2 {{
        color: {PRIMARY_COLOR};
        border-bottom: 2px solid #E5E7EB;
        padding-bottom: 5px;
        margin-top: 1.5rem;
    }}
    
    /* 5. Link Style */
    .sub-link a {{
        color: #64748B;
        text-decoration: none;
        font-size: 0.9rem;
        display: block;
        text-align: center;
        margin-bottom: 2rem;
    }}
    </style>
""", unsafe_allow_html=True)


# --- PLOTLY CONFIGURATION (Professional Theme and Text Size) ---
# Define a base layout template for clean, readable charts
BASE_LAYOUT = go.Layout(
    template='plotly_white', # Professional white theme
    font=dict(size=12, family="Arial"), # Consistent global font size
    title_font_size=18,
    legend_font_size=12,
    xaxis=dict(title_font_size=14, tickfont_size=12),
    yaxis=dict(title_font_size=14, tickfont_size=12),
    hoverlabel=dict(font_size=12) # Consistent hover text size
)

def update_fig_layout(fig):
    """Applies the base layout and professional styling to a Plotly figure."""
    fig.update_layout(BASE_LAYOUT)
    fig.update_traces(marker=dict(line=dict(width=0.5, color='DarkSlateGrey'))) # Subtle borders on traces
    return fig

# --- PROJECT CATEGORIZATION LOGIC ---
def categorize_project_revised(description):
    """
    Categorizes a project description into one of the predefined types.
    """
    desc = str(description).upper()
    
    # 1. AWC Building
    if 'ANGANWADI' in desc or 'AWC' in desc:
        return 'AWC Building'
    
    # 2. Medical Building (Health facilities/hospitals/colleges)
    if 'HOSPITAL' in desc or 'PHC' in desc or 'SUB HEALTH CENTER' in desc or ('MEDICAL' in desc and ('COLLEGE' in desc or 'HEALTH' in desc)):
        return 'Medical Building'
    
    # 3. School/Hostel/Education Building
    if 'SCHOOL' in desc or 'KGBV' in desc or 'ZPHS' in desc or 'HOSTEL' in desc or 'PATASHALA' in desc or 'EDUCATION' in desc or 'LIBRARY' in desc:
        return 'School/Hostel'
    
    # 4. Water/Borewell
    if 'BORE WELL' in desc or 'SUBMERSIBLE PUMPSET' in desc or 'WATER SUPPLY' in desc or 'RWS' in desc or 'SUMP' in desc or 'OVERHEAD' in desc or 'PIPELINE' in desc:
        return 'Water/Borewell'
    
    # 5. CC Road/Drain
    if 'CC ROAD' in desc or 'CC DRAIN' in desc or 'SIDE DRAIN' in desc:
        return 'CC Road/Drain'
    
    # 6. Major Road/Bridge
    if 'PWD ROAD' in desc or 'ZP ROAD' in desc or 'RNB' in desc or 'RENEWAL' in desc or 'WIDENING' in desc or 'STRENGTHENING' in desc or 'BRIDGE' in desc or 'ROAD' in desc or 'R/F' in desc or 'IMPROVEMENTS' in desc:
        return 'Major Road/Bridge'
    
    # 7. Other Building/Civil Works (General/Miscellaneous buildings, including quarters)
    if 'BUILDING' in desc or 'GP' in desc or 'MPP' in desc or 'COMMUNITY HALL' in desc or 'MARKET' in desc or 'BUS STAND SHELTER' in desc or 'TEMPLE' in desc or 'MASJID' in desc or 'COMPLEX' in desc or 'WALL' in desc or 'PACS' in desc or 'ARCH GATE' in desc or 'PILGRIM SHED' in desc or 'PRASADAM COUNTERS' in desc or 'KALYANA KATTA' in desc or 'VAIKUNTA DHAMAM' in desc or 'COMPOUND WALL' in desc or 'ELECTRICAL' in desc or 'VIGRAHAM' in desc or 'HARATHI' in desc or 'PILLARS' in desc or 'CONSTRUCTION OF' in desc or 'BALANCE WORK' in desc or 'FORMATION' in desc or 'QUARTERS' in desc or 'RESIDENTIAL' in desc:
        return 'Other Building/Civil Works'
        
    return 'Uncategorized'


# --- HELPER FUNCTIONS ---

def normalize_budget(value):
    """Standardizes budget strings to Float (Lakhs)."""
    if pd.isna(value):
        return 0.0
    s_val = str(value).lower().replace(',', '').strip()
    numeric_part = re.findall(r"[-+]?\d*\.\d+|\d+", s_val)
    if not numeric_part:
        return 0.0
    number = float(numeric_part[0])
    if "crore" in s_val or "cr" in s_val:
        return number * 100
    elif "lakh" in s_val:
        return number
    elif number > 10000: 
        return number / 100000
    else:
        return number

def clean_dataframe(df, dept_name=None):
    """Standardizes column names and adds Department column."""
    col_map = {}
    for col in df.columns:
        c_lower = str(col).lower()
        if "work name" in c_lower: col_map[col] = "Work Name"
        elif "budget" in c_lower: col_map[col] = "Budget (Lakhs)"
        elif "mandal" in c_lower: col_map[col] = "Mandal"
        elif "village" in c_lower: col_map[col] = "Village"
        elif "agency" in c_lower: col_map[col] = "Agency"
        elif "contractor" in c_lower: col_map[col] = "Contractor"
        elif "stage" in c_lower: col_map[col] = "Status"
        elif "issues" in c_lower: col_map[col] = "Issues"
        elif "completed" in c_lower: col_map[col] = "Is Completed"
        elif "admin sanction date" in c_lower: col_map[col] = "Sanction Date"
        elif "scheme" in c_lower: col_map[col] = "Scheme"
        elif "priority" in c_lower: col_map[col] = "Priority"
        elif "sl. no" in c_lower: col_map[col] = "Sl. No."

    df = df.rename(columns=col_map)
    
    # Add Department Name Column
    if dept_name:
        df["Department"] = dept_name
    
    # Clean Budget
    if "Budget (Lakhs)" in df.columns:
        df["Normalized Budget"] = df["Budget (Lakhs)"].apply(normalize_budget)
    else:
        df["Normalized Budget"] = 0.0

    # Clean Mandal
    if "Mandal" in df.columns:
        df["Mandal"] = df["Mandal"].fillna("N/A")
        df["Mandal"] = df["Mandal"].astype(str).str.strip().str.title()
        df.loc[df["Mandal"].isin(["Nan", "NaN", "", "None", "Nat"]), "Mandal"] = "N/A"
    else:
        df["Mandal"] = "N/A"

    # Clean Priority (Ensure 0 or 1)
    if "Priority" not in df.columns:
        df["Priority"] = 0
    else:
        # Convert to numeric, errors become NaN, then fill with 0
        df["Priority"] = pd.to_numeric(df["Priority"], errors='coerce').fillna(0).astype(int)

    # Clean Completion Status
    def determine_status(row):
        if "Is Completed" in row and row["Is Completed"] == 1:
            return "Completed"
        if "Status" in row:
            val = str(row["Status"]).lower().strip()
            if val in ["nan", "none", "", "nat"]:
                return "N/A"
            if "complete" in val:
                return "Completed"
            return "In Progress"
        return "N/A"

    df["Status Label"] = df.apply(determine_status, axis=1)

    # Clean Issues
    if "Issues" in df.columns:
        df["Issues"] = df["Issues"].fillna("").astype(str)
    else:
        df["Issues"] = ""

    return df

def load_data(file_obj):
    try:
        xls = pd.read_excel(file_obj, sheet_name=None, header=1)
        return xls
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

@st.cache_data(ttl=600)
def fetch_google_sheet(sheet_id):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return io.BytesIO(response.content)
        else:
            st.error(f"Failed to download sheet. Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching data from Google Sheets: {e}")
        return None

# --- MOCK DATA ---
def get_mock_data():
    pr_df = pd.DataFrame({
        "Sl. No.": [1, 2, 3, 4, 5],
        "Work Name": ["PWD Road T02", "ZP Road Vajenepalli", "ZP Road Lingapur", "Anganwadi Center 1", "Anganwadi Center 2"],
        "Mandal": ["Mahamutharam", "mahamutharam", "Mahamutharam", "", "Mahamutharam"],
        "Budget (Lakhs)": [60, 180, 93, 16, 16],
        "Status": ["Progress", "Progress", "Progress", "Completed", ""],
        "Issues": ["", "Land Acquisition", "", "", "Funds"],
        "Priority": [0, 1, 0, 0, 1] # Mock priority
    })
    med_df = pd.DataFrame({
        "Sl. No.": [1, 2, 3, 4],
        "Work Name": ["Nursing College", "Critical Care Block", "Sub Centre Regonda", "Sub Centre Thirumalagiri"],
        "Mandal": ["Bhupalpally", "Bhupalpally", "Regonda", "Regonda"],
        "Budget (Lakhs)": [2600, 2375, 20, 20],
        "Status": ["Retaining wall", "Painting", "Completed", "Completed"],
        "Issues": ["Site Dispute", "", "", ""],
        "Priority": [1, 1, 0, 0] # Mock priority
    })
    return {
        "PR": clean_dataframe(pr_df, "PR"),
        "Medical": clean_dataframe(med_df, "Medical"),
    }

# --- STATE MANAGEMENT ---
if 'view' not in st.session_state:
    st.session_state.view = 'Home'
if 'selected_dept' not in st.session_state:
    st.session_state.selected_dept = None
# Initialize session state for data
if 'data_sheets' not in st.session_state:
    st.session_state.data_sheets = {}
if 'last_source' not in st.session_state:
    st.session_state.last_source = None
if 'uploaded_file_hash' not in st.session_state:
    st.session_state.uploaded_file_hash = None

def switch_view(view_name, dept=None):
    st.session_state.view = view_name
    st.session_state.selected_dept = dept

# --- DATA LOADING ---
st.sidebar.header("Data Source")
source_option = st.sidebar.radio("Select Source:", ["Google Sheet (Live)", "Upload Excel File", "Use Demo Data"])

SHEET_ID = "13Um7uOhz_zAAvMqCpfO-tppyZPoRT6RK"

# Logic to determine if a refresh/re-load is needed (e.g., source changed)
needs_reload = False
if source_option != st.session_state.last_source:
    needs_reload = True
    st.session_state.last_source = source_option

if source_option == "Google Sheet (Live)":
    # Reload if the button is pressed, or if it's the first time running this source AND no data exists
    if st.sidebar.button("🔄 Refresh Data") or (needs_reload and not st.session_state.data_sheets):
        st.cache_data.clear()
        with st.spinner('Fetching data from Google Sheets...'):
            excel_file = fetch_google_sheet(SHEET_ID)
            if excel_file:
                raw_sheets = load_data(excel_file)
                if raw_sheets:
                    temp_data_sheets = {sheet_name: clean_dataframe(df, sheet_name) for sheet_name, df in raw_sheets.items()}
                    st.session_state.data_sheets = temp_data_sheets
                    st.sidebar.success("Data Loaded Successfully!")

elif source_option == "Upload Excel File":
    uploaded_file = st.sidebar.file_uploader("Upload Kataram Civil Works Excel", type=["xlsx", "xls"])
    
    uploaded_file_hash = uploaded_file.file_id if uploaded_file else None
    
    # Reload if a new file is uploaded (different hash) or if the source changed
    if uploaded_file and (uploaded_file_hash != st.session_state.uploaded_file_hash or needs_reload):
        with st.spinner('Processing uploaded file...'):
            raw_sheets = load_data(uploaded_file)
            if raw_sheets:
                temp_data_sheets = {sheet_name: clean_dataframe(df, sheet_name) for sheet_name, df in raw_sheets.items()}
                st.session_state.data_sheets = temp_data_sheets
                st.session_state.uploaded_file_hash = uploaded_file_hash
                st.sidebar.success("File Processed Successfully!")
    elif not st.session_state.data_sheets:
        st.info("Please upload an Excel file to begin.")
        
else: # Use Demo Data
    if needs_reload or not st.session_state.data_sheets:
        st.session_state.data_sheets = get_mock_data()
        st.sidebar.info("Using Demo Data.")

# Stop if no data is loaded
if not st.session_state.data_sheets:
    if source_option != "Upload Excel File": # Allow upload widget to persist
        st.stop()
    else:
        # If it's an upload but no file has been processed yet, stop execution
        if not uploaded_file: 
            st.stop()


# Alias the session state data for easier access in the rest of the script
data_sheets = st.session_state.data_sheets
master_df = pd.concat(data_sheets.values(), ignore_index=True)


# --- APPLY PROJECT CATEGORIZATION ---
if not master_df.empty and "Work Name" in master_df.columns:
    master_df["Project Type"] = master_df["Work Name"].apply(categorize_project_revised)


# --- DASHBOARD LOGIC ---

# 1. Main Header
st.markdown('<div class="main-header">Civil Works Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Kataram Division - Summary Overview</div>', unsafe_allow_html=True)
sheet_url = "https://docs.google.com/spreadsheets/d/13Um7uOhz_zAAvMqCpfO-tppyZPoRT6RK/edit?usp=sharing&ouid=107329449050851078771&rtpof=true&sd=true"

st.markdown(
    f'<div class="sub-link"><a href="{sheet_url}" target="_blank">🔗 Open Source Data Sheet</a></div>',
    unsafe_allow_html=True
)


if st.session_state.view == 'Home':
    if master_df.empty:
        st.warning("No data available.")
    else:
        # Create Tabs
        tab_summary, tab_priority = st.tabs(["📊 Summary", "🔥 High Priority Projects"])

        with tab_summary:
            # KPIS
            total_projects = len(master_df)
            total_investment = master_df["Normalized Budget"].sum()
            issues_df = master_df[
                (master_df["Issues"].str.len() > 1) & 
                (master_df["Issues"].str.lower() != "nan") & 
                (master_df["Issues"].str.strip() != "-")
            ]
            total_issues = len(issues_df)
            completed_total = len(master_df[master_df["Status Label"] == "Completed"])
            completion_rate = int((completed_total / total_projects * 100)) if total_projects > 0 else 0

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total Projects", total_projects)
            k2.metric("Total Investment", f"₹{total_investment:,.0f} Lakhs")
            k3.metric("Overall Completion", f"{completion_rate}%", f"{completed_total} Works")
            k4.metric("Total Issues", total_issues, delta_color="inverse")

            st.divider()

            # Charts
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("🛠️ Project Count by Type")
                
                if "Project Type" in master_df.columns:
                    # Group by Department and Project Type for hierarchical treemap
                    project_type_counts = master_df.groupby(["Department", "Project Type"]).size().reset_index(name="Count")
                    
                    # Treemap
                    fig_treemap = px.treemap(
                        project_type_counts, 
                        path=[px.Constant("All Projects"), 'Department', 'Project Type'], 
                        values='Count',
                        color='Project Type',
                        title="",
                        color_discrete_sequence=COLOR_SEQUENCE
                    )
                    
                    # Customize hover text and appearance
                    fig_treemap.data[0].textinfo = 'label+value'
                    fig_treemap.data[0].hovertemplate = (
                        '<b>%{label}</b><br>' +
                        'Projects: %{value}<br>' +
                        'Total: %{percentRoot:.1f}%<extra></extra>' 
                    )
                    # Apply professional styling and increased font size for readability
                    fig_treemap = update_fig_layout(fig_treemap)
                    fig_treemap.update_traces(textfont=dict(size=14))
                    fig_treemap.update_layout(margin = dict(t=0, l=0, r=0, b=0))
                    
                    st.plotly_chart(fig_treemap, use_container_width=True)
                else:
                    st.info("Work Name column is not available to categorize projects.")

            with c2:
                st.subheader("📊 Project Status by Dept (100% Stacked)")
                status_by_dept = master_df.groupby(["Department", "Status Label"]).size().reset_index(name="Count")
                dept_totals = status_by_dept.groupby("Department")["Count"].transform("sum")
                
                # Calculate total works per department for X-axis label
                total_works_per_dept = master_df.groupby("Department").size().reset_index(name="Total Works")
                total_works_per_dept = total_works_per_dept.sort_values(by="Department") # Ensure sorting matches plot
                
                # Prepare custom tick labels
                dept_tickvals = total_works_per_dept["Department"].tolist()
                dept_ticktext = [f"{dept}<br>({count} works)" for dept, count in zip(dept_tickvals, total_works_per_dept["Total Works"])]
                
                # Ensure percentage is calculated for each department
                status_by_dept["Percentage"] = (status_by_dept["Count"] / dept_totals * 100).fillna(0)
                # Label contains both count and percentage
                status_by_dept["Label"] = status_by_dept.apply(lambda x: f"{x['Count']}<br>({x['Percentage']:.0f}%)", axis=1)
                
                color_map = {"Completed": "#28a745", "In Progress": "#DC3545", "N/A": "#6c757d"} # Green/Red/Gray for status
                
                fig_status = px.bar(
                    status_by_dept, 
                    x="Department", 
                    y="Percentage", 
                    color="Status Label", 
                    color_discrete_map=color_map, 
                    text="Label", 
                    barmode="stack", 
                    title=""
                )
                
                # Apply professional styling
                fig_status = update_fig_layout(fig_status)
                
                # Customization for the X-axis labels
                fig_status.update_layout(
                    xaxis=dict(
                        tickmode='array',
                        tickvals=dept_tickvals,
                        ticktext=dept_ticktext,
                        title_text="Department" # Override default title
                    ),
                    yaxis_tickformat='.0f', 
                    yaxis_title='Percentage of Total Projects'
                )

                fig_status.update_traces(textposition='inside', insidetextanchor='middle', textfont=dict(size=12))
                st.plotly_chart(fig_status, use_container_width=True)

            st.subheader("⚠️ Issues by Department")
            if not issues_df.empty:
                issues_count = issues_df.groupby("Department").size().reset_index(name="Count")
                total_issues_val = issues_count["Count"].sum()
                issues_count["Percentage"] = (issues_count["Count"] / total_issues_val * 100).fillna(0)
                issues_count["Label"] = issues_count.apply(lambda x: f"{x['Count']}<br>({x['Percentage']:.1f}%)", axis=1)
                
                fig_issues = px.bar(issues_count, x="Department", y="Count", color="Department", text="Label", title="", color_discrete_sequence=COLOR_SEQUENCE)
                # Apply professional styling and increased font size
                fig_issues = update_fig_layout(fig_issues)
                fig_issues.update_traces(textposition='outside', textfont=dict(size=12))
                st.plotly_chart(fig_issues, use_container_width=True)
            else:
                st.info("No reported issues found.")
            
            st.divider()
            st.subheader("📂 Department Details")
            dept_list = list(data_sheets.keys())
            cols = st.columns(4)
            for i, dept in enumerate(dept_list):
                with cols[i % 4]:
                    d_rows = len(data_sheets[dept])
                    if st.button(f"{dept}\n({d_rows} Works)", key=f"btn_{dept}"):
                        switch_view('Department', dept)
                        st.rerun()

        with tab_priority:
            st.subheader("🔥 High Priority Projects (All Departments)")
            priority_df = master_df[master_df["Priority"] == 1]
            
            if priority_df.empty:
                st.info("No projects marked as High Priority (Priority = 1).")
            else:
                # Column Config for Tables
                common_col_config = {
                    "Work Name": st.column_config.TextColumn("Work Name", width="large", help="Name of the project"),
                    "Sl. No.": st.column_config.NumberColumn("Sl. No.", width="small"),
                    "Department": st.column_config.TextColumn("Dept", width="small"),
                    "Status Label": st.column_config.TextColumn("Status", width="medium"),
                    "Issues": st.column_config.TextColumn("Issues", width="medium"),
                }
                
                # Order columns: Work Name first
                cols_to_show = ["Sl. No.", "Work Name", "Department", "Village", "Mandal", "Status Label", "Budget (Lakhs)", "Issues", "Contractor"]
                existing_cols = [c for c in cols_to_show if c in priority_df.columns]
                
                st.dataframe(
                    priority_df[existing_cols],
                    use_container_width=True,
                    hide_index=True,
                    column_config=common_col_config
                )

elif st.session_state.view == 'Department':
    dept = st.session_state.selected_dept
    df = data_sheets.get(dept, pd.DataFrame())

    if df.empty:
        st.error("No data found.")
        if st.button("⬅️ Back"):
            switch_view('Home')
            st.rerun()
    else:
        h1, h2 = st.columns([1, 5])
        with h1:
            if st.button("⬅️ Back to Summary"):
                switch_view('Home')
                st.rerun()
        with h2:
            st.title(f"{dept} Department")

        # Filters
        f1, f2, f3, f4 = st.columns(4)
        mandals = ["All"] + sorted(df["Mandal"].unique().tolist()) if "Mandal" in df.columns else ["All"]
        sel_mandal = f1.selectbox("Filter by Mandal", mandals)
        show_pending = f2.toggle("Pending Only")
        show_issues = f3.toggle("Issues Only")
        show_priority = f4.toggle("⭐ Priority Only") 

        filtered_df = df.copy()
        if sel_mandal != "All":
            filtered_df = filtered_df[filtered_df["Mandal"] == sel_mandal]
        if show_pending:
            filtered_df = filtered_df[filtered_df["Status Label"] != "Completed"]
        if show_issues and "Issues" in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df["Issues"].str.len() > 1) & 
                (filtered_df["Issues"].str.lower() != "nan") & 
                (filtered_df["Issues"].str.strip() != "-")
            ]
        if show_priority:
            filtered_df = filtered_df[filtered_df["Priority"] == 1]

        # Stats
        d_total = len(filtered_df)
        d_budget = filtered_df["Normalized Budget"].sum() if "Normalized Budget" in filtered_df.columns else 0
        d_completed = len(filtered_df[filtered_df["Status Label"] == "Completed"])
        
        st.markdown("#### Snapshot")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Works", d_total)
        s2.metric("Budget", f"₹{d_budget:,.1f} L")
        s3.metric("Completed", d_completed)
        s4.metric("Pending", d_total - d_completed)

        st.divider()
        st.subheader("📊 Analytics")
        if not filtered_df.empty:
            dc1, dc2 = st.columns(2)
            with dc1:
                status_counts = filtered_df["Status Label"].value_counts().reset_index()
                status_counts.columns = ["Status", "Count"]
                color_map = {"Completed": "#28a745", "In Progress": "#DC3545", "N/A": "#6c757d"}
                fig_dept_pie = px.pie(status_counts, values='Count', names='Status', hole=0.4, color='Status', color_discrete_map=color_map, title="Completion Status")
                # Apply professional styling and increased font size
                fig_dept_pie = update_fig_layout(fig_dept_pie)
                fig_dept_pie.update_traces(textinfo='value+percent', textfont=dict(size=12))
                st.plotly_chart(fig_dept_pie, use_container_width=True)
            with dc2:
                if "Mandal" in filtered_df.columns and "Normalized Budget" in filtered_df.columns:
                    budget_mandal = filtered_df.groupby("Mandal")["Normalized Budget"].sum().reset_index()
                    total_dept_budget = budget_mandal["Normalized Budget"].sum()
                    budget_mandal["Percentage"] = (budget_mandal["Normalized Budget"] / total_dept_budget * 100).fillna(0)
                    budget_mandal["Label"] = budget_mandal.apply(lambda x: f"₹{x['Normalized Budget']:,.0f}L<br>({x['Percentage']:.1f}%)", axis=1)
                    fig_dept_bar = px.bar(budget_mandal, x="Mandal", y="Normalized Budget", title="Budget by Mandal", text="Label", color_discrete_sequence=COLOR_SEQUENCE)
                    # Apply professional styling and increased font size
                    fig_dept_bar = update_fig_layout(fig_dept_bar)
                    fig_dept_bar.update_traces(textposition='outside', textfont=dict(size=12))
                    st.plotly_chart(fig_dept_bar, use_container_width=True)
        
        st.markdown("#### Detailed Works List")
        
        # TABLE CONFIGURATION
        # 1. Hide Normalized Budget, Status Label, Department, Priority, Is Completed
        cols_to_hide = ["Normalized Budget", "Status Label", "Department", "Priority", "Is Completed", "Project Type"] 
        
        # 2. Prioritize Column Order: Sl. No, Work Name, Village, Mandal, Status...
        desired_order = ["Sl. No.", "Work Name", "Village", "Mandal", "Status", "Budget (Lakhs)", "Issues", "Contractor", "Sanction Date"]
        # Add remaining columns that are not in desired_order or cols_to_hide
        remaining_cols = [c for c in filtered_df.columns if c not in desired_order and c not in cols_to_hide]
        
        final_cols = [c for c in desired_order if c in filtered_df.columns] + remaining_cols
        
        # 3. Column Configuration
        table_config = {
            "Work Name": st.column_config.TextColumn("Work Name", width="large"),
            "Sl. No.": st.column_config.NumberColumn("Sl. No.", width="small"),
            "Status": st.column_config.TextColumn("Status", width="medium"),
            "Issues": st.column_config.TextColumn("Issues", width="medium"),
        }

        st.dataframe(
            filtered_df[final_cols],
            use_container_width=True,
            hide_index=True,
            height=500,
            column_config=table_config
        )
