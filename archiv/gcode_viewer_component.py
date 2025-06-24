#!/usr/bin/env python3
"""
Custom Gradio Component for G-code Visualization
Integrates with external G-code viewers and provides embedded visualization
"""

import gradio as gr
import os
import tempfile
import webbrowser
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import base64


class GCodeViewerComponent:
    """Custom Gradio component for G-code visualization"""
    
    def __init__(self):
        self.supported_viewers = {
            "gcode-viewer.com": {
                "url": "https://gcode-viewer.com",
                "description": "Popular web-based G-code viewer with 3D visualization",
                "features": ["3D visualization", "Layer-by-layer view", "Print time estimation"]
            },
            "ncviewer.com": {
                "url": "https://ncviewer.com",
                "description": "Clean interface for G-code analysis",
                "features": ["Simple interface", "Fast loading", "Basic analysis"]
            },
            "prusaslicer": {
                "url": "local",
                "description": "PrusaSlicer's built-in G-code viewer",
                "features": ["Local application", "Full slicer integration", "Advanced features"]
            }
        }
    
    def create_viewer_interface(self, gcode_path: Optional[str] = None) -> Dict[str, Any]:
        """Create a comprehensive G-code viewer interface"""
        
        # Create HTML for embedded viewer
        html_content = self._create_embedded_viewer_html(gcode_path)
        
        # Create viewer options
        viewer_options = self._create_viewer_options()
        
        return {
            "html": html_content,
            "viewers": viewer_options,
            "gcode_path": gcode_path
        }
    
    def _create_embedded_viewer_html(self, gcode_path: Optional[str] = None) -> str:
        """Create HTML for embedded G-code viewer"""
        
        if not gcode_path or not Path(gcode_path).exists():
            return """
            <div style="text-align: center; padding: 40px; background: #f5f5f5; border-radius: 8px;">
                <h3>🖨️ G-code Visualization</h3>
                <p>No G-code file available. Generate G-code first using the analysis tools.</p>
                <div style="margin-top: 20px;">
                    <button onclick="window.open('https://gcode-viewer.com', '_blank')" 
                            style="background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
                        Open gcode-viewer.com
                    </button>
                </div>
            </div>
            """
        
        # Create embedded iframe for gcode-viewer.com
        gcode_filename = Path(gcode_path).name
        
        html = f"""
        <div style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px; margin-bottom: 20px;">
            <h3>🖨️ G-code Visualization</h3>
            <p><strong>File:</strong> {gcode_filename}</p>
            <div style="margin: 20px 0;">
                <button onclick="openGCodeViewer()" 
                        style="background: #28a745; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; margin: 5px;">
                    🌐 Open in gcode-viewer.com
                </button>
                <button onclick="openNcViewer()" 
                        style="background: #17a2b8; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; margin: 5px;">
                    📊 Open in ncviewer.com
                </button>
                <button onclick="openLocalViewer()" 
                        style="background: #6c757d; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; margin: 5px;">
                    💻 Open Locally
                </button>
            </div>
        </div>
        
        <div style="background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
            <h4>📋 Quick Instructions:</h4>
            <ol style="text-align: left; max-width: 600px; margin: 0 auto;">
                <li>Click any of the viewer buttons above</li>
                <li>Drag and drop your G-code file into the viewer</li>
                <li>Use the 3D controls to rotate, zoom, and pan</li>
                <li>Toggle layer visibility and analyze print paths</li>
            </ol>
        </div>
        
        <script>
        function openGCodeViewer() {{
            window.open('https://gcode-viewer.com', '_blank');
        }}
        
        function openNcViewer() {{
            window.open('https://ncviewer.com', '_blank');
        }}
        
        function openLocalViewer() {{
            // This would trigger a local file open
            console.log('Opening local viewer for: {gcode_filename}');
        }}
        </script>
        """
        
        return html
    
    def _create_viewer_options(self) -> str:
        """Create viewer options display"""
        
        options_html = """
        <div style="background: #f8f9fa; border-radius: 8px; padding: 20px;">
            <h4>🎯 Available G-code Viewers:</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin-top: 15px;">
        """
        
        for name, info in self.supported_viewers.items():
            features_html = "".join([f"<li>{feature}</li>" for feature in info["features"]])
            
            options_html += f"""
            <div style="background: white; border: 1px solid #ddd; border-radius: 6px; padding: 15px;">
                <h5 style="margin: 0 0 10px 0; color: #333;">{name.title()}</h5>
                <p style="margin: 0 0 10px 0; color: #666; font-size: 14px;">{info['description']}</p>
                <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #555;">
                    {features_html}
                </ul>
            </div>
            """
        
        options_html += """
            </div>
        </div>
        """
        
        return options_html
    
    def open_viewer(self, viewer_name: str, gcode_path: Optional[str] = None) -> str:
        """Open G-code in specified viewer"""
        
        if viewer_name not in self.supported_viewers:
            return f"❌ Unknown viewer: {viewer_name}"
        
        viewer_info = self.supported_viewers[viewer_name]
        
        if viewer_name == "prusaslicer":
            return self._open_local_viewer(gcode_path)
        else:
            return self._open_web_viewer(viewer_info["url"], gcode_path)
    
    def _open_web_viewer(self, url: str, gcode_path: Optional[str] = None) -> str:
        """Open web-based G-code viewer"""
        try:
            webbrowser.open(url)
            if gcode_path:
                return f"✅ Opened {url} - drag and drop '{Path(gcode_path).name}' to visualize"
            else:
                return f"✅ Opened {url} - upload your G-code file to visualize"
        except Exception as e:
            return f"❌ Failed to open {url}: {str(e)}"
    
    def _open_local_viewer(self, gcode_path: Optional[str] = None) -> str:
        """Open local G-code viewer (PrusaSlicer)"""
        if not gcode_path or not Path(gcode_path).exists():
            return "❌ No G-code file available for local viewing"
        
        try:
            # Try to open with PrusaSlicer
            if os.name == 'nt':  # Windows
                # Try common PrusaSlicer paths
                slicer_paths = [
                    r"C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer.exe",
                    r"C:\Program Files (x86)\Prusa3D\PrusaSlicer\prusa-slicer.exe"
                ]
                
                for path in slicer_paths:
                    if Path(path).exists():
                        subprocess.run([path, gcode_path], check=True)
                        return f"✅ Opened {Path(gcode_path).name} in PrusaSlicer"
                
                # Fallback to default application
                os.startfile(gcode_path)
                return f"✅ Opened {Path(gcode_path).name} in default application"
                
            elif os.name == 'posix':  # macOS/Linux
                # Try to open with PrusaSlicer on macOS
                if os.uname().sysname == 'Darwin':  # macOS
                    slicer_paths = [
                        "/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer",
                        "/Applications/Original Prusa Drivers/PrusaSlicer.app/Contents/MacOS/PrusaSlicer"
                    ]
                    
                    for path in slicer_paths:
                        if Path(path).exists():
                            subprocess.run([path, gcode_path], check=True)
                            return f"✅ Opened {Path(gcode_path).name} in PrusaSlicer"
                
                # Fallback to default application
                subprocess.run(['open', gcode_path], check=True)
                return f"✅ Opened {Path(gcode_path).name} in default application"
                
        except Exception as e:
            return f"❌ Failed to open local viewer: {str(e)}"
        
        return "❌ Could not find suitable local viewer"


