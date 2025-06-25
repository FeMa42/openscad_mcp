#!/usr/bin/env python3
"""
Enhanced OpenSCAD Chat with Smart Camera Positioning and Auto-Rotation
Includes automatic camera adjustment and turntable rotation for optimal viewing
"""

import gradio as gr
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
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
import math
import argparse

# 3D processing imports
try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    print("⚠️ Trimesh not available. Install with: pip install trimesh")


class SmartCameraCalculator:
    """Calculate optimal camera positioning based on 3D object properties"""

    @staticmethod
    def calculate_optimal_camera_position(measurements: Dict[str, Any]) -> List[float]:
        """Calculate optimal camera position based on object dimensions"""
        if not measurements.get('available', False):
            # Default camera position for unknown objects
            return [200, 200, 200]

        dims = measurements['dimensions']
        bbox = measurements['bounding_box']

        # Get the maximum dimension to determine camera distance
        max_dim = max(dims['length'], dims['width'], dims['height'])

        # Calculate optimal distance (typically 2-4x the max dimension)
        optimal_distance = max_dim * 3.5

        # Ensure minimum distance for very small objects
        optimal_distance = max(optimal_distance, 50)

        # Position camera at 45-degree angles for good visibility
        # Slightly elevated to show top details
        angle_h = 45  # horizontal angle (degrees)
        angle_v = 30  # vertical angle (degrees)

        # Convert to radians
        angle_h_rad = math.radians(angle_h)
        angle_v_rad = math.radians(angle_v)

        # Calculate camera position
        x = optimal_distance * math.cos(angle_v_rad) * math.cos(angle_h_rad)
        y = optimal_distance * math.cos(angle_v_rad) * math.sin(angle_h_rad)
        z = optimal_distance * math.sin(angle_v_rad)

        # Adjust based on object center
        center = bbox.get('center', [0, 0, 0])
        camera_pos = [
            x + center[0],
            y + center[1],
            z + center[2]
        ]

        print(f"Calculated optimal camera position: {camera_pos}")
        print(f"Object dimensions: {dims}")
        print(
            f"Max dimension: {max_dim:.2f}mm, Distance: {optimal_distance:.2f}mm")

        return camera_pos

    @staticmethod
    def get_camera_presets(measurements: Dict[str, Any]) -> Dict[str, List[float]]:
        """Get multiple camera preset positions for different views"""
        if not measurements.get('available', False):
            return {
                "isometric": [200, 200, 200],
                "front": [300, 0, 0],
                "side": [0, 300, 0],
                "top": [0, 0, 300]
            }

        dims = measurements['dimensions']
        center = measurements['bounding_box'].get('center', [0, 0, 0])
        max_dim = max(dims['length'], dims['width'], dims['height'])
        distance = max(max_dim * 3.5, 100)

        return {
            "isometric": [
                distance * 0.7 + center[0],
                distance * 0.7 + center[1],
                distance * 0.5 + center[2]
            ],
            "front": [distance + center[0], center[1], center[2]],
            "side": [center[0], distance + center[1], center[2]],
            "top": [center[0], center[1], distance + center[2]],
            "bottom": [center[0], center[1], -distance + center[2]]
        }


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
    """Enhanced OpenSCAD chat with smart camera and auto-rotation"""

    def __init__(self, model="gpt-4o", force_instructions=False):
        self.model = model
        self.force_instructions = force_instructions
        self.agent = None
        self.current_image = None
        self.current_code = None
        self.current_3d_model = None
        self.current_measurements = {}
        self.current_camera_position = [200, 200, 200]
        self.conversation_history = []
        self.system_prompt = None
        self.client = None
        self.session_context = None
        self.session = None
        self.stl_processor = STLProcessor()
        self.camera_calculator = SmartCameraCalculator()
        
        # Supported models configuration
        self.supported_models = {
            # OpenAI models
            "gpt-4o": {"provider": "openai", "model": "gpt-4o", "display": "GPT-4o"},
            "gpt-4o-mini": {"provider": "openai", "model": "gpt-4o-mini", "display": "GPT-4o Mini"},
            "gpt-4-turbo": {"provider": "openai", "model": "gpt-4-turbo", "display": "GPT-4 Turbo"},
            
            # Anthropic Claude 4 models (latest)
            "claude-4-sonnet": {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "display": "Claude 4 Sonnet"},
            "claude-4-opus": {"provider": "anthropic", "model": "claude-opus-4-20250514", "display": "Claude 4 Opus"},
        }

    def _create_llm(self):
        """Create the appropriate LLM based on the selected model"""
        # Get model configuration
        if self.model in self.supported_models:
            model_config = self.supported_models[self.model]
            provider = model_config["provider"]
            model_name = model_config["model"]
        else:
            # Default to OpenAI if model not recognized
            print(f"⚠️ Model '{self.model}' not recognized, defaulting to gpt-4o")
            provider = "openai"
            model_name = "gpt-4o"

        # Create LLM based on provider
        if provider == "anthropic":
            print(f"🤖 Initializing Claude model: {model_name}")
            return ChatAnthropic(
                model=model_name,
                # temperature=0.7,
                max_tokens=4096
            )
        else:  # OpenAI
            print(f"🤖 Initializing OpenAI model: {model_name}")
            return ChatOpenAI(
                model=model_name,
                #temperature=0.7
            )

    def _load_system_prompt(self, force_instructions: bool = False) -> str:
        """Load system prompt from XML or instructions.txt file"""
        import xml.etree.ElementTree as ET
        import re
        
        # If forced to use instructions.txt or XML file doesn't exist, try instructions.txt first
        if force_instructions:
            print("🔄 Force using instructions.txt as requested")
            return self._load_fallback_instructions()
        
        system_prompt_path = Path("system_prompt.xml")
        
        if not system_prompt_path.exists():
            print(f"❌ System prompt XML file not found: {system_prompt_path}")
            print("🔄 Falling back to instructions.txt...")
            return self._load_fallback_instructions()
        
        try:
            # First, try XML parsing
            xml_content = system_prompt_path.read_text(encoding='utf-8')
            
            # Parse XML and extract content from <SYSTEM_PROMPT> tags
            root = ET.fromstring(xml_content)
            
            # The root element IS the SYSTEM_PROMPT tag
            if root.tag == 'SYSTEM_PROMPT':
                # Get the inner text content, preserving formatting
                system_prompt_text = ET.tostring(root, encoding='unicode', method='text')
                print(f"✅ Loaded advanced system prompt from XML ({len(system_prompt_text)} characters)")
                return system_prompt_text.strip()
            else:
                print(f"❌ Expected <SYSTEM_PROMPT> root tag, found: {root.tag}")
                raise ValueError(f"Expected SYSTEM_PROMPT root tag, found: {root.tag}")
                
        except ET.ParseError as e:
            print(f"❌ XML parsing failed: {e}")
            print("🔄 Trying text-based extraction from XML file...")
            return self._load_xml_as_text(system_prompt_path)
        except Exception as e:
            print(f"❌ Error loading XML system prompt: {e}")
            print("🔄 Trying text-based extraction from XML file...")
            return self._load_xml_as_text(system_prompt_path)

    def _load_xml_as_text(self, xml_path: Path) -> str:
        """Fallback: Extract content between <SYSTEM_PROMPT> tags using text processing"""
        try:
            content = xml_path.read_text(encoding='utf-8')
            
            # Use regex to extract content between <SYSTEM_PROMPT> and </SYSTEM_PROMPT> tags
            import re
            pattern = r'<SYSTEM_PROMPT>\s*(.*?)\s*</SYSTEM_PROMPT>'
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                extracted_content = match.group(1).strip()
                print(f"✅ Extracted system prompt using text processing ({len(extracted_content)} characters)")
                return extracted_content
            else:
                print("❌ Could not find <SYSTEM_PROMPT> tags in XML file")
                print("🔄 Falling back to instructions.txt...")
                return self._load_fallback_instructions()
                
        except Exception as e:
            print(f"❌ Text-based XML extraction failed: {e}")
            print("🔄 Falling back to instructions.txt...")
            return self._load_fallback_instructions()

    def _load_fallback_instructions(self) -> str:
        """Fallback to instructions.txt if XML loading fails"""
        try:
            instructions_path = Path("instructions.txt")
            prompt = instructions_path.read_text()
            print(f"✅ Loaded fallback system prompt from {instructions_path}")
            return prompt
        except FileNotFoundError:
            print("❌ Instructions.txt also not found, using basic fallback")
            return self._get_fallback_prompt()

    def _get_fallback_prompt(self) -> str:
        """Basic fallback system prompt"""
        return "You are a helpful OpenSCAD design assistant. Help users create 3D objects using OpenSCAD code."

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

        # Load system prompt from XML file (or instructions.txt if specified)
        self.system_prompt = self._load_system_prompt(force_instructions=self.force_instructions)

        # Create LLM based on model selection
        llm = self._create_llm()

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

        return "✅ Ready with smart camera positioning and auto-rotation!"

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
        self.current_camera_position = [200, 200, 200]

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
        """Process 3D output files (STL) and generate optimized models with smart camera"""
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

            # Extract measurements first
            measurements = self.stl_processor.extract_measurements(latest_stl)

            # Calculate optimal camera position
            optimal_camera = self.camera_calculator.calculate_optimal_camera_position(
                measurements)
            self.current_camera_position = optimal_camera

            # Convert STL to GLB for better web performance
            optimized_model = self.stl_processor.convert_stl_to_glb(
                latest_stl, optimize=True)

            self.current_3d_model = str(
                optimized_model) if optimized_model else None
            self.current_measurements = measurements

            print(f"✅ 3D model processed: {self.current_3d_model}")
            print(f"📸 Camera positioned at: {self.current_camera_position}")
            return True

        print("⚠️ No STL files found")
        return False

    def _process_image_content(self, content) -> bool:
        """Process various image content formats and set self.current_image"""
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

    async def chat(self, message: str, history: List) -> Tuple[List, Optional[str], str, Dict, str]:
        """Process chat message and return updated outputs including camera info"""
        if not self.agent:
            new_message = {"role": "assistant",
                           "content": "❌ Not initialized!"}
            return history + [{"role": "user", "content": message}, new_message], None, "", {}, ""

        # Clear previous outputs
        self._clear_current_outputs()

        # Add user message to history if not already there
        user_msg = {"role": "user", "content": message}
        thinking_msg = {"role": "assistant",
                        "content": "🤔 Thinking... (generating 3D model with smart camera)"}

        if not (history and len(history) > 0 and history[-1].get("content") == message and "🤔 Thinking..." in str(history[-1].get("content", ""))):
            history = history + [user_msg, thinking_msg]

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
                # Update the last message with the actual response
                history[-1] = {"role": "assistant", "content": ai_content}
            else:
                history[-1] = {"role": "assistant",
                               "content": "❌ No response generated"}

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
            history[-1] = {"role": "assistant",
                           "content": f"❌ Error: {str(e)}"}

        return (
            history,
            self.current_3d_model,
            self.current_code or "",
            self.current_measurements,
        )


