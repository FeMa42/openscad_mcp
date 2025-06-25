#!/usr/bin/env python3
"""
Enhanced OpenSCAD MCP Server with API-Based Embeddings Support
"""

import os
import sys
import time
import uuid
import base64
import asyncio
import subprocess
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict
from PIL import Image as PILImage
from io import BytesIO

from fastmcp import FastMCP, Image


# Import the printing pipeline
try:
    from printing_pipeline import (
        generate_and_print_gcode,
        print_gcode_file
    )
    PRINTING_AVAILABLE = True
except ImportError as e:
    PRINTING_AVAILABLE = False
    print(f"Warning: Printing pipeline not available: {e}")
    print("Save the G-code generation implementation as printing_pipeline.py to enable printing features")


# API-based embeddings imports
try:
    from langchain_openai import OpenAIEmbeddings
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: langchain-openai not installed. Install with: pip install langchain-openai")

# Fallback to local embeddings if API not available
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    LOCAL_EMBEDDINGS_AVAILABLE = True
except ImportError:
    LOCAL_EMBEDDINGS_AVAILABLE = False
    print("Warning: langchain-huggingface not available")

from langchain_community.vectorstores import FAISS

# Configure logging to stderr ONLY
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("OpenSCAD Server")

# Global variables
db = None
retriever = None
generation_id = str(uuid.uuid4())

# Configuration
OPENSCAD_EXECUTABLE = os.environ.get('OPENSCAD_EXECUTABLE', 'openscad')
OUTPUT_DIR = os.environ.get('OPENSCAD_OUTPUT_DIR', 'scad_output')
FAISS_INDEX_PATH = os.environ.get(
    'FAISS_INDEX_PATH', 'faiss_index_api_v1')  # Updated default path
OPENSCAD_LIBRARY_PATH = os.environ.get(
    'OPENSCAD_USER_LIBRARY_PATH',
    str(Path.home() / "Documents" / "OpenSCAD" / "libraries")
)
OPENSCAD_INFO_DIR = os.environ.get(
    'OPENSCAD_INFO_DIR', 'openscad_info')

# Embedding configuration
EMBEDDING_PROVIDER = os.environ.get(
    'EMBEDDING_PROVIDER', 'openai')  # 'openai', 'local', or 'auto'
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_EMBEDDING_MODEL = os.environ.get(
    'OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')

# Configuration for library configs directory
LIBRARY_CONFIGS_DIR = os.environ.get(
    'LIBRARY_CONFIGS_DIR', 'library_configs')

