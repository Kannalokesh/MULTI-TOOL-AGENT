
# 🍵 Tea and Tool Time — Multi-Tool AI Chatbot

A conversational AI chatbot built with **LangGraph** and **Streamlit**, capable of answering questions using multiple tools — web search, stock prices, calculator, currency conversion, weather, Wikipedia, and RAG over uploaded documents — all within persistent, multi-threaded chat sessions.

---

## ✨ Features

### 🧠 Agent & Backend
- 🔍 **Web Search** — Real-time answers via Tavily Search
- 📈 **Stock Price Lookup** — Fetch live stock quotes using Alpha Vantage
- 🧮 **Calculator** — Precise arithmetic without hallucination
- 💱 **Currency Converter** — Convert between currencies using Frankfurter API (no key needed)
- 🌤️ **Weather Lookup** — Current weather for any city via wttr.in (no key needed)
- 📖 **Wikipedia Search** — General knowledge and concept explanations
- 📄 **RAG (Document Q&A)** — Upload documents and ask questions using FAISS vector search
- 📄 **Source Citations** — RAG answers include filename and page number references
- 💾 **Persistent FAISS Index** — Document indexes saved to disk, survive app restarts
- 🧠 **Memory Summarization** — Long conversations are auto-summarized to stay within token limits
- 📁 **Multi-file Upload** — Accepts `.pdf`, `.txt`, `.doc`, `.docx` files per thread

### 🖥️ Frontend & UI
- 🧵 **Multi-threaded Conversations** — Each chat session is isolated with its own thread ID
- 💾 **Persistent Conversations** — Checkpointed to SQLite, survive app restarts
- ✍️ **Auto Thread Naming** — LLM generates a short title from the first message
- 🗑️ **Delete Chats** — Remove individual threads from history
- ⏰ **Chat Timestamps** — Every message shows the time it was sent
- 🏷️ **Tool Usage Badge** — Shows which tool was used for each assistant response
- 📡 **Streaming Responses** — Live token-by-token output with tool status indicators

---

## 🗂️ Project Structure

```
multi-tool-agent/
│
├── langgraph_backend.py      # LangGraph agent, tools, PDF ingestion, graph definition
├── streamlit_frontend.py     # Streamlit UI — sidebar, chat, streaming
├── chatbot.db                # SQLite checkpoint store (auto-created)
├── faiss_store/              # Persisted FAISS indexes per thread (auto-created)
├── thread_names.json         # Auto-generated thread titles (auto-created)
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

> **Note:** Currency converter and weather tools use free APIs — no additional keys required.
> Alpha Vantage stock price tool uses a free key with 25 requests/day - get from the site

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
wikipedia==1.4.0
python-docx==1.1.2
```

---

## 🧠 How It Works

```
User Query
    │
    ▼
should_summarize?  ──► YES ──► summarize_node (condense old messages)
    │ NO                              │
    ▼                                 ▼
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
- **SQLite** checkpointing saves full message history per thread
- **FAISS** stores document embeddings on disk per thread for fast similarity search
- **Memory summarization** kicks in when a thread exceeds 10 messages

---

## 🖥️ Usage

1. Open the app in your browser (default: `http://localhost:8501`)
2. Use the **sidebar** to start a new chat or revisit past conversations
3. Optionally **upload documents** (PDF, TXT, DOC, DOCX) to enable document Q&A
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
| `What is the population of india?` | `wikipedia_search` |

---

## 🔧 Tool Overview

| Tool | API Used | Key Required |
|------|----------|--------------|
| `tavily_search` | Tavily | ✅ Yes |
| `get_stock_price` | Alpha Vantage | ✅ Yes (free tier) |
| `calculator` | Built-in | ❌ No |
| `currency_converter` | Frankfurter API | ❌ No |
| `get_weather` | wttr.in | ❌ No |
| `wikipedia_search` | Wikipedia | ❌ No |
| `rag_tool` | FAISS + OpenAI | ✅ OpenAI key |

---

## 🔒 Notes

- `.env`, `chatbot.db`, `faiss_store/`, and `thread_names.json` are all in `.gitignore`
- Each thread has its own isolated FAISS index — uploading in one thread does not affect others
- FAISS indexes persist to disk — no need to re-upload documents after restart
- Memory summarization keeps long conversations efficient and within token limits
