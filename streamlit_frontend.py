import os
import json
import uuid
import secrets        
import shutil
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from datetime import datetime

from auth import (
    upsert_user,          
    create_session,       
    validate_session,     
    delete_session,       
    check_rate_limit,
    purge_expired_sessions, 
)

from google_oauth import build_auth_url, exchange_code, get_user_info  

from langraph_backend import (
    chatbot,
    conn,
    ingest_file,
    FAISS_STORE_DIR,
    retrieve_all_threads,
    save_thread_name,
    load_thread_names,
)


# ─── Handle OAuth callback ────────────────────────────────────────
query_params = st.query_params
if "code" in query_params and "state" in query_params:
    returned_state = query_params.get("state", "")
    
    # Read state from temp file instead of session_state
    state_file = ".oauth_state.json"
    stored_state = ""
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            stored_state = json.load(f).get("state", "")
        os.remove(state_file)   # delete immediately after reading

    if stored_state and stored_state == returned_state:
        try:
            token_data = exchange_code(query_params["code"])
            user_info  = get_user_info(token_data["access_token"])
            user = upsert_user(
                google_id = user_info["sub"],
                email     = user_info["email"],
                name      = user_info.get("name", user_info["email"]),
                picture   = user_info.get("picture", ""),
            )
            session_token = create_session(user["google_id"])
            st.session_state["session_token"] = session_token
            st.session_state["user"]          = user
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"OAuth error: {e}")
            st.stop()
    else:
        st.error("State mismatch — please try again.")
        st.query_params.clear()
        st.stop()

# ─── Validate session ─────────────────────────────────────────────
purge_expired_sessions()
session_token = st.session_state.get("session_token")
current_user  = validate_session(session_token) if session_token else None

# ─── Login wall ───────────────────────────────────────────────────

