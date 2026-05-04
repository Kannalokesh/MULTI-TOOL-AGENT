# 🍵 Tea and Tool Time — Multi-Tool AI Agent Chatbot

A conversational AI chatbot built with **LangGraph** and **Streamlit**, capable of answering questions using multiple tools — web search, stock prices, calculator, weather, currency conversion, Wikipedia, and RAG over uploaded documents — all within persistent, multi-threaded chat sessions.

---

## ✨ Features

- 🔍 **Web Search** — Real-time answers via Tavily Search
- 📈 **Stock Price Lookup** — Fetch live stock quotes using Alpha Vantage
- 🧮 **Calculator** — Precise arithmetic without hallucination
- 💱 **Currency Converter** — Convert between currencies using Frankfurter API (no key needed)
- 🌤️ **Weather Lookup** — Current weather for any city via wttr.in (no key needed)
- 📖 **Wikipedia Search** — General knowledge and concept explanations
- 📄 **RAG (Document Q&A)** — Upload documents and ask questions using FAISS vector search
- 📁 **Multi-file Support** — Upload multiple `.pdf`, `.txt`, `.doc`, `.docx` files per thread
- 🧵 **Multi-threaded Conversations** — Each chat session is isolated with its own thread ID
- ✍️ **Auto Thread Naming** — LLM auto-generates a short title from the first message
- 💾 **Persistent Memory** — Conversations checkpointed to SQLite, FAISS indexes saved to disk
- 🧠 **Memory Summarization** — Older messages are summarized to stay within token limits
- 📄 **Source Citations** — RAG answers cite the source filename and page number
- ⏰ **Chat Timestamps** — Every message shows when it was sent
- 🏷️ **Tool Usage Badges** — Each response shows which tool was used
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
├── thread_names.json         # Auto-generated thread titles (auto-created)
├── faiss_store/              # Persisted FAISS indexes per thread (auto-created)
│   └── <thread-id>/
│       ├── index.faiss
│       ├── index.pkl
│       └── metadata.json
├── requirements.txt          # Python dependencies
└── .env                      # API keys (not committed)
```

---

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone https://github.com/Kannalokesh/MULTI-TOOL-AGENT.git
cd MULTI-TOOL-AGENT
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
```

| Key | Where to get it |
|-----|----------------|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) |
| `TAVILY_API_KEY` | [app.tavily.com](https://app.tavily.com) |
| `ALPHAVANTAGE_API_KEY` | [app.alphavantage.com](https://www.alphavantage.co/support/#api-key) |

> **Note:** Currency converter and weather tools require **no API keys** — they use free public APIs.
> Alpha Vantage stock price tool uses a free key  (25 requests/day limit) get from the site.

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
python-docx==1.1.2
wikipedia==1.4.0
```

---

## 🧠 How It Works

```
User Query
    │
    ▼
should_summarize?  ──► YES ──► summarize_node (condense old messages)
    │ NO                              │
    ▼                                ▼
 chat_node  ◄─────────────────────────
    │
    ▼
 LLM selects tool
    │
    ▼
 tool_node  ──► rag_tool / tavily_search / get_stock_price /
                calculator / currency_converter /
                get_weather / wikipedia_search
    │
    ▼
 chat_node  ──► LLM formulates final response
    │
    ▼
 Streamlit  ──► Streams response with timestamps + tool badges
```

- **LangGraph** state machine routes between LLM and tools automatically
- **Memory summarization** kicks in when messages exceed 10, keeping token usage efficient
- **SQLite** checkpointing saves full message history per thread
- **FAISS** indexes are persisted to disk and auto-loaded on app restart
- **Tool badges** show which tool was used for each response

---

## 🖥️ Usage

1. Open the app in your browser (default: `http://localhost:8501`)
2. Use the **sidebar** to start a new chat or revisit past conversations
3. Optionally **upload documents** (`.pdf`, `.txt`, `.doc`, `.docx`) to enable RAG for that thread
4. Type your query — the agent picks the right tool automatically

### Example Queries

| Query | Tool Used |
|-------|-----------|
| `What is the stock price of Tesla?` | `get_stock_price` |
| `What does the document say about revenue?` | `rag_tool` |
| `What are the latest AI news?` | `tavily_search` |
| `What is 2345 multiplied by 67?` | `calculator` |
| `Convert 100 USD to INR` | `currency_converter` |
| `What is the weather in Hyderabad?` | `weather_lookup` |
| `What is the population of India?` | `wikipedia_search` |

---

## 🔒 Notes

- The `.env` file is **never committed** — add it to `.gitignore`
- `chatbot.db`, `faiss_store/`, and `thread_names.json` are auto-created on first run
- Each thread maintains its own document index — uploading in one thread does not affect others
- FAISS indexes survive app restarts — no need to re-upload documents
- Memory summarization triggers automatically after 10 messages per thread

