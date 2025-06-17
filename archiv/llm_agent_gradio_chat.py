#!/usr/bin/env python3
"""
LLM Agent-based Gradio Chat Interface for OpenSCAD MCP
Uses smolagents CodeAgent with MCP tools integration
"""

import gradio as gr
import asyncio
import json
import base64
import uuid
import os
from io import BytesIO
from PIL import Image
from pathlib import Path

# LLM Agent imports
from smolagents import tool, CodeAgent, InferenceClientModel, LiteLLMModel

# MCP imports
import mcp
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class MCPToolBridge:
    """Bridge between MCP server and smolagents tools"""

    def __init__(self, config_file="openscad_config.json"):
        self.config_file = config_file
        self.config = None
        self.session = None
        self.generation_id = str(uuid.uuid4())

    def load_config(self):
        """Load MCP server configuration"""
        config_path = Path(self.config_file)
        if not config_path.exists():
            print(f"Config file not found: {config_path}")
            return False

        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading config: {e}")
            return False

    async def connect_mcp(self):
        """Connect to MCP server"""
        if not self.config and not self.load_config():
            raise Exception("Failed to load MCP configuration")

        if "openscad" not in self.config:
            raise Exception("No 'openscad' section in config")

        openscad_config = self.config["openscad"]

        server_params = StdioServerParameters(
            command=openscad_config.get("command", "python"),
            args=openscad_config.get("args", []),
            env=openscad_config.get("env", {})
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self.session = session

                # Test connection
                tools = await session.list_tools()
                print(
                    f"✅ Connected to MCP server with tools: {[t.name for t in tools.tools]}")
                return True

    async def call_mcp_tool(self, tool_name, arguments=None):
        """Call MCP tool and return result"""
        if not self.session:
            await self.connect_mcp()

        if arguments is None:
            arguments = {}

        try:
            result = await self.session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            print(f"MCP tool call failed: {e}")
            raise


# Global MCP bridge instance
mcp_bridge = MCPToolBridge()

# Smolagents tools that use MCP backend


@tool
def render_scad(code: str, iteration: int = 0) -> str:
    """
    Render OpenSCAD code and return the path to the rendered image.
    
    Args:
        code: The OpenSCAD code to render. Should include quality settings like $fa=1; $fs=0.4;
        iteration: The iteration number (default: 0)
    
    Returns:
        The file path to the rendered PNG image
    """
    try:
        # Run the async MCP call in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                mcp_bridge.call_mcp_tool("render_scad", {
                    "code": code,
                    "iteration": iteration
                })
            )

            # Extract image path or data from MCP result
            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'type'):
                        if content.type == 'text':
                            return content.text  # Return path
                        elif content.type == 'image':
                            # Save image data to file
                            image_data = base64.b64decode(content.data)
                            image = Image.open(BytesIO(image_data))

                            # Save to local path
                            output_dir = f"scad_output/{mcp_bridge.generation_id}/{iteration}"
                            os.makedirs(output_dir, exist_ok=True)
                            image_path = f"{output_dir}/rendered.png"
                            image.save(image_path)
                            return image_path

            return "Error: No valid result from render_scad"

        finally:
            loop.close()

    except Exception as e:
        return f"Error rendering OpenSCAD: {str(e)}"


@tool
def openscad_doc_search(query: str) -> str:
    """
    Search OpenSCAD documentation, tutorials, and examples.
    
    Args:
        query: The search query for OpenSCAD documentation
        
    Returns:
        Relevant documentation snippets
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                mcp_bridge.call_mcp_tool(
                    "openscad_doc_search", {"query": query})
            )

            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        return content.text

            return "No documentation found for your query."

        finally:
            loop.close()

    except Exception as e:
        return f"Error searching documentation: {str(e)}"


@tool
def list_openscad_libraries() -> str:
    """
    List available OpenSCAD libraries and their usage.
    
    Returns:
        Information about installed OpenSCAD libraries
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                mcp_bridge.call_mcp_tool("list_openscad_libraries", {})
            )

            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        return content.text

            return "No library information available."

        finally:
            loop.close()

    except Exception as e:
        return f"Error listing libraries: {str(e)}"


