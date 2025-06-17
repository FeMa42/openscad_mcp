#!/usr/bin/env python3
"""
Minimal OpenSCAD Chat using LangGraph + MCP with Persistent Session
Shows proper session management to avoid server restarts with improved conversation history management
"""

import gradio as gr
import asyncio
from typing import List, Dict, Any
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import BaseTool
import base64
from PIL import Image
from io import BytesIO
from pathlib import Path
import json
import re

class PersistentMCPOpenSCADChat:
    """OpenSCAD chat assistant with persistent MCP session management and proper conversation history"""
    
    def __init__(self, model="gpt-4o"):
        self.model = model
        self.agent = None
        self.current_image = None
        self.current_code = None
        self.conversation_history = []
        self.system_prompt = None  # Store system prompt separately
        self.client = None
        self.session_context = None
        self.session = None
        
    async def initialize(self):
        """Initialize with persistent MCP session and proper system prompt setup"""
        # Load MCP server configuration
        with open('config.json') as f:
            config = json.load(f)
        print("📋 Configuration loaded:", config)
        
        # Extract servers config
        mcp_config = config.get("mcpServers", config)
        
        # Create MCP client
        self.client = MultiServerMCPClient(mcp_config)
        
        # Create and maintain persistent session
        print("🔌 Creating persistent MCP session...")
        self.session_context = self.client.session("openscad")
        self.session = await self.session_context.__aenter__()
        
        # Load tools from persistent session
        tools = await load_mcp_tools(self.session)
        print(f"🔧 Loaded {len(tools)} tools with persistent session: {[tool.name for tool in tools]}")
        
        # Load instructions and store as system prompt
        try:
            self.system_prompt = Path("instructions.txt").read_text()
        except FileNotFoundError:
            self.system_prompt = "You are a helpful OpenSCAD design assistant. Help users create 3D objects using OpenSCAD code."
        
        # Create LLM
        llm = ChatOpenAI(model=self.model, temperature=0.7)
        
        # Create agent with system prompt - use prompt parameter with function
        def _add_system_prompt(state):
            """Add system prompt to the conversation"""
            messages = state.get("messages", [])
            # If no system message exists as first message, add it
            if not messages or not isinstance(messages[0], SystemMessage):
                return [SystemMessage(content=self.system_prompt)] + messages
            return messages
        
        self.agent = create_react_agent(
            llm, 
            tools, 
            prompt=_add_system_prompt  # This properly handles system prompt in conversation
        )

        # Initialize conversation history with system message
        self._initialize_conversation_history()

        return "✅ Ready with persistent MCP session and proper conversation history! Server will not restart on tool calls."
    
    def _initialize_conversation_history(self):
        """Initialize conversation history with system message"""
        self.conversation_history = [
            SystemMessage(content=self.system_prompt)
        ]
    
    async def cleanup(self):
        """Properly clean up the persistent session"""
        if self.session_context:
            try:
                await self.session_context.__aexit__(None, None, None)
                print("🧹 MCP session cleaned up properly")
            except Exception as e:
                print(f"❌ Error cleaning up session: {e}")
    
    def reset_conversation(self):
        """Reset the conversation history but keep system prompt"""
        self._initialize_conversation_history()
        self.current_image = None
        self.current_code = None
    
    def _clear_current_image(self):
        """Clear the current image to ensure fresh updates"""
        if self.current_image:
            try:
                self.current_image.close()  # Properly close PIL image
            except:
                pass
        self.current_image = None
    
    def _create_fresh_image_copy(self, img_data_bytes):
        """Create a fresh PIL Image copy to avoid Gradio caching issues"""
        try:
            # Create image from bytes
            img = Image.open(BytesIO(img_data_bytes))
            
            # Force load the image data
            img.load()
            
            # Create a completely new image copy to avoid reference issues
            if img.mode in ('RGBA', 'LA'):
                # Convert RGBA to RGB with white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Create a fresh copy by saving to bytes and reloading
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            # Return a completely fresh image object
            fresh_img = Image.open(buffer)
            fresh_img.load()  # Force load to ensure it's in memory
            
            return fresh_img
            
        except Exception as e:
            print(f"Error creating fresh image copy: {e}")
            return None
    
    def _get_conversation_messages(self):
        """Get properly formatted conversation messages for the agent"""
        # Always ensure system message is first
        if not self.conversation_history or not isinstance(self.conversation_history[0], SystemMessage):
            self._initialize_conversation_history()
            
        return self.conversation_history.copy()
    
    async def chat(self, message: str, history: List):
        """Process chat message with persistent session and proper history management"""
        if not self.agent:
            # If already in history, just update the response
            if history and history[-1][0] == message and history[-1][1] is None:
                history[-1][1] = "❌ Not initialized!"
                return history
            return history + [[message, "❌ Not initialized!"]]
            
        # Clear previous image to ensure fresh updates
        self._clear_current_image()
        
        # Check if user message is already in history (from immediate display)
        if history and history[-1][0] == message and "🤔 Thinking..." in str(history[-1][1]):
            # Message already added by handle_message, just continue processing
            pass
        else:
            # Add user message if not already there
            history = history + [[message, "🤔 Thinking... (using persistent session)"]]
        
        try:
            # Add user message to conversation history
            self.conversation_history.append(HumanMessage(content=message))
            
            # Get properly formatted messages for the agent
            agent_messages = self._get_conversation_messages()
            
            # Invoke agent with proper message history
            response = await self.agent.ainvoke({
                "messages": agent_messages
            })
            
            # Extract AI response from the response messages
            latest_ai_message = None
            for msg in reversed(response["messages"]):
                if isinstance(msg, AIMessage):
                    latest_ai_message = msg
                    break
            
            if latest_ai_message:
                ai_content = latest_ai_message.content
                # Add AI response to conversation history
                self.conversation_history.append(AIMessage(content=ai_content))
                history[-1][1] = ai_content
            else:
                history[-1][1] = "❌ No response generated"
            
            # Extract images and code from tool responses
            self._extract_outputs(response["messages"])
                                
        except Exception as e:
            history[-1][1] = f"❌ Error: {str(e)}"
            
        return history
    
    def _process_image_content(self, content) -> bool:
        """
        Process various image content formats and set self.current_image.
        
        Args:
            content: The content from MCP tool response
            
        Returns:
            bool: True if image was successfully processed, False otherwise
        """
        # Early exit for obviously non-image content
        if not content:
            return False
            
        # Skip error messages and other non-image strings
        if isinstance(content, str):
            if (content.startswith("Error:") or 
                content.startswith("ToolException") or 
                len(content) < 50):  # Too short to be base64 image
                return False
        
        print(f"🔍 Processing potential image content: {type(content)}")
        
        # 1. Handle MCP Image objects directly (most common success case)
        if hasattr(content, 'data') and hasattr(content, 'format'):
            try:
                if isinstance(content.data, bytes):
                    self.current_image = self._create_fresh_image_copy(content.data)
                    if self.current_image:
                        print("✅ Loaded image from MCP Image object")
                        return True
            except Exception as e:
                print(f"Failed to load MCP Image object: {e}")
        
        # 2. Handle fastmcp Image objects specifically (if available)
        try:
            from fastmcp import Image as MCPImage
            if isinstance(content, MCPImage):
                self.current_image = self._create_fresh_image_copy(content.data)
                if self.current_image:
                    print("✅ Loaded fastmcp Image object")
                    return True
        except (ImportError, Exception) as e:
            if not isinstance(e, ImportError):
                print(f"Failed to load fastmcp Image object: {e}")
        
        # 3. Handle string content (base64 formats)
        if isinstance(content, str):
            # Data URL format
            if content.startswith("data:image"):
                try:
                    header, data = content.split(",", 1)
                    img_data = base64.b64decode(data)
                    self.current_image = self._create_fresh_image_copy(img_data)
                    if self.current_image:
                        print("✅ Loaded image from data URL")
                        return True
                except Exception as e:
                    print(f"Failed to decode data URL: {e}")
            
            # Raw base64 (check for image signatures)
            elif content.startswith(("iVBOR", "/9j/", "R0lGOD")):
                try:
                    img_data = base64.b64decode(content)
                    self.current_image = self._create_fresh_image_copy(img_data)
                    if self.current_image:
                        print("✅ Loaded image from raw base64")
                        return True
                except Exception as e:
                    print(f"Failed to decode raw base64: {e}")
        
        # 4. Handle dict content (serialized MCP Image)
        elif isinstance(content, dict):
            for key in ['data', 'image_data', 'content']:
                if key in content:
                    data = content[key]
                    try:
                        if isinstance(data, bytes):
                            self.current_image = self._create_fresh_image_copy(data)
                            if self.current_image:
                                print(f"✅ Loaded image from dict bytes field: {key}")
                                return True
                        elif isinstance(data, str) and len(data) > 100:
                            img_data = base64.b64decode(data)
                            self.current_image = self._create_fresh_image_copy(img_data)
                            if self.current_image:
                                print(f"✅ Loaded image from dict base64 field: {key}")
                                return True
                    except Exception:
                        continue
        
        return False

    def _extract_outputs(self, messages):
        """Extract images and code from tool responses"""
        for msg in messages:
            # Check for tool calls (to get code)
            if hasattr(msg, "tool_calls"):
                for tool_call in msg.tool_calls:
                    if tool_call["name"] == "render_scad":
                        self.current_code = tool_call["args"].get("code", "")
                        
            # Check tool responses for images
            if hasattr(msg, "name") and msg.name == "render_scad":
                content = msg.content
                
                # Try to process image content, fallback if no image found
                if not self._process_image_content(content) and self.current_image is None:
                    self._load_fallback_image()
    
    def _load_fallback_image(self):
        """Load most recent image file as fallback"""
        try:
            output_dir = Path("../output")
            if output_dir.exists():
                png_files = list(output_dir.rglob("*.png"))
                if png_files:
                    latest_png = max(png_files, key=lambda p: p.stat().st_mtime)
                    # Read the file as bytes and create fresh copy
                    with open(latest_png, 'rb') as f:
                        img_bytes = f.read()
                    self.current_image = self._create_fresh_image_copy(img_bytes)
                    if self.current_image:
                        print(f"✅ Loaded fallback image: {latest_png}")
        except Exception as e:
            print(f"Failed to load fallback image: {e}")


