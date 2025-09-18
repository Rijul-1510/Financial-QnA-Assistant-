# modules/qa_engine.py
import requests
import textwrap

OLLAMA_URL = "http://localhost:11434/api/generate"  # Local Ollama endpoint

def build_context_string(docs_context):
    """
    Build a compact context string for the LLM prompt.
    Includes extracted metrics and short text snippets.
    """
    parts = []
    for d in docs_context:
        parts.append(f"Document: {d['name']}")
        cur = d.get("metrics", {})
        currency = d.get("currency", None)
        
        # Metrics
        if isinstance(cur, dict):
            metrics = cur.get("metrics", {})
            if metrics:
                parts.append("KeyMetrics:")
                for m, v in metrics.items():
                    parts.append(f"- {m}: {v}")
        
        # Currency if present
        if currency:
            parts.append(f"Currency: {currency}")

        # Snippet for context (first 800 chars of raw text)
        snippet = (d.get("raw_text") or "")[:800]
        if snippet:
            parts.append("TextSnippet:")
            parts.append(snippet)

        parts.append("---")
    return "\n".join(parts)

def ask_question(question, docs_context, chat_history=None):
    """
    Hybrid answering:
    1. Try direct metrics lookup.
    2. If not found, query Ollama.
    3. If Ollama fails, fallback rule-based response.
    """
    # Step 1: Try direct lookup
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

    # Include chat history for conversational context
    history_text = ""
    if chat_history:
        for msg in chat_history[-6:]:  # last 3 exchanges
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n"

    user_prompt = f"""
    Document Metrics:
    {metrics_text}

    Conversation so far:
    {history_text}

    Current Question: {question}
    """

    prompt_obj = {
        "model": "llama2",  # Replace with your Ollama model name
        "prompt": f"{system_prompt}\n\n{user_prompt}",
        "max_tokens": 512,
        "temperature": 0.0,
    }

    try:
        resp = requests.post(OLLAMA_URL, json=prompt_obj, timeout=30)
        if resp.status_code == 200:
            j = resp.json()
            if isinstance(j, dict) and "text" in j:
                return j["text"].strip()
            return str(j)
        else:
            return fallback_answer(question, docs_context)
    except Exception as e:
        return fallback_answer(question, docs_context, error=e)

def lookup_metrics(question, docs_context):
    """
    Direct lookup: if the user asks for revenue, profit, assets, etc.
    """
    q = question.lower()
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
        if any(kw in q for kw in kws):
            for d in docs_context:
                metrics = d.get("metrics", {}).get("metrics", {})
                val = metrics.get(m)
                if val is not None:
                    answers.append(f"{m.replace('_',' ').title()} (from {d['name']}): {val}")

    if answers:
        return "\n".join(answers)
    return None

def fallback_answer(question, docs_context, error=None):
    """
    Fallback if Ollama is unreachable.
    """
    err_msg = f" (Ollama error: {error})" if error else ""
    return "I couldn't find the requested value in the uploaded documents." + err_msg
