from __future__ import annotations

import os
import json
import sqlite3
import tempfile
import wikipedia
from typing import Annotated, Any, Dict, Optional, TypedDict
from dotenv import load_dotenv
from docx import Document as DocxDocument
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.messages import BaseMessage, SystemMessage, RemoveMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_tavily import TavilySearch
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import requests

load_dotenv()

FAISS_STORE_DIR = "faiss_store"
os.makedirs(FAISS_STORE_DIR, exist_ok=True)


# -------------------
# 1. LLM + embeddings
# -------------------
llm = ChatOpenAI(model="gpt-4o-mini")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# -------------------
# 2. PDF retriever store (per thread)
# -------------------
_THREAD_RETRIEVERS: Dict[str, Any] = {}
_THREAD_METADATA: Dict[str, dict] = {}


def _get_retriever(thread_id: Optional[str]):
    """Fetch the retriever for a thread if available."""
    if thread_id and thread_id in _THREAD_RETRIEVERS:
        return _THREAD_RETRIEVERS[thread_id]
    return None


def _load_file(file_path: str, filename: str) -> list:
    ext = os.path.splitext(filename)[-1].lower()

    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        # Override source with actual filename
        for doc in docs:
            doc.metadata["source"] = filename
        return docs

    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return [Document(page_content=text, metadata={"source": filename, "page": 0})]

    elif ext in [".doc", ".docx"]:
        docx = DocxDocument(file_path)
        text = "\n".join([para.text for para in docx.paragraphs if para.text.strip()])
        return [Document(page_content=text, metadata={"source": filename, "page": 0})]

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def ingest_file(
    file_bytes: bytes, thread_id: str, filename: Optional[str] = None
) -> dict:
    """
    Build or update a FAISS retriever for the uploaded file and store it for the thread.
    Supports .pdf, .txt, .doc, .docx files.
    Multiple files per thread are merged into one index.
    """
    if not file_bytes:
        raise ValueError("No bytes received for ingestion.")

    ext = os.path.splitext(filename)[-1].lower() if filename else ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name

    try:
        docs = _load_file(temp_path, filename)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(docs)

        faiss_path = os.path.join(FAISS_STORE_DIR, str(thread_id))

        # If index already exists for this thread, merge into it
        if str(thread_id) in _THREAD_RETRIEVERS and os.path.exists(faiss_path):
            existing_store = FAISS.load_local(
                faiss_path, embeddings, allow_dangerous_deserialization=True
            )
            existing_store.add_documents(chunks)
            vector_store = existing_store
        else:
            vector_store = FAISS.from_documents(chunks, embeddings)

        # Save updated index to disk
        vector_store.save_local(faiss_path)

        retriever = vector_store.as_retriever(
            search_type="similarity", search_kwargs={"k": 4}
        )
        _THREAD_RETRIEVERS[str(thread_id)] = retriever

        # Update metadata — track all files
        existing_meta = _THREAD_METADATA.get(str(thread_id), {"files": [], "total_chunks": 0, "total_documents": 0})
        existing_meta["files"].append(filename)
        existing_meta["total_documents"] += len(docs)
        existing_meta["total_chunks"] += len(chunks)
        _THREAD_METADATA[str(thread_id)] = existing_meta

        # Save metadata to disk
        meta_path = os.path.join(faiss_path, "metadata.json")
        with open(meta_path, "w") as f:
            json.dump(_THREAD_METADATA[str(thread_id)], f)

        return {
            "filename": filename,
            "documents": len(docs),
            "chunks": len(chunks),
        }
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


# -------------------
# 3. Tools
# -------------------
search_tool = TavilySearch(max_results=5)

# calculator
@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}

        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result,
        }
    except Exception as e:
        return {"error": str(e)}

