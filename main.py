# develop by Gary Wee
# 2025-04-18 10:43:00

import os
import json
import re
import datetime
import streamlit as st
import requests
from pathlib import Path
import socket
import uuid

# App title and configuration
st.set_page_config(page_title="GPT Chat with Obsidian Integration", layout="wide")

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "api_key_valid" not in st.session_state:
    st.session_state.api_key_valid = False
if "current_file" not in st.session_state:
    st.session_state.current_file = None

# Function to get existing chat files
def get_chat_files(directory):
    if not os.path.exists(directory):
        return []
    
    files = []
    for file in os.listdir(directory):
        if file.endswith('.md') and re.match(r'^\d{8}-\d{2}\.md$', file):
            files.append(file)
    
    # Sort files by name (which effectively sorts by date and sequence)
    files.sort(reverse=True)
    return files

# Function to generate next file name in sequence
def generate_next_filename(directory):
    today = datetime.datetime.now().strftime("%Y%m%d")
    
    # Find the highest sequence number for today
    highest_seq = 0
    pattern = re.compile(f"^{today}-(\\d{{2}})\\.md$")
    
    if os.path.exists(directory):
        for file in os.listdir(directory):
            match = pattern.match(file)
            if match:
                seq = int(match.group(1))
                highest_seq = max(highest_seq, seq)
    
    # Create the next filename in sequence
    next_seq = highest_seq + 1
    return f"{today}-{next_seq:02d}.md"

# Function to parse markdown file and extract messages
def extract_messages_from_md(filepath):
    messages = []
    current_role = None
    current_content = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            
            for line in lines:
                if line.startswith('### User'):
                    if current_role and current_content:
                        messages.append({"role": current_role, "content": "".join(current_content).strip()})
                    current_role = "user"
                    current_content = []
                elif line.startswith('### Assistant'):
                    if current_role and current_content:
                        messages.append({"role": current_role, "content": "".join(current_content).strip()})
                    current_role = "assistant"
                    current_content = []
                elif current_role:
                    current_content.append(line)
        
        # Add the last message
        if current_role and current_content:
            messages.append({"role": current_role, "content": "".join(current_content).strip()})
            
        return messages
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return []

# Sidebar for configuration
with st.sidebar:
    st.title("Configuration")
    
    # OpenAI API key input
    api_key = st.text_input("OpenAI API Key", type="password", value=api_key)
    
    # Test API key functionality
    if st.button("Test API Key"):
        if not api_key:
            st.error("Please enter an API key")
        else:
            with st.spinner("Testing API key..."):
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": "gpt-4.1-mini",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 5
                }
                try:
                    response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=data
                    )
                    response.raise_for_status()
                    st.success("API key is valid!")
                    st.session_state.api_key_valid = True
                except requests.exceptions.RequestException as e:
                    error_msg = str(e)
                    if "401" in error_msg:
                        st.error("Invalid API key or unauthorized access.")
                    elif "429" in error_msg:
                        st.error("Rate limit exceeded or quota issues.")
                    else:
                        st.error(f"API Error: {error_msg}")
                    st.session_state.api_key_valid = False
    
    # Model selection
    model = st.selectbox(
        "Select GPT Model",
        ["gpt-4.1-mini", "gpt-4", "gpt-3.5-turbo"],
        index=0
    )
    
    # Obsidian vault path
    obsidian_path = st.text_input(
        "Obsidian Vault Path",
        value=os.path.expanduser("/Users/user/Documents/ChatGPT")
    )
    
    # Test Obsidian path
    if st.button("Test Obsidian Path"):
        try:
            os.makedirs(obsidian_path, exist_ok=True)
            test_file = os.path.join(obsidian_path, ".test_file.md")
            with open(test_file, "w") as f:
                f.write("# Test\n\nThis is a test file.")
            st.success(f"Successfully created test file at {test_file}")
            os.remove(test_file)
        except Exception as e:
            st.error(f"Error accessing path: {str(e)}")
    
    # Load existing chat files
    chat_files = get_chat_files(obsidian_path)
    
    # Chat history selection
    st.subheader("Chat History")
    
    if chat_files:
        selected_file = st.selectbox(
            "Select a previous chat",
            ["New Chat"] + chat_files,
            index=0
        )
        
        if selected_file != "New Chat" and selected_file != st.session_state.current_file:
            # Load the selected chat file
            if st.button("Load Selected Chat"):
                filepath = os.path.join(obsidian_path, selected_file)
                loaded_messages = extract_messages_from_md(filepath)
                if loaded_messages:
                    st.session_state.messages = loaded_messages
                    st.session_state.current_file = selected_file
                    st.session_state.conversation_id = selected_file[:-3]  # Remove .md extension
                    st.rerun()
    else:
        st.info("No previous chats found")
    
    # Reset conversation button
    if st.button("New Conversation"):
        st.session_state.messages = []
        st.session_state.conversation_id = str(uuid.uuid4())
        st.session_state.current_file = None
        st.rerun()
    
    # Temperature setting
    temperature = st.slider("Temperature", min_value=0.0, max_value=2.0, value=0.7, step=0.1)
    
    # System prompt
    system_prompt = st.text_area(
        "System Prompt",
        value="You are a helpful assistant.",
        height=100
    )
    
    # Display local network access info
    st.subheader("Network Access")
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        st.info(f"Access this app at: http://{local_ip}:8501")
    except:
        st.warning("Could not determine local IP address.")

