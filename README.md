# 🍵 Tea and Tool Time — Multi-Tool AI Chatbot

A conversational AI chatbot built with **LangGraph** and **Streamlit**, capable of answering questions using multiple tools — web search, stock prices, calculator, currency conversion, weather, Wikipedia, and RAG over uploaded documents — all within persistent, multi-threaded chat sessions with Google OAuth authentication.

> 🚀 **Live Demo**: [mulit-tool-agent.up.railway.app](https://multi-tool-agent-production.up.railway.app/) *(restricted to authorized test users)*

***

## ✨ Features

### 🔐 Authentication
- **Google OAuth 2.0** — Secure sign-in with Google accounts
- **Session Management** — Persistent login sessions stored in SQLite
- **Multi-user Support** — Each user has isolated chat threads and document indexes
- **Test-Mode Access Control** — OAuth app kept in "Testing" mode; only whitelisted Google accounts can sign in
- **Sign Out** — Session invalidation with full state cleanup

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
- 🛡️ **Guardrails** — Off-topic, harmful, or inappropriate queries are blocked before reaching the LLM

### 🖥️ Frontend & UI
- 🧵 **Multi-threaded Conversations** — Each chat session is isolated with its own thread ID
- 💾 **Persistent Conversations** — Checkpointed to SQLite, survive app restarts
- ✍️ **Auto Thread Naming** — LLM generates a short title from the first message
- 🗑️ **Delete Chats** — Remove individual threads from history
- ⏰ **Chat Timestamps** — Every message shows the time it was sent
- 🏷️ **Tool Usage Badge** — Shows which tool was used for each assistant response
- 📡 **Streaming Responses** — Live token-by-token output with tool status indicators
- 🚦 **Rate Limiting** — Per-user rate limiting to prevent abuse and excessive API usage

***

## 🗂️ Project Structure

```
multi-tool-agent/
│
├── streamlit_frontend.py     # Streamlit UI — sidebar, chat, streaming
├── langgraph_backend.py      # LangGraph agent, tools, PDF ingestion, graph definition
├── auth.py                   # Session management and user authentication logic
├── google_oauth.py           # Google OAuth 2.0 flow
├── dockerfile                # Docker container build config
├── docker-compose.yml        # Multi-container orchestration
├── chatbot.db                # SQLite checkpoint + session store (auto-created)
├── faiss_store/              # Persisted FAISS indexes per thread (auto-created)
├── thread_names.json         # Auto-generated thread titles (auto-created)
├── requirements.txt          # Python dependencies
└── .env                      # API keys and secrets (not committed)
```

***

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
ALPHAVANTAGE_API_KEY=your_alphavantage_api_key

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
SECRET_KEY=your_random_secret_key
REDIRECT_URI=http://localhost:8501
```

| Key | Where to get it |
|-----|----------------|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) |
| `TAVILY_API_KEY` | [app.tavily.com](https://app.tavily.com) |
| `ALPHAVANTAGE_API_KEY` | [alphavantage.co](https://www.alphavantage.co/support/#api-key) |
| `GOOGLE_CLIENT_ID` | [console.cloud.google.com](https://console.cloud.google.com) → OAuth 2.0 Credentials |
| `GOOGLE_CLIENT_SECRET` | Same as above |
| `SECRET_KEY` | Any long random string (used for session signing) |

> **Note:** Currency converter and weather tools use free APIs — no additional keys required.
> Alpha Vantage free tier allows 25 requests/day.

### 5. Set up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use an existing one)
3. Navigate to **APIs & Services → Credentials**
4. Click **Create Credentials → OAuth 2.0 Client ID**
5. Set application type to **Web application**
6. Add `http://localhost:8501` to **Authorized Redirect URIs**
7. Copy the **Client ID** and **Client Secret** into your `.env`

> **Access control:** The app is kept in **Testing mode** in Google Cloud Console with a fixed list of authorized test users. Only those accounts can sign in — anyone else is blocked at the Google OAuth screen.

### 6. Run the app

```bash
streamlit run streamlit_frontend.py
```

***

## 🐳 Docker Setup

### Build and run with Docker Compose

```bash
docker-compose up --build
```

The app will be available at `http://localhost:8501`.

### Run with Docker directly

```bash
docker build -t tea-and-tool-time .
docker run -p 8501:8501 --env-file .env tea-and-tool-time
```

> **Note:** Make sure your `.env` file is present before running. The `REDIRECT_URI` should match the host you're deploying on.

***

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
authlib
httpx
```

***

## 🧠 How It Works

```
User visits app
    │
    ▼
Authenticated? ──► NO ──► Google OAuth Login
    │ YES                        │
    ▼                            ▼
Session restored ◄──── Session created + stored
    │
    ▼
Guardrails check ──► BLOCKED ──► Rejection message returned
    │ PASSED
    ▼
Rate limit check ──► EXCEEDED ──► "Too many requests" message
    │ OK
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

- **Google OAuth 2.0** handles authentication; sessions are stored in SQLite and tied to each user
- **LangGraph** state machine routes between LLM and tools automatically
- **SQLite** checkpointing saves full message history per thread per user
- **FAISS** stores document embeddings on disk per thread for fast similarity search
- **Memory summarization** kicks in when a thread exceeds 10 messages
- **Guardrails** intercept off-topic or harmful queries before they reach the LLM
- **Rate limiting** tracks per-user request counts to prevent API credit abuse

***

## 🖥️ Usage

1. Open the app in your browser (default: `http://localhost:8501`)
2. **Sign in with your Google account** *(only authorized accounts can access the app)*
3. Use the **sidebar** to start a new chat or revisit past conversations
4. Optionally **upload documents** (PDF, TXT, DOC, DOCX) to enable document Q&A
5. Type your query — the agent picks the right tool automatically
6. **Sign out** from the sidebar when done

### Example Queries

| Query | Tool Used |
|-------|-----------|
| `What is the stock price of Tesla?` | `get_stock_price` |
| `What does the document say about revenue?` | `rag_tool` |
| `What are the latest AI news?` | `tavily_search` |
| `What is 2345 multiplied by 67?` | `calculator` |
| `Convert 100 USD to INR` | `currency_converter` |
| `What is the weather in Hyderabad?` | `get_weather` |
| `What is the population of India?` | `wikipedia_search` |

***

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

***

## 🛡️ Security & Access Control

- **Google OAuth Testing Mode** — App is kept in "Testing" status in Google Cloud Console. Only the configured test users can authenticate; all others are blocked automatically by Google.
- **No public sign-up** — There is no self-registration flow. Access is explicitly granted per user.
- **OpenAI spend cap** — A monthly spending limit is set on the OpenAI account to prevent runaway costs even in edge cases.
- **Per-user rate limiting** — Each authenticated user has a request cap to prevent any single user from draining API quotas.
- **Guardrails** — The agent rejects off-topic, harmful, or prompt-injection attempts before they consume tokens.
- **Isolated data per user** — Each user's threads and FAISS indexes are namespaced by their user ID; no cross-user data access is possible.

***

## 🔒 Notes

- `.env`, `chatbot.db`, `faiss_store/`, and `thread_names.json` are all in `.gitignore`
- Each user's threads are isolated — one user cannot access another's conversations or documents
- Each thread has its own isolated FAISS index — uploading in one thread does not affect others
- FAISS indexes persist to disk — no need to re-upload documents after restart
- Memory summarization keeps long conversations efficient and within token limits
- Sessions are stored in SQLite and expire on sign out