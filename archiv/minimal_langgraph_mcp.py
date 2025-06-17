#!/usr/bin/env python3
"""
Minimal OpenSCAD Chat using LangGraph + MCP
Focus on simplicity and readability
"""

import gradio as gr
import asyncio
from typing import List, Dict, Any
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import base64
from PIL import Image
from io import BytesIO
from pathlib import Path
import json
import re

# Try to import MCP Image for proper handling
try:
    from fastmcp import Image as MCPImage
    MCP_IMAGE_AVAILABLE = True
except ImportError:
    MCPImage = None
    MCP_IMAGE_AVAILABLE = False

class SimpleOpenSCADChat:
    """Minimal OpenSCAD chat assistant with persistent MCP session"""
    
    def __init__(self, model="gpt-4o"):
        self.model = model
        self.agent = None
        self.current_image = None
        self.current_code = None
        self.conversation_history = []
        self.client = None
        self.session_context = None  # Store the context manager for proper cleanup
        
    async def initialize(self):
        """One-time setup of MCP connection and agent"""
        # MCP server configuration
        with open('config.json') as f:
            config = json.load(f)
        print(config)
        
        # Extract servers from mcpServers section (Claude Desktop format)
        mcp_config = config.get("mcpServers", config)
        
        # Create MCP client
        self.client = MultiServerMCPClient(mcp_config)
        
        # Create a persistent session instead of using get_tools()
        # Store the context manager itself for proper cleanup
        self.session_context = self.client.session("openscad")
        session = await self.session_context.__aenter__()
        
        # Load tools from the persistent session
        tools = await load_mcp_tools(session)
        print(f"Loaded {len(tools)} tools with persistent session: {[tool.name for tool in tools]}")
        
        # Read instructions
        try:
            instructions = Path("instructions.txt").read_text()
            print(instructions)
        except FileNotFoundError:
            instructions = "You are a helpful OpenSCAD design assistant. Help users create 3D objects using OpenSCAD code."
        
        # Create LLM with system message
        llm = ChatOpenAI(model=self.model, temperature=0.7)
        
        # Create agent with tools from persistent session
        self.agent = create_react_agent(
            llm, tools, prompt=SystemMessage(content=instructions))

        return "✅ Ready to create 3D objects with persistent MCP session!"
    
    def reset_conversation(self):
        """Reset the conversation history"""
        self.conversation_history = []
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
    
    async def cleanup(self):
        """Clean up the persistent session"""
        if self.session_context:
            try:
                session = await self.session_context.__aexit__(None, None, None)
                print("✅ MCP session cleaned up")
            except Exception as e:
                print(f"Error cleaning up session: {e}")
    
    async def chat(self, message: str, history: List):
        """Process a chat message"""
        if not self.agent:
            return history + [[message, "❌ Not initialized!"]]
            
        # Clear previous image to ensure fresh updates
        self._clear_current_image()
        
        # Add user message
        history = history + [[message, "🤔 Thinking..."]]
        
        try:
            # Add current user message to conversation history
            self.conversation_history.append(HumanMessage(content=message))
            
            # Invoke agent with full conversation history
            response = await self.agent.ainvoke({
                "messages": self.conversation_history
            })
            
            # Extract the latest AI response
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
            
            # Check for rendered images and code in tool calls and responses
            for msg in response["messages"]:
                if hasattr(msg, "tool_calls"):
                    for tool_call in msg.tool_calls:
                        if tool_call["name"] == "render_scad":
                            self.current_code = tool_call["args"].get("code", "")
                            
                # Check tool responses for images and data
                if hasattr(msg, "name") and msg.name == "render_scad":
                    content = msg.content
                    
                    # Process image content
                    if self._process_image_content(content):
                        continue
                                        
                    # As a fallback, try to find the most recent image file in output directory
                    if self.current_image is None:
                        try:
                            from pathlib import Path
                            output_dir = Path("../output")  # From gradio_app to output dir
                            if output_dir.exists():
                                # Find the most recent PNG file
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
                                
        except Exception as e:
            history[-1][1] = f"❌ Error: {str(e)}"
            
        return history

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
        
        # 2. Handle fastmcp Image objects specifically
        if MCP_IMAGE_AVAILABLE and isinstance(content, MCPImage):
            try:
                self.current_image = self._create_fresh_image_copy(content.data)
                if self.current_image:
                    print("✅ Loaded fastmcp Image object")
                    return True
            except Exception as e:
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


# Create Gradio interface
def create_app():
    """Create the Gradio app"""
    chat_assistant = SimpleOpenSCADChat()
    
    with gr.Blocks(title="OpenSCAD Chat", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🎨 OpenSCAD Design Chat")
        gr.Markdown("Describe what you want to create and I'll help you design it!")
        
        # Status
        status = gr.Markdown("⏳ Initializing...")
        
        with gr.Row():
            # Chat area
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(height=450)
                msg = gr.Textbox(
                    placeholder="Try: 'Create a red cube with rounded corners'",
                    show_label=False
                )
                with gr.Row():
                    send_btn = gr.Button("Send", variant="primary")
                    clear_btn = gr.Button("Clear Chat", variant="secondary")
                
            # Preview area
            with gr.Column(scale=1):
                preview = gr.Image(label="3D Preview", height=300)
                
                with gr.Accordion("Code", open=False):
                    code_view = gr.Code(language="c", show_label=False)
        
        # Initialize on load
        async def startup():
            return await chat_assistant.initialize()
        
        # Handle messages
        async def handle_message(message, history):
            if not message:
                return "", history, None, None
                
            # Process message
            new_history = await chat_assistant.chat(message, history)
            
            # Update displays
            return "", new_history, chat_assistant.current_image, chat_assistant.current_code
        
        # Handle clear chat
        def clear_chat():
            chat_assistant.reset_conversation()
            chat_assistant._clear_current_image()
            return [], None, None
        
        # Clean up on app close
        async def cleanup():
            await chat_assistant.cleanup()
        
        # Wire up events
        app.load(startup, outputs=status)
        msg.submit(handle_message, [msg, chatbot], [msg, chatbot, preview, code_view])
        send_btn.click(handle_message, [msg, chatbot], [msg, chatbot, preview, code_view])
        clear_btn.click(clear_chat, outputs=[chatbot, preview, code_view])
        
        # Clean up when app is closed (this might not work in all environments)
        app.unload(cleanup)
        
        # Add examples
        gr.Examples(
            examples=[
                "Create a simple cube",
                "Make a gear with 20 teeth", 
                "Design a phone stand",
                "Build a parametric box with lid"
            ],
            inputs=msg
        )
    
    return app


# Run the app
if __name__ == "__main__":
    import os
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY environment variable")
        exit(1)
    
    print("🚀 Starting OpenSCAD Chat...")
    app = create_app()
    app.launch(server_port=7860)
