"""
Quantum Computing Dashboard - Real QPU Performance Metrics
A lightweight dashboard showing cloud-accessible quantum computers and their specifications.
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

# Page config
st.set_page_config(
    page_title="Quantum QPU Dashboard",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-top: 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load QPU data from JSON file."""
    data_path = Path(__file__).parent / "data" / "qpu_data.json"
    with open(data_path, "r") as f:
        data = json.load(f)

    df = pd.DataFrame(data["qpus"])

    # Process cloud_access to be a string for display
    df["cloud_platforms"] = df["cloud_access"].apply(
        lambda x: ", ".join(x) if isinstance(x, list) else "N/A"
    )

    return df, data["last_updated"], data["data_sources"]

def create_fidelity_chart(df):
    """Create a bar chart comparing gate fidelities."""
    # Filter to only rows with fidelity data
    fidelity_df = df[df["q2_fidelity"].notna()].copy()
    fidelity_df = fidelity_df.sort_values("q2_fidelity", ascending=True)

    fig = go.Figure()

    # Add 2-qubit fidelity bars
    fig.add_trace(go.Bar(
        y=fidelity_df["company"] + " - " + fidelity_df["qpu_name"],
        x=fidelity_df["q2_fidelity"],
        orientation='h',
        name='2-Qubit Gate Fidelity (%)',
        marker_color='#1E88E5',
        text=fidelity_df["q2_fidelity"].apply(lambda x: f"{x:.2f}%"),
        textposition='outside'
    ))

    fig.update_layout(
        title="Two-Qubit Gate Fidelity Comparison",
        xaxis_title="Fidelity (%)",
        yaxis_title="",
        height=max(400, len(fidelity_df) * 35),
        xaxis=dict(range=[95, 100.5]),
        showlegend=False,
        margin=dict(l=200)
    )

    return fig

def create_qubit_chart(df):
    """Create a bar chart comparing qubit counts."""
    qubit_df = df[df["physical_qubits"].notna()].copy()
    qubit_df = qubit_df.sort_values("physical_qubits", ascending=True)

    # Color by technology
    colors = {
        "Superconducting": "#1E88E5",
        "Trapped Ion": "#43A047",
        "Neutral Atom": "#FB8C00",
        "Quantum Annealing": "#8E24AA",
        "Superconducting (Cat Qubits)": "#E53935"
    }

    qubit_df["color"] = qubit_df["qubit_technology"].map(colors).fillna("#666666")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=qubit_df["company"] + " - " + qubit_df["qpu_name"],
        x=qubit_df["physical_qubits"],
        orientation='h',
        marker_color=qubit_df["color"],
        text=qubit_df["physical_qubits"].astype(int),
        textposition='outside'
    ))

    fig.update_layout(
        title="Physical Qubit Count by System",
        xaxis_title="Number of Qubits",
        yaxis_title="",
        height=max(400, len(qubit_df) * 35),
        showlegend=False,
        margin=dict(l=200),
        xaxis_type="log"
    )

    return fig

