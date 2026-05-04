# 🍵 Tea and Tool Time — Multi-Tool AI Chatbot

A conversational AI chatbot built with **LangGraph** and **Streamlit**, capable of answering questions using multiple tools — web search, stock prices, arithmetic, and RAG over uploaded PDFs — all within persistent, multi-threaded chat sessions.

---

## ✨ Features

- 🔍 **Web Search** — Real-time answers via Tavily Search
- 📈 **Stock Price Lookup** — Fetch live stock quotes using Alpha Vantage
- 🧮 **Calculator** — Precise arithmetic without hallucination
- 📄 **RAG (PDF Q&A)** — Upload a PDF and ask questions about it using FAISS vector search
- 🧵 **Multi-threaded Conversations** — Each chat session is isolated with its own thread ID
- 💾 **Persistent Memory** — Conversations are checkpointed to SQLite and survive app restarts
- 🗑️ **Delete Chats** — Remove individual threads from history
- 📡 **Streaming Responses** — Live token-by-token output with tool status indicators

---

## 🗂️ Project Structure

```
multi-tool-agent/
│
├── langgraph_backend.py      # LangGraph agent, tools, PDF ingestion, graph definition
├── streamlit_frontend.py     # Streamlit UI — sidebar, chat, streaming
├── chatbot.db                # SQLite checkpoint store (auto-created)
├── requirements.txt          # Python dependencies
└── .env                      # API keys (not committed)
```

---

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone https://github.com/Kannalokesh/MULTI-TOOL-AGENT.git
cd multi-tool-agent
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
ALPHAVANTAGE_API_KEY=your_alphavantage_api_key
```

| Key | Where to get it |
|-----|----------------|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) |
| `TAVILY_API_KEY` | [app.tavily.com](https://app.tavily.com) |
| `ALPHAVANTAGE_API_KEY` | [alphavantage.co](https://www.alphavantage.co/support/#api-key) |

### 5. Run the app

```bash
streamlit run streamlit_frontend.py
```

---

## 📦 Requirements

```
python-dotenv==1.2.2
requests==2.33.1
streamlit==1.57.0
langchain==1.2.17
langchain-core==1.3.2
langchain-community==0.4.1
langchain-openai==1.2.1
langchain-text-splitters==1.1.2
langchain-tavily==0.2.18
langgraph==1.1.10
langgraph-checkpoint-sqlite==3.0.3
faiss-cpu==1.13.2
pypdf==6.10.2
```

---

## 🧠 How It Works

```
User Query
    │
    ▼
 chat_node  ──► LLM decides which tool to call
    │
    ▼
 tool_node  ──► Executes: rag_tool / tavily_search / get_stock_price / calculator
    │
    ▼
 chat_node  ──► LLM formulates final response
    │
    ▼
 Streamlit  ──► Streams response to user
```

- The **LangGraph** state machine routes between the LLM and tools automatically
- **SQLite** checkpointing saves the full message history per thread
- **FAISS** stores PDF embeddings in-memory per thread for fast similarity search

---

## 🖥️ Usage

1. Open the app in your browser (default: `http://localhost:8501`)
2. Use the **sidebar** to start a new chat or revisit past conversations
3. Optionally **upload a PDF** to enable document Q&A for that thread
4. Type your query in the chat input — the agent will pick the right tool automatically

### Example queries

| Query | Tool Used |
|-------|-----------|
| `What is the stock price of Tesla?` | `get_stock_price` |
| `What does the document say about revenue?` | `rag_tool` |
| `What are the latest AI news?` | `tavily_search` |
| `What is 2345 multiplied by 67?` | `calculator` |

---

## 🔒 Notes

- The `.env` file is **never committed** — add it to `.gitignore`
- `chatbot.db` is auto-created on first run
- Each chat thread maintains its own PDF index — uploading in one thread does not affect others
- PDF data is stored **in-memory** and lost on app restart (re-upload if needed)

---

## 📄 License

MIT License — feel free to use, modify, and build on this project.