def create_gcode_viewer_tab():
    """Create a G-code viewer tab component"""
    
    viewer_component = GCodeViewerComponent()
    
    with gr.TabItem("🖨️ G-code Visualization"):
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 🎯 G-code Viewer Options")
                
                viewer_dropdown = gr.Dropdown(
                    choices=list(viewer_component.supported_viewers.keys()),
                    value="gcode-viewer.com",
                    label="Select Viewer",
                    info="Choose your preferred G-code visualization tool"
                )
                
                open_viewer_btn = gr.Button(
                    "🚀 Open Selected Viewer",
                    variant="primary"
                )
                
                viewer_status = gr.Markdown("Ready to open G-code viewer")
            
            with gr.Column(scale=2):
                gr.Markdown("### 📋 Viewer Information")
                viewer_info = gr.HTML(
                    value=viewer_component._create_viewer_options(),
                    label="Available Viewers"
                )
        
        gr.Markdown("---")
        
        gr.Markdown("### 🎮 Quick Start")
        gr.Markdown("""
        1. **Generate G-code** using the chat interface (e.g., "Generate G-code for the latest model")
        2. **Select a viewer** from the dropdown above
        3. **Click "Open Selected Viewer"** to launch the visualization tool
        4. **Upload your G-code file** to the viewer
        5. **Explore the 3D visualization** with rotation, zoom, and layer controls
        """)
        
        return viewer_dropdown, open_viewer_btn, viewer_status


# Integration function for the main app
def integrate_gcode_viewer(chat_assistant):
    """Integrate G-code viewer with the main chat assistant"""
    
    viewer_component = GCodeViewerComponent()
    
    def open_selected_viewer(viewer_name: str) -> str:
        """Open the selected G-code viewer"""
        # Get the latest G-code file from the assistant
        latest_gcode = chat_assistant.gcode_analyzer.find_latest_gcode([
            "../output", "scad_output", "output", "."
        ])
        
        gcode_path = str(latest_gcode) if latest_gcode else None
        return viewer_component.open_viewer(viewer_name, gcode_path)
    
    return open_selected_viewer


if __name__ == "__main__":
    # Test the component
    viewer = GCodeViewerComponent()
    
    # Test with a sample G-code path
    test_path = "/path/to/test.gcode"
    result = viewer.create_viewer_interface(test_path)
    
    print("G-code Viewer Component Test:")
    print(f"HTML Content Length: {len(result['html'])}")
    print(f"Viewers Available: {len(result['viewers'])}") 