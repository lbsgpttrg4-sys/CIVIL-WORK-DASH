import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import requests
import io

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="CIVIL WORKS SUMMARY",
    page_icon="🏛️",
    layout="wide"
)

# --- CUSTOM CSS FOR "CM DASHBOARD" LOOK ---
st.markdown("""
    <style>
    /* Fixed: Increased top padding to prevent title clipping */
    .block-container {
        padding-top: 3rem;
        padding-bottom: 1rem;
    }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stButton button {
        width: 100%;
        height: 3.5rem;
        font-weight: bold;
        border-radius: 8px;
    }
    /* Custom header style */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A; /* Dark Blue */
        text-align: center;
        margin-bottom: 1rem;
        margin-top: 0rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #64748B;
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

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

    df = df.rename(columns=col_map)
    
    # Add Department Name Column
    if dept_name:
        df["Department"] = dept_name
    
    # Clean Budget
    if "Budget (Lakhs)" in df.columns:
        df["Normalized Budget"] = df["Budget (Lakhs)"].apply(normalize_budget)
    else:
        df["Normalized Budget"] = 0.0

    # Clean Completion Status
    if "Status" in df.columns:
        df["Status Label"] = df["Status"].astype(str).apply(
            lambda x: "Completed" if "complete" in x.lower() else "In Progress"
        )
    elif "Is Completed" in df.columns:
        df["Status Label"] = df["Is Completed"].apply(lambda x: "Completed" if x == 1 else "In Progress")
    else:
         df["Status Label"] = "In Progress"

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
    """Downloads the Excel file from Google Sheets and returns it as a BytesIO object."""
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
    # Mock data as fallback
    pr_df = pd.DataFrame({
        "Work Name": ["PWD Road T02", "ZP Road Vajenepalli", "ZP Road Lingapur", "Anganwadi Center 1", "Anganwadi Center 2"],
        "Mandal": ["Mahamutharam", "Mahamutharam", "Mahamutharam", "Mahamutharam", "Mahamutharam"],
        "Budget (Lakhs)": [60, 180, 93, 16, 16],
        "Status": ["Progress", "Progress", "Progress", "Completed", "Progress"],
        "Issues": ["", "Land Acquisition", "", "", "Funds"],
    })
    med_df = pd.DataFrame({
        "Work Name": ["Nursing College", "Critical Care Block", "Sub Centre Regonda", "Sub Centre Thirumalagiri"],
        "Mandal": ["Bhupalpally", "Bhupalpally", "Regonda", "Regonda"],
        "Budget (Lakhs)": [2600, 2375, 20, 20],
        "Status": ["Retaining wall", "Painting", "Completed", "Completed"],
        "Issues": ["Site Dispute", "", "", ""],
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

def switch_view(view_name, dept=None):
    st.session_state.view = view_name
    st.session_state.selected_dept = dept

# --- DATA LOADING & PROCESSING ---
st.sidebar.header("Data Source")
source_option = st.sidebar.radio("Select Source:", ["Google Sheet (Live)", "Upload Excel File", "Use Demo Data"])

data_sheets = {}
SHEET_ID = "13Um7uOhz_zAAvMqCpfO-tppyZPoRT6RK"

if source_option == "Google Sheet (Live)":
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
    
    with st.spinner('Fetching data from Google Sheets...'):
        excel_file = fetch_google_sheet(SHEET_ID)
        if excel_file:
            raw_sheets = load_data(excel_file)
            if raw_sheets:
                for sheet_name, df in raw_sheets.items():
                    data_sheets[sheet_name] = clean_dataframe(df, sheet_name)
                st.sidebar.success("Data Loaded Successfully!")

elif source_option == "Upload Excel File":
    uploaded_file = st.sidebar.file_uploader("Upload Kataram Civil Works Excel", type=["xlsx", "xls"])
    if uploaded_file:
        raw_sheets = load_data(uploaded_file)
        if raw_sheets:
            for sheet_name, df in raw_sheets.items():
                data_sheets[sheet_name] = clean_dataframe(df, sheet_name)
    else:
        st.info("Please upload an Excel file to begin.")
        st.stop()
else:
    data_sheets = get_mock_data()

# Combine all data for Master View
master_df = pd.DataFrame()
if data_sheets:
    master_df = pd.concat(data_sheets.values(), ignore_index=True)

# --- DASHBOARD LOGIC ---

if st.session_state.view == 'Home':
    # === HOME VIEW: CM DASHBOARD ===
    
    st.markdown('<div class="main-header">CIVIL WORKS SUMMARY</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Kataram Division Overview</div>', unsafe_allow_html=True)

    if master_df.empty:
        st.warning("No data available. Please check the data source.")
    else:
        # 1. Global KPIs
        total_projects = len(master_df)
        total_investment = master_df["Normalized Budget"].sum()
        
        # Count issues (non-empty, non-nan, non-dash)
        issues_df = master_df[
            (master_df["Issues"].str.len() > 1) & 
            (master_df["Issues"].str.lower() != "nan") & 
            (master_df["Issues"].str.strip() != "-")
        ]
        total_issues = len(issues_df)
        
        completed_total = len(master_df[master_df["Status Label"] == "Completed"])
        completion_rate = int((completed_total / total_projects * 100)) if total_projects > 0 else 0

        # KPI Row
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Projects", total_projects)
        k2.metric("Total Investment", f"₹{total_investment:,.0f} Lakhs")
        k3.metric("Overall Completion", f"{completion_rate}%", f"{completed_total} Works")
        k4.metric("Critical Issues", total_issues, delta_color="inverse")

        st.divider()

        # 2. Department Comparison Charts
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("💰 Budget Allocation by Dept")
            budget_by_dept = master_df.groupby("Department")["Normalized Budget"].sum().reset_index()
            fig_budget = px.bar(
                budget_by_dept, 
                x="Department", 
                y="Normalized Budget",
                text="Normalized Budget",
                color="Department",
                title=""
            )
            fig_budget.update_traces(texttemplate='₹%{text:.2s}', textposition='outside')
            st.plotly_chart(fig_budget, use_container_width=True)

        with c2:
            st.subheader("📊 Project Status by Dept")
            status_by_dept = master_df.groupby(["Department", "Status Label"]).size().reset_index(name="Count")
            
            color_map = {"Completed": "#28a745", "In Progress": "#dc3545"}
            
            fig_status = px.bar(
                status_by_dept,
                x="Department",
                y="Count",
                color="Status Label",
                color_discrete_map=color_map,
                barmode="stack",
                title=""
            )
            st.plotly_chart(fig_status, use_container_width=True)

        st.divider()

        # 3. Department Drill-Down Buttons
        st.subheader("📂 Department Details")
        st.caption("Click a department below to view detailed reports.")
        
        dept_list = list(data_sheets.keys())
        
        # Create a grid of buttons (3 per row)
        cols = st.columns(4)
        for i, dept in enumerate(dept_list):
            with cols[i % 4]:
                # Calculate small stats for the button label
                d_rows = len(data_sheets[dept])
                d_budget = data_sheets[dept]["Normalized Budget"].sum()
                
                if st.button(f"{dept}\n({d_rows} Works)", key=f"btn_{dept}", help=f"Budget: ₹{d_budget:,.0f} Lakhs"):
                    switch_view('Department', dept)
                    st.rerun()

        # # 4. Critical Issues Section
        # if total_issues > 0:
        #     st.markdown("---")
        #     st.subheader("⚠️ Critical Issues Alert")
            
        #     # Show top 5 issues
        #     issues_display = issues_df[["Department", "Work Name", "Issues", "Mandal"]].head(5)
        #     st.dataframe(
        #         issues_display, 
        #         use_container_width=True, 
        #         hide_index=True
        #     )

elif st.session_state.view == 'Department':
    # === DEPARTMENT VIEW ===
    
    dept = st.session_state.selected_dept
    df = data_sheets.get(dept, pd.DataFrame())

    if df.empty:
        st.error(f"No data found for department: {dept}")
        if st.button("⬅️ Back"):
            switch_view('Home')
            st.rerun()
    else:
        # Header Row with Back Button
        h1, h2 = st.columns([1, 5])
        with h1:
            if st.button("⬅️ Back"):
                switch_view('Home')
                st.rerun()
        with h2:
            st.title(f"{dept} Department Report")

        # Filters
        f1, f2, f3 = st.columns(3)
        
        mandals = ["All"] + sorted(df["Mandal"].dropna().astype(str).unique().tolist()) if "Mandal" in df.columns else ["All"]
        sel_mandal = f1.selectbox("Filter by Mandal", mandals)
        
        show_pending = f2.toggle("Pending / In Progress Only")
        show_issues = f3.toggle("Has Issues Only")

        # Filter Logic
        filtered_df = df.copy()
        if sel_mandal != "All":
            filtered_df = filtered_df[filtered_df["Mandal"].astype(str) == sel_mandal]
        if show_pending:
            filtered_df = filtered_df[filtered_df["Status Label"] != "Completed"]
        if show_issues and "Issues" in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df["Issues"].str.len() > 1) & 
                (filtered_df["Issues"].str.lower() != "nan") & 
                (filtered_df["Issues"].str.strip() != "-")
            ]

        # Dept Stats
        d_total = len(filtered_df)
        d_budget = filtered_df["Normalized Budget"].sum() if "Normalized Budget" in filtered_df.columns else 0
        d_completed = len(filtered_df[filtered_df["Status Label"] == "Completed"])
        
        st.markdown("#### Snapshot")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Works Listed", d_total)
        s2.metric("Budget", f"₹{d_budget:,.1f} L")
        s3.metric("Completed", d_completed)
        s4.metric("Pending", d_total - d_completed)

        # --- NEW: DEPARTMENT LEVEL GRAPHS ---
        st.divider()
        st.subheader("📊 Department Analytics")
        
        if not filtered_df.empty:
            dc1, dc2 = st.columns(2)
            
            with dc1:
                # Status Breakdown
                status_counts = filtered_df["Status Label"].value_counts().reset_index()
                status_counts.columns = ["Status", "Count"]
                color_map = {"Completed": "#28a745", "In Progress": "#dc3545"}
                
                fig_dept_pie = px.pie(
                    status_counts, 
                    values='Count', 
                    names='Status', 
                    hole=0.4,
                    color='Status',
                    color_discrete_map=color_map,
                    title="Completion Status"
                )
                st.plotly_chart(fig_dept_pie, use_container_width=True)
                
            with dc2:
                # Budget by Mandal (if available)
                if "Mandal" in filtered_df.columns and "Normalized Budget" in filtered_df.columns:
                    budget_mandal = filtered_df.groupby("Mandal")["Normalized Budget"].sum().reset_index()
                    
                    fig_dept_bar = px.bar(
                        budget_mandal,
                        x="Mandal",
                        y="Normalized Budget",
                        title="Budget Distribution by Mandal (Lakhs)",
                        text="Normalized Budget"
                    )
                    fig_dept_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside')
                    st.plotly_chart(fig_dept_bar, use_container_width=True)
                else:
                    st.info("Not enough data for Mandal-wise Budget analysis")
        else:
            st.warning("No data matches the selected filters.")

        # Table
        st.markdown("#### Detailed Works List")
        
        cols_to_hide = ["Normalized Budget", "Status Label", "Department"]
        cols_to_show = [c for c in filtered_df.columns if c not in cols_to_hide]
        
        st.dataframe(
            filtered_df[cols_to_show],
            use_container_width=True,
            hide_index=True,
            height=500

        )

