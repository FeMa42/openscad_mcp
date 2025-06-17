#!/usr/bin/env python3
"""
Lightweight OpenSCAD Assistant using LangGraph + MCP
Minimal implementation leveraging LangGraph's built-in capabilities
"""

import gradio as gr
import asyncio
import os
from typing import TypedDict, List, Dict, Any, Annotated, Literal
from pathlib import Path
import base64
from io import BytesIO
from PIL import Image
import json

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# LangChain imports
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# MCP imports
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp.client.session import ClientSession


# State definition for our workflow
class AgentState(TypedDict):
    """Minimal state for the conversation"""
    messages: Annotated[List, add_messages]
    current_design: Dict[str, Any]  # Stores current OpenSCAD code and image
    feedback_needed: bool
    

class OpenSCADAssistant:
    """Lightweight OpenSCAD assistant using LangGraph + MCP"""
    
    def __init__(self, model_name: str = "gpt-4o", mcp_config: Dict = None):
        self.model_name = model_name
        self.mcp_config = self._default_mcp_config(mcp_config)
        self.mcp_client = None
        self.agent_executor = None
        self.workflow = None
        self.memory = MemorySaver()  # For conversation persistence
        
    def _default_mcp_config(self, mcp_config: str) -> Dict:
        """Default MCP configuration for OpenSCAD server"""
        with open(mcp_config) as f:
            config = json.load(f)
        mcp_config = config.get("mcpServers", config)
        return mcp_config
    
    async def initialize(self):
        """Initialize MCP client and LangGraph workflow"""
        # Initialize MCP client
        
        self.mcp_client = MultiServerMCPClient(self.mcp_config)
        
        # Get LLM
        if "gpt" in self.model_name:
            llm = ChatOpenAI(model=self.model_name, streaming=True)
        else:
            llm = ChatAnthropic(model=self.model_name, streaming=True)
        
        # Load MCP tools
        async with self.mcp_client.session("openscad") as session:
            tools = await load_mcp_tools(session)
            
            # Create ReAct agent with MCP tools
            self.agent_executor = create_react_agent(
                llm, 
                tools,
                prompt=self._create_system_message()
            )
        
        # Build the workflow
        self._build_workflow()
    
    def _create_system_message(self) -> str:
        """System message for the agent"""
        instructions = Path("instructions.txt").read_text()
        system_message = SystemMessage(
            content=instructions
        )
        return system_message
    
    def _build_workflow(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Define nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("process_feedback", self._process_feedback_node)
        
        # Define flow
        workflow.set_entry_point("agent")
        
        # Conditional edge based on whether feedback is needed
        workflow.add_conditional_edges(
            "agent",
            self._should_get_feedback,
            {
                "feedback": "process_feedback",
                "continue": "agent",
                "end": END
            }
        )
        
        workflow.add_edge("process_feedback", "agent")
        
        # Compile with memory for persistence
        self.workflow = workflow.compile(
            checkpointer=self.memory,
            interrupt_before=["process_feedback"]  # Pause for user input
        )
    
    async def _agent_node(self, state: AgentState) -> AgentState:
        """Main agent node that processes messages"""
        # Run the ReAct agent
        result = await self.agent_executor.ainvoke(state)
        
        # Check if we generated any OpenSCAD code/image
        if self._check_for_design_output(result):
            state["feedback_needed"] = True
            state["current_design"] = self._extract_design_info(result)
        else:
            state["feedback_needed"] = False
            
        return state
    
    async def _process_feedback_node(self, state: AgentState) -> AgentState:
        """Process user feedback"""
        # This node is interrupted before execution, allowing user input
        # The actual processing happens in the next agent call
        state["feedback_needed"] = False
        return state
    
    def _should_get_feedback(self, state: AgentState) -> Literal["feedback", "continue", "end"]:
        """Decide next step based on state"""
        last_message = state["messages"][-1]
        
        # End if user says goodbye
        if isinstance(last_message, HumanMessage):
            content = last_message.content.lower()
            if any(word in content for word in ["bye", "exit", "quit", "thanks that's all"]):
                return "end"
        
        # Get feedback if we just created something
        if state.get("feedback_needed", False):
            return "feedback"
            
        # Continue conversation
        return "continue"
    
    def _check_for_design_output(self, result: Dict) -> bool:
        """Check if the agent created any OpenSCAD design"""
        # Look for render_scad tool calls in the messages
        for msg in result.get("messages", []):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if tool_call.get("name") == "render_scad":
                        return True
        return False
    
    def _extract_design_info(self, result: Dict) -> Dict[str, Any]:
        """Extract OpenSCAD code and image from agent result"""
        design_info = {"code": None, "image": None}
        
        for msg in result.get("messages", []):
            # Extract code from tool calls
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if tool_call.get("name") == "render_scad":
                        design_info["code"] = tool_call.get("args", {}).get("code", "")
            
            # Extract image from tool responses
            if isinstance(msg, ToolMessage):
                # Handle MCP image response
                content = msg.content
                if isinstance(content, list):
                    for item in content:
                        if item.get("type") == "image":
                            design_info["image"] = item.get("data")  # Base64 image
                elif "scad_output/" in str(content):
                    # Path to image file
                    design_info["image_path"] = str(content).strip()
                    
        return design_info
    
    async def stream_conversation(self, message: str, thread_id: str):
        """Stream conversation updates"""
        # Add user message
        user_msg = HumanMessage(content=message)
        
        # Stream the agent response
        config = {"configurable": {"thread_id": thread_id}}
        
        async for event in self.workflow.astream_events(
            {"messages": [user_msg]}, 
            config,
            version="v2"
        ):
            yield event


# Gradio Interface
class GradioInterface:
    """Minimal Gradio interface for the OpenSCAD assistant"""
    
    def __init__(self, model_name: str = "gpt-4o-mini", mcp_config: Dict = None):
        self.mcp_config = mcp_config 
        self.model_name = model_name
        self.assistant = None
        self.thread_id = "default"
        
    async def initialize_assistant(self):
        """Initialize the assistant"""
        self.assistant = OpenSCADAssistant(self.model_name, self.mcp_config)
        await self.assistant.initialize()
        return "✅ Assistant initialized and ready!"
    
    async def process_message(self, message: str, history: List):
        """Process a message and update the interface"""
        if not self.assistant:
            yield history + [[message, "❌ Assistant not initialized!"]], None, None
            return
            
        # Add user message to history
        history = history + [[message, ""]]
        yield history, None, None
        
        # Track current response
        current_response = ""
        current_image = None
        current_code = None
        
        # Stream events from the assistant
        try:
            async for event in self.assistant.stream_conversation(message, self.thread_id):
                # Handle different event types
                if event["event"] == "on_chat_model_stream":
                    # Streaming tokens from LLM
                    content = event["data"]["chunk"].content
                    if content:
                        current_response += content
                        history[-1][1] = current_response
                        yield history, current_image, current_code
                        
                elif event["event"] == "on_tool_end":
                    # Tool execution completed
                    if event["name"] == "render_scad":
                        # Extract image from tool output
                        output = event["data"]["output"]
                        if isinstance(output, dict):
                            # Handle MCP response format
                            for content in output.get("content", []):
                                if content.get("type") == "image":
                                    # Decode base64 image
                                    image_data = base64.b64decode(content["data"])
                                    current_image = Image.open(BytesIO(image_data))
                                    
                        # Also try to get the code that was rendered
                        if "args" in event["data"]:
                            current_code = event["data"]["args"].get("code", "")
                            
                        yield history, current_image, current_code
                        
                elif event["event"] == "on_chain_end":
                    # Conversation step completed
                    if event["name"] == "LangGraph":
                        # Final state update
                        yield history, current_image, current_code
                        
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            history[-1][1] = error_msg
            yield history, None, None
    
    def create_interface(self):
        """Create the Gradio interface"""
        with gr.Blocks(title="OpenSCAD Assistant", theme=gr.themes.Soft()) as demo:
            gr.Markdown("# 🎨 OpenSCAD Design Assistant")
            gr.Markdown("Chat naturally about 3D design - powered by LangGraph + MCP")
            
            # Initialize on load
            status = gr.Markdown("⏳ Initializing assistant...")
            
            with gr.Row():
                # Chat interface
                with gr.Column(scale=2):
                    chatbot = gr.Chatbot(
                        height=600,
                        show_label=False,
                        elem_classes=["chat-window"]
                    )
                    
                    with gr.Row():
                        msg = gr.Textbox(
                            placeholder="Describe what you'd like to create...",
                            show_label=False,
                            scale=5
                        )
                        send_btn = gr.Button("Send", variant="primary", scale=1)
                
                # Output panel
                with gr.Column(scale=1):
                    image_output = gr.Image(
                        label="3D Preview",
                        height=300
                    )
                    
                    with gr.Accordion("Generated Code", open=True):
                        code_output = gr.Code(
                            language="c",
                            show_label=False
                        )
                    
                    # Examples
                    gr.Examples(
                        examples=[
                            "Help me Create a phone stand",
                            "Design a parametric box with a separate lid",
                            "Create a gear with 20 teeth"
                        ],
                        inputs=msg
                    )
            
            # Event handlers
            async def send_message(message, history):
                if not message.strip():
                    yield "", history, None, None
                    
                async for hist, img, code in interface.process_message(message, history):
                    yield "", hist, img, code
            
            # Connect events
            msg.submit(send_message, [msg, chatbot], [msg, chatbot, image_output, code_output])
            send_btn.click(send_message, [msg, chatbot], [msg, chatbot, image_output, code_output])
            
            # Initialize assistant on load
            demo.load(
                lambda: asyncio.run(interface.initialize_assistant()),
                outputs=status
            )
            
            # Custom CSS
            demo.css = """
            .chat-window { border-radius: 10px; }
            .chat-window .message { padding: 10px; margin: 5px; border-radius: 8px; }
            """
            
        return demo


# Main execution
if __name__ == "__main__":
    # Set up configuration
    import argparse
    parser = argparse.ArgumentParser(description="OpenSCAD Assistant with LangGraph + MCP")
    parser.add_argument("--model", default="gpt-4o", help="LLM model to use")
    parser.add_argument("--mcp_config", default="config.json", help="MCP configuration file")
    parser.add_argument("--port", type=int, default=7860, help="Port for Gradio")
    args = parser.parse_args()
    
    # Verify environment
    if "gpt" in args.model and not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY environment variable")
        exit(1)
    elif "claude" in args.model and not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        exit(1)
    
    # Create and launch interface
    print("🚀 Starting OpenSCAD Assistant...")
    interface = GradioInterface(args.model, args.mcp_config)
    demo = interface.create_interface()
    
    print(f"✨ Launching on http://localhost:{args.port}")
    demo.launch(server_port=args.port, share=False)