if not current_user:
    if "oauth_state" not in st.session_state:
        state = secrets.token_urlsafe(16)
        st.session_state["oauth_state"] = state
        with open(".oauth_state.json", "w") as f:
            json.dump({"state": state}, f)

    auth_url = build_auth_url(st.session_state["oauth_state"])

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&display=swap');

    .login-title {
        font-family: 'Playfair Display', serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px !important;
    }
    </style>
    """, unsafe_allow_html=True)


    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&display=swap');
                
    #MainMenu, footer, header {{visibility: hidden;}}
    .stAppDeployButton {{display: none;}}

    .stApp {{
        background: radial-gradient(ellipse at 60% 20%, #e0d4f7 0%, #ede8f8 40%, #f0ecfa 100%);
    }}

    .login-wrap {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 90vh;
        padding: 2rem 1rem;
    }}

    .login-card {{
        background: rgba(240, 236, 250, 0.97);
        border: 1px solid rgba(160, 130, 210, 0.25);
        border-radius: 28px;
        padding: 3rem 3rem 2.5rem 3rem;
        max-width: 440px;
        width: 100%;
        box-shadow:
            0 2px 8px rgba(120,90,180,0.07),
            0 8px 32px rgba(120,90,180,0.10),
            0 0 0 1px rgba(200,185,240,0.18);
        text-align: center;
        position: relative;
        overflow: hidden;
    }}

    .login-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 4px;
        background: linear-gradient(90deg, #9b6fd4, #c49ee8, #9b6fd4);
        border-radius: 28px 28px 0 0;
    }}

    .login-emoji {{
        font-size: 4.5rem;
        display: block;
        margin-bottom: 0.75rem;
        filter: drop-shadow(0 6px 12px rgba(120,80,180,0.18));
    }}

    .login-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        background: rgba(150,110,210,0.1);
        border: 1px solid rgba(150,110,210,0.2);
        border-radius: 999px;
        padding: 0.25rem 0.75rem;
        font-family: 'Playfair Display', serif !important;
        font-size: 0.72rem;
        color: #6b3fa0;
        margin-bottom: 1.2rem;
    }}

    .login-title {{
        font-size: 2rem;
        font-weight: 800;
        color: #1e0e30;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
    }}

    .login-subtitle {{
        font-size: 0.95rem;
        font-family: 'Playfair Display', serif !important;
        color: #7a5a9a;
        margin-bottom: 1.6rem;
        line-height: 1.6;
    }}

    .login-divider {{
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin: 0 auto 1.8rem auto;
    }}

    .login-divider-line {{
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(150,110,210,0.3), transparent);
    }}

    .login-divider-icon {{
        font-size: 0.85rem;
        color: #a87ed4;
    }}

    .login-features {{
        font-family: 'Playfair Display', serif !important;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.75rem;
        margin-bottom: 2rem;
    }}

    .login-feature-item {{
        background: #e8e0f5;
        border: 1px solid rgba(150,120,200,0.25);
        border-radius: 14px;
        padding: 0.85rem 0.6rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.35rem;
        transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
        cursor: default;
    }}

    .login-feature-item:hover {{
        background: #ddd4f0;
        border-color: rgba(140,100,200,0.5);
        transform: translateY(-4px) scale(1.03);
        box-shadow:
            0 8px 20px rgba(120,90,180,0.14),
            0 0 0 1px rgba(160,130,210,0.2);
    }}

    .login-feature-item:hover .login-feature-icon {{
        filter: drop-shadow(0 4px 8px rgba(120,80,180,0.25));
        transform: scale(1.15);
        transition: all 0.25s ease;
        display: inline-block;
    }}

    .login-feature-item:hover .login-feature-label {{
        color: #3a1a6a;
        transition: color 0.2s ease;
    }}

    .login-feature-icon {{
        font-size: 1.5rem;
    }}

    .login-feature-label {{
        font-size: 0.78rem;
        color: #4a3070;
        font-weight: 500;
        line-height: 1.3;
    }}

    .google-btn {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.6rem;
        width: 100%;
        padding: 0.85rem 1.5rem;
        background: #ffffff;
        border: 1.5px solid rgba(150,110,210,0.35);
        border-radius: 12px;
        font-family: 'Playfair Display', serif !important;
        font-size: 0.95rem;
        font-weight: 600;
        color: #2d1050;
        text-decoration: none;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(120,90,180,0.08);
        transition: all 0.2s ease;
        margin-bottom: 1rem;
    }}

    .google-btn:hover {{
        background: #f0eaff;
        border-color: rgba(150,110,210,0.6);
        box-shadow: 0 4px 16px rgba(120,90,180,0.14);
        transform: translateY(-1px);
        text-decoration: none;
        color: #2d1050;
    }}

    .login-footer {{
        font-size: 0.72rem;
        font-family: 'Playfair Display', serif !important;
        color: #9a7ab8;
    }}
    </style>
    

    <div class="login-wrap">
        <div class="login-card">
            <span class="login-emoji">🍵</span>
            <div class="login-badge">✦ AI-Powered</div>
            <div class="login-title">Tea &amp; Tool Time</div>
            <div class="login-subtitle">Your warm, intelligent workspace.<br>Brew a conversation.</div>
            <div class="login-divider">
                <div class="login-divider-line"></div>
                <div class="login-divider-icon">✦</div>
                <div class="login-divider-line"></div>
            </div>
            <div class="login-features">
                <div class="login-feature-item">
                    <span class="login-feature-icon">📄</span>
                    <span class="login-feature-label">Chat with<br>Documents</span>
                </div>
                <div class="login-feature-item">
                    <span class="login-feature-icon">📈</span>
                    <span class="login-feature-label">Stocks &amp;<br>Currency</span>
                </div>
                <div class="login-feature-item">
                    <span class="login-feature-icon">🌤️</span>
                    <span class="login-feature-label">Weather<br>Lookup</span>
                </div>
                <div class="login-feature-item">
                    <span class="login-feature-icon">📖</span>
                    <span class="login-feature-label">Wikipedia<br>Search</span>
                </div>
            </div>
            <a href="{auth_url}" class="google-btn">
                🔐 Sign in with Google
            </a>
            <div class="login-footer"> Secure Google login &nbsp;·&nbsp; Your data stays private</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.stop()



# =========================== Utilities ===========================
def get_timestamp():
    return datetime.now().strftime("%I:%M %p · %b %d")  # e.g. "10:35 AM · May 04"

def generate_thread_id():
    return f"{google_id}_{uuid.uuid4()}"

def generate_thread_name(first_message: str) -> str:
    """Use LLM to generate a short title from the first user message."""
    from langraph_backend import llm
    response = llm.invoke(
        f"Generate a very short 3-5 word title for a chat that starts with this message: "
        f'"{first_message}". Reply with ONLY the title, no quotes, no punctuation at the end.'
    )
    return response.content.strip()

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state["thread_id"] = thread_id
    add_thread(thread_id)
    st.session_state["message_history"] = []


def add_thread(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)

def delete_thread(thread_id):
    thread_id_str = str(thread_id)
    if thread_id_str in st.session_state.get("thread_names", {}):
        del st.session_state["thread_names"][thread_id_str]
    save_thread_name(thread_id_str, None)
    if thread_id in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].remove(thread_id)
    if thread_id_str in st.session_state["ingested_docs"]:
        del st.session_state["ingested_docs"][thread_id_str]

    # Delete FAISS store from disk
    faiss_path = os.path.join(FAISS_STORE_DIR, thread_id_str)
    if os.path.exists(faiss_path):
        shutil.rmtree(faiss_path)

    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}
        for table in ["checkpoints", "checkpoint_writes", "checkpoint_blobs"]:
            if table in existing_tables:
                conn.execute(f"DELETE FROM {table} WHERE thread_id = ?", (thread_id_str,))
        conn.commit()
    except Exception:
        pass


def load_conversation(thread_id):
    state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
    messages = state.values.get("messages", [])
    # Filter out ToolMessages and empty AIMessages
    return [
        msg for msg in messages
        if isinstance(msg, (HumanMessage, AIMessage))
        and msg.content  # skip empty content
        and not isinstance(msg.content, list)  # skip tool call messages
    ]

google_id = current_user["google_id"]

# ======================= Session Initialization ===================
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_names" not in st.session_state:
    st.session_state["thread_names"] = load_thread_names()

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

# filter by current user's google_id
if "chat_threads" not in st.session_state:
    all_threads = retrieve_all_threads()
    st.session_state["chat_threads"] = [
        t for t in all_threads
        if str(t).startswith(google_id)
    ]

if "ingested_docs" not in st.session_state:
    st.session_state["ingested_docs"] = {}

add_thread(st.session_state["thread_id"])

thread_key = str(st.session_state["thread_id"])
thread_docs = st.session_state["ingested_docs"].setdefault(thread_key, {})
threads = st.session_state["chat_threads"][::-1]
selected_thread = None

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&display=swap');
            
[data-testid="stSidebar"] {
    background: #e8e0f5;
}
            
/* ── Sidebar title ── */
[data-testid="stSidebar"] h1 {
    font-family: 'Playfair Display', serif !important;
    color: #4a3070 !important;
    font-size: 2rem !important;
}

/* ── Sidebar caption ── */
[data-testid="stSidebar"] small {
    font-size: 1.3rem !important;   
    color: #4a3070 !important;
    font-family: 'Playfair Display', serif !important;
}

/* ── Sidebar info box ── */
[data-testid="stSidebar"] [data-testid="stNotification"] p,
[data-testid="stSidebar"] .stAlert p {
    font-size: 0.95rem !important;
    font-family: 'Playfair Display', serif !important;
    color: #4a3070 !important;
}
                     
/* ── Sidebar subheader ── */
[data-testid="stSidebar"] h3 {
    font-family: 'Playfair Display', serif !important;
    color: #4a3070 !important;
    font-size: 1.5rem !important;
}    
              
[data-testid="stSidebar"] button p {
    font-family: 'Playfair Display', serif !important;
    color: #4a3070 !important;
    font-size: 1.1rem !important;        
}           
[data-testid="stChatMessage"] td {
    font-size: 1.3rem !important;     
    line-height: 1.75 !important;
}
                       
/* ── Chat input box font size ── */
[data-testid="stChatInput"] textarea {
    font-size: 1.3rem !important;
}
            
/* ── User & AI message text ── */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] span {
    font-size: 1.2rem !important;
    line-height: 1.8 !important;
}
</style>
""", unsafe_allow_html=True)



