#!/usr/bin/env python3
"""
Enhanced OpenSCAD Chat with 3D STL Visualization and Measurement Extraction
Combines existing functionality with native Gradio Model3D component
"""

import gradio as gr
import asyncio
from typing import List, Dict, Any, Optional, Tuple
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
import tempfile
import os

# 3D processing imports
try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    print("⚠️ Trimesh not available. Install with: pip install trimesh")

try:
    import open3d as o3d
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False
    print("⚠️ Open3D not available. Install with: pip install open3d")


class STLProcessor:
    """Handle STL file processing and optimization for web display"""

    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def find_latest_stl(self, output_dirs: List[str]) -> Optional[Path]:
        """Find the most recently created STL file"""
        stl_files = []

        for output_dir in output_dirs:
            dir_path = Path(output_dir)
            if dir_path.exists():
                stl_files.extend(dir_path.rglob("*.stl"))

        if not stl_files:
            return None

        # Return the most recently modified STL file
        latest_stl = max(stl_files, key=lambda p: p.stat().st_mtime)
        print(f"🔍 Found latest STL: {latest_stl}")
        return latest_stl

    def convert_stl_to_glb(self, stl_path: Path, optimize: bool = True) -> Optional[Path]:
        """Convert STL to GLB format for better web performance"""
        if not TRIMESH_AVAILABLE:
            print("❌ Trimesh not available for STL conversion")
            return stl_path  # Return original STL

        try:
            # Load STL file
            mesh = trimesh.load(str(stl_path))

            if optimize:
                # Optimization pipeline
                print(f"🔧 Original mesh: {len(mesh.faces)} faces")

                # Remove duplicate faces and vertices
                mesh.remove_duplicate_faces()
                mesh.remove_degenerate_faces()
                mesh.merge_vertices()

                # Simplify if too many faces (target max 50K for web performance)
                if len(mesh.faces) > 50000:
                    target_faces = 50000
                    mesh = mesh.simplify_quadratic_decimation(target_faces)
                    print(f"🔧 Simplified to: {len(mesh.faces)} faces")

            # Export as GLB (binary glTF format - better for web)
            glb_path = self.temp_dir / f"{stl_path.stem}.glb"
            mesh.export(str(glb_path))

            print(f"✅ Converted STL to GLB: {glb_path}")
            return glb_path

        except Exception as e:
            print(f"❌ Failed to convert STL to GLB: {e}")
            return stl_path  # Fallback to original STL

    def extract_measurements(self, stl_path: Path) -> Dict[str, Any]:
        """Extract dimensional measurements from STL file"""
        measurements = {
            'available': False,
            'dimensions': {},
            'properties': {},
            'bounding_box': {}
        }

        if not TRIMESH_AVAILABLE:
            return measurements

        try:
            mesh = trimesh.load(str(stl_path))

            # Basic bounding box measurements
            bbox_extents = mesh.bounding_box.extents
            bbox_bounds = mesh.bounds

            measurements.update({
                'available': True,
                'dimensions': {
                    'length': float(bbox_extents[0]),
                    'width': float(bbox_extents[1]),
                    'height': float(bbox_extents[2])
                },
                'properties': {
                    'volume': float(mesh.volume) if mesh.is_volume else 0.0,
                    'surface_area': float(mesh.area),
                    'center_of_mass': mesh.center_mass.tolist() if mesh.is_volume else [0, 0, 0],
                    'is_watertight': bool(mesh.is_watertight),
                    'face_count': int(len(mesh.faces)),
                    'vertex_count': int(len(mesh.vertices))
                },
                'bounding_box': {
                    'min_point': bbox_bounds[0].tolist(),
                    'max_point': bbox_bounds[1].tolist(),
                    'center': mesh.bounding_box.centroid.tolist()
                }
            })

            print(f"📏 Extracted measurements: {measurements['dimensions']}")

        except Exception as e:
            print(f"❌ Failed to extract measurements: {e}")

        return measurements

    def create_measurement_summary(self, measurements: Dict[str, Any]) -> str:
        """Create a formatted measurement summary"""
        if not measurements['available']:
            return "⚠️ Measurements not available (install trimesh: pip install trimesh)"

        dims = measurements['dimensions']
        props = measurements['properties']

        summary = f"""## 📏 Object Measurements

**Dimensions:**
- Length: {dims['length']:.2f} mm
- Width: {dims['width']:.2f} mm  
- Height: {dims['height']:.2f} mm

**Properties:**
- Volume: {props['volume']:.2f} mm³
- Surface Area: {props['surface_area']:.2f} mm²
- Faces: {props['face_count']:,}
- Vertices: {props['vertex_count']:,}
- Watertight: {'✅' if props['is_watertight'] else '❌'}
"""

        return summary


