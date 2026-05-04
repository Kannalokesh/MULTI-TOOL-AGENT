import os
import uuid
import shutil
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from datetime import datetime


from langraph_backend import (
    chatbot,
    conn,
    ingest_file,
    FAISS_STORE_DIR,
    retrieve_all_threads,
    save_thread_name,
    load_thread_names,
)


# =========================== Utilities ===========================
def get_timestamp():
    return datetime.now().strftime("%I:%M %p · %b %d")  # e.g. "10:35 AM · May 04"

def generate_thread_id():
    return uuid.uuid4()

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


# ======================= Session Initialization ===================
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_names" not in st.session_state:
    st.session_state["thread_names"] = load_thread_names()

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = retrieve_all_threads()

if "ingested_docs" not in st.session_state:
    st.session_state["ingested_docs"] = {}

add_thread(st.session_state["thread_id"])

thread_key = str(st.session_state["thread_id"])
thread_docs = st.session_state["ingested_docs"].setdefault(thread_key, {})
threads = st.session_state["chat_threads"][::-1]
selected_thread = None

# ============================ Sidebar ============================
st.sidebar.title("Multi Tool Agent")
st.sidebar.markdown(f"**Thread ID:** `{thread_key}`")

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
        label = ("🟢 " if is_active else "") + thread_name

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
st.title("🍵 Tea and Tool Time")

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
