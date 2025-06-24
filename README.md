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

3. **Option C - MacPorts:**
   ```bash
   sudo port install openscad
   ```

#### Linux:

**Ubuntu/Debian:**
```bash
# Official repositories (recommended for most users)
sudo apt update
sudo apt install openscad

# Executable location: /usr/bin/openscad
```

**Fedora:**
```bash
sudo dnf install openscad
# For MCAD library:
sudo dnf install openscad-MCAD
```

**Arch Linux:**
```bash
sudo pacman -S openscad
```

**Universal Linux (AppImage):**
```bash
# Download AppImage from https://openscad.org/downloads.html
wget https://files.openscad.org/snapshots/OpenSCAD-x86_64.AppImage
chmod +x OpenSCAD-x86_64.AppImage
./OpenSCAD-x86_64.AppImage
```

**Alternative Package Managers:**
```bash
# Snap
sudo snap install openscad

# Flatpak
flatpak install flathub org.openscad.OpenSCAD
```

### 3. Install PrusaSlicer

PrusaSlicer is required for G-code generation and 3D printing workflow.

#### Windows:
1. **Download:**
   - Go to [PrusaSlicer Downloads](https://www.prusa3d.com/page/prusaslicer_424/) or [GitHub Releases](https://github.com/prusa3d/PrusaSlicer/releases)
   - Download the latest Windows version (e.g., `PrusaSlicer-2.9.0+win64.zip`)
   - File size: ~80-90MB

2. **Install Option A - Installer:**
   - If downloading the `.exe` installer, run it and follow the setup wizard
   - Default location: `C:\Program Files\PrusaSlicer\`

3. **Install Option B - Portable:**
   - If downloading the `.zip` file, extract to a folder (e.g., `C:\PrusaSlicer\`)
   - Run `prusa-slicer.exe` from the extracted folder

4. **Find executable path:**
   - Installer: `C:\Program Files\PrusaSlicer\prusa-slicer.exe`
   - Portable: `C:\PrusaSlicer\prusa-slicer.exe` (or your chosen folder)

#### macOS:
1. **Download:**
   - Download the `.dmg` file from [PrusaSlicer Downloads](https://www.prusa3d.com/page/prusaslicer_424/)
   - File size: ~100MB

2. **Install:**
   - Open the `.dmg` file
   - Drag PrusaSlicer to the Applications folder
   - If you see a security warning, go to System Preferences > Security & Privacy > Click "Open Anyway"

3. **Executable location:**
   - `/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer`

#### Linux:
**Flatpak (Recommended for most distributions):**
```bash
# Install Flatpak if not already installed
sudo apt install flatpak  # Ubuntu/Debian
sudo dnf install flatpak  # Fedora

# Add Flathub repository
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

# Install PrusaSlicer
flatpak install flathub com.prusa3d.PrusaSlicer

# Run PrusaSlicer
flatpak run com.prusa3d.PrusaSlicer

# Executable for scripts: flatpak run com.prusa3d.PrusaSlicer
```

**AppImage (Alternative):**
```bash
# Download from GitHub releases
wget https://github.com/prusa3d/PrusaSlicer/releases/download/version_2.9.0/PrusaSlicer-2.9.0+linux-x64.AppImage
chmod +x PrusaSlicer-2.9.0+linux-x64.AppImage
./PrusaSlicer-2.9.0+linux-x64.AppImage
```

**Without superuser privileges:**
```bash
# Install Flatpak for current user only
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub com.prusa3d.PrusaSlicer
```

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
# For OpenAI models (gpt-4o, gpt-4o-mini, gpt-4-turbo)
export OPENAI_API_KEY="your-openai-api-key-here"

# For Anthropic Claude models (claude-4-sonnet, claude-4-opus)
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
```

**Make it permanent:**

**Windows:**
- Add to System Environment Variables via System Properties > Advanced > Environment Variables

**macOS/Linux:**
```bash
# Add to your shell profile (~/.bashrc, ~/.zshrc, ~/.bash_profile)
echo 'export OPENAI_API_KEY="your-key-here"' >> ~/.bashrc
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

#### Option B: .env File
Create a `.env` file in the project root:
```
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

**Getting API Keys:**
- **OpenAI:** [platform.openai.com](https://platform.openai.com/api-keys)
- **Anthropic:** [console.anthropic.com](https://console.anthropic.com/)

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
python app.py --model gpt-4o
python app.py --model claude-4-opus
python app.py --model gpt-4o-mini
```

**Available models:**
- `claude-4-sonnet` (default) - Most capable for 3D modeling
- `claude-4-opus` - Maximum capability but more expensive
- `gpt-4o` - OpenAI's latest
- `gpt-4o-mini` - Faster, more economical

### 3. Access the Web Interface

1. The application will start and display a URL in the terminal (typically `http://localhost:7861/`)
2. Open this URL in your web browser
3. Wait for the application to load completely (this may take 30-60 seconds on first startup)

## Troubleshooting

### Common Issues

**1. "Command not found" errors:**
- Make sure you've activated the virtual environment
- Check that all paths in `config.json` are correct and use full absolute paths
- On Windows, use backslashes (`\`) or double backslashes (`\\`) in JSON

**2. "Permission denied" errors:**
- On macOS/Linux, make sure executable files have proper permissions:
  ```bash
  chmod +x /path/to/openscad
  chmod +x /path/to/prusaslicer
  ```

**3. "API key not found" errors:**
- Verify that environment variables are set: `echo $OPENAI_API_KEY`
- Check that you have sufficient API credits
- Try restarting your terminal after setting environment variables

**4. "Module not found" errors:**
- Make sure virtual environment is activated
- Try reinstalling dependencies: `pip install -r requirements.txt --force-reinstall`

**5. Application won't start:**
- Check Python version: `python --version` (must be 3.8+)
- Try running with verbose output: `python app.py --verbose`
- Check system requirements (minimum 4GB RAM recommended)

**6. OpenSCAD/PrusaSlicer not found:**
- Verify installation by running the software manually first
- Check the exact executable path and update `config.json`
- On Linux with Flatpak, use the full command: `flatpak run com.prusa3d.PrusaSlicer`

## Features

- **AI-Powered 3D Modeling:** Chat naturally about 3D designs with advanced AI models
- **Real-time Visualization:** See your designs rendered in 2D and 3D as you build them
- **Smart Camera Positioning:** Automatic optimal camera angles for 3D model viewing
- **Parametric Design:** Create customizable, parameter-driven models
- **3D Printing Integration:** Generate G-code and manage printing workflows
- **Comprehensive Libraries:** Access to BOSL, BOLTS, and other OpenSCAD libraries
- **Multi-Model Support:** Choose from various AI models for different use cases