# Dynamic library loading from JSON configs
def load_library_configs() -> Dict[str, Dict]:
    """Load library configurations from JSON files"""
    configs = {}
    config_dir = Path(LIBRARY_CONFIGS_DIR)
    
    if not config_dir.exists():
        logger.warning(f"Library configs directory not found: {config_dir}")
        return configs
    
    # Load all JSON files from the configs directory
    for json_file in config_dir.glob("*.json"):
        try:
            import json
            with open(json_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # Validate required fields
            required_fields = ['name', 'description', 'main_files', 'usage']
            if all(field in config for field in required_fields):
                library_name = config['name']
                configs[library_name] = config
                logger.info(f"Loaded library config: {library_name}")
            else:
                logger.warning(f"Invalid config file {json_file}: missing required fields")
                
        except Exception as e:
            logger.error(f"Error loading config file {json_file}: {e}")
    
    return configs

# Load library configurations from JSON files
AVAILABLE_LIBRARIES = load_library_configs()


class EmbeddingManager:
    """Manages different embedding providers"""

    @staticmethod
    def create_openai_embeddings(api_key: str = None, model: str = "text-embedding-3-small"):
        """Create OpenAI embeddings"""
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI embeddings not available. Install: pip install langchain-openai")

        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key

        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

        return OpenAIEmbeddings(
            model=model,
            show_progress_bar=False  # Disable for server usage
        )

    @staticmethod
    def create_lightweight_local_embeddings():
        """Create lightweight local embeddings as fallback"""
        if not LOCAL_EMBEDDINGS_AVAILABLE:
            raise ImportError(
                "Local embeddings not available. Install: pip install sentence-transformers")

        return HuggingFaceEmbeddings(
            model_name="Salesforce/SFR-Embedding-2_R",  # BAAI/bge-base-en-v1.5
            model_kwargs={'device': 'mps'},
            encode_kwargs={'normalize_embeddings': True}
        )

    @staticmethod
    def get_embeddings_model(provider: str = 'auto', api_key: str = None, model: str = None):
        """Get the appropriate embeddings model"""

        if provider == 'openai' or (provider == 'auto' and OPENAI_AVAILABLE and OPENAI_API_KEY):
            try:
                model_name = model or OPENAI_EMBEDDING_MODEL
                logger.info(f"Using OpenAI embeddings: {model_name}")
                return EmbeddingManager.create_openai_embeddings(api_key, model_name)
            except Exception as e:
                logger.warning(f"Failed to create OpenAI embeddings: {e}")
                if provider == 'openai':  # If explicitly requested OpenAI, fail
                    raise

        if provider == 'local' or provider == 'auto':
            try:
                logger.info("Using lightweight local embeddings")
                return EmbeddingManager.create_lightweight_local_embeddings()
            except Exception as e:
                logger.error(f"Failed to create local embeddings: {e}")
                if provider == 'local':  # If explicitly requested local, fail
                    raise

        raise RuntimeError(f"No embeddings available for provider: {provider}")


def init_knowledge_base():
    """Initialize the knowledge base with API-based embeddings"""
    global db, retriever
    try:
        logger.info("Loading OpenSCAD knowledge base...")
        logger.info(f"FAISS index path: {FAISS_INDEX_PATH}")
        logger.info(f"Embedding provider: {EMBEDDING_PROVIDER}")

        # Create embeddings model
        embeddings = EmbeddingManager.get_embeddings_model(
            provider=EMBEDDING_PROVIDER,
            api_key=OPENAI_API_KEY,
            model=OPENAI_EMBEDDING_MODEL
        )

        # Load the FAISS index
        if not Path(FAISS_INDEX_PATH).exists():
            logger.error(f"FAISS index not found at: {FAISS_INDEX_PATH}")
            logger.info(
                "Please build the knowledge base first using the updated build_knowledge_base.py")
            return

        db = FAISS.load_local(
            FAISS_INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )

        # Increased k for better results
        retriever = db.as_retriever(search_kwargs={'k': 5})
        logger.info("Knowledge base loaded successfully!")

        # Test the retriever
        test_results = retriever.invoke("OpenSCAD cube")
        logger.info(
            f"Knowledge base test successful - found {len(test_results)} results")

    except Exception as e:
        logger.warning(f"Knowledge base not loaded: {e}")
        logger.info("The documentation search feature will not be available")


def detect_available_libraries() -> Dict[str, Dict]:
    """Detect which libraries are actually installed"""
    available = {}
    lib_path = Path(OPENSCAD_LIBRARY_PATH)

    if not lib_path.exists():
        logger.warning(f"OpenSCAD library path not found: {lib_path}")
        return available

    for lib_name, lib_info in AVAILABLE_LIBRARIES.items():
        lib_dir = lib_path / lib_name
        if lib_dir.exists() and lib_dir.is_dir():
            # Check if main files exist
            main_files_found = []
            for main_file in lib_info["main_files"]:
                if (lib_dir / main_file).exists():
                    main_files_found.append(main_file)

            if main_files_found:
                available[lib_name] = {
                    **lib_info,
                    "path": str(lib_dir),
                    "found_files": main_files_found
                }
                logger.info(f"Found library: {lib_name} at {lib_dir}")

    # Also detect libraries that exist physically but don't have configs
    for item in lib_path.iterdir():
        if item.is_dir() and item.name not in available:
            logger.info(f"Found unconfigured library: {item.name} (no JSON config found)")
            # Add basic info for unconfigured libraries
            available[item.name] = {
                "name": item.name,
                "description": f"Library {item.name} (no configuration available)",
                "main_files": ["*.scad"],
                "usage": f"// {item.name} usage:\n// use <{item.name}/filename.scad>\n// (Check library documentation for specific usage)",
                "common_modules": ["Check library documentation"],
                "path": str(item),
                "found_files": [f.name for f in item.glob("*.scad")][:5],  # Limit to first 5 files
                "unconfigured": True
            }

    return available

# Initialize available libraries
INSTALLED_LIBRARIES = detect_available_libraries()

# Tool: Search documentation
@mcp.tool()
def openscad_doc_search(query: str) -> str:
    """
    Search the OpenSCAD documentation for relevant information.
    
    Use this tool to find information about OpenSCAD commands, techniques,
    best practices, and examples from the documentation.
    
    Args:
        query: Search query (e.g., "how to create rounded corners", "boolean operations")
    
    Returns:
        Relevant documentation snippets and examples
    """
    if not retriever:
        return "Documentation search is not available. Knowledge base failed to load."

    try:
        # Search for relevant documents
        results = retriever.invoke(query)

        if not results:
            return f"No relevant documentation found for: {query}"

        # Format results
        response = f"Found {len(results)} relevant documentation entries for '{query}':\n\n"

        for i, doc in enumerate(results, 1):
            content = doc.page_content.strip()
            source = doc.metadata.get('filename', 'Unknown source')
            file_type = doc.metadata.get('file_type', 'unknown')

            # Truncate very long content
            if len(content) > 500:
                content = content[:500] + "..."

            response += f"## Result {i} (from {source}, {file_type})\n"
            response += f"{content}\n\n"
            response += "-" * 50 + "\n\n"

        return response

    except Exception as e:
        logger.error(f"Error during documentation search: {e}")
        return f"Error searching documentation: {str(e)}"


# Tool: List available libraries
@mcp.tool()
def list_openscad_libraries() -> str:
    """
    List all available OpenSCAD libraries and their usage.
    
    Returns information about installed libraries including
    how to include them in OpenSCAD code.
    """
    if not INSTALLED_LIBRARIES:
        return f"No OpenSCAD libraries found in: {OPENSCAD_LIBRARY_PATH}\n\nTo install libraries, place them in this directory."

    result = f"Available OpenSCAD Libraries (in {OPENSCAD_LIBRARY_PATH}):\n\n"
    
    # Separate configured and unconfigured libraries
    configured_libs = {k: v for k, v in INSTALLED_LIBRARIES.items() if not v.get('unconfigured', False)}
    unconfigured_libs = {k: v for k, v in INSTALLED_LIBRARIES.items() if v.get('unconfigured', False)}

    # Show configured libraries first
    if configured_libs:
        result += "## 📚 Configured Libraries (with JSON configs)\n\n"
        for lib_name, lib_info in configured_libs.items():
            result += f"### {lib_name}\n"
            result += f"{lib_info['description']}\n\n"
            
            # Add documentation URL if available
            if 'documentation_url' in lib_info:
                result += f"**Documentation:** {lib_info['documentation_url']}\n\n"
            
            # Add license info if available
            if 'license' in lib_info:
                result += f"**License:** {lib_info['license']}\n\n"
                
            result += f"**Usage:**\n```openscad\n{lib_info['usage'].strip()}\n```\n\n"
            
            if lib_info.get('common_modules'):
                result += f"**Common modules:** {', '.join(lib_info['common_modules'])}\n\n"
            
            result += f"**Available files:** {', '.join(lib_info['found_files'])}\n\n"
            result += "-" * 50 + "\n\n"

    # Show unconfigured libraries
    if unconfigured_libs:
        result += "## ⚠️  Unconfigured Libraries (missing JSON configs)\n\n"
        result += "These libraries are installed but don't have configuration files.\n"
        result += f"Add JSON configs in `{LIBRARY_CONFIGS_DIR}/` to get better usage information.\n\n"
        
        for lib_name, lib_info in unconfigured_libs.items():
            result += f"### {lib_name}\n"
            result += f"**Available files:** {', '.join(lib_info['found_files'])}\n"
            result += f"**Usage:** Check library documentation for specific usage\n\n"

    result += f"\n💡 **Tip:** Add new library configs in `{LIBRARY_CONFIGS_DIR}/library_name.json` to get detailed usage information!\n"
    
    return result


def validate_camera_params(camera_str: str) -> str:
    """
    Validate and format camera parameters.
    
    Accepts either:
    - "translate_x,y,z,rot_x,y,z,dist" (7 values)
    - "eye_x,y,z,center_x,y,z" (6 values)
    """
    try:
        # Remove any whitespace and split by comma
        params = [float(x.strip()) for x in camera_str.split(',')]

        if len(params) == 7:
            # translate_x,y,z,rot_x,y,z,dist format
            logger.info("Using translate/rotate camera format")
            return ','.join(map(str, params))
        elif len(params) == 6:
            # eye_x,y,z,center_x,y,z format
            logger.info("Using eye/center camera format")
            return ','.join(map(str, params))
        else:
            raise ValueError(
                f"Camera parameters must have 6 or 7 values, got {len(params)}")

    except ValueError as e:
        raise ValueError(
            f"Invalid camera parameters: {camera_str}. Error: {e}")


# Enhanced render tool that can auto-detect library usage
@mcp.tool()
def render_scad(code: str, iteration: int = 0, auto_fix_libraries: bool = True, camera: Optional[str] = None) -> Image:
    """
    Render OpenSCAD code and return the rendered image.
    
    Can automatically detect library usage and helps to add proper include paths.
    The code should follow the OpenSCAD best practices and include quality settings like $fa=1; $fs=0.4;
    Check the `get_instructions()` tool for more information. Very useful 
    for getting a good overview on how to use this MCP server.
    
    Args:
        code: The OpenSCAD code to render
        iteration: The iteration number (default: 0)
        auto_fix_libraries: Automatically fix library include paths (default: True)
        camera: Camera parameters in format "translate_x,y,z,rot_x,y,z,dist" or "eye_x,y,z,center_x,y,z" (default: None, leave None for default camera)
    
    Returns:
        Rendered PNG image of the 3D model
    """
    try:
        # Auto-fix library paths if needed
        if auto_fix_libraries:
            code = fix_library_includes(code)

        # Create directories
        output_dir = Path(OUTPUT_DIR) / generation_id / str(iteration)
        output_dir.mkdir(parents=True, exist_ok=True)

        scad_file = output_dir / "output.scad"
        png_file = output_dir / "output.png"
        stl_file = output_dir / "output.stl"

        # Write SCAD code
        scad_file.write_text(code)
        logger.debug(f"Wrote SCAD file: {scad_file}")

        # Helper function to check for OpenSCAD errors in stderr
        def check_openscad_errors(stderr_output: str, operation: str) -> None:
            """Check stderr for OpenSCAD errors and raise exception if found"""
            if not stderr_output:
                return
                
            # Common OpenSCAD error patterns
            error_patterns = [
                "ERROR:",
                "Assertion.*failed:",
                "Can't open library",
                "Can't open file",
                "Parse error",
                "Lexical error", 
                "syntax error",
                "WARNING: Object may not be a valid 2-manifold",
                "CGAL error"
            ]
            
            # Check for error patterns
            for pattern in error_patterns:
                if re.search(pattern, stderr_output, re.IGNORECASE):
                    # Extract the specific error message
                    error_lines = [line.strip() for line in stderr_output.split('\n') 
                                 if line.strip() and any(re.search(p, line, re.IGNORECASE) for p in error_patterns)]
                    main_error = error_lines[0] if error_lines else stderr_output.strip()
                    
                    raise Exception(f"OpenSCAD {operation} failed with error: {main_error}")

        # First, create STL file and check for errors
        logger.info("Creating STL file...")
        stl_result = subprocess.run(
            [OPENSCAD_EXECUTABLE, '-o', str(stl_file), str(scad_file)],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Check STL generation errors
        if stl_result.returncode != 0:
            error_msg = stl_result.stderr if stl_result.stderr else stl_result.stdout
            logger.error(f"STL generation failed with exit code {stl_result.returncode}: {error_msg}")
            raise Exception(f"STL generation failed: {error_msg}")
        
        # Check STL stderr for errors even if exit code is 0
        if stl_result.stderr:
            logger.info(f"STL generation stderr: {stl_result.stderr}")
            check_openscad_errors(stl_result.stderr, "STL generation")
            
        # Verify STL file was actually created
        if not stl_file.exists():
            raise Exception(f"STL file was not created at {stl_file}. Check your OpenSCAD code for errors.")
        else:
            logger.info(f"✅ STL file created successfully: {stl_file}")
        
        # Now create PNG render
        logger.info("Creating PNG render...")
        cmd = [
            OPENSCAD_EXECUTABLE,
            '-o', str(png_file),
            str(scad_file)
        ]

        # Add camera parameters if provided
        if camera:
            validated_camera = validate_camera_params(camera)
            cmd.extend(['--camera', validated_camera])
            logger.info(f"Using camera parameters: {validated_camera}")

        png_result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Check PNG generation errors  
        if png_result.returncode != 0:
            error_msg = png_result.stderr if png_result.stderr else png_result.stdout
            logger.error(f"PNG rendering failed with exit code {png_result.returncode}: {error_msg}")

            # Check if it's a library issue
            if "Can't open library" in error_msg or "Can't open file" in error_msg:
                libraries_info = list_openscad_libraries()
                raise Exception(
                    f"Library error. Available libraries:\n{libraries_info}\n\nOriginal error: {error_msg}")

            raise Exception(f"PNG rendering failed: {error_msg}")
        
        # Check PNG stderr for errors even if exit code is 0 
        if png_result.stderr:
            logger.info(f"PNG generation stderr: {png_result.stderr}")
            check_openscad_errors(png_result.stderr, "PNG rendering")
        
        # Log stdout/stderr for debugging
        if png_result.stdout:
            logger.info(f"OpenSCAD stdout: {png_result.stdout}")

        # Verify PNG file was created
        if not png_file.exists():
            raise Exception(f"PNG file was not created at {png_file}. Rendering may have failed silently.")

        # Process and return the image
        with PILImage.open(png_file) as img:
            # Convert to RGB
            if img.mode in ('RGBA', 'LA'):
                background = PILImage.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Resize if too large
            buffer = BytesIO()
            img.thumbnail((1024, 1024), PILImage.Resampling.LANCZOS)
            img.save(buffer, format='PNG', optimize=True)
            image_data = buffer.getvalue()

            logger.info(f"✅ Rendering successful: {img.size[0]}x{img.size[1]} pixels, {len(image_data)} bytes")
            return Image(data=image_data, format="png")

    except Exception as e:
        logger.error(f"❌ Error during rendering: {str(e)}")
        raise


def fix_library_includes(code: str) -> str:
    """Fix library include/use statements to use correct paths"""
    lines = code.split('\n')
    fixed_lines = []

    for line in lines:
        # Fix BOSL includes
        if 'include <BOSL/' in line or 'use <BOSL/' in line:
            # Already correct format
            fixed_lines.append(line)
        elif 'include <bosl/' in line:
            # Fix lowercase
            fixed_lines.append(line.replace(
                'include <bosl/', 'include <BOSL/'))
        elif 'use <bosl/' in line:
            fixed_lines.append(line.replace('use <bosl/', 'use <BOSL/'))
        elif ('transforms.scad' in line or 'shapes.scad' in line or
              'constants.scad' in line or 'masks.scad' in line) and 'BOSL' not in line:
            # Add BOSL prefix if missing
            if 'include <' in line:
                fixed = line.replace('include <', 'include <BOSL/')
            elif 'use <' in line:
                fixed = line.replace('use <', 'use <BOSL/')
            else:
                fixed = line
            fixed_lines.append(fixed)
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines)


# Enhanced instructions resource that includes library info
# @mcp.resource("openscad://instructions")
@mcp.tool()
def get_instructions() -> str:
    """OpenSCAD best practices and guidelines with library information.
    Check the `get_instructions()` tool for more information. Very useful 
    for getting a good overview on how to use this MCP server.
    """
    instructions_path = Path(OPENSCAD_INFO_DIR) / "instructions.txt"
    base_instructions = ""

    if instructions_path.exists():
        base_instructions = instructions_path.read_text()

    # Append library information
    library_section = "\n\n## Available Libraries\n\n"

    if INSTALLED_LIBRARIES:
        library_section += "The following libraries are installed and available:\n\n"
        for lib_name, lib_info in INSTALLED_LIBRARIES.items():
            library_section += f"### {lib_name}\n"
            library_section += f"{lib_info['description']}\n"
            library_section += f"```openscad\n{lib_info['usage'].strip()}\n```\n\n"
    else:
        library_section += f"No additional libraries found. Install libraries in: {OPENSCAD_LIBRARY_PATH}\n"

    library_section += "\nUse the `list_openscad_libraries()` tool for detailed library information.\n"
    library_section += "\nUse the `openscad_doc_search()` tool to search documentation for specific topics.\n"

    return base_instructions + library_section


# Resource for BOSL-specific examples
# @mcp.resource("openscad://examples/bosl")
@mcp.tool()
def get_bosl_examples() -> str:
    """BOSL library examples"""
    if "BOSL" not in INSTALLED_LIBRARIES:
        return "BOSL library not installed. Install it in: " + OPENSCAD_LIBRARY_PATH

    bosl_instructions_path = Path(OPENSCAD_INFO_DIR) / "bosl_instructions.txt"
    if bosl_instructions_path.exists():
        return bosl_instructions_path.read_text()
    else:
        return "BOSL library not installed. Install it in: " + OPENSCAD_LIBRARY_PATH


@mcp.tool()
def get_gear_parameter() -> str:
    """OpenSCAD Parameterizable Gears Library Reference and parameter examples for DIN gears"""

    gears_library_path = Path(OPENSCAD_INFO_DIR) / "gears_library.txt"
    if gears_library_path.exists():
        text = ""
        for line in gears_library_path.read_text().split("\n"):
            if line.startswith("{"):
                text += line + "\n"
            else:
                text += line + "\n"
        return text
    else:
        return "Instructions for gears not found. Add it in: " + OPENSCAD_INFO_DIR + "/gears_library.txt"


@mcp.tool()
def get_gear_generation_instructions() -> str:
    """Detailed instructions for gear generation."""

    gears_instructions_path = Path(
        OPENSCAD_INFO_DIR) / "gears_instructions.txt"
    if gears_instructions_path.exists():
        text = ""
        for line in gears_instructions_path.read_text().split("\n"):
            if line.startswith("{"):
                text += line + "\n"
            else:
                text += line + "\n"
        return text
    else:
        return "Instructions for gears not found. Add it in: " + OPENSCAD_INFO_DIR + "/gears_instructions.txt"


@mcp.tool()
async def generate_gcode(
    radius_threshold: float = 50.0,
    inner_density: int = 15,
    outer_density: int = 60,
    print_quality: str = "quality",
    auto_start_print: bool = False,
    printer_settings: str = "PLA_default"
) -> str:
    """
    Generate G-code with variable density optimization for 3D printing.
    
    Also implements the reinforcement requirement: "Verstärke alles außerhalb von 50 mm Radius 
    mit einem stabileren Material" by using variable infill density.
    
    Args:
        radius_threshold: Radius in mm where reinforcement starts (default: 50mm)
        inner_density: Infill percentage inside radius (5-30%, default: 15%)
        outer_density: Infill percentage outside radius (30-80%, default: 60%)
        print_quality: Quality preset ("fast", "quality", "strong")
        auto_start_print: Whether to automatically start printing via OctoPrint
        printer_settings: Material preset ("PLA_default", "PETG_strong", "ABS_temp")
    
    Returns:
        Status message with G-code generation results and file paths
    """

    if not PRINTING_AVAILABLE:
        return "❌ Printing pipeline not available. Please install the printing_pipeline module.\n\n" \
               "1. Install PrusaSlicer: brew install --cask prusaslicer\n" \
               "2. Restart the MCP server"

    # Find the most recent STL file from rendering
    output_dir = Path(OUTPUT_DIR) / generation_id
    stl_files = list(output_dir.rglob("*.stl"))

    if not stl_files:
        return "❌ No STL file found. Please render an OpenSCAD model first using render_scad()."

    # Use the most recent STL
    latest_stl = max(stl_files, key=lambda p: p.stat().st_mtime)

    # Create G-code output directory
    gcode_output_dir = output_dir / "gcode"
    gcode_output_dir.mkdir(exist_ok=True)

    # Material-specific settings
    material_settings = {
        "PLA_default": {
            "temperature": 215,
            "bed_temperature": 60,
            "retraction_length": 0.8
        },
        "PETG_strong": {
            "temperature": 240,
            "bed_temperature": 80,
            "retraction_length": 1.0,
            "print_speed": 35  # Slower for better adhesion
        },
        "ABS_temp": {
            "temperature": 250,
            "bed_temperature": 100,
            "retraction_length": 1.2,
            "enclosure_temp": 40  # Prusa Core One has enclosure
        }
    }

    custom_settings = material_settings.get(
        printer_settings, material_settings["PLA_default"])

    try:
        # Generate G-code with variable density
        result = await generate_and_print_gcode(
            stl_path=str(latest_stl),
            output_dir=str(gcode_output_dir),
            strengthen_radius=radius_threshold,
            inner_density=inner_density,
            outer_density=outer_density,
            profile=print_quality,
            auto_print=auto_start_print
        )

        # Add material info to result
        result += f"\n🧪 Material settings: {printer_settings}\n"
        result += f"   - Extruder: {custom_settings.get('temperature', 215)}°C\n"
        result += f"   - Bed: {custom_settings.get('bed_temperature', 60)}°C\n"

        if auto_start_print:
            result += f"\n🎯 Variable density strategy applied:\n"
            result += f"   - Weak areas (center, r<{radius_threshold*0.9}mm): {inner_density}% infill\n"
            result += f"   - Strong areas (edges, r>{radius_threshold*1.1}mm): {outer_density}% infill\n"
            result += f"   - Material saved: ~{((outer_density-inner_density)/outer_density)*100:.1f}% less plastic in center\n"

        return result

    except Exception as e:
        logger.error(f"G-code generation failed: {e}")
        return f"❌ G-code generation failed: {str(e)}"


@mcp.tool()
async def print_last_gcode() -> str:
    """
    Call to print the last generated G-code. 
    """
    if not PRINTING_AVAILABLE:
        return "❌ Printing pipeline not available. Please install the printing_pipeline module.\n\n" \
               "1. Install PrusaSlicer: brew install --cask prusaslicer\n" \
               "2. Restart the MCP server"
    # find the most recent G-code file
    gcode_output_dir = Path(OUTPUT_DIR) / generation_id / "gcode"
    gcode_files = list(gcode_output_dir.rglob("*.gcode"))
    if not gcode_files:
        return "❌ No G-code file found. Please generate a G-code file first using generate_gcode()."
    latest_gcode = max(gcode_files, key=lambda p: p.stat().st_mtime)
    # print the G-code file
    if print_gcode_file(latest_gcode):
        return "G-Code successfully send to printer. Print job started."
    else:
        return "❌ Failed to print G-code file. Please try again."


@mcp.tool()
def get_printing_presets() -> str:
    """
    Get available printing presets and variable density examples.
    
    Returns:
        Information about available presets and usage examples
    """
    return """
🎯 **Available Print Quality Presets:**

**fast** - Quick prototypes (0.3mm layers)
- Speed: 60mm/s, Infill: 15%, Supports: No
- Use for: Concept models, fit tests

**quality** - Balanced printing (0.2mm layers) 
- Speed: 45mm/s, Infill: 20%, Supports: Yes
- Use for: General purpose, functional parts

**strong** - Maximum strength (0.25mm layers)
- Speed: 40mm/s, Infill: 40%, Supports: Yes  
- Use for: Mechanical parts, gears, stress parts

🧪 **Material Presets:**
- **PLA_default**: 215°C/60°C, general purpose
- **PETG_strong**: 240°C/80°C, chemical resistance
- **ABS_temp**: 250°C/100°C, high temperature parts

🎯 **Variable Density Examples:**

```python
# Light center, strong edges (gear teeth)
generate_gcode(radius_threshold=50, inner_density=10, outer_density=70)

# Minimal material usage with edge reinforcement  
generate_gcode(radius_threshold=30, inner_density=5, outer_density=50)

# Heavy duty with gradient reinforcement
generate_gcode(radius_threshold=40, inner_density=25, outer_density=80)
```

**Reinforcement Use Case Implementation:**
"Verstärke alles außerhalb von 50 mm Radius mit einem stabileren Material"
→ `generate_gcode(radius_threshold=50, inner_density=15, outer_density=60)`

This creates:
- Weak center (0-45mm): 15% infill → saves material, fast printing
- Transition zone (45-55mm): gradient 15%→60% → smooth stress distribution  
- Strong edges (55mm+): 60% infill → reinforced against tooth breakage
"""

def main():
    """Run FastMCP server"""
    logger.info(
        "Starting Enhanced OpenSCAD FastMCP Server with API Embeddings...")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Library path: {OPENSCAD_LIBRARY_PATH}")
    logger.info(f"FAISS index path: {FAISS_INDEX_PATH}")
    logger.info(f"Embedding provider: {EMBEDDING_PROVIDER}")
    logger.info(f"Found libraries: {list(INSTALLED_LIBRARIES.keys())}")

    # Initialize knowledge base
    init_knowledge_base()

    logger.info("Available tools:")
    logger.info("  - render_scad: Render OpenSCAD code with auto library detection")
    logger.info("  - list_openscad_libraries: List installed libraries")
    logger.info("  - openscad_doc_search: Search documentation (API-powered)")
    logger.info("  - generate_gcode: Generate G-code with variable density optimization, and start print job automatically")
    logger.info("  - print_last_gcode: Print the last generated G-code")

    mcp.run()


if __name__ == "__main__":
    main()
