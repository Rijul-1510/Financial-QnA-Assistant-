# -------------------- Imports --------------------
import streamlit as st
import pandas as pd
import plotly.express as px
from modules.extractor import extract_from_pdf, extract_from_excel
from modules.processor import structure_financial_data, pretty_print_metrics
from modules.qa_engine import ask_question


# -------------------- Streamlit Page Config --------------------
st.set_page_config(
    page_title="Financial Document Q&A Assistant",  # Page title
    page_icon="💹",                                # Favicon
    layout="wide",                                 # Use wide layout
    initial_sidebar_state="expanded"               # Sidebar expanded by default
)

st.title("💹 Financial Document Q&A Assistant")
st.markdown("Upload a financial PDF or Excel file and **chat with your data**")


# -------------------- Session State --------------------
# Keep track of uploaded documents and chat history across interactions
if "documents" not in st.session_state:
    st.session_state.documents = []
if "chat" not in st.session_state:
    st.session_state.chat = []


# -------------------- Sidebar (Upload + Management) --------------------
with st.sidebar:
    st.header("📂 Upload Document")
    uploaded = st.file_uploader(
        "Upload PDF/Excel",             # Label
        type=["pdf", "xlsx", "xls"],    # Allowed file formats
        accept_multiple_files=False     # Only one file at a time
    )

    st.markdown("---")
    st.header("🗑️ Data Management")
    
    # Buttons for clearing chat or all data
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear Chat Only"):
            st.session_state.chat = []
            st.success("Chat history cleared!")
    with col2:
        if st.button("Clear All Data"):
            st.session_state.documents = []
            st.session_state.chat = []
            st.success("Cleared all uploaded data & chat.")

    st.markdown("---")


# -------------------- Process Uploaded File --------------------
if uploaded:
    try:
        # Extract based on file type
        if uploaded.name.lower().endswith(".pdf"):
            raw_text, tables = extract_from_pdf(uploaded)
        else:
            raw_text, tables = extract_from_excel(uploaded)

        # Convert raw data into structured metrics
        metrics = structure_financial_data(raw_text, tables)

        # If document already uploaded, replace it; else add new one
        existing_idx = None
        for i, doc in enumerate(st.session_state.documents):
            if doc["name"] == uploaded.name:
                existing_idx = i
                break
                
        if existing_idx is not None:
            st.session_state.documents[existing_idx] = {
                "name": uploaded.name,
                "raw_text": raw_text,
                "tables": tables,
                "metrics": metrics
            }
            st.sidebar.success(f"Updated {uploaded.name}")
        else:
            st.session_state.documents.append({
                "name": uploaded.name,
                "raw_text": raw_text,
                "tables": tables,
                "metrics": metrics
            })
            st.sidebar.success(f"Added {uploaded.name}")
            
    except Exception as e:
        st.sidebar.error(f"Failed to process {uploaded.name}: {e}")


