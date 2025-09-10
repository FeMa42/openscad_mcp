# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an OpenSCAD Model Collaborative Programming (MCP) system that provides an intelligent assistant for 3D modeling with OpenSCAD and 3D printing workflows. The system integrates with Claude/ChatGPT via MCP (Model Context Protocol) to enable natural language 3D design conversations.

### Core Architecture

The project consists of two main components:

1. **MCP Server** (`openscad_fastmcp_server.py`): FastMCP-based server that provides OpenSCAD tools, knowledge retrieval, and 3D printing pipeline integration
2. **Gradio Chat App** (`gradio_app/app.py`): Web-based chat interface with 3D visualization, smart camera positioning, and auto-rotation features

### Key Directories

- `gradio_app/`: Web interface with chat, 3D viewer, and model configuration
- `openscad_documentation/`: Comprehensive OpenSCAD library documentation and tutorials
- `library_configs/`: JSON configs for OpenSCAD libraries (BOSL, BOLTS, etc.)
- `openscad_info/`: Text-based reference materials and instructions
- `output/`: Generated 3D models, renders, and G-code files
- `archiv/`: Legacy code and experimental features

## Development Commands

### Running the Application

```bash
# Start the main Gradio chat application
cd gradio_app
python app.py

# Or with specific AI model
python app.py --model gpt-4o
python app.py --model claude-4-opus
```

### Testing

```bash
# Test the MCP server directly
python test_fastmcp_server.py

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
# Install all dependencies
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
- API keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`

## Code Architecture

### MCP Server Tools
The server provides these main tool categories:
- **OpenSCAD Operations**: Code generation, rendering, STL export
- **Knowledge Retrieval**: FAISS-based semantic search of documentation
- **3D Printing**: G-code generation via PrusaSlicer integration
- **Library Management**: Dynamic loading of OpenSCAD library configs

### Chat Application Features
- **LangGraph Agent**: React-style agent for multi-step reasoning
- **Smart Camera System**: Automatic optimal camera positioning for 3D models
- **Auto-rotation**: Turntable effect for better model visualization
- **Multi-model Support**: OpenAI GPT and Anthropic Claude models

### Knowledge Base
Uses FAISS vector store with:
- OpenSCAD documentation (manuals, tutorials, libraries)
- Semantic search for contextual help
- API-based embeddings (OpenAI) with local fallback (HuggingFace)

## Important File Patterns

- `*.scad`: OpenSCAD 3D model files
- `*.stl`: 3D mesh files for printing
- `*.gcode`: 3D printer instruction files
- `library_configs/*.json`: OpenSCAD library configurations
- `output/*/`: Generated files organized by session UUID

## Testing Approach

Run `test_fastmcp_server.py` to verify:
- OpenSCAD rendering functionality
- Knowledge base retrieval
- File generation and cleanup

No formal test framework is used - testing is done through direct script execution and manual verification of outputs.