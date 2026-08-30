# ============================================================================
# ARCHER2 Workload Research Dashboard
# A Streamlit web app for exploring HPC job and resource usage patterns
# ============================================================================
#
# python -m streamlit run "InteractiveWebApp.py"



from pathlib import Path

import io

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# Configure the Streamlit page with title and wide layout for more screen space
st.set_page_config(page_title="ARCHER2 Workload Research", layout="wide")


# ============================================================================
# DATA LOADING FUNCTION
# ============================================================================

@st.cache_data  # Cache the loaded data so it's only read once, improving app speed
def load_data():
    """Load and validate ARCHER2 HPC usage data from CSV file.
    
    Returns:
        DataFrame: Cleaned and processed ARCHER2 data with Year, Month, Jobs, 
                   Nodeh (node-hours), and Season columns.
                   
    Raises:
        ValueError: If required columns are missing from the CSV.
    """
    # Find the CSV file in the project data folder; fall back to the same folder
    # if the file has been kept locally with the dashboard script.
    candidate_paths = [
        Path(__file__).resolve().parent.parent / "data" / "archer2_HPC_data_without_overall_and_aOut.csv",
        Path(__file__).resolve().with_name("archer2_HPC_data_without_overall_and_aOut.csv"),
    ]

    data_path = next((p for p in candidate_paths if p.exists()), candidate_paths[0])
    data = pd.read_csv(data_path)
    
    # Check that all required columns exist in the data
    required_columns = {"Software", "Year", "Month", "Jobs", "Nodeh"}
    missing_columns = required_columns.difference(data.columns)
    if missing_columns:
        raise ValueError(f"The CSV is missing columns: {', '.join(sorted(missing_columns))}")

    # Convert numeric columns to proper data types
    data["Year"] = pd.to_numeric(data["Year"], errors="coerce").astype("Int64")
    data["Month"] = pd.to_numeric(data["Month"], errors="coerce").astype("Int64")
    data["Jobs"] = pd.to_numeric(data["Jobs"], errors="coerce").fillna(0)
    data["Nodeh"] = pd.to_numeric(data["Nodeh"], errors="coerce").fillna(0)
    
    # Add Season column based on month for seasonal trend analysis
    if "Season" not in data.columns:
        seasons = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring",
                   6: "Summer", 7: "Summer", 8: "Summer", 9: "Autumn", 10: "Autumn", 11: "Autumn"}
        data["Season"] = data["Month"].map(seasons)
    
    # Remove rows with missing critical data
    return data.dropna(subset=["Software", "Year", "Month"])


# ============================================================================
# APP TITLE AND DESCRIPTION
# ============================================================================

st.title("ARCHER2 Workload Research")
st.write("Explore job volume and node-hour patterns across ARCHER2 software usage.")

# ============================================================================
# LOAD DATA AND HANDLE ERRORS
# ============================================================================

df = pd.DataFrame()

try:
    df = load_data()
except (FileNotFoundError, ValueError) as error:
    # If data file is missing or invalid, display error and stop
    st.error(str(error))
    st.stop()


# ============================================================================
# CALCULATE SUMMARY STATISTICS FOR SIDEBAR FILTERS
# ============================================================================

# Calculate total node-hours by software and sort by highest usage
software_totals = df.groupby("Software", as_index=False)["Nodeh"].sum().sort_values("Nodeh", ascending=False)

# Set the top 5 most-used software as default selections in the filter
default_software = software_totals.head(5)["Software"].tolist()

# Get all unique software names for the dropdown menu
software_options = software_totals["Software"].tolist()

# ============================================================================
# SIDEBAR INTERACTIVE FILTERS
# ============================================================================

# Multi-select dropdown to filter by software (defaults to top 5 most used)
selected_software = st.sidebar.multiselect(
    "Software to compare",
    software_options,
    default=default_software,
)

