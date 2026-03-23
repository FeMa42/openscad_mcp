#!/usr/bin/env python3
"""
Enhanced OpenSCAD Chat with Smart Camera Positioning, Auto-Rotation, and Web Search
Includes automatic camera adjustment, turntable rotation, and web search capabilities for optimal assistance
"""

# Fix HuggingFace tokenizer warning in multiprocessing environments
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import gradio as gr
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    logger.warning("⚠️ langchain-google-genai not available. Install with: pip install langchain-google-genai")
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import BaseTool
import base64
from PIL import Image
from io import BytesIO
from pathlib import Path
import json
import re
import tempfile
import math
import argparse
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('openscad_chat.log', encoding='utf-8')  # File output
    ]
)
logger = logging.getLogger(__name__)

# Web search imports
try:
    from langchain_tavily import TavilySearch
    from langchain_core.tools import Tool
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    logger.warning("⚠️ TavilySearch not available. Install with: pip install langchain-tavily")

# Optional: LangSmith for comprehensive tracing
try:
    import langsmith
    from langsmith import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    logger.info("💡 For advanced tracing, install LangSmith: pip install langsmith")

# 3D processing imports
try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    logger.warning("⚠️ Trimesh not available. Install with: pip install trimesh")


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

        logger.info(f"Calculated optimal camera position: {camera_pos}")
        logger.info(f"Object dimensions: {dims}")
        logger.info(
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
        """Find the most recently created STL file, preferring current generation"""
        stl_files = []
        current_time = time.time()
        
        # Only consider files modified in the last 5 minutes (300 seconds)
        max_age_seconds = 300

        for output_dir in output_dirs:
            dir_path = Path(output_dir)
            if dir_path.exists():
                for stl_file in dir_path.rglob("*.stl"):
                    # Check if file is recent enough
                    file_age = current_time - stl_file.stat().st_mtime
                    if file_age <= max_age_seconds:
                        stl_files.append(stl_file)
                    else:
                        logger.info(f"Skipping old STL file: {stl_file} (age: {file_age:.1f}s)")

        if not stl_files:
            logger.warning("⚠️ No recent STL files found (within last 5 minutes)")
            return None

        # Prefer files from generation-specific directories
        generation_files = [f for f in stl_files if any(
            part.startswith(('scad_output', 'output')) 
            for part in f.parts
        )]
        
        files_to_consider = generation_files if generation_files else stl_files

        # Return the most recently modified STL file
        latest_stl = max(files_to_consider, key=lambda p: p.stat().st_mtime)
        file_age = current_time - latest_stl.stat().st_mtime
        logger.info(f"🔍 Found latest STL: {latest_stl} (age: {file_age:.1f}s)")
        return latest_stl

    def convert_stl_to_glb(self, stl_path: Path, optimize: bool = True) -> Optional[Path]:
        """Convert STL to GLB format for better web performance"""
        if not TRIMESH_AVAILABLE:
            logger.warning("❌ Trimesh not available for STL conversion")
            return stl_path  # Return original STL

        try:
            # Load STL file
            mesh = trimesh.load(str(stl_path))

            if optimize:
                # Optimization pipeline
                logger.info(f"🔧 Original mesh: {len(mesh.faces)} faces")

                # Remove duplicate faces and vertices
                mesh.update_faces(mesh.unique_faces())
                mesh.update_faces(mesh.nondegenerate_faces())
                mesh.merge_vertices()

                # Simplify if too many faces (target max 50K for web performance)
                if len(mesh.faces) > 50000:
                    target_faces = 50000
                    mesh = mesh.simplify_quadratic_decimation(target_faces)
                    logger.info(f"🔧 Simplified to: {len(mesh.faces)} faces")

            # Export as GLB (binary glTF format - better for web)
            glb_path = self.temp_dir / f"{stl_path.stem}.glb"
            mesh.export(str(glb_path))

            logger.info(f"✅ Converted STL to GLB: {glb_path}")
            return glb_path

        except Exception as e:
            logger.error(f"❌ Failed to convert STL to GLB: {e}")
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

            logger.info(f"📏 Extracted measurements: {measurements['dimensions']}")

        except Exception as e:
            logger.error(f"❌ Failed to extract measurements: {e}")

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
            "gpt-5": {"provider": "openai", "model": "gpt-5-2025-08-07", "display": "GPT-5"},
            "gpt-5-mini": {"provider": "openai", "model": "gpt-5-mini-2025-08-07", "display": "GPT-5 Mini"},
            "gpt-oss": {"provider": "openai", "model": "gpt-oss-120b", "display": "GPT-OSS 120B"},
            
            # Anthropic Claude 4 models (latest)
            "claude-opus-4-6": {"provider": "anthropic", "model": "claude-opus-4-6", "display": "Claude Opus 4.6"},
            "claude-sonnet-4-6": {"provider": "anthropic", "model": "claude-sonnet-4-6", "display": "Claude Sonnet 4.6"},
            "claude-haiku-4-5-20251001": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001", "display": "Claude Haiku 4.5"},
            "claude-4-sonnet": {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "display": "Claude 4 Sonnet"},
            "claude-4-opus": {"provider": "anthropic", "model": "claude-opus-4-1-20250805", "display": "Claude 4 Opus"},
            
            # Google Gemini models
            "gemini-2.5-pro": {"provider": "google", "model": "gemini-2.5-pro", "display": "Gemini 2.5 Pro"},
            "gemini-2.5-flash": {"provider": "google", "model": "gemini-2.5-flash", "display": "Gemini 2.5 Flash"},
            
            # OpenRouter models
            "gemini-3.1-or": {"provider": "openrouter", "model": "google/gemini-3.1-pro-preview", "display": "Gemini 3.1 (OR)"},
            "claude-sonnet-4.6-or": {"provider": "openrouter", "model": "anthropic/claude-sonnet-4.6", "display": "Claude Sonnet 4.6 (OR)"},
            "claude-opus-4-6-or": {"provider": "openrouter", "model": "anthropic/claude-opus-4-6", "display": "Claude Opus 4.6 (OR)"},
            "qwen3-coder-next": {"provider": "openrouter", "model": "qwen/qwen3-coder-next", "display": "Qwen3-Coder Next"},
            "qwen3": {"provider": "openrouter", "model": "qwen/qwen3-235b-a22b-2507", "display": "Qwen3"},
            "qwen3-coder": {"provider": "openrouter", "model": "qwen/qwen3-coder", "display": "Qwen3-Coder 480B"},
            "qwen3-coder-free": {"provider": "openrouter", "model": "qwen/qwen3-coder:free", "display": "Qwen3-Coder (Free)"},
            "claude-3-sonnet-or": {"provider": "openrouter", "model": "anthropic/claude-3-sonnet", "display": "Claude 3 Sonnet (OR)"},
            "llama-3-70b": {"provider": "openrouter", "model": "meta-llama/llama-3-70b-instruct", "display": "Llama 3 70B"},
            "codestral": {"provider": "openrouter", "model": "mistralai/codestral-mamba", "display": "Codestral Mamba"},
            "deepseek-coder": {"provider": "openrouter", "model": "deepseek/deepseek-coder", "display": "DeepSeek Coder"},
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
            logger.warning(f"⚠️ Model '{self.model}' not recognized, defaulting to gpt-4o")
            provider = "openai"
            model_name = "gpt-5-2025-08-07"

        # Create LLM based on provider
        if provider == "anthropic":
            logger.info(f"🤖 Initializing Claude model: {model_name}")
            return ChatAnthropic(
                model=model_name,
                # temperature=0.7,
                max_tokens=4096
            )
        elif provider == "google":
            if not GOOGLE_GENAI_AVAILABLE:
                raise ImportError("Google Gemini models require: pip install langchain-google-genai")
            logger.info(f"🤖 Initializing Google Gemini model: {model_name}")
            return ChatGoogleGenerativeAI(
                model=model_name,
                # temperature=0.7,
                max_tokens=4096,
                thinking_budget=512  # Control thinking output to prevent contamination
            )
        elif provider == "openrouter":
            # OpenRouter configuration
            api_key = os.getenv('OPENROUTER_API_KEY')
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable is required for OpenRouter models")
            
            site_url = os.getenv('OPENROUTER_SITE_URL', 'http://localhost:7861')
            site_name = os.getenv('OPENROUTER_SITE_NAME', 'OpenSCAD Assistant')
            
            logger.info(f"🤖 Initializing OpenRouter model: {model_name}")
            return ChatOpenAI(
                model=model_name,
                # temperature=0.7,
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    'HTTP-Referer': site_url,
                    'X-Title': site_name,
                }
            )
        else:  # OpenAI
            logger.info(f"🤖 Initializing OpenAI model: {model_name}")
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
            logger.info("🔄 Force using instructions.txt as requested")
            return self._load_fallback_instructions()
        
        system_prompt_path = Path("system_prompt.xml")
        
        if not system_prompt_path.exists():
            logger.warning(f"❌ System prompt XML file not found: {system_prompt_path}")
            logger.info("🔄 Falling back to instructions.txt...")
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
                logger.info(f"✅ Loaded advanced system prompt from XML ({len(system_prompt_text)} characters)")
                return system_prompt_text.strip()
            else:
                logger.error(f"❌ Expected <SYSTEM_PROMPT> root tag, found: {root.tag}")
                raise ValueError(f"Expected SYSTEM_PROMPT root tag, found: {root.tag}")
                
        except ET.ParseError as e:
            logger.error(f"❌ XML parsing failed: {e}")
            logger.info("🔄 Trying text-based extraction from XML file...")
            return self._load_xml_as_text(system_prompt_path)
        except Exception as e:
            logger.error(f"❌ Error loading XML system prompt: {e}")
            logger.info("🔄 Trying text-based extraction from XML file...")
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
                logger.info(f"✅ Extracted system prompt using text processing ({len(extracted_content)} characters)")
                return extracted_content
            else:
                logger.warning("❌ Could not find <SYSTEM_PROMPT> tags in XML file")
                logger.info("🔄 Falling back to instructions.txt...")
                return self._load_fallback_instructions()
                
        except Exception as e:
            logger.error(f"❌ Text-based XML extraction failed: {e}")
            logger.info("🔄 Falling back to instructions.txt...")
            return self._load_fallback_instructions()

    def _load_fallback_instructions(self) -> str:
        """Fallback to instructions.txt if XML loading fails"""
        try:
            instructions_path = Path("instructions.txt")
            prompt = instructions_path.read_text()
            logger.info(f"✅ Loaded fallback system prompt from {instructions_path}")
            return prompt
        except FileNotFoundError:
            logger.error("❌ Instructions.txt also not found, using basic fallback")
            return self._get_fallback_prompt()

    def _get_fallback_prompt(self) -> str:
        """Basic fallback system prompt"""
        return "You are a helpful OpenSCAD design assistant. Help users create 3D objects using OpenSCAD code."

    async def initialize(self):
        """Initialize with persistent MCP session, web search, and proper system prompt setup"""
        logger.info("🚀 Starting OpenSCAD Chat initialization...")
        
        # Setup tracing based on available services
        tracing_mode = setup_tracing()
        
        # Load MCP server configuration
        with open('config.json') as f:
            config = json.load(f)
        logger.info(f"📋 Configuration loaded: {list(config.keys())}")

        # Extract servers config
        mcp_config = config.get("mcpServers", config)

        # Create MCP client
        self.client = MultiServerMCPClient(mcp_config)
        logger.info("🔌 Created MultiServerMCP client")

        # Create and maintain persistent session
        logger.info("🔌 Creating persistent MCP session...")
        self.session_context = self.client.session("openscad")
        self.session = await self.session_context.__aenter__()

        # Load tools from persistent session
        tools = await load_mcp_tools(self.session)
        logger.info(f"🔧 Loaded {len(tools)} MCP tools: {[tool.name for tool in tools]}")

        # Add web search tool if available
        web_search_tools = []
        web_search_tool = create_web_search_tool()
        if web_search_tool:
            web_search_tools.append(web_search_tool)
            logger.info("🌐 Web search enabled with TavilySearch")
        elif not os.getenv("TAVILY_API_KEY"):
            logger.warning("⚠️ TAVILY_API_KEY not set - web search disabled")
        
        # Combine all tools
        all_tools = tools + web_search_tools
        logger.info(f"🔧 Total tools available: {len(all_tools)} (MCP: {len(tools)}, Web: {len(web_search_tools)})")
        logger.info(f"🔍 Tracing mode: {tracing_mode}")

        # Store reference to session for direct access if needed
        self.mcp_session = self.session

        # Load system prompt from XML file (or instructions.txt if specified)
        logger.info("📄 Loading system prompt...")
        self.system_prompt = self._load_system_prompt(force_instructions=self.force_instructions)
        logger.info(f"📄 System prompt loaded: {len(self.system_prompt)} characters")

        # Create LLM based on model selection
        logger.info(f"🤖 Initializing LLM: {self.model}")
        llm = self._create_llm()

        # Create agent with system prompt
        def _add_system_prompt(state):
            """Add system prompt to the conversation"""
            messages = state.get("messages", [])
            if not messages or not isinstance(messages[0], SystemMessage):
                return [SystemMessage(content=self.system_prompt)] + messages
            return messages

        logger.info("🧠 Creating React agent...")
        self.agent = create_react_agent(
            llm,
            all_tools,  # Use combined tools including web search
            prompt=_add_system_prompt
        )

        # Initialize conversation history with system message
        self._initialize_conversation_history()
        logger.info("💾 Initialized conversation history")

        web_status = "with web search" if web_search_tools else "without web search"
        success_msg = f"✅ Ready with smart camera positioning, auto-rotation, and {len(all_tools)} tools ({web_status})!"
        logger.info(success_msg)
        
        return success_msg

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
                logger.info("🧹 MCP session cleaned up properly")
            except Exception as e:
                logger.error(f"❌ Error cleaning up session: {e}")

    def reset_conversation(self):
        """Reset the conversation history but keep system prompt"""
        self._initialize_conversation_history()
        self.current_image = None
        self.current_code = None
        logger.info("🔍 reset_conversation: Setting current_3d_model to None")
        self.current_3d_model = None
        self.current_measurements = {}
        self.current_camera_position = [200, 200, 200]

    def _filter_ai_thinking_content(self, value):
        """Filter out Gemini thinking content from file paths only"""
        if not isinstance(value, str):
            return value
            
        # Only filter if this looks like thinking content being used as a file path
        thinking_patterns = [
            '### CRITIQUE', '### THOUGHT', '### PLAN', '### ANALYSIS'
        ]
        
        # Only filter if it contains thinking patterns AND is being used as a file path
        if any(pattern in value for pattern in thinking_patterns):
            # If it's a long string with thinking content, it's probably not a valid file path
            if len(value) > 200:
                logger.warning(f"🧠 Filtered out AI thinking content: {repr(value[:100])}")
                return ""
            
        return value
        
    def _clear_current_outputs(self):
        """Clear current outputs to ensure fresh updates"""
        if self.current_image:
            try:
                self.current_image.close()
            except:
                pass
        self.current_image = None
        logger.info("🔍 _clear_current_outputs: Setting current_3d_model to None")
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
            logger.error(f"Error creating fresh image copy: {e}")
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
            logger.info(f"🎯 Processing 3D model: {latest_stl}")

            # Extract measurements first
            measurements = self.stl_processor.extract_measurements(latest_stl)

            # Calculate optimal camera position
            optimal_camera = self.camera_calculator.calculate_optimal_camera_position(
                measurements)
            self.current_camera_position = optimal_camera

            # Convert STL to GLB for better web performance
            optimized_model = self.stl_processor.convert_stl_to_glb(
                latest_stl, optimize=True)

            processed_model_path = str(optimized_model) if optimized_model else None
            logger.info(f"🔍 Setting current_3d_model to: {repr(processed_model_path)}")
            self.current_3d_model = processed_model_path
            self.current_measurements = measurements

            logger.info(f"✅ 3D model processed: {self.current_3d_model}")
            logger.info(f"📸 Camera positioned at: {self.current_camera_position}")
            return True

        logger.warning("⚠️ No STL files found")
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

        logger.info(f"🔍 Processing potential image content: {type(content)}")

        # 1. Handle MCP CallToolResult with ImageContent list (new MCP format)
        if isinstance(content, list) and len(content) > 0:
            first_item = content[0]
            if hasattr(first_item, 'type') and first_item.type == 'image' and hasattr(first_item, 'data'):
                try:
                    img_data = base64.b64decode(first_item.data)
                    self.current_image = self._create_fresh_image_copy(
                        img_data)
                    if self.current_image:
                        logger.info("✅ Loaded image from ImageContent")
                        return True
                except Exception as e:
                    logger.error(f"Failed to load ImageContent: {e}")

        return False

    def _extract_outputs(self, messages):
        """Extract images, code, and 3D models from tool responses"""
        logger.info(f"🔍 _extract_outputs: Processing {len(messages)} messages")

        for i, msg in enumerate(messages):
            # Check for tool calls (to get code)
            if hasattr(msg, "tool_calls"):
                for tool_call in msg.tool_calls:
                    if tool_call["name"] == "render_scad":
                        self.current_code = tool_call["args"].get("code", "")
                        logger.info(f"✅ Extracted code from tool call")

            # Check tool responses for images and errors
            if hasattr(msg, "name") and msg.name == "render_scad":
                content = msg.content
                logger.info(f"🔍 Found render_scad response with content: {type(content)}")

                # Check if the response contains an error
                if isinstance(content, str) and any(error_word in content.lower() for error_word in ["error", "failed", "exception"]):
                    logger.error(f"❌ Detected error in render_scad response: {content}")
                    # Don't try to process this as a successful render
                    return
                
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

        # Log the incoming user message
        logger.info(f"💬 User message: {message}")

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

            # Log agent invocation
            logger.info(f"🤖 Invoking agent with {len(agent_messages)} messages")

            # Invoke agent with proper message history
            response = await self.agent.ainvoke({
                "messages": agent_messages
            })

            # Log tool usage
            self._log_tool_usage(response.get("messages", []))

            # Extract AI response
            latest_ai_message = None
            for msg in reversed(response["messages"]):
                if isinstance(msg, AIMessage):
                    latest_ai_message = msg
                    break

            if latest_ai_message:
                ai_content = latest_ai_message.content
                
                # Log if Gemini thinking content is detected but don't filter chat content
                if isinstance(ai_content, str) and any(section in ai_content for section in ["### CRITIQUE", "### THOUGHT", "### PLAN"]):
                    logger.warning("🧠 Detected Gemini thinking content in response - filtering will be applied to file paths only")
                
                self.conversation_history.append(AIMessage(content=ai_content))
                # Update the last message with the actual response
                history[-1] = {"role": "assistant", "content": ai_content}
                logger.info(f"🤖 Agent response: {ai_content[:200]}...")
            else:
                history[-1] = {"role": "assistant",
                               "content": "❌ No response generated"}
                logger.warning("⚠️ No AI response generated")

            # Extract outputs from tool responses
            self._extract_outputs(response["messages"])

            # Try direct MCP call for immediate results
            if self.current_code:
                logger.info("🔧 Attempting direct MCP call for immediate OpenSCAD rendering")
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
                    error_msg = str(e)
                    logger.error(f"❌ Direct MCP call failed: {error_msg}")
                    
                    # Update the chat history to show the error to the user
                    if "OpenSCAD" in error_msg and ("failed" in error_msg or "error" in error_msg.lower()):
                        # This is an OpenSCAD-specific error, show it to the user
                        error_response = f"❌ OpenSCAD Error: {error_msg}\n\nPlease check your code and try again."
                        history[-1] = {"role": "assistant", "content": error_response}
                        logger.error(f"🔄 Updated chat history with OpenSCAD error")

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            history[-1] = {"role": "assistant", "content": error_msg}
            logger.error(f"💥 Chat processing error: {str(e)}")

        # Log final outputs
        logger.info(f"📊 Chat complete - 3D model: {'✅' if self.current_3d_model else '❌'}, "
                   f"Code: {'✅' if self.current_code else '❌'}, "
                   f"Measurements: {'✅' if self.current_measurements.get('available') else '❌'}")

        return (
            history,
            self.current_3d_model,
            self.current_code or "",
            self.current_measurements,
        )

    def _log_tool_usage(self, messages: List) -> None:
        """Log tool usage from agent messages"""
        tool_calls = []
        tool_responses = []
        
        for msg in messages:
            # Log tool calls
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get("name", "unknown")
                    tool_args = tool_call.get("args", {})
                    tool_calls.append(f"{tool_name}({list(tool_args.keys())})")
                    logger.info(f"🔧 Tool call: {tool_name} with args: {list(tool_args.keys())}")
            
            # Log tool responses
            if hasattr(msg, "name") and msg.name:
                tool_name = msg.name
                content_type = type(msg.content).__name__
                tool_responses.append(f"{tool_name}({content_type})")
                logger.info(f"📤 Tool response: {tool_name} returned {content_type}")
        
        if tool_calls:
            logger.info(f"🛠️  Total tool calls in this conversation: {', '.join(tool_calls)}")
        if tool_responses:
            logger.info(f"📨 Total tool responses: {', '.join(tool_responses)}")


