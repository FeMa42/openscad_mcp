# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an OpenSCAD Model Collaborative Programming (MCP) system with two purposes:

1. **Interactive 3D Modeling Assistant**: Natural language 3D design via MCP (Model Context Protocol), integrating with multiple LLM providers
2. **LLM Benchmarking Platform (GearSet Benchmark)**: Evaluates LLM capabilities on OpenSCAD gear generation tasks across difficulty levels

### Core Architecture

The project consists of two main components:

1. **MCP Server** (`openscad_fastmcp_server.py`): FastMCP-based server providing 14 tools for OpenSCAD rendering, knowledge retrieval, and 3D printing pipeline integration
2. **Gradio Chat App** (`gradio_app/app.py`): Web-based chat interface with 3D visualization, multi-view rendering, smart camera positioning, auto-rotation, and support for 4 LLM providers (OpenAI, Anthropic, Google, OpenRouter)

### Key Directories

- `gradio_app/`: Web interface with chat, 3D viewer, and model configuration
- `openscad_documentation/`: Comprehensive OpenSCAD library documentation and tutorials
- `library_configs/`: JSON configs for OpenSCAD libraries (BOSL, BOLTS, etc.)
- `openscad_info/`: Reference materials, instructions, and BOSL2 gear documentation
- `output/`: Generated 3D models, renders, and G-code files
- `archiv/`: Legacy code, benchmark plans (`benchmarkin_plan.md`), and BOSL2 migration plan

## MCP Server Tools (14 tools)

### Knowledge & Documentation (7)
- `openscad_doc_search` — FAISS semantic search of OpenSCAD documentation
- `list_openscad_libraries` — Library listing with function signatures
- `get_instructions` — System instructions for the assistant
- `get_bosl_examples` — BOSL library examples
- `get_bosl2_gear_docs` — BOSL2 gear module documentation
- `get_gear_parameter` — Gear parameter reference
- `get_gear_generation_instructions` — Step-by-step gear generation guide

### Rendering (4)
- `render_scad` — Single-view render with auto-fix and optional camera params
- `render_scad_multi` — Multi-view render (7 camera angles)
- `get_available_views` — List views from a multi-view session
- `get_view` — Retrieve a specific view image by ID

### 3D Printing (3)
- `generate_gcode` — G-code generation via PrusaSlicer
- `print_last_gcode` — Send last generated G-code to printer
- `get_printing_presets` — Available printing configurations

## Supported LLM Providers & Models

| Provider | Key | Models |
|----------|-----|--------|
| **OpenAI** | `OPENAI_API_KEY` | GPT-5, GPT-5 Mini, GPT-OSS 120B |
| **Anthropic** | `ANTHROPIC_API_KEY` | Claude Opus 4.6, Claude Sonnet 4.6, Claude Haiku 4.5, Claude 4 Sonnet (default), Claude 4 Opus |
| **Google** | `GOOGLE_API_KEY` | Gemini 2.5 Pro, Gemini 2.5 Flash, Gemini 2.5 Flash Lite, Gemini 3.1 Pro (Preview), Gemini 3.1 Flash (Preview), Gemini 3.1 Flash Lite (Preview) |
| **OpenRouter** | `OPENROUTER_API_KEY` | Gemini 3.1, Claude Sonnet/Opus 4.6, Qwen3-Coder (Next/480B/Free), Qwen3, Claude 3 Sonnet, Llama 3 70B, Codestral Mamba, DeepSeek Coder |

## GearSet Benchmark

Evaluates LLMs on OpenSCAD gear generation across 3 difficulty levels (12 prompts total). **BOSL2 is the preferred gear library** — models should use `include <BOSL2/std.scad>` and `include <BOSL2/gears.scad>`.

**Metrics**: Success Rate (SR@k), Parameter Accuracy (PA), Code Validity Rate (CVR), Aesthetic/Instruction Score (AIS), Spatial Correctness Assessment (SCA).

See `archiv/benchmarkin_plan.md` for the full benchmark specification.

## Development Commands

### Running the Application

```bash
# Start the main Gradio chat application
cd gradio_app
python app.py

# With a specific model
python app.py --model claude-4-sonnet
python app.py --model gemini-2.5-pro
python app.py --model qwen3-coder
```

### Testing

```bash
# Test the MCP server directly
python test_fastmcp_server.py

# Test multi-view rendering
python test_multiview.py

# Verify server configuration
python verify_server.py
```

### Building Knowledge Base

```bash
# Rebuild the FAISS vector database from documentation
python build_knowledge_base.py
```

### Dependencies

```bash
pip install -r requirements.txt

# For virtual environment setup
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

## Configuration

### Main Config File
`gradio_app/config.json` contains MCP server configuration with paths to:
- Python executable and MCP server script
- OpenSCAD executable path
- PrusaSlicer path for G-code generation
- Output directories and library paths
- Embedding provider settings

### Environment Variables
Key environment variables (defined in config.json env section):
- `OPENSCAD_EXECUTABLE`: Path to OpenSCAD binary
- `PRUSASLICER_PATH`: Path to PrusaSlicer for G-code generation
- `FAISS_INDEX_PATH`: Vector database location for knowledge retrieval
- `EMBEDDING_PROVIDER`: "openai", "local", or "auto"
- API keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`

## Important File Patterns

- `*.scad`: OpenSCAD 3D model files
- `*.stl`: 3D mesh files for printing
- `*.gcode`: 3D printer instruction files
- `library_configs/*.json`: OpenSCAD library configurations
- `system_prompt*.xml`: System prompt templates for the assistant
- `output/*/`: Generated files organized by session UUID

## Testing Approach

Run `test_fastmcp_server.py` to verify:
- OpenSCAD rendering functionality
- Knowledge base retrieval
- File generation and cleanup

Run `test_multiview.py` to verify multi-view rendering pipeline.

No formal test framework is used — testing is done through direct script execution and manual verification of outputs.