@tool
def get_gear_parameter() -> str:
    """
    Get information about gear generation parameters and examples.
    
    Returns:
        Gear parameter reference and examples
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                mcp_bridge.call_mcp_tool("get_gear_parameter", {})
            )

            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        return content.text

            return "No gear parameter information available."

        finally:
            loop.close()

    except Exception as e:
        return f"Error getting gear parameters: {str(e)}"


def process_render_output(step_log, agent):
    """
    Callback to process rendered images and add them to agent's visual memory.
    """
    if hasattr(step_log, 'observations') and step_log.observations:
        observations_str = str(step_log.observations)

        # Check if observations contain a path to a rendered image
        if 'scad_output/' in observations_str and '.png' in observations_str:
            # Extract image path
            for line in observations_str.split('\n'):
                if 'scad_output/' in line and '.png' in line:
                    path = line.strip()
                    if os.path.exists(path):
                        try:
                            # Load image and add to visual memory
                            image = Image.open(path)
                            step_log.observations_images = [image.copy()]
                            print(
                                f"Added rendered image to visual memory: {image.size}")
                        except Exception as e:
                            print(f"Error loading image from {path}: {e}")


class OpenSCADLLMChat:
    """LLM Agent-based OpenSCAD chat"""

    def __init__(self, model_id="meta-llama/Llama-4-Scout-17B-16E-Instruct"):
        self.agent = None
        self.model_id = model_id
        self.conversation_history = []
        self.is_initialized = False
        self.initialization_error = None

    def create_agent(self):
        """Create the smolagents CodeAgent"""
        print(f"🧠 Creating LLM agent with model: {self.model_id}")

        # Set up tools
        tools = [render_scad, openscad_doc_search,
                 list_openscad_libraries, get_gear_parameter]

        # Create model
        if "openai/" in self.model_id:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise Exception("OPENAI_API_KEY environment variable not set")

            model = LiteLLMModel(
                model_id=self.model_id,
                api_key=api_key
            )
        else:
            token = os.getenv("HF_TOKEN")
            if not token:
                raise Exception("HF_TOKEN environment variable not set")

            model = InferenceClientModel(
                model_id=self.model_id,
                token=token
            )

        # Create agent
        self.agent = CodeAgent(
            tools=tools,
            model=model,
            add_base_tools=True,
            additional_authorized_imports=[
                'json', 'math', 'time', 'os', 'PIL', 'base64', 'io'
            ],
            step_callbacks=[process_render_output]
        )

        # Load OpenSCAD instructions
        instructions_path = Path("instructions.txt")
        if instructions_path.exists():
            print("📚 Loading OpenSCAD instructions...")
            with open(instructions_path, 'r') as f:
                openscad_instructions = f.read()

            # Modify system prompt
            self.agent.prompt_templates["system_prompt"] = (
                self.agent.prompt_templates["system_prompt"].replace("Now Begin!", "") +
                "\n\n" + openscad_instructions
            )

        print(f"✅ LLM agent created successfully")

    async def initialize(self):
        """Initialize the MCP connection and agent"""
        try:
            print("🔧 Initializing OpenSCAD LLM Chat System...")

            # Initialize MCP bridge
            print("📡 Loading MCP configuration...")
            if not mcp_bridge.config and not mcp_bridge.load_config():
                raise Exception("Failed to load MCP configuration")

            # Test MCP connection
            print("🔌 Connecting to OpenSCAD MCP server...")
            await mcp_bridge.connect_mcp()

            # Create agent
            print("🤖 Setting up LLM agent...")
            self.create_agent()

            # Test the agent with a simple query
            print("🧪 Testing agent functionality...")
            test_result = self.agent.run(
                "Hello! Are you ready to help with OpenSCAD?")

            self.is_initialized = True
            print("🎉 Initialization complete! Agent is ready.")

            return True

        except Exception as e:
            error_msg = f"Failed to initialize: {str(e)}"
            print(f"❌ {error_msg}")
            self.initialization_error = error_msg
            return False

    def chat(self, message: str) -> tuple[str, Image.Image]:
        """
        Chat with the LLM agent
        
        Returns:
            (response_text, rendered_image_or_none)
        """
        if not self.is_initialized:
            if self.initialization_error:
                return f"❌ Agent not initialized: {self.initialization_error}", None
            else:
                return "❌ Agent not initialized. Please restart the application.", None

        try:
            # Run the agent
            print(f"💭 Processing: {message[:50]}...")
            result = self.agent.run(message)

            # Extract response
            if hasattr(result, 'text'):
                response_text = result.text
            else:
                response_text = str(result)

            # Look for rendered images in the conversation
            rendered_image = None

            # Check for recent rendered image files
            output_base = f"scad_output/{mcp_bridge.generation_id}"
            if os.path.exists(output_base):
                for root, dirs, files in os.walk(output_base):
                    for file in files:
                        if file.endswith('.png'):
                            image_path = os.path.join(root, file)
                            try:
                                rendered_image = Image.open(image_path)
                                print(
                                    f"🖼️ Loaded rendered image: {image_path}")
                                break
                            except Exception as e:
                                print(f"Error loading image {image_path}: {e}")
                    if rendered_image:
                        break

            print(f"✅ Response generated")
            return response_text, rendered_image

        except Exception as e:
            error_msg = f"❌ Error in agent conversation: {str(e)}"
            print(error_msg)
            return error_msg, None


# Global chat instance
openscad_chat = None


async def initialize_chat_system(config_file="openscad_config.json", model_id="meta-llama/Llama-4-Scout-17B-16E-Instruct"):
    """Initialize the complete chat system"""
    global openscad_chat, mcp_bridge

    print("\n" + "="*60)
    print("🚀 INITIALIZING OPENSCAD LLM AGENT SYSTEM")
    print("="*60)

    try:
        # Initialize MCP bridge
        mcp_bridge = MCPToolBridge(config_file)

        # Initialize chat system
        openscad_chat = OpenSCADLLMChat(model_id)

        # Run async initialization
        success = await openscad_chat.initialize()

        if success:
            print("\n🎉 SUCCESS! OpenSCAD LLM Agent is ready to chat!")
            print(f"📡 MCP Server: Connected")
            print(f"🧠 Model: {model_id}")
            print(f"🔧 Tools: render_scad, doc_search, libraries, gears")
            print("-" * 60)
            return True
        else:
            print(f"\n❌ INITIALIZATION FAILED")
            if openscad_chat.initialization_error:
                print(f"Error: {openscad_chat.initialization_error}")
            return False

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {str(e)}")
        return False


def initialize_chat(config_file="openscad_config.json", model_id="meta-llama/Llama-4-Scout-17B-16E-Instruct"):
    """Sync wrapper for async initialization"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(initialize_chat_system(config_file, model_id))
    finally:
        loop.close()