def setup_tracing():
    """Setup tracing based on available services"""
    # Option 1: LangSmith (most comprehensive)
    if os.getenv("LANGCHAIN_API_KEY") and LANGSMITH_AVAILABLE:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = "OpenSCAD-Agent"
        logger.info("🔍 LangSmith tracing enabled - full tool and search logging available")
        return "langsmith"
    
    # Option 2: Basic Python logging (what we already have)
    logger.info("🔍 Using basic Python logging for tool tracking")
    return "basic"


def create_web_search_tool():
    """Create web search tool with logging based on available tracing"""
    if not TAVILY_AVAILABLE or not os.getenv("TAVILY_API_KEY"):
        return None
        
    # Create standard TavilySearch tool
    tavily_tool = TavilySearch(
        max_results=3,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=False
    )
    
    # If LangSmith is available, it will automatically trace everything
    if os.getenv("LANGCHAIN_TRACING_V2") == "true":
        logger.info("🌐 Web search with LangSmith tracing enabled")
        return tavily_tool
    
    # Otherwise, create a wrapper tool that adds logging
    search_count = 0
    
    def logged_tavily_search(query: str):
        """Wrapper function that adds logging to TavilySearch"""
        nonlocal search_count
        search_count += 1
        
        logger.info(f"🔍 WEB SEARCH #{search_count}: {query}")
        start_time = time.time()
        
        try:
            result = tavily_tool.invoke(query)
            elapsed = time.time() - start_time
            
            # Log basic search info
            if isinstance(result, dict) and 'results' in result:
                results_count = len(result['results'])
                logger.info(f"✅ Found {results_count} results in {elapsed:.2f}s")
                
                # Log top result
                if result['results']:
                    top_result = result['results'][0]
                    logger.info(f"🔗 Top result: {top_result.get('title', 'No title')}")
                    logger.info(f"🌐 URL: {top_result.get('url', 'No URL')}")
            else:
                logger.info(f"✅ Search completed in {elapsed:.2f}s")
                
            return result
            
        except Exception as e:
            logger.error(f"❌ Search failed: {str(e)}")
            raise
    
    # Create a new tool with the same interface but with logging
    from langchain_core.tools import Tool
    
    logging_tool = Tool(
        name="tavily_search_results_json",
        description=tavily_tool.description,
        func=logged_tavily_search
    )
    
    logger.info("🌐 Web search with basic logging enabled")
    return logging_tool


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
            logger.info("🎬 Starting Gradio app startup sequence...")
            result = await chat_assistant.initialize()
            logger.info(f"🎉 Startup complete: {result}")
            return result


        async def handle_message_chat_only(message, history):
            """Handle message and update only chat history (no loading on 3D/code)"""
            if not message:
                return "", history

            # Process the message
            updated_history, model_3d_path, code, measurements = await chat_assistant.chat(message, history)

            return "", updated_history

        async def update_3d_model():
            """Update 3D model separately (shows loading only when needed)"""
            model_path = chat_assistant.current_3d_model
            
            logger.info(f"🔍 update_3d_model called with: {type(model_path)} = {repr(model_path)[:200] if model_path else 'None'}")
            
            # Apply AI content filtering to prevent Gemini thinking contamination
            filtered_path = chat_assistant._filter_ai_thinking_content(model_path)
            
            if filtered_path != model_path:
                logger.error(f"❌ Gemini thinking content detected and filtered out from 3D model path")
                return None
            
            # Additional validation for file paths
            if filtered_path and isinstance(filtered_path, str):
                # Check if file exists
                from pathlib import Path
                if not Path(filtered_path).exists():
                    logger.warning(f"⚠️ 3D model file not found: {filtered_path}")
                    return None
                    
                logger.info(f"✅ Valid 3D model path being returned: {filtered_path}")
            
            logger.info(f"🔄 update_3d_model returning: {repr(filtered_path)[:100] if filtered_path else 'None'}")
            return filtered_path

        async def update_code_viewer():
            """Update code viewer separately (shows loading only when needed)"""
            return chat_assistant.current_code or ""

        async def update_measurements():
            """Update measurements separately (shows loading only when needed)"""
            if chat_assistant.current_measurements.get('available', False):
                summary = chat_assistant.stl_processor.create_measurement_summary(
                    chat_assistant.current_measurements)
                # Ensure measurements don't contain AI thinking content
                filtered_summary = chat_assistant._filter_ai_thinking_content(summary)
                return filtered_summary if filtered_summary else "No measurements available"
            return "No measurements available"

        async def update_2d_preview():
            """Update 2D preview separately (shows loading only when needed)"""
            return chat_assistant.current_image

        def clear_chat():
            """Clear conversation and outputs"""
            logger.info("🧹 Clearing chat conversation and outputs")
            chat_assistant.reset_conversation()
            return [], None, None, "No measurements available", ""

        async def cleanup():
            """Clean up resources"""
            logger.info("🧹 Starting cleanup process...")
            await chat_assistant.cleanup()
            logger.info("✅ Cleanup complete")

        # Wire up events
        app.load(startup, outputs=status)

        # Optimized message handling with controlled loading states
        # Main chat handler - updates chat history immediately (no loading)
        msg.submit(
            handle_message_chat_only,
            [msg, chatbot],
            [msg, chatbot],
            queue=False  # No loading state for chat updates
        ).then(
            update_3d_model,
            outputs=model_3d
        ).then(
            update_code_viewer,
            outputs=code_view
        ).then(
            update_measurements,
            outputs=measurements_display
        ).then(
            update_2d_preview,
            outputs=preview_2d
        )

        # Send button - same optimized flow
        send_btn.click(
            handle_message_chat_only,
            [msg, chatbot],
            [msg, chatbot],
            queue=False  # No loading state for chat updates
        ).then(
            update_3d_model,
            outputs=model_3d
        ).then(
            update_code_viewer,
            outputs=code_view
        ).then(
            update_measurements,
            outputs=measurements_display
        ).then(
            update_2d_preview,
            outputs=preview_2d
        )

        clear_btn.click(
            clear_chat,
            outputs=[chatbot, model_3d,
                     preview_2d, measurements_display, code_view],
            queue=False  # No loading for clear operation
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
                        help="Model to use (default: claude-4-sonnet). Available models include: gpt-5, claude-4-sonnet, qwen3-coder, qwen3-coder-free, llama-3-70b, codestral, deepseek-coder")
    parser.add_argument('--prompt-source', type=str, choices=['xml', 'instructions'], default='xml',
                        help="Source for system prompt: 'xml' for system_prompt.xml, 'instructions' for instructions.txt (default: xml)")
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
                        help="Logging level (default: INFO)")
    args = parser.parse_args()
    
    selected_model = args.model
    force_instructions = (args.prompt_source == 'instructions')

    # Set logging level based on argument
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    logger.info("🚀 OpenSCAD 3D Assistant Starting Up")
    logger.info(f"🤖 Selected model: {selected_model}")
    logger.info(f"📝 Prompt source: {args.prompt_source}")
    logger.info(f"📊 Log level: {args.log_level}")

    # Check for at least one API key
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    langsmith_key = os.getenv("LANGCHAIN_API_KEY")
    
    if not openai_key and not anthropic_key and not google_key and not openrouter_key:
        logger.error("❌ Please set at least one of OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, or OPENROUTER_API_KEY environment variables.")
        logger.info("   For OpenRouter models (including qwen/qwen3-coder): export OPENROUTER_API_KEY=your_key")
        exit(1)
    
    # Log available services
    services = []
    if openai_key:
        services.append("OpenAI")
    if anthropic_key:
        services.append("Anthropic")
    if google_key:
        services.append("Google Gemini")
    if openrouter_key:
        services.append("OpenRouter")
    if tavily_key:
        services.append("Tavily Search")
    if langsmith_key:
        services.append("LangSmith Tracing")
    
    logger.info(f"🔑 Available services: {', '.join(services)}")

    # Log tracing recommendations
    if not langsmith_key:
        logger.info("💡 For advanced tool tracing, set LANGCHAIN_API_KEY for LangSmith")
        logger.info("   Sign up at: https://smith.langchain.com/")
    
    # Check for required dependencies
    if not TRIMESH_AVAILABLE:
        logger.warning("⚠️ For full 3D functionality, install: pip install trimesh")
    else:
        logger.info("✅ Trimesh available for 3D processing")
        
    if not TAVILY_AVAILABLE:
        logger.warning("⚠️ For web search functionality, install: pip install langchain-tavily")
    else:
        logger.info("✅ TavilySearch available for web search")
        
    if not LANGSMITH_AVAILABLE:
        logger.info("💡 For advanced tracing, install: pip install langsmith")
    else:
        logger.info("✅ LangSmith available for advanced tracing")

    logger.info(f"🌐 Starting Smart 3D OpenSCAD Chat with Model: {selected_model}")
    logger.info(f"📝 Using prompt source: {args.prompt_source}")
    
    try:
        app = create_enhanced_app(default_model=selected_model, force_instructions=force_instructions)
        logger.info("🎯 Gradio app created successfully")
        logger.info("🌐 Launching on http://localhost:7861")
        app.launch(server_port=7861)
    except Exception as e:
        logger.error(f"💥 Failed to start application: {str(e)}")
        raise