def create_enhanced_app(default_model="gpt-4o", force_instructions=False):
    """Create enhanced Gradio app with smart camera and auto-rotation"""
    chat_assistant = Enhanced3DOpenSCADChat(model=default_model, force_instructions=force_instructions)

    with gr.Blocks(title="OpenSCAD Assistant", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🤖 OpenSCAD Design Assistant")
        gr.Markdown(
            "Chat naturally about 3D design with AI models from OpenAI and Anthropic")

        # Status indicator
        status = gr.Markdown("⏳ Initializing MCP server...")

        with gr.Row():
            # Chat interface
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    height=900, show_label=False, type='messages')
                msg = gr.Textbox(
                    placeholder="Try: 'Create a phone stand'",
                    show_label=False
                )
                with gr.Row():
                    send_btn = gr.Button("Send", variant="primary")
                    clear_btn = gr.Button("Clear Chat", variant="secondary")

            # Enhanced preview panel
            with gr.Column(scale=2):
                with gr.Tabs():
                    # Enhanced 3D Model Tab with smart camera
                    with gr.TabItem("🎯 Smart 3D Viewer"):
                        # Gradio native Model3D with dynamic camera positioning
                        model_3d = gr.Model3D(
                            label="3D Model (Auto-adjusting camera)",
                            height=600,
                            display_mode="solid",
                            # Will be updated dynamically
                            camera_position=[200, 200, 200]
                        )

                    # 2D Preview Tab (fallback)
                    with gr.TabItem("🖼️ 2D Preview"):
                        preview_2d = gr.Image(label="2D Preview", height=400)

                # Enhanced measurements panel with camera info
                with gr.Accordion("📏 Measurements & Camera Info", open=False):
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
            """Handle user messages with smart 3D processing"""
            if not message:
                return "", history, None, "", None, "No measurements available", ""

            # Process the message
            updated_history, model_3d_path, code, measurements = await chat_assistant.chat(message, history)

            # Create enhanced measurements display
            measurements_text = "No measurements available"
            if measurements.get('available', False):
                measurements_text = chat_assistant.stl_processor.create_measurement_summary(
                    measurements)

            # Update Model3D with smart camera position
            updated_model_3d = gr.Model3D(
                value=model_3d_path,
                camera_position=chat_assistant.current_camera_position,
                display_mode="solid",
                height=400
            ) if model_3d_path else None

            return (
                "",  # Clear input
                updated_history,  # Updated chat history
                updated_model_3d,  # 3D model with smart camera
                chat_assistant.current_image,  # 2D preview image
                measurements_text,  # Enhanced measurements with camera info
                code  # Generated code
            )

        def clear_chat():
            """Clear conversation and outputs"""
            chat_assistant.reset_conversation()
            return [], None, None, None, "No measurements available", ""

        async def cleanup():
            """Clean up resources"""
            await chat_assistant.cleanup()

        # Wire up events
        app.load(startup, outputs=status)

        # Message handling with enhanced outputs
        msg.submit(
            handle_message,
            [msg, chatbot],
            [msg, chatbot, model_3d,
                preview_2d, measurements_display, code_view]
        )
        send_btn.click(
            handle_message,
            [msg, chatbot],
            [msg, chatbot, model_3d,
                preview_2d, measurements_display, code_view]
        )

        clear_btn.click(
            clear_chat,
            outputs=[chatbot, model_3d,
                     preview_2d, measurements_display, code_view]
        )

        # Cleanup on app close
        app.unload(cleanup)

        # Enhanced example prompts showcasing smart camera features
        gr.Examples(
            examples=[
                "Create a small phone stand",
                "Make a large gear with 50 teeth", 
                "Design a tall pencil holder that's 120mm high",
                "Build a tiny bearing that's only 10mm diameter",
                "Create a wide platform that's 200mm x 100mm x 5mm",
                "Design a spiral staircase with parametric steps",
                "Make a customizable box with rounded corners"
            ],
            inputs=msg
        )

    return app


# Main execution
if __name__ == "__main__":
    import os

    parser = argparse.ArgumentParser(description="OpenSCAD 3D Assistant")
    parser.add_argument('--model', type=str, default="claude-4-sonnet",
                        help="Model to use (default: claude-4-sonnet)")
    parser.add_argument('--prompt-source', type=str, choices=['xml', 'instructions'], default='xml',
                        help="Source for system prompt: 'xml' for system_prompt.xml, 'instructions' for instructions.txt (default: xml)")
    args = parser.parse_args()
    selected_model = args.model
    force_instructions = (args.prompt_source == 'instructions')

    # Check for at least one API key
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not openai_key and not anthropic_key:
        print("❌ Please set at least one of OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables.")
        exit(1)

    # Check for required dependencies
    if not TRIMESH_AVAILABLE:
        print("⚠️ For full 3D functionality, install: pip install trimesh")

    print(f"🚀 Starting Smart 3D OpenSCAD Chat with Model: {selected_model}")
    print(f"📝 Using prompt source: {args.prompt_source}")
    app = create_enhanced_app(default_model=selected_model, force_instructions=force_instructions)
    app.launch(server_port=7861)