# ============================ Sidebar ============================

st.sidebar.title("Multi Tool Agent")

st.sidebar.caption(f"👤 {current_user['name']}  ·  {current_user['email']}")
if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    delete_session(session_token)
    for key in ["session_token", "user", "message_history",
                "thread_id", "chat_threads", "thread_names", "ingested_docs"]:
        st.session_state.pop(key, None)
    st.rerun()
st.sidebar.divider()

if st.sidebar.button("New Chat", use_container_width=True):
    reset_chat()
    st.rerun()

if thread_docs:
    st.sidebar.success(f"📁 {len(thread_docs)} file(s) indexed")
    for doc_name in thread_docs:
        st.sidebar.caption(f"• {doc_name}")
else:
    st.sidebar.info("No PDF indexed yet.")

uploaded_files = st.sidebar.file_uploader(
    "Upload files for this chat",
    type=["pdf", "txt", "doc", "docx"],
    accept_multiple_files=True
)
if uploaded_files:
    for uploaded_file in uploaded_files:
        if uploaded_file.name in thread_docs:
            st.sidebar.info(f"`{uploaded_file.name}` already processed.")
        else:
            with st.sidebar.status(f"Indexing `{uploaded_file.name}`…", expanded=True) as status_box:
                summary = ingest_file(
                    uploaded_file.getvalue(),
                    thread_id=thread_key,
                    filename=uploaded_file.name,
                )
                thread_docs[uploaded_file.name] = summary
                status_box.update(label=f"✅ `{uploaded_file.name}` indexed", state="complete", expanded=False)

