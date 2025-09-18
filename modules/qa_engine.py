# -------------------- Imports --------------------
import requests
import textwrap

# Ollama API endpoint (local LLM server)
OLLAMA_URL = "http://localhost:11434/api/generate"


# -------------------- Context Builder --------------------
def build_context_string(docs_context):
    """
    Build a compact context string for the LLM prompt.

    Includes:
        - Document name
        - Extracted metrics
        - Currency (if detected)
        - Raw text snippet (first 800 chars)

    Args:
        docs_context (list[dict]): Uploaded documents and their extracted info

    Returns:
        str: Combined context string
    """
    parts = []
    for d in docs_context:
        parts.append(f"Document: {d['name']}")
        cur = d.get("metrics", {})
        currency = d.get("currency", None)
        
        # Add metrics if available
        if isinstance(cur, dict):
            metrics = cur.get("metrics", {})
            if metrics:
                parts.append("KeyMetrics:")
                for m, v in metrics.items():
                    parts.append(f"- {m}: {v}")
        
        # Add currency if present
        if currency:
            parts.append(f"Currency: {currency}")

        # Add short raw text snippet for extra context
        snippet = (d.get("raw_text") or "")[:800]
        if snippet:
            parts.append("TextSnippet:")
            parts.append(snippet)

        # Separator between documents
        parts.append("---")
    return "\n".join(parts)


# -------------------- Main Q&A --------------------
def ask_question(question, docs_context, chat_history=None):
    """
    Hybrid answering approach:
    1. Try direct metrics lookup (fast, rule-based).
    2. If not found, query Ollama LLM with document context.
    3. If Ollama fails, fallback to rule-based error message.

    Args:
        question (str): User query
        docs_context (list[dict]): Uploaded documents info
        chat_history (list[dict], optional): Previous chat messages

    Returns:
        str: Assistant's answer
    """
    # Step 1: Direct metrics lookup
    direct_answer = lookup_metrics(question, docs_context)
    if direct_answer:
        return direct_answer

    # Step 2: Build prompt for Ollama
    metrics_text = build_context_string(docs_context)

    system_prompt = textwrap.dedent(f"""
    You are a helpful financial assistant.
    Use ONLY the information in 'Document Metrics' to answer the user's question.
    If the information is not present, say:
    "I couldn't find the requested value in the uploaded documents."
    Do not hallucinate additional facts.
    """)

    # Include recent chat history for context (last 3 exchanges = 6 messages)
    history_text = ""
    if chat_history:
        for msg in chat_history[-6:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n"

    # Build user-specific part of the prompt
    user_prompt = f"""
    Document Metrics:
    {metrics_text}

    Conversation so far:
    {history_text}

    Current Question: {question}
    """

    # Request payload for Ollama API
    prompt_obj = {
        "model": "llama2",  # Change this to your installed Ollama model name
        "prompt": f"{system_prompt}\n\n{user_prompt}",
        "max_tokens": 512,
        "temperature": 0.0,  # Deterministic answers
    }

    # Step 3: Call Ollama API
    try:
        resp = requests.post(OLLAMA_URL, json=prompt_obj, timeout=30)
        if resp.status_code == 200:
            j = resp.json()
            if isinstance(j, dict) and "text" in j:
                return j["text"].strip()  # Return clean text answer
            return str(j)  # Fallback: return raw JSON if unexpected format
        else:
            return fallback_answer(question, docs_context)
    except Exception as e:
        # Network/timeout/connection errors → fallback
        return fallback_answer(question, docs_context, error=e)


# -------------------- Direct Metric Lookup --------------------
def lookup_metrics(question, docs_context):
    """
    Fast rule-based lookup: directly check if user is asking
    about common financial metrics (revenue, profit, assets, etc.).

    Args:
        question (str): User query
        docs_context (list[dict]): Uploaded documents

    Returns:
        str | None: Answer if found, else None
    """
    q = question.lower()

    # Mapping of keywords → metric keys
    possible_metrics = {
        "revenue": ["revenue", "sales"],
        "net_income": ["net income", "net profit", "profit"],
        "gross_profit": ["gross profit"],
        "ebitda": ["ebitda"],
        "total_assets": ["total assets", "assets"],
        "total_liabilities": ["liabilities"],
        "expenses": ["expenses", "costs"],
    }

    answers = []
    for m, kws in possible_metrics.items():
        if any(kw in q for kw in kws):  # If question contains keyword
            for d in docs_context:
                metrics = d.get("metrics", {}).get("metrics", {})
                val = metrics.get(m)
                if val is not None:
                    answers.append(f"{m.replace('_',' ').title()} (from {d['name']}): {val}")

    return "\n".join(answers) if answers else None


# -------------------- Fallback Answer --------------------
def fallback_answer(question, docs_context, error=None):
    """
    Fallback response if Ollama is unreachable or fails.

    Args:
        question (str): User query
        docs_context (list[dict]): Uploaded docs
        error (Exception, optional): Error message if any

    Returns:
        str: Safe fallback response
    """
    err_msg = f" (Ollama error: {error})" if error else ""
    return "I couldn't find the requested value in the uploaded documents." + err_msg