async def chat_interface(message, history):
    """Gradio chat interface - now expects pre-initialized system"""
    try:
        if not openscad_chat or not openscad_chat.is_initialized:
            error_msg = "❌ System not properly initialized. Please restart the application."
            if openscad_chat and openscad_chat.initialization_error:
                error_msg += f"\nError: {openscad_chat.initialization_error}"

            history.append([message, error_msg])
            return history, None

        # Get response from LLM agent
        response, image = openscad_chat.chat(message)

        # Add to history
        history.append([message, response])

        return history, image

    except Exception as e:
        error_msg = f"❌ Unexpected error: {str(e)}"
        print(error_msg)
        history.append([message, error_msg])
        return history, None


def create_gradio_interface():
    """Create the Gradio interface"""

    # Get agent status for display
    if openscad_chat and openscad_chat.is_initialized:
        agent_status = f"🟢 **Ready** - Model: `{openscad_chat.model_id}`"
        agent_info = f"""
        **Model:** {openscad_chat.model_id}
        **Status:** ✅ Initialized and ready
        **MCP Server:** ✅ Connected
        
        **Available Capabilities:**
        - 🧠 Intelligent reasoning and planning
        - 🔍 Documentation search  
        - 🎨 3D object generation and rendering
        - ⚙️ Gear design and generation
        - 📚 Library integration (BOSL, etc.)
        - 👁️ Image analysis and feedback
        """
    else:
        agent_status = "🔴 **Not Ready** - Initialization failed"
        error_details = openscad_chat.initialization_error if openscad_chat else "Unknown error"
        agent_info = f"""
        **Status:** ❌ Initialization failed
        **Error:** {error_details}
        
        Please check:
        - Configuration file paths
        - API tokens (HF_TOKEN or OPENAI_API_KEY)
        - OpenSCAD MCP server accessibility
        """

    with gr.Blocks(title="OpenSCAD LLM Agent", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🤖 OpenSCAD LLM Agent Chat")
        gr.Markdown(
            "Intelligent OpenSCAD assistant powered by LLM reasoning and MCP tools!")

        # Status indicator
        with gr.Row():
            gr.Markdown(f"### Agent Status: {agent_status}")

        with gr.Row():
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    height=500,
                    show_label=False,
                    container=True,
                    bubble_full_width=False,
                    avatar_images=("🧑‍💻", "🤖")
                )

                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="Ask me to create 3D objects, search docs, or help with OpenSCAD..." if openscad_chat and openscad_chat.is_initialized else "⚠️ Agent not ready - check configuration and restart",
                        show_label=False,
                        scale=4,
                        container=False,
                        interactive=openscad_chat and openscad_chat.is_initialized
                    )
                    submit_btn = gr.Button(
                        "Send",
                        scale=1,
                        variant="primary" if openscad_chat and openscad_chat.is_initialized else "secondary",
                        interactive=openscad_chat and openscad_chat.is_initialized
                    )

            with gr.Column(scale=1):
                image_output = gr.Image(
                    label="Rendered 3D Object",
                    height=400,
                    show_download_button=True
                )

                if openscad_chat and openscad_chat.is_initialized:
                    gr.Markdown("### 🎯 Example Prompts:")
                    gr.Markdown("""
                    - "Create a red cube with a blue sphere on top"
                    - "Make a gear with 20 teeth and 5mm thickness" 
                    - "Design a low poly car with wheels"
                    - "Search documentation for hull operations"
                    - "Show me available OpenSCAD libraries"
                    - "Create a rounded box using BOSL library"
                    """)

                with gr.Accordion("🔧 Agent Info", open=False):
                    gr.Markdown(agent_info)

        # Handle message submission only if initialized
        def submit_message(message, history):
            if not openscad_chat or not openscad_chat.is_initialized:
                if message.strip():
                    error_msg = "❌ Agent not initialized. Please restart the application."
                    if openscad_chat and openscad_chat.initialization_error:
                        error_msg += f"\nError: {openscad_chat.initialization_error}"
                    history.append([message, error_msg])
                return "", history, None

            if message.strip():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    updated_history, image = loop.run_until_complete(
                        chat_interface(message, history)
                    )
                    return "", updated_history, image
                finally:
                    loop.close()
            return message, history, None

        # Connect events
        submit_btn.click(
            submit_message,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot, image_output]
        )

        msg.submit(
            submit_message,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot, image_output]
        )

        # Clear button
        with gr.Row():
            clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")
            clear_btn.click(lambda: ([], None), outputs=[
                            chatbot, image_output])

    return demo