# -------------------- Main Tabs --------------------
if st.session_state.documents:
    tab1, tab2, tab3 = st.tabs(["📊 Metrics", "📜 Preview", "💬 Chat"])

    # ---------- Metrics Tab ----------
    with tab1:
        st.subheader("Extracted Metrics")
        doc = st.session_state.documents[0]  # Show first doc for now
        st.markdown(f"### 📄 {doc['name']}")
        
        # Show extracted metrics as styled dataframe
        df = pretty_print_metrics(doc["metrics"])
        st.dataframe(df.style.background_gradient(cmap="Blues"), width="stretch")

        # Allow user to download metrics as CSV
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Metrics as CSV",
            data=csv_data,
            file_name=f"{doc['name'].replace(' ', '_')}_metrics.csv",
            mime="text/csv"
        )

        # Extract main metrics and yearly metrics if available
        metrics = doc["metrics"].get("metrics", {})
        yearly_metrics = doc["metrics"].get("yearly_metrics", {}) if "yearly_metrics" in doc["metrics"] else {}

        # KPI cards for quick insights
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Revenue", metrics.get("revenue", "N/A"))
        col2.metric("📈 Net Income", metrics.get("net_income", "N/A"))
        col3.metric("🏦 Total Assets", metrics.get("total_assets", "N/A"))

        # If multiple years of data exist → show bar/line charts
        if yearly_metrics:
            st.subheader("📊 Multi-Year Financial Analysis")
            
            # Prepare structured plot data
            years = sorted(yearly_metrics.keys())
            metrics_to_plot = ["revenue", "gross_profit", "net_income"]
            
            plot_data = []
            for year in years:
                for metric in metrics_to_plot:
                    if metric in yearly_metrics[year]:
                        plot_data.append({
                            "Year": year,
                            "Metric": metric.replace("_", " ").title(),
                            "Value": yearly_metrics[year][metric]
                        })
            
            if plot_data:
                df_plot = pd.DataFrame(plot_data)
                
                # Bar chart
                fig = px.bar(df_plot, x="Year", y="Value", color="Metric", 
                             barmode="group", title="Financial Metrics by Year")
                st.plotly_chart(fig, width="stretch")
                
                # Line chart
                fig2 = px.line(df_plot, x="Year", y="Value", color="Metric", 
                              markers=True, title="Financial Trends Over Years")
                st.plotly_chart(fig2, width="stretch")
                
                # Show yearly table
                st.subheader("📋 Yearly Financial Data")
                yearly_df = pd.DataFrame([
                    {"Year": year, **{
                        metric.replace("_", " ").title(): yearly_metrics[year].get(metric)
                        for metric in metrics_to_plot
                    }} for year in years
                ])
                st.dataframe(yearly_df.style.format("{:,.0f}"), width="stretch")
                
                # Growth analysis (% change year-over-year)
                if len(years) > 1:
                    st.subheader("📈 Growth Analysis")
                    growth_data = []
                    for metric in metrics_to_plot:
                        if all(metric in yearly_metrics[year] for year in years):
                            values = [yearly_metrics[year][metric] for year in years]
                            growth_rates = [""] + [f"{((values[i] - values[i-1]) / values[i-1]) * 100:.1f}%"
                                                   for i in range(1, len(values))]
                            for i, year in enumerate(years):
                                growth_data.append({
                                    "Year": year,
                                    "Metric": metric.replace("_", " ").title(),
                                    "Value": values[i],
                                    "Growth": growth_rates[i]
                                })
                    if growth_data:
                        growth_df = pd.DataFrame(growth_data)
                        st.dataframe(growth_df, width="stretch")

        # If only single-year metrics exist → simple bar chart
        elif metrics.get("revenue") and metrics.get("net_income"):
            df_plot = pd.DataFrame({
                "Metric": ["Revenue", "Net Income"],
                "Value": [metrics["revenue"], metrics["net_income"]]
            })
            fig = px.bar(df_plot, x="Metric", y="Value", color="Metric", text="Value")
            fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
            fig.update_layout(title="Key Financials", showlegend=False)
            st.plotly_chart(fig, width="stretch")

        # Fallback: extract year-over-year trend directly from uploaded tables
        for t in doc["tables"]:
            df_years = t.copy()
            df_years.columns = df_years.columns.astype(str)
            year_cols = [c for c in df_years.columns if c.isdigit() and len(c) == 4]
            if year_cols:
                df_long = df_years.melt(
                    id_vars=[df_years.columns[0]], value_vars=year_cols,
                    var_name="Year", value_name="Value"
                )
                df_long.columns = ["Metric", "Year", "Value"]
                df_long = df_long[df_long["Metric"].str.lower().str.contains("revenue|net income|profit")]
                if not df_long.empty:
                    st.subheader("📉 Year-over-Year Trend")
                    fig = px.line(df_long, x="Year", y="Value", color="Metric", markers=True)
                    fig.update_layout(title="Revenue & Net Income Trend")
                    st.plotly_chart(fig, width="stretch")
                    break

    # ---------- Preview Tab ----------
    with tab2:
        st.subheader("Document Raw Text Preview")
        doc = st.session_state.documents[0]
        with st.expander(f"📄 {doc['name']}", expanded=False):
            # Show only first 50 lines for readability
            st.code("\n".join(doc["raw_text"].splitlines()[:50]))

    # ---------- Chat Tab ----------
    with tab3:
        st.subheader("🤖 AI Assistant")

        # Initial welcome message
        if not st.session_state.chat:
            st.session_state.chat.append(("assistant",
                "👋 Hi, I'm your financial assistant. Upload a document and ask me anything about revenue, expenses, or profits!"))

        # User query input
        query = st.chat_input("Ask a financial question...")
        if query:
            st.session_state.chat.append(("user", query))
            with st.spinner("Thinking..."):
                answer = ask_question(query, st.session_state.documents)
            st.session_state.chat.append(("assistant", answer))

        # Display chat messages
        for role, msg in st.session_state.chat:
            st.chat_message(role).write(msg)


# -------------------- Empty State (No Docs) --------------------
else:
    st.info("Upload a PDF or Excel file from the sidebar to get started.")
    
    # Help instructions
    with st.expander("ℹ️ How to use this app"):
        st.markdown("""
        1. **Upload Documents**: Use the sidebar to upload financial PDFs or Excel files
        2. **View Metrics**: Check the Metrics tab to see extracted financial data
        3. **Ask Questions**: Use the Chat tab to ask questions about your financial data
        4. **Compare Documents**: Upload multiple documents to compare financial metrics
        
        **Supported Financial Metrics**:
        - Revenue, Gross Profit, Net Income
        - EBITDA, Operating Income
        - Total Assets, Liabilities, Equity
        - Cash and Equivalents
        - Cost of Revenue
        
        **Supported Calculations**:
        - Profit margins
        - Debt to equity ratios
        - Financial comparisons
        """)

    # Example queries for user guidance
    st.subheader("💡 Example Questions")
    examples = [
        "What is the revenue?",
        "Show me the net income",
        "What's the profit margin?",
        "Compare assets and liabilities",
        "Calculate debt to equity ratio"
    ]
    
    for example in examples:
        if st.button(example, key=f"example_{example}"):
            st.info(f"Try asking: '{example}' after uploading a document")