st.sidebar.subheader("History")
if not threads:
    st.sidebar.write("No past conversations yet.")
else:
    for thread_id in threads:
        thread_id_str = str(thread_id)
        is_active = thread_id_str == thread_key
        thread_name = st.session_state["thread_names"].get(thread_id_str, thread_id_str[:16] + "...")
        label = ("⚡   " if is_active else "") + thread_name

        col1, col2 = st.sidebar.columns([5, 1])
        with col1:
            if st.button(label, key=f"side-thread-{thread_id}", use_container_width=True):
                selected_thread = thread_id
        with col2:
            if st.button("🗑", key=f"delete-thread-{thread_id}", use_container_width=True):
                delete_thread(thread_id)
                if is_active:
                    # Switch to the most recent remaining thread instead of creating new
                    remaining = [t for t in st.session_state["chat_threads"]]
                    if remaining:
                        st.session_state["thread_id"] = remaining[-1]
                        messages = load_conversation(remaining[-1])
                        temp_messages = []
                        for msg in messages:
                            role = "user" if isinstance(msg, HumanMessage) else "assistant"
                            temp_messages.append({"role": role, "content": msg.content})
                        st.session_state["message_history"] = temp_messages
                    else:
                        # No threads left at all — only then create a new one
                        reset_chat()
                st.rerun()

# ============================ Main Layout ========================
#st.title("🍵 Tea and Tool Time")