# Multi-select dropdown to filter by year (defaults to all years, sorted newest first)
selected_years = st.sidebar.multiselect(
    "Years",
    sorted(df["Year"].dropna().unique(), reverse=True),
    default=sorted(df["Year"].dropna().unique(), reverse=True),
)

# ============================================================================
# FILTER DATA BASED ON USER SELECTIONS
# ============================================================================

# Apply the selected filters to create a subset of the data
filtered = df[df["Software"].isin(selected_software) & df["Year"].isin(selected_years)]

# Calculate summary metrics from filtered data
total_jobs = filtered.groupby("Software")["Jobs"].sum().sum()  # Total number of jobs submitted
total_nodeh = filtered.groupby("Software")["Nodeh"].sum().sum()  # Total node-hours used
top_software = filtered.groupby("Software")["Nodeh"].sum().idxmax() if not filtered.empty else "None"  # Software with highest usage

# ============================================================================
# DISPLAY KEY METRICS AT THE TOP OF THE PAGE
# ============================================================================

# Create 4 columns to display metrics side-by-side
metric_one, metric_two, metric_three, metric_four = st.columns(4)
metric_one.metric("Total jobs", f"{total_jobs:,.0f}")  # Format number with commas
metric_two.metric("Total node-hours", f"{total_nodeh:,.1f}")  # Format with one decimal place
metric_three.metric("Average node-hour use", f"{total_nodeh / total_jobs if total_jobs > 0 else 0:,.1f}")  # Show which software used the most
# metric_four.metric("Top 5 highest node-hour use", ", ".join(software_totals.head(5)["Software"].tolist()))  # List top 5 software in vertical format
top5_list = software_totals.head(5)["Software"].tolist()
st.markdown("### Top 5 highest node-hour use")
for counter in range (0, len(top5_list)):
    st.markdown(f"{counter + 1}. {top5_list[counter]}")


# ============================================================================
# VALIDATION CHECK: Warn user if no data matches their filters
# ============================================================================

if filtered.empty:
    st.warning("Select at least one software application and one year.")
    st.stop()


# ============================================================================
# CREATE TABBED INTERFACE FOR DIFFERENT VISUALIZATIONS
# ============================================================================

# Create 4 tabs organized by analysis type
tab_seasonal, tab_yearly, tab_distribution, tab_data = st.tabs(
    ["Seasonal patterns", "Yearly trends", "Usage distribution", "Data"]
)

# ============================================================================
# TAB 1: SEASONAL PATTERNS
# ============================================================================
# Show how node-hour usage varies by month across the year

with tab_seasonal:
    # Group data by month and software, summing node-hours for each combination
    seasonal = filtered.groupby(["Month", "Software"], as_index=False)["Nodeh"].sum()
    
    # Create a line plot with matplotlib
    fig, ax = plt.subplots(figsize=(11, 5))
    
    # Plot a separate line for each software application
    for software, group in seasonal.groupby("Software"):
        ax.plot(group["Month"], group["Nodeh"], marker="o", label=software)

    # Add colored background spans to indicate seasons on the x-axis (months 1-12)

    # WINTER (Dec–Feb)
    ax.axvspan(12, 13, color='lightblue', alpha=0.2)  # December
    ax.axvspan(1, 3, color='lightblue', alpha=0.2)    # Jan–Feb

    # SPRING (Mar–May)
    ax.axvspan(3, 6, color='lightgreen', alpha=0.2)

    # SUMMER (Jun–Aug)
    ax.axvspan(6, 9, color='yellow', alpha=0.2)

    # AUTUMN (Sep–Nov)
    ax.axvspan(9, 12, color='orange', alpha=0.2)

    
    # Format and label the chart
    ax.set_title("Monthly node-hour use by software")
    ax.set_xlabel("Month")
    ax.set_ylabel("Node-hours")
    ax.set_xticks(range(1, 13))  # Show all 12 months on x-axis
    ax.grid(alpha=0.25)  # Add subtle grid lines
    ax.legend(title="Software", bbox_to_anchor=(1.02, 1), loc="upper left")  # Place legend outside plot
    
    # Display the chart in Streamlit
    st.pyplot(fig, use_container_width=True)
    
    # Save figure to buffer for download
    buf_seasonal = io.BytesIO()
    fig.savefig(buf_seasonal, format="png", dpi=300, bbox_inches="tight")
    buf_seasonal.seek(0)
    
    # Display download button for the chart
    st.download_button(
        label="Download chart as PNG",
        data=buf_seasonal.getvalue(),
        file_name="archer2_seasonal_patterns_chart.png",
        mime="image/png"
    )


    # plt.grid(False)

