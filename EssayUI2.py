import streamlit as st
import uuid
from langchain_core.messages import HumanMessage, AIMessage
from EssayOwnCode2 import graph 


def generate_thread_id():
    """Generates a unique ID for each new evaluation session."""
    return str(uuid.uuid4())

def reset_chat():
    """Resets the chat state for a new evaluation."""
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(thread_id)
    st.session_state['essay_history'] = []

def add_thread(thread_id):
    """Adds a new thread ID to the session state if it doesn't exist."""
    if thread_id not in st.session_state['essay_threads']:
        st.session_state['essay_threads'].append(thread_id)

def load_conversation(thread_id):
    """Loads a conversation from a specific thread ID."""
    state = graph.get_state(config={"configurable": {"thread_id": thread_id}})
    return state.values.get("messages", [])


# Initialize session state variables if they don't exist
if 'essay_history' not in st.session_state:
    st.session_state['essay_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'essay_threads' not in st.session_state:
    st.session_state['essay_threads'] = []

add_thread(st.session_state['thread_id'])


# Sidebar UI
st.sidebar.title("Essay Evaluator")

if st.sidebar.button("New Evaluation"):
    reset_chat()

st.sidebar.header("My Evaluations")

for thread_id in st.session_state['essay_threads'][::-1]:
    if st.sidebar.button(str(thread_id)):
        st.session_state['thread_id'] = thread_id
        messages = load_conversation(thread_id)
        
        temp_history = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, AIMessage):
                role = "assistant"
            else:
                continue
            temp_history.append({"role": role, "content": msg.content})
        st.session_state['essay_history'] = temp_history


# Main UI
st.title("Essay Evaluation Assistant")

# Display the conversation history first.
for message in st.session_state['essay_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

# Add an expandable text area and a submit button
with st.form(key='essay_form'):
    essay_input = st.text_area("Paste your UPSC essay here...", height=200)
    submit_button = st.form_submit_button(label='Get Evaluation')

    if submit_button and essay_input:
        # Append the user's essay to the chat history
        st.session_state['essay_history'].append({"role": "user", "content": essay_input})
        with st.chat_message("user"):
            st.markdown(essay_input)

        CONFIG = {"configurable": {"thread_id": st.session_state['thread_id']}}

        with st.spinner("Evaluating your essay..."):
            try:
                # Run the entire LangGraph to get the final state.
                final_state = graph.invoke(
                    {"essay": essay_input, "messages": [HumanMessage(content=essay_input)]},
                    config=CONFIG
                )

                # Construct the final, formatted output string using Markdown
                ai_output = f"""
**1. Language Evaluation**
> {final_state.get('language_feedback', 'N/A')}
**Score:** {final_state['individual_scores'][0] if final_state.get('individual_scores') and len(final_state['individual_scores']) > 0 else 'N/A'}/10

**2. Depth of Analysis Evaluation**
> {final_state.get('analysis_feedback', 'N/A')}
**Score:** {final_state['individual_scores'][1] if final_state.get('individual_scores') and len(final_state['individual_scores']) > 1 else 'N/A'}/10

**3. Clarity of Thought Evaluation**
> {final_state.get('clarity_feedback', 'N/A')}
**Score:** {final_state['individual_scores'][2] if final_state.get('individual_scores') and len(final_state['individual_scores']) > 2 else 'N/A'}/10

---

**Overall Evaluation & Final Score**
{final_state.get('overall_feedback', 'N/A')}
**Average Score:** {final_state.get('avg_score', 'N/A'):.2f}/10
"""
                
                # Display the formatted output to the user
                with st.chat_message("assistant"):
                    st.markdown(ai_output)

                # Store the assistant's response in the chat history
                st.session_state['essay_history'].append({"role": "assistant", "content": ai_output})

            except Exception as e:
                st.error(f"An error occurred: {e}")