def main():
    """Main function - initializes everything before starting UI"""
    print("🤖 OpenSCAD LLM Agent Chat Interface")
    print("=" * 50)

    # Get configuration from environment or use defaults
    config_file = os.getenv("OPENSCAD_CONFIG_PATH", "openscad_config.json")
    model_id = os.getenv("OPENSCAD_MODEL_ID",
                         "meta-llama/Llama-4-Scout-17B-16E-Instruct")

    print(f"📄 Config file: {config_file}")
    print(f"🧠 Model: {model_id}")

    # Check if config file exists
    if not Path(config_file).exists():
        print(f"\n❌ Configuration file not found: {config_file}")
        print("Please create the configuration file first!")
        print("Run the startup script to create a template:")
        print(f"  python llm_agent_startup.py")
        return

    # Initialize the complete system before starting UI
    print(f"\n🔄 Initializing system...")
    success = initialize_chat(config_file, model_id)

    if not success:
        print("\n❌ INITIALIZATION FAILED!")
        print("Cannot start the web interface.")
        print("\nPlease check:")
        print("1. Configuration file has correct paths")
        print("2. OpenSCAD MCP server is accessible")
        print("3. Required API tokens are set (HF_TOKEN or OPENAI_API_KEY)")
        print("4. All dependencies are installed")
        return

    # Create and launch interface only after successful initialization
    print(f"\n🌐 Starting web interface...")
    demo = create_gradio_interface()

    # Show welcome message
    print("\n" + "="*60)
    print("🎉 OpenSCAD LLM Agent is ready!")
    print("="*60)
    print(f"🌐 Web interface: http://localhost:7860")
    print(f"🧠 Model: {model_id}")
    print(f"🔧 MCP Tools: Available and connected")
    print(f"📚 Documentation: Searchable")
    print(f"⚙️ Gear generation: Ready")
    print("-" * 60)
    print("💬 Start chatting! The agent is fully initialized and ready.")
    print("="*60)

    # Launch with configuration
    demo.launch(
        server_name="0.0.0.0",  # Allow external access
        server_port=7860,       # Default Gradio port
        share=False,            # Set to True to create public link
        debug=True,             # Enable debug mode
        show_error=True         # Show detailed errors
    )


if __name__ == "__main__":
    main()