# stock price
@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA')
    using Alpha Vantage with API key in the URL.
    """
    url = (
        "https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE&symbol={symbol}&apikey=C9PE94QUEW9VWGFM"
    )
    r = requests.get(url)
    return r.json()


# Currency Converter
@tool
def currency_converter(amount: float, from_currency: str, to_currency: str) -> dict:
    """
    Convert an amount from one currency to another.
    Examples: from_currency='USD', to_currency='INR', amount=100
    """
    try:
        url = f"https://api.frankfurter.app/latest?amount={amount}&from={from_currency.upper()}&to={to_currency.upper()}"
        r = requests.get(url)
        data = r.json()
        if "rates" not in data:
            return {"error": "Invalid currency or conversion not available."}
        result = data["rates"].get(to_currency.upper())
        return {
            "amount": amount,
            "from": from_currency.upper(),
            "to": to_currency.upper(),
            "result": result,
            "date": data.get("date"),
        }
    except Exception as e:
        return {"error": str(e)}


#  Weather
@tool
def get_weather(city: str) -> dict:
    """
    Get ONLY the current weather conditions (temperature, humidity, wind, description)
    for a given city name. Use this for weather and climate queries ONLY.
    Do NOT use this for stock prices, currency, or any financial queries.
    Example: city='Hyderabad', city='London', city='New York'
    """
    try:
        url = f"https://wttr.in/{city}?format=j1"
        r = requests.get(url, timeout=10)
        data = r.json()
        current = data["current_condition"][0]
        return {
            "city": city,
            "temperature_c": current["temp_C"],
            "temperature_f": current["temp_F"],
            "feels_like_c": current["FeelsLikeC"],
            "humidity": current["humidity"],
            "description": current["weatherDesc"][0]["value"],
            "wind_speed_kmph": current["windspeedKmph"],
        }
    except Exception as e:
        return {"error": str(e)}


#  Wikipedia
@tool
def wikipedia_search(query: str) -> dict:
    """
    Search Wikipedia and return a summary for the given query.
    Use for general knowledge, historical facts, or concept explanations.
    """
    try:
        page = wikipedia.page(query, auto_suggest=True)
        summary = wikipedia.summary(query, sentences=5, auto_suggest=True)
        return {
            "title": page.title,
            "summary": summary,
            "url": page.url,
        }
    except wikipedia.exceptions.DisambiguationError as e:
        return {"error": f"Ambiguous query. Did you mean: {e.options[:5]}"}
    except wikipedia.exceptions.PageError:
        return {"error": f"No Wikipedia page found for '{query}'"}
    except Exception as e:
        return {"error": str(e)}

# rag 
@tool
def rag_tool(query: str, thread_id: Optional[str] = None) -> dict:
    """
    Retrieve relevant information from the uploaded PDF for this chat thread.
    ALWAYS call this tool first for any user question when a document is available.
    Always include the thread_id when calling this tool.
    """
    retriever = _get_retriever(thread_id)

    if retriever is None:
        return {
            "error": "No document indexed for this chat. Upload a PDF first.",
            "query": query,
        }

    result = retriever.invoke(query)
    # Build cited chunks with page numbers
    cited_chunks = []
    for doc in result:
        cited_chunks.append({
            "content": doc.page_content,
            "page": doc.metadata.get("page", "unknown"),
            "source": doc.metadata.get("source", _THREAD_METADATA.get(str(thread_id), {}).get("filename", "document")),
        })

    return {
        "query": query,
        "results": cited_chunks,
        "source_file": _THREAD_METADATA.get(str(thread_id), {}).get("filename"),
    }


tools = [search_tool, get_stock_price, calculator, rag_tool, currency_converter, get_weather, wikipedia_search]
llm_with_tools = llm.bind_tools(tools)


# -------------------
# 4. State
# -------------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# -------------------
# 5. Nodes
# -------------------
def chat_node(state: ChatState, config=None):
    """LLM node that may answer or request a tool call."""
    thread_id = None
    if config and isinstance(config, dict):
        thread_id = config.get("configurable", {}).get("thread_id")
  
    system_message = SystemMessage(
    content=(
        "You are a precise, tool-driven assistant. "
        "You NEVER answer from memory when a tool is available. "
        "Always select the single most appropriate tool for each query.\n\n"

        "## Tool Selection Rules (follow strictly in order)\n\n"

        "1. **rag_tool** — HIGHEST PRIORITY\n"
        f"   - thread_id for this session: `{thread_id}`\n"
        "   - Invoke IMMEDIATELY if the user asks ANYTHING about an uploaded document, "
        "file, PDF, or says 'according to the document', 'what does it say', 'summarize', etc.\n"
        "   - Also invoke if a document was previously uploaded in this thread — "
        "check thread memory before deciding to skip.\n"
        "   - ALWAYS pass `thread_id` when calling this tool.\n"
        "   - ALWAYS cite the source at the end: `📄 Source: filename, Page(s): X`\n"
        "   - If rag_tool returns no results, fall back to `wikipedia_search` or `tavily_search`.\n\n"

        "2. **get_stock_price** — for stock/share price queries\n"
        "   - Invoke for any query mentioning a stock, share price, ticker, or market value.\n"
        "   - Accepts ticker symbols (e.g. AAPL, TSLA, INFY).\n\n"

        "3. **calculator** — for arithmetic only\n"
        "   - Invoke for any addition, subtraction, multiplication, or division.\n"
        "   - NEVER compute math mentally — always use this tool.\n\n"

        "4. **currency_converter** — for currency conversion\n"
        "   - Invoke when user asks to convert between currencies.\n"
        "   - Accepts: amount, from_currency, to_currency (e.g. 100 USD to INR).\n\n"

        "5. **get_weather** — ONLY for weather, temperature, humidity, forecast questions.\n"
        "   - Keywords: weather, temperature, hot, cold, raining, forecast, climate.\n"
        "   - Accepts a city name (e.g. Hyderabad, Mumbai, New York).\n"
        "   - This is NEVER used for stock prices or financial data.\n\n"

        "6. **wikipedia_search** — for general knowledge\n"
        "   - Invoke for concepts, definitions, historical facts, or well-known topics.\n"
        "   - Prefer this over tavily_search for established knowledge.\n\n"

        "7. **tavily_search** — for real-time web search\n"
        "   - Invoke for current events, recent news, or anything time-sensitive.\n"
        "   - Use only when other tools are not suitable.\n\n"

        "## Hard Rules\n"
        "- NEVER answer from your own knowledge if a relevant tool exists.\n"
        "- NEVER skip rag_tool if a document is available in this thread.\n"
        "- NEVER fabricate data — if a tool returns no result, say so honestly.\n"
        "- ONE tool per query unless chaining is explicitly needed (e.g. fetch stock price THEN calculate).\n"
        "- If unsure between two tools, pick the more specific one."
        )
    )

    messages = [system_message, *state["messages"]]
    response = llm_with_tools.invoke(messages, config=config)
    return {"messages": [response]}

SUMMARY_THRESHOLD = 10
def summarize_node(state: ChatState, config=None):
    """Summarize older messages when conversation gets too long."""
    messages = state["messages"]

    if len(messages) <= SUMMARY_THRESHOLD:
        return {}

    # Split into old and recent
    messages_to_summarize = messages[:-6]  # everything except last 6
    recent_messages = messages[-6:]        # keep last 6 intact

    # Build summary prompt
    summary_prompt = (
        "Summarize the following conversation history concisely, "
        "preserving all key facts, answers, and context:\n\n"
        + "\n".join(
            f"{m.type.upper()}: {m.content}"
            for m in messages_to_summarize
            if hasattr(m, "content") and m.content
        )
    )

    summary_response = llm.invoke([HumanMessage(content=summary_prompt)])
    summary_text = f"[Conversation Summary]: {summary_response.content}"

    # Remove old messages and replace with summary
    messages_to_remove = [RemoveMessage(id=m.id) for m in messages_to_summarize]
    summary_message = SystemMessage(content=summary_text)

    return {"messages": messages_to_remove + [summary_message] + recent_messages}

tool_node = ToolNode(tools)

# -------------------
# 6. Checkpointer
# -------------------
conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

# -------------------
# 7. Graph
# -------------------
def should_summarize(state: ChatState):
    """Route to summarize_node if messages exceed threshold."""
    if len(state["messages"]) > SUMMARY_THRESHOLD:
        return "summarize"
    return "chat_node"

# nodes
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)
graph.add_node("summarize_node", summarize_node)

# edges
graph.add_conditional_edges(START, should_summarize)
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")
graph.add_edge("summarize_node", "chat_node")


chatbot = graph.compile(checkpointer=checkpointer)


# -------------------
# 8. Helpers
# -------------------
def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)


def thread_has_document(thread_id: str) -> bool:
    return str(thread_id) in _THREAD_RETRIEVERS


def thread_document_metadata(thread_id: str) -> dict:
    return _THREAD_METADATA.get(str(thread_id), {})