class Enhanced3DOpenSCADChat:
    """Enhanced OpenSCAD chat with 3D visualization and measurements"""

    def __init__(self, model="gpt-4o"):
        self.model = model
        self.agent = None
        self.current_image = None
        self.current_code = None
        self.current_3d_model = None
        self.current_measurements = {}
        self.conversation_history = []
        self.system_prompt = None
        self.client = None
        self.session_context = None
        self.session = None
        self.stl_processor = STLProcessor()

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
        print(
            f"🔧 Loaded {len(tools)} tools with persistent session: {[tool.name for tool in tools]}")

        # Store reference to session for direct access if needed
        self.mcp_session = self.session

        # Load instructions and store as system prompt
        try:
            self.system_prompt = Path("instructions.txt").read_text()
        except FileNotFoundError:
            self.system_prompt = "You are a helpful OpenSCAD design assistant. Help users create 3D objects using OpenSCAD code."

        # Create LLM
        llm = ChatOpenAI(model=self.model, temperature=0.7)

        # Create agent with system prompt
        def _add_system_prompt(state):
            """Add system prompt to the conversation"""
            messages = state.get("messages", [])
            if not messages or not isinstance(messages[0], SystemMessage):
                return [SystemMessage(content=self.system_prompt)] + messages
            return messages

        self.agent = create_react_agent(
            llm,
            tools,
            prompt=_add_system_prompt
        )

        # Initialize conversation history with system message
        self._initialize_conversation_history()

        return "✅ Ready with 3D visualization and measurement extraction!"

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
        self.current_3d_model = None
        self.current_measurements = {}

    def _clear_current_outputs(self):
        """Clear current outputs to ensure fresh updates"""
        if self.current_image:
            try:
                self.current_image.close()
            except:
                pass
        self.current_image = None
        self.current_3d_model = None
        self.current_measurements = {}

    def _create_fresh_image_copy(self, img_data_bytes):
        """Create a fresh PIL Image copy to avoid Gradio caching issues"""
        try:
            img = Image.open(BytesIO(img_data_bytes))
            img.load()

            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)

            fresh_img = Image.open(buffer)
            fresh_img.load()

            return fresh_img

        except Exception as e:
            print(f"Error creating fresh image copy: {e}")
            return None

    def _process_3d_output(self):
        """Process 3D output files (STL) and generate optimized models"""
        # Common output directories to check
        output_dirs = [
            "../output",  # Your current output directory
            "scad_output",  # Default MCP output
            "output",
            "."
        ]

        # Find the latest STL file
        latest_stl = self.stl_processor.find_latest_stl(output_dirs)

        if latest_stl:
            print(f"🎯 Processing 3D model: {latest_stl}")

            # Convert STL to GLB for better web performance
            optimized_model = self.stl_processor.convert_stl_to_glb(
                latest_stl, optimize=True)

            # Extract measurements
            measurements = self.stl_processor.extract_measurements(latest_stl)

            self.current_3d_model = str(
                optimized_model) if optimized_model else None
            self.current_measurements = measurements

            print(f"✅ 3D model processed: {self.current_3d_model}")
            return True

        print("⚠️ No STL files found")
        return False

    def _process_image_content(self, content) -> bool:
        """Process various image content formats and set self.current_image"""
        # [Keep your existing image processing logic here - it's working well]

        # Early exit for obviously non-image content
        if not content:
            return False

        # Skip error messages and other non-image strings
        if isinstance(content, str):
            if (content.startswith("Error:") or
                content.startswith("ToolException") or
                    len(content) < 50):
                return False

        print(f"🔍 Processing potential image content: {type(content)}")

        # 1. Handle MCP CallToolResult with ImageContent list (new MCP format)
        if isinstance(content, list) and len(content) > 0:
            first_item = content[0]
            if hasattr(first_item, 'type') and first_item.type == 'image' and hasattr(first_item, 'data'):
                try:
                    img_data = base64.b64decode(first_item.data)
                    self.current_image = self._create_fresh_image_copy(
                        img_data)
                    if self.current_image:
                        print("✅ Loaded image from ImageContent")
                        return True
                except Exception as e:
                    print(f"Failed to load ImageContent: {e}")

        # [Include your other image processing methods here...]

        return False

    def _extract_outputs(self, messages):
        """Extract images, code, and 3D models from tool responses"""
        print(f"🔍 _extract_outputs: Processing {len(messages)} messages")

        for i, msg in enumerate(messages):
            # Check for tool calls (to get code)
            if hasattr(msg, "tool_calls"):
                for tool_call in msg.tool_calls:
                    if tool_call["name"] == "render_scad":
                        self.current_code = tool_call["args"].get("code", "")
                        print(f"✅ Extracted code from tool call")

            # Check tool responses for images
            if hasattr(msg, "name") and msg.name == "render_scad":
                content = msg.content
                print(
                    f"🔍 Found render_scad response with content: {type(content)}")

                # Try to process image content
                self._process_image_content(content)

        # After processing messages, look for 3D output files
        if self.current_code:  # If we have code, likely means rendering happened
            self._process_3d_output()

    def _get_conversation_messages(self):
        """Get properly formatted conversation messages for the agent"""
        if not self.conversation_history or not isinstance(self.conversation_history[0], SystemMessage):
            self._initialize_conversation_history()
        return self.conversation_history.copy()

    async def chat(self, message: str, history: List) -> Tuple[List, Optional[str], str, Dict]:
        """Process chat message and return updated outputs"""
        if not self.agent:
            return history + [[message, "❌ Not initialized!"]], None, "", {}

        # Clear previous outputs
        self._clear_current_outputs()

        # Add user message to history if not already there
        if not (history and history[-1][0] == message and "🤔 Thinking..." in str(history[-1][1])):
            history = history + \
                [[message, "🤔 Thinking... (generating 3D model)"]]

        try:
            # Add user message to conversation history
            self.conversation_history.append(HumanMessage(content=message))

            # Get properly formatted messages for the agent
            agent_messages = self._get_conversation_messages()

            # Invoke agent with proper message history
            response = await self.agent.ainvoke({
                "messages": agent_messages
            })

            # Extract AI response
            latest_ai_message = None
            for msg in reversed(response["messages"]):
                if isinstance(msg, AIMessage):
                    latest_ai_message = msg
                    break

            if latest_ai_message:
                ai_content = latest_ai_message.content
                self.conversation_history.append(AIMessage(content=ai_content))
                history[-1][1] = ai_content
            else:
                history[-1][1] = "❌ No response generated"

            # Extract outputs from tool responses
            self._extract_outputs(response["messages"])

            # Try direct MCP call for immediate results
            if self.current_code:
                try:
                    direct_result = await self.mcp_session.call_tool(
                        "render_scad",
                        arguments={"code": self.current_code}
                    )

                    # Process direct result for image
                    if hasattr(direct_result, 'content') and direct_result.content:
                        self._process_image_content(direct_result.content)

                    # Look for 3D output after direct call
                    await asyncio.sleep(1)  # Give time for file generation
                    self._process_3d_output()

                except Exception as e:
                    print(f"❌ Direct MCP call failed: {e}")

        except Exception as e:
            history[-1][1] = f"❌ Error: {str(e)}"

        return (
            history,
            self.current_3d_model,
            self.current_code or "",
            self.current_measurements
        )