# Main app interface
st.title("GPT Chat with Obsidian Integration")

# Show current chat file if any
if st.session_state.current_file:
    st.caption(f"Current chat: {st.session_state.current_file}")

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Function to save chat to Obsidian
def save_to_obsidian(messages):
    try:
        # Create the directory if it doesn't exist
        os.makedirs(obsidian_path, exist_ok=True)
        
        # Use the current file if it exists, otherwise generate a new filename
        if st.session_state.current_file:
            filename = st.session_state.current_file
        else:
            filename = generate_next_filename(obsidian_path)
            st.session_state.current_file = filename
            st.session_state.conversation_id = filename[:-3]  # Remove .md extension
        
        filepath = os.path.join(obsidian_path, filename)
        
        # Format the markdown content
        md_content = f"# Chat with GPT - {filename[:-3]}\n\n"
        md_content += f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        md_content += f"Model: {model}\n\n"
        md_content += "## Conversation\n\n"
        
        for msg in messages:
            role = msg["role"].capitalize()
            content = msg["content"]
            md_content += f"### {role}\n\n{content}\n\n"
        
        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        return filepath, None
    except Exception as e:
        return None, str(e)

# Function to call OpenAI API
def get_gpt_response(messages, api_key, model, temperature=0.7):
    if not api_key:
        return "Please provide an OpenAI API key in the sidebar.", True
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Format messages for API
    formatted_messages = []
    
    # Add system message
    formatted_messages.append({"role": "system", "content": system_prompt})
    
    # Add conversation history
    for msg in messages:
        formatted_messages.append({"role": msg["role"], "content": msg["content"]})
    
    data = {
        "model": model,
        "messages": formatted_messages,
        "temperature": temperature
    }
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"], False
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if "401" in error_msg:
            return "Error: Unauthorized. Your API key appears to be invalid or expired. Please check your API key in the sidebar.", True
        elif "429" in error_msg:
            return "Error: Rate limit exceeded or quota issues with your OpenAI account.", True
        elif "404" in error_msg:
            return f"Error: Model '{model}' not found. Please select a different model.", True
        elif "timeout" in error_msg.lower():
            return "Error: Request timed out. Please try again.", True
        else:
            return f"Error connecting to OpenAI API: {error_msg}", True

# User input and GPT response
user_input = st.chat_input("Type your message here...")

if user_input:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Get GPT response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response, is_error = get_gpt_response(
                st.session_state.messages,
                api_key,
                model,
                temperature
            )
            st.markdown(response)
            if is_error:
                st.error("Failed to get response from OpenAI API. See message above.")
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Only save to Obsidian if we got a valid response
    if not is_error:
        filepath, save_error = save_to_obsidian(st.session_state.messages)
        if save_error:
            st.error(f"Failed to save to Obsidian: {save_error}")
        else:
            # Display subtle success message
            st.caption(f"Saved to: {os.path.basename(filepath)}")

# Display instructions or API key warning
if not st.session_state.messages:
    st.info("👋 Enter your message above to start chatting with GPT. Your conversation will be automatically saved to your Obsidian vault.")
    
    if not api_key:
        st.warning("⚠️ Please enter your OpenAI API key in the sidebar to use this app.")