# ============================================================================
# TAB 2: YEARLY TRENDS
# ============================================================================
# Show how node-hour usage has changed year-over-year for each software

with tab_yearly:
    # Group data by year and software, summing node-hours for each combination
    yearly = filtered.groupby(["Year", "Software"], as_index=False)["Nodeh"].sum()
    
    # Pivot the data so years are rows and software names are columns (good for bar charts)
    yearly_pivot = yearly.pivot(index="Year", columns="Software", values="Nodeh").fillna(0)
    
    # Create a matplotlib figure for the bar chart (instead of using st.bar_chart)
    fig_yearly, ax_yearly = plt.subplots(figsize=(11, 5))
    yearly_pivot.plot(kind="bar", ax=ax_yearly)
    ax_yearly.set_title("Yearly node-hour use by software")
    ax_yearly.set_xlabel("Year")
    ax_yearly.set_ylabel("Node-hours")
    ax_yearly.legend(title="Software", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax_yearly.grid(alpha=0.25)
    plt.xticks(rotation=45)
    
    # Display the chart in Streamlit
    st.pyplot(fig_yearly, use_container_width=True)
    
    # Add a caption explaining the chart
    st.caption("Node-hour totals grouped by year and software.")
    
    # Save figure to buffer for download
    buf_yearly = io.BytesIO()
    fig_yearly.savefig(buf_yearly, format="png", dpi=300, bbox_inches="tight")
    buf_yearly.seek(0)
    
    # Display download button for the chart
    st.download_button(
        label="Download chart as PNG",
        data=buf_yearly.getvalue(),
        file_name="archer2_yearly_trends_chart.png",
        mime="image/png"
    )

# ============================================================================
# TAB 3: USAGE DISTRIBUTION
# ============================================================================
# Show the distribution of individual job sizes (node-hours per job) for each software

with tab_distribution:
    # Create a histogram to visualize the distribution of node-hour values
    fig, ax = plt.subplots(figsize=(11, 5))
    
    # Plot overlapping histograms for each software application
    for software, group in filtered.groupby("Software"):
        ax.hist(group["Nodeh"], bins=30, alpha=0.55, label=software)  # Alpha = transparency
    
    # Format and label the chart
    ax.set_title("Distribution of node-hour values")
    ax.set_xlabel("Node-hours")
    ax.set_ylabel("Frequency")
    ax.grid(alpha=0.25)
    ax.legend(title="Software", bbox_to_anchor=(1.02, 1), loc="upper left")
    
    # Display the chart in Streamlit
    st.pyplot(fig, use_container_width=True)
    
    # Save figure to buffer for download
    buf_distribution = io.BytesIO()
    fig.savefig(buf_distribution, format="png", dpi=300, bbox_inches="tight")
    buf_distribution.seek(0)

    # Display download button for the chart
    st.download_button(
        label="Download chart as PNG",
        data=buf_distribution.getvalue(),
        file_name="archer2_distribution_chart.png",
        mime="image/png"
    )


# ============================================================================
# TAB 4: RAW DATA TABLE
# ============================================================================
# Display the underlying data in a sortable, interactive table

with tab_data:
    # Sort data by year (newest first), month (earliest first), and node-hours (highest first)
    sorted_data = filtered.sort_values(["Year", "Month", "Nodeh"], ascending=[False, True, False])
    
    # Display as an interactive table that users can scroll, sort, and search
    st.dataframe(sorted_data, use_container_width=True)