def create_app():
    """Create Gradio app with persistent MCP session"""
    chat_assistant = PersistentMCPOpenSCADChat()
    
    with gr.Blocks(title="OpenSCAD Assistant", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🎨 OpenSCAD Design Assistant")
        gr.Markdown("Chat naturally about 3D design - powered by OpenSCAD + LangGraph + MCP")
        
        # Status indicator
        status = gr.Markdown("⏳ Initializing MCP server...")
        
        with gr.Row():
            # Chat interface
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(height=600, show_label=False)
                msg = gr.Textbox(
                    placeholder="Try: 'Help me Create a phone stand'",
                    show_label=False
                )
                with gr.Row():
                    send_btn = gr.Button("Send", variant="primary")
                    clear_btn = gr.Button("Clear Chat", variant="secondary")
                
            # Preview panel
            with gr.Column(scale=1):
                preview = gr.Image(label="3D Preview", height=300)
                
                with gr.Accordion("Generated Code", open=True):
                    code_view = gr.Code(language="c", show_label=False)
        
        # Event handlers
        async def startup():
            """Initialize the assistant"""
            return await chat_assistant.initialize()
        
        async def handle_message(message, history):
            """Handle user messages with immediate display and processing"""
            if not message:
                return "", history, None, None
            
            # Step 1: Immediately show user message with thinking indicator
            updated_history = history + [[message, "🤔 Thinking... (using persistent session)"]]
            
            try:
                # Step 2: Process with agent directly
                # Clear previous image to ensure fresh updates
                chat_assistant._clear_current_image()
                
                # Add user message to conversation history
                chat_assistant.conversation_history.append(HumanMessage(content=message))
                
                # Get properly formatted messages for the agent
                agent_messages = chat_assistant._get_conversation_messages()
                
                # Invoke agent with proper message history
                response = await chat_assistant.agent.ainvoke({
                    "messages": agent_messages
                })
                
                # Extract AI response from the response messages
                latest_ai_message = None
                for msg in reversed(response["messages"]):
                    if isinstance(msg, AIMessage):
                        latest_ai_message = msg
                        break
                
                if latest_ai_message:
                    ai_content = latest_ai_message.content
                    # Add AI response to conversation history
                    chat_assistant.conversation_history.append(AIMessage(content=ai_content))
                    updated_history[-1][1] = ai_content
                else:
                    updated_history[-1][1] = "❌ No response generated"
                
                # Extract images and code from tool responses
                chat_assistant._extract_outputs(response["messages"])
                
                return "", updated_history, chat_assistant.current_image, chat_assistant.current_code
                
            except Exception as e:
                # Update the last message with error
                updated_history[-1][1] = f"❌ Error: {str(e)}"
                return "", updated_history, chat_assistant.current_image, chat_assistant.current_code
        
        def clear_chat():
            """Clear conversation"""
            chat_assistant.reset_conversation()
            chat_assistant._clear_current_image()
            return [], None, None
        
        async def cleanup():
            """Clean up resources"""
            await chat_assistant.cleanup()
        
        # Wire up events
        app.load(startup, outputs=status)
        
        # Single async message handling
        msg.submit(handle_message, [msg, chatbot], [msg, chatbot, preview, code_view])
        send_btn.click(handle_message, [msg, chatbot], [msg, chatbot, preview, code_view])
        
        clear_btn.click(clear_chat, outputs=[chatbot, preview, code_view])
        
        # Try to clean up on app close (may not work in all environments)
        app.unload(cleanup)
        
        # Example prompts
        gr.Examples(
            examples=[
                "Help me Create a phone stand",
                "Make a gear with 20 teeth", 
                "Create a parametric box with a separate lid",
                "Build a box with hinged lid",
                "Create a spiral vase"
            ],
            inputs=msg
        )
    
    return app


# Main execution
if __name__ == "__main__":
    import os
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY environment variable")
        exit(1)
    
    print("🚀 Starting OpenSCAD Chat with Persistent MCP Session...")
    app = create_app()
    app.launch(server_port=7861)  # Different port to avoid conflicts 