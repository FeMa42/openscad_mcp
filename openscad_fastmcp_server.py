#!/usr/bin/env python3
"""
Enhanced OpenSCAD MCP Server with Library Support
"""

import os
import sys
import uuid
import base64
import subprocess
import logging
from pathlib import Path
from typing import Optional, List, Dict
from PIL import Image as PILImage
from io import BytesIO

from fastmcp import FastMCP, Image
from langchain_huggingface import HuggingFaceEmbeddings
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
FAISS_INDEX_PATH = os.environ.get('FAISS_INDEX_PATH', 'faiss_index')
OPENSCAD_LIBRARY_PATH = os.environ.get(
    'OPENSCAD_USER_LIBRARY_PATH',
    str(Path.home() / "Documents" / "OpenSCAD" / "libraries")
)

# Library configurations
AVAILABLE_LIBRARIES = {
    "BOSL": {
        "description": "Belfry OpenSCAD Library - tools, shapes, and helpers",
        "main_files": ["constants.scad", "transforms.scad", "shapes.scad", "masks.scad"],
        "usage": """
// Basic BOSL usage:
include <BOSL/constants.scad>
use <BOSL/transforms.scad>
use <BOSL/shapes.scad>

// Then use BOSL functions like:
cuboid([20,20,30], fillet=5);
xcyl(l=20, d=4);
""",
        "common_modules": [
            "transforms: up(), down(), left(), right(), xrot(), yrot(), zrot()",
            "shapes: cuboid(), prismoid(), xcyl(), ycyl(), zcyl()",
            "masks: chamfer_mask_z(), fillet_mask_z()"
        ]
    },
    "BOLTS": {
        "description": "BOLTS is an Open Library for Technical Specifications.",
        "main_files": ["BOLTS.scad"],
        "usage": """
// BOLTS usage:
include <BOLTS/BOLTS.scad>
DIN931();
""",
        "common_modules": []
    },
    "constructive": {
        "description": "Constructive Library - a library of shapes and primitives",
        "main_files": ["constructive-compiled.scad"],
        "usage": """
// Constructive usage:
use <constructive/constructive-compiled.scad>
box(size=10);
""",
        "common_modules": []
    },
    "pathbuilder": {
        "description": "Pathbuilder Library - Pathbuilder is a tool for openSCAD that make the creation of complex 2D shapes easier with a syntax similar to the one used for svg path.",
        "main_files": ["pathbuilder.scad"],
        "usage": """
// Pathbuilder usage:
include <pathbuilder/pathbuilder.scad>
svgShape("m 0 0chamfer8h20fillet2v20fillet10h20v-10fillet2l35 20fillet2l-35 20fillet2v-10h-40fillet30", $fn=32);
""",
        "common_modules": []
    },
    "parameterizable_gears": {
        "description": "Parameterizable Gears Library - a library of gears with parameters",
        "main_files": ["gears.scad"],
        "usage": """
// Parameterizable Gears usage:
use <parameterizable_gears/gears.scad>

zahnstange(modul=0.5, laenge=50, hoehe=4, breite=5,
           eingriffswinkel=20, schraegungswinkel=20);
""",
        "common_modules": []
    },
    "UB": {
        "description": "This library is a full 3Dprinting workflow solution for openSCAD v.21 and above.",
        "main_files": ["ub.scad"],
        "usage": """
// UB usage:
include<UB/ub.scad>//->http://v.gd/ubaer or https://github.com/UBaer21/UB.scad
/*[Hidden]*/
  useVersion=22.046;
  designVersion=1.0;

/*[Basics]*/
  vp=false;
  bed=false;
  pPos=[0,0];
  info=true;
  nozzle=.2;

/*[ Gears ]*/
z=10; // number teeth 
f=3; // teeth width divisior
modul=2; // teeth size
h=5; // height
w=30; // helical teeth skew
achse=3;// arbor

function pitchcircle(z=z)=z*modul/f;

T(printPos){ 
//gear
  CyclGetriebe(h=h,z=z,f=f,modul=modul,linear=false,w=w,achse=achse,help=true);
  %Tz(h/2)color("chartreuse")Kreis(d=pitchcircle(z),rand=.1);
// gears
T(pitchcircle(z)*2){ 
  CyclGetriebe(h=h,z=z,f=f,modul=modul,linear=false,center=false,w=w,achse=achse);
  mirror([1,0])CyclGetriebe(h=h,z=z,f=f,modul=modul,linear=false,center=false,rotZahn=-1,w=w,achse=achse);
  }
// inner teeth
T(pitchcircle(z)*4)rotate(180){ 
  CyclGetriebe(h=h,z=z*3,f=f,modul=modul,linear=false,center=false,d=pitchcircle(z*3)+modul,w=w,achse=achse);
  CyclGetriebe(h=h,z=z,f=f,modul=modul,linear=false,center=false,w=w,achse=achse);
  }
  
// rack
  T(0,-pitchcircle(z)*2){
    CyclGetriebe(h=h,z=z,f=f,modul=modul,linear=modul*2,center=false,w=w,achse=achse);
    CyclGetriebe(h=h,z=z,f=f,modul=modul,center=2,rotZahn=0,w=w,achse=achse);
  }
  
// features

  T(pitchcircle(z)*2,pitchcircle(z)+pitchcircle(z*3)/2)CyclGetriebe(h=h,z=z*3,f=f,lock=5,light=5,modul=modul,w=w,achse=achse);
}
""",
        "common_modules": []
    }
}


