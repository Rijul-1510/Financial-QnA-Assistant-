# 📊 Financial Document QnA Assistant

An interactive **LLM-powered application** that processes financial documents (PDF & Excel) and enables users to **query financial data in natural language**. 
The system combines **document parsing, RAG (Retrieval-Augmented Generation), and vector semantic search** to deliver accurate insights about revenue, 
expenses, profits, and other financial metrics.

## 🚀 Overview

Businesses generate complex financial statements across formats (PDFs, Excels). Extracting and analyzing these requires significant manual effort.

This project automates the process by:

1. **Extracting** structured and unstructured financial information from documents.
2. **Indexing** data using embeddings in a **vector database**.
3. **Answering questions** using an **LLM with RAG**, ensuring responses are grounded in source documents.

---

## 🛠️ Installation

1. Clone this repository:

```bash
git clone https://github.com/yourusername/Financial_Document_QnA_Assistant.git
cd Financial_Document_QnA_Assistant
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

---

## ▶️ Usage

Run the Streamlit app:

```bash
streamlit run app.py
```

### Steps:

1. Upload a **PDF** or **Excel** financial document.
2. The system extracts text and tabular data using:

   * **PyMuPDF** & **pdfplumber** (PDF parsing & chunking)
   * **Pandas** (Excel/CSV parsing)
3. Ask questions like:

   * “What was the net income in 2022?”
   * “Show me the revenue trend over the years.”
   * “Compare assets vs liabilities.”
4. The app will return **answers, charts, and downloadable results**.

---

## 📂 Directory Structure

```
Financial_Document_QnA_Assistant/
│── app.py                 # Streamlit frontend
│── requirements.txt        # Dependencies
│── modules/
│   ├── extractor.py        # Handles document text & table extraction
│   ├── processor.py        # Processes metrics, multi-year extraction
│   ├── qa_engine.py        # LLM + RAG + vector semantic search
│   ├── utils.py            # Helper functions
│── sample.pdf              # Example financial document
```

---

## ✨ Key Features

* **Multi-format support**: Handles **PDF** (via PyMuPDF, pdfplumber) and **Excel**.
* **Chunking**: Splits large documents for efficient vector embedding & retrieval.
* **Vector Semantic Search**: Embeds chunks & stores in a **vector database** for fast retrieval.
* **RAG with LLM**: Ensures answers are contextual and document-grounded.
* **Interactive Visualizations**: Revenue, profit, and multi-year trends.
* **Downloadable Outputs**: Export extracted financial tables.

---

## 📈 Results & Performance

* Successfully extracts **multi-year metrics** (revenue, profit, assets, liabilities).
* Answers natural language queries with high accuracy using **semantic search + LLM reasoning**.
* Handles **structured (tables)** and **unstructured (text)** data equally well.

Performance depends on:

* **LLM backend** (local Ollama / external APIs).
* **Vector database efficiency** for semantic retrieval.
* **Document complexity** (clean tabular vs scanned).

---

## 🔮 Future Work

* **LangChain Integration**: Orchestration of multi-step reasoning pipelines.
* **Support for external LLMs**: Gemini, GPT-4, Claude, OpenAI APIs.
* **Advanced Analytics**: Ratio analysis (ROE, margins, liquidity).
* **Table Structure Preservation**: Improve parsing of complex nested tables.
* **Cloud Deployment**: Expose as a SaaS API.
* **Multi-document QnA**: Compare across multiple companies/years.

---

## ⚙️ Tech Stack

* **Python** (Streamlit, Pandas, NumPy)
* **PyMuPDF** & **pdfplumber** (document parsing)
* **Vector Database** (FAISS/Chroma/Weaviate-ready)
* **LLM** (Ollama local models, expandable to GPT, Gemini, Claude)
* **RAG** (retrieval-augmented answering)

---

## 🙌 Acknowledgements

* [PyMuPDF](https://pymupdf.readthedocs.io/)
* [pdfplumber](https://github.com/jsvine/pdfplumber)
* [Streamlit](https://streamlit.io/)
* [Ollama](https://ollama.ai/)

---