def create_technology_pie(df):
    """Create a pie chart of qubit technologies."""
    tech_counts = df["qubit_technology"].value_counts()

    colors = {
        "Superconducting": "#1E88E5",
        "Trapped Ion": "#43A047",
        "Neutral Atom": "#FB8C00",
        "Quantum Annealing": "#8E24AA",
        "Superconducting (Cat Qubits)": "#E53935"
    }

    fig = px.pie(
        values=tech_counts.values,
        names=tech_counts.index,
        title="QPUs by Technology Type",
        color=tech_counts.index,
        color_discrete_map=colors
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')

    return fig

def main():
    # Load data
    df, last_updated, data_sources = load_data()

    # Header
    st.markdown('<p class="main-header">⚛️ Quantum Computing Dashboard</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-header">Real-time QPU performance metrics from cloud-accessible quantum computers | Last updated: {last_updated}</p>', unsafe_allow_html=True)

    # Sidebar filters
    st.sidebar.header("Filters")

    # Technology filter
    technologies = ["All"] + sorted(df["qubit_technology"].unique().tolist())
    selected_tech = st.sidebar.selectbox("Qubit Technology", technologies)

    # Cloud platform filter
    all_platforms = set()
    for platforms in df["cloud_access"]:
        if isinstance(platforms, list):
            all_platforms.update(platforms)
    platform_options = ["All"] + sorted(list(all_platforms))
    selected_platform = st.sidebar.selectbox("Cloud Platform", platform_options)

    # Status filter
    statuses = ["All"] + sorted(df["status"].unique().tolist())
    selected_status = st.sidebar.selectbox("Status", statuses)

    # Apply filters
    filtered_df = df.copy()
    if selected_tech != "All":
        filtered_df = filtered_df[filtered_df["qubit_technology"] == selected_tech]
    if selected_platform != "All":
        filtered_df = filtered_df[filtered_df["cloud_access"].apply(
            lambda x: selected_platform in x if isinstance(x, list) else False
        )]
    if selected_status != "All":
        filtered_df = filtered_df[filtered_df["status"] == selected_status]

    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total QPUs", len(filtered_df))
    with col2:
        max_qubits = filtered_df["physical_qubits"].max()
        max_qubit_system = filtered_df[filtered_df["physical_qubits"] == max_qubits].iloc[0] if max_qubits else None
        st.metric(
            "Max Qubits",
            f"{int(max_qubits):,}" if pd.notna(max_qubits) else "N/A",
            delta=max_qubit_system["qpu_name"] if max_qubit_system is not None else None
        )
    with col3:
        max_fidelity = filtered_df["q2_fidelity"].max()
        max_fidelity_system = filtered_df[filtered_df["q2_fidelity"] == max_fidelity].iloc[0] if pd.notna(max_fidelity) else None
        st.metric(
            "Best 2Q Fidelity",
            f"{max_fidelity:.3f}%" if pd.notna(max_fidelity) else "N/A",
            delta=max_fidelity_system["qpu_name"] if max_fidelity_system is not None else None
        )
    with col4:
        companies = filtered_df["company"].nunique()
        st.metric("Companies", companies)

    st.divider()

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Charts", "🔬 Detailed Specs", "ℹ️ About"])

    with tab1:
        st.subheader("Cloud-Accessible Quantum Computers")

        # Create display dataframe with key columns
        display_cols = [
            "company", "qpu_name", "qubit_technology", "physical_qubits",
            "q1_fidelity", "q2_fidelity", "quantum_volume", "cloud_platforms",
            "year_released", "status"
        ]

        display_df = filtered_df[display_cols].copy()
        display_df.columns = [
            "Company", "QPU", "Technology", "Qubits",
            "1Q Fidelity (%)", "2Q Fidelity (%)", "QV", "Cloud Access",
            "Released", "Status"
        ]

        # Format fidelity columns
        display_df["1Q Fidelity (%)"] = display_df["1Q Fidelity (%)"].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "-"
        )
        display_df["2Q Fidelity (%)"] = display_df["2Q Fidelity (%)"].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "-"
        )
        display_df["Qubits"] = display_df["Qubits"].apply(
            lambda x: f"{int(x):,}" if pd.notna(x) else "-"
        )
        display_df["QV"] = display_df["QV"].apply(
            lambda x: f"{int(x):,}" if pd.notna(x) else "-"
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=500
        )

        # Technology breakdown
        st.subheader("Technology Distribution")
        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(create_technology_pie(filtered_df), use_container_width=True)

        with col2:
            # Summary stats by technology
            tech_stats = filtered_df.groupby("qubit_technology").agg({
                "physical_qubits": ["count", "max", "mean"],
                "q2_fidelity": "max"
            }).round(2)
            tech_stats.columns = ["Count", "Max Qubits", "Avg Qubits", "Best 2Q Fidelity"]
            st.dataframe(tech_stats, use_container_width=True)

    with tab2:
        st.subheader("Performance Comparisons")

        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(create_fidelity_chart(filtered_df), use_container_width=True)

        with col2:
            st.plotly_chart(create_qubit_chart(filtered_df), use_container_width=True)

        # Coherence times chart
        st.subheader("Coherence Times (T1)")
        coherence_df = filtered_df[filtered_df["t1_us"].notna() & (filtered_df["t1_us"] > 0)].copy()
        if not coherence_df.empty:
            coherence_df = coherence_df.sort_values("t1_us", ascending=True)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=coherence_df["company"] + " - " + coherence_df["qpu_name"],
                x=coherence_df["t1_us"],
                orientation='h',
                marker_color='#43A047',
                text=coherence_df["t1_us"].apply(lambda x: f"{x:,.0f} µs"),
                textposition='outside'
            ))
            fig.update_layout(
                title="T1 Coherence Time Comparison",
                xaxis_title="T1 (µs)",
                yaxis_title="",
                height=max(300, len(coherence_df) * 40),
                xaxis_type="log",
                margin=dict(l=200)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No coherence time data available for the selected filters.")

    with tab3:
        st.subheader("Detailed QPU Specifications")

        # Select a specific QPU
        qpu_options = filtered_df.apply(lambda x: f"{x['company']} - {x['qpu_name']}", axis=1).tolist()
        selected_qpu = st.selectbox("Select QPU for Details", qpu_options)

        if selected_qpu:
            company, qpu_name = selected_qpu.split(" - ", 1)
            qpu_data = filtered_df[(filtered_df["company"] == company) & (filtered_df["qpu_name"] == qpu_name)].iloc[0]

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Basic Information")
                st.write(f"**Company:** {qpu_data['company']}")
                st.write(f"**QPU Name:** {qpu_data['qpu_name']}")
                st.write(f"**Technology:** {qpu_data['qubit_technology']}")
                st.write(f"**Physical Qubits:** {int(qpu_data['physical_qubits']):,}" if pd.notna(qpu_data['physical_qubits']) else "**Physical Qubits:** N/A")
                if pd.notna(qpu_data.get('logical_qubits')):
                    st.write(f"**Logical Qubits:** {int(qpu_data['logical_qubits'])}")
                st.write(f"**Year Released:** {int(qpu_data['year_released'])}" if pd.notna(qpu_data['year_released']) else "**Year Released:** N/A")
                st.write(f"**Status:** {qpu_data['status']}")

            with col2:
                st.markdown("### Performance Metrics")
                if pd.notna(qpu_data.get('q1_fidelity')):
                    st.write(f"**1-Qubit Gate Fidelity:** {qpu_data['q1_fidelity']:.4f}%")
                if pd.notna(qpu_data.get('q2_fidelity')):
                    st.write(f"**2-Qubit Gate Fidelity:** {qpu_data['q2_fidelity']:.4f}%")
                if pd.notna(qpu_data.get('spam_fidelity')):
                    st.write(f"**SPAM Fidelity:** {qpu_data['spam_fidelity']:.2f}%")
                if pd.notna(qpu_data.get('quantum_volume')):
                    st.write(f"**Quantum Volume:** {int(qpu_data['quantum_volume']):,}")
                if pd.notna(qpu_data.get('t1_us')):
                    st.write(f"**T1 Coherence:** {qpu_data['t1_us']:,.0f} µs")
                if pd.notna(qpu_data.get('t2_us')):
                    st.write(f"**T2 Coherence:** {qpu_data['t2_us']:,.0f} µs")

            st.markdown("### Cloud Access")
            st.write(qpu_data['cloud_platforms'])

            if pd.notna(qpu_data.get('native_gates')) and qpu_data['native_gates']:
                st.markdown("### Native Gates")
                st.write(", ".join(qpu_data['native_gates']) if isinstance(qpu_data['native_gates'], list) else qpu_data['native_gates'])

            if pd.notna(qpu_data.get('notes')):
                st.markdown("### Notes")
                st.info(qpu_data['notes'])

    with tab4:
        st.subheader("About This Dashboard")

        st.markdown("""
        This dashboard provides real-time performance metrics for cloud-accessible quantum computers.

        ### Data Sources
        All specifications are gathered from official company documentation and cloud provider APIs:
        """)

        for source in data_sources:
            st.write(f"- {source}")

        st.markdown("""
        ### Key Metrics Explained

        | Metric | Description |
        |--------|-------------|
        | **Physical Qubits** | The total number of hardware qubits available on the system |
        | **Logical Qubits** | Error-corrected qubits (when available) |
        | **1Q Fidelity** | Single-qubit gate fidelity (higher is better) |
        | **2Q Fidelity** | Two-qubit gate fidelity (higher is better, harder to achieve) |
        | **Quantum Volume** | IBM's holistic benchmark combining qubits, connectivity, and fidelity |
        | **T1 (µs)** | Amplitude relaxation time - how long qubits maintain energy state |
        | **T2 (µs)** | Phase coherence time - how long qubits maintain quantum superposition |
        | **SPAM** | State Preparation and Measurement fidelity |

        ### Qubit Technologies

        - **Superconducting**: Uses Josephson junctions at millikelvin temperatures (IBM, Google, Rigetti, IQM)
        - **Trapped Ion**: Uses individual ions held in electromagnetic traps (IonQ, Quantinuum, AQT)
        - **Neutral Atom**: Uses arrays of neutral atoms trapped by laser light (QuEra, Atom Computing, Infleqtion)
        - **Quantum Annealing**: Specialized for optimization problems (D-Wave)

        ### Update Frequency
        Data is refreshed daily from public documentation and APIs.
        """)

        st.divider()
        st.markdown(f"*Dashboard built with Streamlit | Data last updated: {last_updated}*")

if __name__ == "__main__":
    main()