def create_enhanced_app():
    """Create enhanced Gradio app with 3D visualization"""
    chat_assistant = Enhanced3DOpenSCADChat()

    with gr.Blocks(title="Enhanced OpenSCAD Assistant", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🎨 Enhanced OpenSCAD Design Assistant")
        gr.Markdown(
            "Chat naturally about 3D design - Now with **3D visualization** and **measurement extraction**!")

        # Status indicator
        status = gr.Markdown("⏳ Initializing enhanced MCP server...")

        with gr.Row():
            # Chat interface
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(height=800, show_label=False)
                msg = gr.Textbox(
                    placeholder="Try: 'Create a phone stand with measurements'",
                    show_label=False
                )
                with gr.Row():
                    send_btn = gr.Button("Send", variant="primary")
                    clear_btn = gr.Button("Clear Chat", variant="secondary")

            # Enhanced preview panel
            with gr.Column(scale=2):
                with gr.Tabs():
                    # 3D Model Tab
                    with gr.TabItem("🎯 3D Model"):
                        model_3d = gr.Model3D(
                            label="3D Model",
                            height=400,
                            display_mode="solid",
                            camera_position=[300, 450, 450]
                        )

                    # 2D Preview Tab (fallback)
                    with gr.TabItem("🖼️ 2D Preview"):
                        preview_2d = gr.Image(label="2D Preview", height=400)

                # Measurements panel
                with gr.Accordion("📏 Measurements", open=False):
                    measurements_display = gr.Markdown(
                        "No measurements available")

                # Code panel
                with gr.Accordion("💻 Generated Code", open=True):
                    code_view = gr.Code(language="c", show_label=False)

        # Event handlers
        async def startup():
            """Initialize the assistant"""
            result = await chat_assistant.initialize()
            return result

        async def handle_message(message, history):
            """Handle user messages with 3D processing"""
            if not message:
                return "", history, None, None, "No measurements available", ""

            # Process the message
            updated_history, model_3d_path, code, measurements = await chat_assistant.chat(message, history)

            # Create measurements display
            measurements_text = "No measurements available"
            if measurements.get('available', False):
                measurements_text = chat_assistant.stl_processor.create_measurement_summary(
                    measurements)

            return (
                "",  # Clear input
                updated_history,  # Updated chat history
                model_3d_path,  # 3D model file path
                chat_assistant.current_image,  # 2D preview image
                measurements_text,  # Measurements markdown
                code  # Generated code
            )

        def clear_chat():
            """Clear conversation and outputs"""
            chat_assistant.reset_conversation()
            return [], None, None, "No measurements available", ""

        async def cleanup():
            """Clean up resources"""
            await chat_assistant.cleanup()

        # Wire up events
        app.load(startup, outputs=status)

        # Message handling
        msg.submit(
            handle_message,
            [msg, chatbot],
            [msg, chatbot, model_3d, preview_2d, measurements_display, code_view]
        )
        send_btn.click(
            handle_message,
            [msg, chatbot],
            [msg, chatbot, model_3d, preview_2d, measurements_display, code_view]
        )

        clear_btn.click(
            clear_chat,
            outputs=[chatbot, model_3d, preview_2d,
                     measurements_display, code_view]
        )

        # Cleanup on app close
        app.unload(cleanup)

        # Enhanced example prompts
        gr.Examples(
            examples=[
                "Create a phone stand with angled back support",
                "Make a parametric gear with 20 teeth and show me its dimensions",
                "Design a pencil holder that's 80mm tall",
                "Build a simple bearing holder with precise measurements",
                "Create a spiral vase and tell me its volume"
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

    # Check for required dependencies
    if not TRIMESH_AVAILABLE:
        print("⚠️ For full 3D functionality, install: pip install trimesh")

    print("🚀 Starting Enhanced OpenSCAD Chat with 3D Visualization...")
    app = create_enhanced_app()
    app.launch(server_port=7861)