# Empty state — show when no messages yet
if not st.session_state["message_history"]:
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&display=swap');
    </style>
                
    <div style="
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 3rem 1rem 2rem;
        text-align: center;
    ">
        <div style="font-size:3.5rem; margin-bottom:1rem; 
                    filter: drop-shadow(0 6px 12px rgba(160,80,20,0.2));">🍵</div>
        <div style="font-size:2rem; font-weight:700; color: #4a3070; 
                    margin-bottom:0.5rem; letter-spacing:-0.3px;
                    font-family:'Playfair Display', serif;">
            Good to see you, {current_user['name'].split()[0]}!
        </div>
        <div style="font-size:1.2rem; color: #4a3070;; 
                    margin-bottom:2rem; line-height:1.7; max-width:36ch;
                    font-family:'Playfair Display', serif;">
            Your workspace is ready. Ask anything or pick a suggestion below.
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.65rem; 
                    max-width:480px; width:100%;">
            <div style="background:#e8e0f5; border:0;
                        border-radius:14px; padding:1rem; cursor:pointer;
                        box-shadow:0 2px 8px rgba(140,80,20,0.07);">
                <div style="font-size:1.4rem; margin-bottom:0.4rem;">📄</div>
                <div style="font-size:1rem; font-weight:600; color: #4a3070;;font-family:'Playfair Display', serif;">
                    Upload a PDF and ask questions</div>
            </div>
            <div style="background:#e8e0f5; border:0;
                        border-radius:14px; padding:1rem; cursor:pointer;
                        box-shadow:0 2px 8px rgba(140,80,20,0.07);">
                <div style="font-size:1.4rem; margin-bottom:0.4rem;">📈</div>
                <div style="font-size:1rem; font-weight:600; color: #4a3070;;font-family:'Playfair Display', serif;"">
                    What's Tesla's stock price?</div>
            </div>
            <div style="background:#e8e0f5; border:0;
                        border-radius:14px; padding:1rem; cursor:pointer;
                        box-shadow:0 2px 8px rgba(140,80,20,0.07);">
                <div style="font-size:1.4rem; margin-bottom:0.4rem;">🌤️</div>
                <div style="font-size:1rem; font-weight:600; color: #4a3070;;font-family:'Playfair Display', serif;"">
                    Weather in Hyderabad today?</div>
            </div>
            <div style="background:#e8e0f5; border:0;
                        border-radius:14px; padding:1rem; cursor:pointer;
                        box-shadow:0 2px 8px rgba(140,80,20,0.07);">
                <div style="font-size:1.4rem; margin-bottom:0.4rem;">📖</div>
                <div style="font-size:1rem; font-weight:600; color: #4a3070;;font-family:'Playfair Display', serif;"">
                    Wikipedia search</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Chat area
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("timestamp"):
            st.caption(message["timestamp"])
        if message.get("tools_used"):
            tool_icons = {
                "rag_tool": "📄",
                "calculator": "🧮",
                "get_stock_price": "📈",
                "currency_converter": "💱",
                "weather_lookup": "🌤️",
                "wikipedia_search": "📖",
                "tavily_search": "🔍",
            }
            badges = " · ".join(
                f"{tool_icons.get(t, '🔧')} `{t}`"
                for t in message["tools_used"]
            )
            st.caption(f"Tools used: {badges}")

user_input = st.chat_input("Ask about your document or use tools")

if user_input:
    allowed, used, remaining = check_rate_limit(google_id)
    if not allowed:
        st.warning("⚠️ Rate limit hit — wait a moment.")
        st.stop()
    st.session_state["message_history"].append(
        {"role": "user", "content": user_input, "timestamp": get_timestamp()})
    
    if len(st.session_state["message_history"]) == 1:
        thread_name = generate_thread_name(user_input)
        st.session_state["thread_names"][thread_key] = thread_name
        save_thread_name(thread_key, thread_name)

    with st.chat_message("user"):
        st.markdown(user_input)
        st.caption(get_timestamp())

    CONFIG = {
        "configurable": {"thread_id": thread_key},
        "metadata": {"thread_id": thread_key},
        "run_name": "chat_turn",
    }

    with st.chat_message("assistant"):
        status_holder = {"box": None, "tools_used": []}

        def ai_only_stream():
            for message_chunk, _ in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")
                    if tool_name not in status_holder["tools_used"]:
                        status_holder["tools_used"].append(tool_name)
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            f"🔧 Using `{tool_name}` …", expanded=True
                        )
                    else:
                        status_holder["box"].update(
                            label=f"🔧 Using `{tool_name}` …",
                            state="running",
                            expanded=True,
                        )

                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())

        if status_holder["box"] is not None:
            status_holder["box"].update(
                label="✅ Tool finished", state="complete", expanded=False
            )

        st.caption(get_timestamp())
        if status_holder["tools_used"]:
            tool_icons = {
                "rag_tool": "📄",
                "calculator": "🧮",
                "get_stock_price": "📈",
                "currency_converter": "💱",
                "weather_lookup": "🌤️",
                "wikipedia_search": "📖",
                "tavily_search": "🔍",
            }
            badges = " · ".join(
                f"{tool_icons.get(t, '🔧')} `{t}`"
                for t in status_holder["tools_used"]
            )
            st.caption(f"Tools used: {badges}")
        

    st.session_state["message_history"].append(
        {"role": "assistant", "content": ai_message, "timestamp": get_timestamp(), "tools_used": status_holder["tools_used"]}
    )

st.divider()

if selected_thread:
    st.session_state["thread_id"] = selected_thread
    messages = load_conversation(selected_thread)

    temp_messages = []
    for msg in messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        temp_messages.append({"role": role, "content": msg.content, "timestamp": None})
    st.session_state["message_history"] = temp_messages
    st.session_state["ingested_docs"].setdefault(str(selected_thread), {})
    st.rerun()
