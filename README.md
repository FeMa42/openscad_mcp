# openscad_mcp

OpenSCAD Model Collaborative Programming (MCP) - An intelligent assistant for 3D modeling with OpenSCAD and 3D printing workflow.

## Prerequisites

Before installing this application, you'll need to install the following software dependencies and set up your environment.

### 1. Install Python (Required)

This application requires Python 3.8 or higher. 

**Check if Python is installed:**
```bash
python3 --version
# or
python --version
```

**Install Python if needed:**

### 2. Install OpenSCAD

OpenSCAD is the core 3D modeling software required for this application.

#### Windows:
1. **Download the installer:**
   - Go to [OpenSCAD Downloads](https://openscad.org/downloads.html)
   - Download "OpenSCAD x86 (64-bit) - exe installer" (or 32-bit if needed)
   - File size: ~20MB

2. **Install:**
   - Run the downloaded `.exe` file
   - Follow the installation wizard
   - Default installation path: `C:\Program Files\OpenSCAD\`

3. **Find the executable path:**
   - Typical location: `C:\Program Files\OpenSCAD\openscad.exe`
   - Or: `C:\Program Files (x86)\OpenSCAD\openscad.exe`

#### macOS:
1. **Option A - Homebrew (Recommended):**
   ```bash
   brew install openscad
   ```
   - Executable location: `/opt/homebrew/bin/openscad` (Apple Silicon) or `/usr/local/bin/openscad` (Intel)

2. **Option B - Manual Download:**
   - Download the `.dmg` file from [OpenSCAD Downloads](https://openscad.org/downloads.html)
   - Open the `.dmg` file and drag OpenSCAD to Applications folder
   - Executable location: `/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD`

#### Linux:

**Ubuntu/Debian:**
```bash
# Official repositories (recommended for most users)
sudo apt update
sudo apt install openscad

# Executable location: /usr/bin/openscad
```

**Linux Instructions:** [OpenSCAD Linux](https://openscad.org/downloads.html#linux)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/FeMa42/openscad_mcp.git
cd openscad_mcp
```

### 2. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**If you encounter dependency conflicts:**
```bash
# Try upgrading pip first
pip install --upgrade pip

# Or install with --no-deps flag for specific packages
pip install --no-deps package_name
```

### 4. Configure Application Paths

You need to update the configuration file with the correct paths to your installed software.

**Edit `gradio_app/config.json`:**

The configuration file should look like this, but with paths updated for your system:

```json
{
    "mcpServers": {
        "openscad": {
            "command": "/path/to/your/python",
            "args": [
                "/path/to/your/openscad_mcp/openscad_fastmcp_server.py"
            ],
            "transport": "stdio",
            "env": {
                "PYTHONUNBUFFERED": "1",
                "OPENSCAD_OUTPUT_DIR": "/path/to/your/openscad_mcp/output",
                "OPENSCAD_INFO_DIR": "/path/to/your/openscad_mcp/openscad_info",
                "FAISS_INDEX_PATH": "/path/to/your/openscad_mcp/faiss_index_modern",
                "OPENSCAD_USER_LIBRARY_PATH": "/path/to/openscad/libraries",
                "OPENSCAD_EXECUTABLE": "/path/to/openscad/executable",
                "EMBEDDING_PROVIDER": "local",
                "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
                "PRUSASLICER_PATH": "/path/to/prusaslicer/executable"
            }
        }
    }
}
```

**Update the following paths in the config file:**

#### For Windows:
```json
{
    "mcpServers": {
        "openscad": {
            "command": "C:\\path\\to\\your\\venv\\Scripts\\python.exe",
            "args": [
                "C:\\path\\to\\your\\openscad_mcp\\openscad_fastmcp_server.py"
            ],
            "transport": "stdio",
            "env": {
                "PYTHONUNBUFFERED": "1",
                "OPENSCAD_OUTPUT_DIR": "C:\\path\\to\\your\\openscad_mcp\\output",
                "OPENSCAD_INFO_DIR": "C:\\path\\to\\your\\openscad_mcp\\openscad_info",
                "FAISS_INDEX_PATH": "C:\\path\\to\\your\\openscad_mcp\\faiss_index_modern",
                "OPENSCAD_USER_LIBRARY_PATH": "C:\\Users\\YourName\\Documents\\OpenSCAD\\libraries",
                "OPENSCAD_EXECUTABLE": "C:\\Program Files\\OpenSCAD\\openscad.exe",
                "EMBEDDING_PROVIDER": "local",
                "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
                "PRUSASLICER_PATH": "C:\\Program Files\\PrusaSlicer\\prusa-slicer.exe"
            }
        }
    }
}
```

#### For macOS:
```json
{
    "mcpServers": {
        "openscad": {
            "command": "/Users/yourusername/openscad_mcp/venv/bin/python",
            "args": [
                "/Users/yourusername/openscad_mcp/openscad_fastmcp_server.py"
            ],
            "transport": "stdio",
            "env": {
                "PYTHONUNBUFFERED": "1",
                "OPENSCAD_OUTPUT_DIR": "/Users/yourusername/openscad_mcp/output",
                "OPENSCAD_INFO_DIR": "/Users/yourusername/openscad_mcp/openscad_info",
                "FAISS_INDEX_PATH": "/Users/yourusername/openscad_mcp/faiss_index_modern",
                "OPENSCAD_USER_LIBRARY_PATH": "/Users/yourusername/Documents/OpenSCAD/libraries",
                "OPENSCAD_EXECUTABLE": "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
                "EMBEDDING_PROVIDER": "local",
                "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
                "PRUSASLICER_PATH": "/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer"
            }
        }
    }
}
```

#### For Linux:
```json
{
    "mcpServers": {
        "openscad": {
            "command": "/home/yourusername/openscad_mcp/venv/bin/python",
            "args": [
                "/home/yourusername/openscad_mcp/openscad_fastmcp_server.py"
            ],
            "transport": "stdio",
            "env": {
                "PYTHONUNBUFFERED": "1",
                "OPENSCAD_OUTPUT_DIR": "/home/yourusername/openscad_mcp/output",
                "OPENSCAD_INFO_DIR": "/home/yourusername/openscad_mcp/openscad_info",
                "FAISS_INDEX_PATH": "/home/yourusername/openscad_mcp/faiss_index_modern",
                "OPENSCAD_USER_LIBRARY_PATH": "/home/yourusername/.local/share/OpenSCAD/libraries",
                "OPENSCAD_EXECUTABLE": "/usr/bin/openscad",
                "EMBEDDING_PROVIDER": "local",
                "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
                "PRUSASLICER_PATH": "flatpak run com.prusa3d.PrusaSlicer"
            }
        }
    }
}
```

**Finding your exact paths:**

- **Current directory:** Run `pwd` (macOS/Linux) or `cd` (Windows)
- **Python path:** Run `which python` (macOS/Linux) or `where python` (Windows)
- **OpenSCAD path:** Run `which openscad` (macOS/Linux) or `where openscad` (Windows)

### 5. Set Up API Keys

The application supports multiple AI models. You need at least one API key:

#### Option A: Environment Variables (Recommended)
```bash
# For OpenAI models (gpt-5, gpt-5-mini, gpt-oss)
export OPENAI_API_KEY="your-openai-api-key-here"

# For Anthropic Claude models (claude-4-sonnet, claude-4-opus, etc.)
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"

# For Google Gemini models (gemini-2.5-pro, gemini-3.1-pro, etc.)
export GOOGLE_API_KEY="your-google-api-key-here"

# For OpenRouter models (Qwen3, Llama, DeepSeek, etc.)
export OPENROUTER_API_KEY="your-openrouter-api-key-here"
```

**Make it permanent:**

**Windows:**
- Add to System Environment Variables via System Properties > Advanced > Environment Variables

**macOS/Linux:**
```bash
# Add to your shell profile (~/.bashrc, ~/.zshrc, ~/.bash_profile)
echo 'export OPENAI_API_KEY="your-key-here"' >> ~/.bashrc
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.bashrc
echo 'export GOOGLE_API_KEY="your-key-here"' >> ~/.bashrc
echo 'export OPENROUTER_API_KEY="your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

#### Option B: .env File
Create a `.env` file in the project root:
```
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
GOOGLE_API_KEY=your-google-api-key-here
OPENROUTER_API_KEY=your-openrouter-api-key-here
```

**Getting API Keys:**
- **OpenAI:** [platform.openai.com](https://platform.openai.com/api-keys)
- **Anthropic:** [console.anthropic.com](https://console.anthropic.com/)
- **Google:** [aistudio.google.com](https://aistudio.google.com/apikey)
- **OpenRouter:** [openrouter.ai](https://openrouter.ai/keys)

## Running the Application

### 1. Activate Virtual Environment (if not already active)

```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 2. Start the Application

```bash
# Navigate to the application directory
cd gradio_app

# Run with default model (Claude Sonnet 4)
python app.py

# Or specify a different model
python app.py --model claude-4-sonnet
python app.py --model gemini-2.5-pro
python app.py --model qwen3-coder
```

**Available models by provider:**
- **OpenAI**: `gpt-5`, `gpt-5-mini`, `gpt-oss`
- **Anthropic**: `claude-4-sonnet` (default), `claude-4-opus`, `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`
- **Google**: `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-3.1-pro`, `gemini-3.1-flash`, `gemini-3.1-flash-lite`
- **OpenRouter**: `qwen3-coder`, `qwen3-coder-free`, `qwen3`, `gemini-3.1-or`, `llama-3-70b`, `deepseek-coder`, `codestral`, etc.

### 3. Access the Web Interface

1. The application will start and display a URL in the terminal (typically `http://localhost:7861/`)
2. Open this URL in your web browser
3. Wait for the application to load completely (this may take a few seconds on first startup)