def init_knowledge_base():
    """Initialize the knowledge base"""
    global db, retriever
    try:
        logger.info("Loading OpenSCAD knowledge base...")
        embeddings = HuggingFaceEmbeddings(
            model_name="Salesforce/SFR-Embedding-2_R",
            model_kwargs={'device': 'cpu'}
        )
        db = FAISS.load_local(
            FAISS_INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )
        retriever = db.as_retriever(search_kwargs={'k': 3})
        logger.info("Knowledge base loaded successfully!")
    except Exception as e:
        logger.warning(f"Knowledge base not loaded: {e}")


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

    return available


# Initialize available libraries
INSTALLED_LIBRARIES = detect_available_libraries()

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

    for lib_name, lib_info in INSTALLED_LIBRARIES.items():
        result += f"## {lib_name}\n"
        result += f"{lib_info['description']}\n\n"
        result += f"**Usage:**\n```openscad\n{lib_info['usage'].strip()}\n```\n\n"
        result += f"**Common modules:** {', '.join(lib_info['common_modules'])}\n\n"
        result += f"**Available files:** {', '.join(lib_info['found_files'])}\n\n"
        result += "-" * 50 + "\n\n"

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
    
    Automatically detects library usage and adds proper include paths.
    The code should include quality settings like $fa=1; $fs=0.4;
    
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

        # Write SCAD code
        scad_file.write_text(code)
        logger.debug(f"Wrote SCAD file: {scad_file}")

        # Render with library path
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
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            logger.error(f"OpenSCAD rendering failed: {error_msg}")

            # Check if it's a library issue
            if "Can't open library" in error_msg or "Can't open file" in error_msg:
                libraries_info = list_openscad_libraries()
                raise Exception(
                    f"Library error. Available libraries:\n{libraries_info}\n\nOriginal error: {error_msg}")

            raise Exception(f"Rendering failed: {error_msg}")
        else:
            # check for stdout and stderr and log them
            logger.info(f"OpenSCAD stdout: {result.stdout}")
            logger.info(f"OpenSCAD stderr: {result.stderr}")

        if not png_file.exists():
            raise Exception("PNG file was not created")

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

            logger.info(
                f"Rendered: {img.size[0]}x{img.size[1]} pixels, {len(image_data)} bytes")
            return Image(data=image_data, format="png")

    except Exception as e:
        logger.error(f"Error during rendering: {str(e)}")
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
@mcp.resource("openscad://instructions")
def get_instructions() -> str:
    """OpenSCAD best practices and guidelines with library information"""
    instructions_path = Path("instructions.txt")
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

    return base_instructions + library_section

# Resource for BOSL-specific examples
@mcp.resource("openscad://examples/bosl")
def get_bosl_examples() -> str:
    """BOSL library examples"""
    if "BOSL" not in INSTALLED_LIBRARIES:
        return "BOSL library not installed. Install it in: " + OPENSCAD_LIBRARY_PATH

    bosl_instructions_path = Path("bosl_instructions.txt")
    if bosl_instructions_path.exists():
        return bosl_instructions_path.read_text()
    else:
        return "BOSL library not installed. Install it in: " + OPENSCAD_LIBRARY_PATH


def main():
    """Run the enhanced FastMCP server"""
    logger.info("Starting Enhanced OpenSCAD FastMCP Server...")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Library path: {OPENSCAD_LIBRARY_PATH}")
    logger.info(f"Found libraries: {list(INSTALLED_LIBRARIES.keys())}")

    init_knowledge_base()

    logger.info("Available tools:")
    logger.info("  - render_scad: Render with auto library detection")
    logger.info("  - list_openscad_libraries: List installed libraries")
    logger.info("  - openscad_doc_search: Search documentation")
    logger.info("  - validate_scad: Syntax validation")

    mcp.run()


if __name__ == "__main__":
    main()
