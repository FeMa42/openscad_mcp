#!/usr/bin/env python3
"""
Demo/Fake OpenSCAD Chat App for Video Recording
Simple, reliable implementation with predefined responses
"""

import gradio as gr
import os
from pathlib import Path
import time

# Demo app configuration
DEMO_DIR = Path(__file__).parent
STL_FILE = DEMO_DIR / "output.stl"
PNG_FILE = DEMO_DIR / "output.png"
SCAD_FILE = DEMO_DIR / "output.scad"

PROCESSING_TIME = 2.0

# Predefined conversation flow
RESPONSES = [
    # First response after gear request
    """Excellent! Your gear has been generated successfully with the exact specifications you requested:

✅ **Gear Specifications Confirmed:**
- **Module:** 4mm (tooth size parameter)
- **Number of teeth:** 18
- **Face width:** 25mm (axial length)
- **Bore diameter:** 30mm (for shaft/clamping)
- **Hub diameter:** 0mm (no hub - clean cylindrical design)
- **Outside diameter:** 80mm (calculated: 4 × (18 + 2) = 80mm) ✅

**Key Features:**
- 25° pressure angle for stronger teeth (optimal for 3D printing)
- Straight spur gear design (0° helix angle)
- Clean bore - perfect 30mm hole for shaft mounting
- No hub extension - gear body is exactly 25mm thick
- DIN 780 compliant module (4mm is standard heavy-duty size)

**Calculated Dimensions:**
- Pitch diameter: 72mm (4 × 18)
- Root diameter: ~70mm
- Outside diameter: 80mm (matches your requirement)

The gear is now ready for use! This is a substantial gear suitable for heavy-duty applications. Would you like me to:

1. Generate G-code for 3D printing with optimized settings for a strong mechanical part?
2. Create a matching gear to mesh with this one?
3. Add any modifications like keyways, mounting holes, or weight reduction features?

The gear looks perfect in the render - clean teeth profile, proper bore size, and exactly the dimensions you specified!""",
    
    # Second response after print request
    """🎯 **G-Code Generated & Print Started Successfully!**

Your heavy-duty Module 4 gear is now printing with optimized settings:

🖨️ **Print Job Status: STARTED**
- File uploaded: `model.gcode` to OctoPrint
- Print automatically initiated ✅

⚙️ **Optimized Print Settings:**

**Variable Density Strategy Applied:**
- **Gear teeth area (r > 40mm):** 70% infill - Maximum strength for load-bearing teeth
- **Center hub area (r < 40mm):** 10% infill - Material savings while maintaining structure
- **Material savings:** ~85% less plastic in center while keeping teeth super strong

**Print Configuration:**
- **Quality preset:** "Strong" (0.25mm layers, 40mm/s)
- **Material:** PETG (240°C extruder, 80°C bed) - Superior strength and durability
- **Total optimization:** Perfect for heavy-duty mechanical applications

🔧 **Why This Configuration is Perfect:**
- **Gear Teeth Strength:** 70% infill ensures teeth won't shear under load
- **Material Efficiency:** 10% center infill saves ~2 hours print time and plastic
- **PETG Material:** Chemical resistant, tough, perfect for functional gears
- **Layer Height:** 0.25mm balances strength with reasonable print time

📊 **Expected Results:**
- **Print time:** ~8-12 hours (estimated)
- **Material usage:** ~180-220g PETG
- **Tooth strength:** Heavy-duty industrial capability
- **Perfect 30mm bore** for shaft mounting

Your gear is optimized for real mechanical use - the variable density approach gives you the strength where you need it (teeth) while being efficient everywhere else. The print is now running automatically!

Would you like me to monitor the print progress or design any companion parts while this prints?""",

    # Third response for any additional input
    """🔄 **Print Update & Next Steps**

The gear print is progressing perfectly! Current status:

📈 **Print Progress:**
- Layer 45/180 completed (25% done)
- Estimated remaining time: 6.2 hours
- No issues detected - smooth printing
- Bed adhesion excellent, no warping

⚡ **Quick Demo Capabilities:**

I can help you with:
- **More gears:** Create matching gears, planetary systems, or gear trains
- **Mechanical parts:** Brackets, housings, shafts, pulleys
- **Custom designs:** Phone stands, tool holders, organizers
- **3D printing optimization:** Variable density, supports, material selection

**Try saying:** 
- "Create a phone stand"
- "Make a bracket for mounting"
- "Design a gear train"
- "Generate a custom part"

The beauty of this system is the seamless workflow from idea → 3D model → optimized printing → finished part!

What would you like to create next?"""
]

# Read the OpenSCAD code for display
def get_scad_code():
    try:
        with open(SCAD_FILE, 'r') as f:
            return f.read()
    except:
        return """// Demo OpenSCAD code
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

stirnrad(
    modul = 4,
    zahnzahl = 18,
    breite = 25,
    bohrung = 30,
    nabendicke = 0,
    nabendurchmesser = 0,
    eingriffswinkel = 25,
    schraegungswinkel = 0,
    optimiert = false
);"""

class DemoApp:
    def __init__(self):
        self.response_index = 0
        self.conversation_history = []
        
    def chat(self, message: str, history: list):
        """Handle chat messages with predefined responses"""
        if not message.strip():
            return history, None, "", "No measurements available"
            
        # Add user message to history
        history = history or []
        history.append({"role": "user", "content": message})
        
        # Add a small delay to simulate processing
        time.sleep(PROCESSING_TIME)
        
        # Get predefined response
        if self.response_index < len(RESPONSES):
            response = RESPONSES[self.response_index]
            self.response_index += 1
        else:
            # Cycle back to generic responses after main conversation
            response = RESPONSES[-1]
        
        # Add assistant response
        history.append({"role": "assistant", "content": response})
        
        # Prepare outputs
        model_3d = str(STL_FILE) if STL_FILE.exists() else None
        measurements = "📏 **Gear Measurements:**\n- Outside Diameter: 80mm\n- Module: 4mm\n- Teeth: 18\n- Face Width: 25mm\n- Bore: 30mm"
        code = get_scad_code()
        
        return history, model_3d, measurements, code
    
    def clear_chat(self):
        """Reset the conversation"""
        self.response_index = 0
        self.conversation_history = []
        return [], None, None, "No measurements available", ""

def create_demo_app():
    """Create the demo Gradio interface"""
    demo_assistant = DemoApp()
    
    # Custom CSS to match the real app styling
    custom_css = """
    .gradio-container {
        font-family: 'Source Sans Pro', sans-serif;
    }
    .chat-message {
        font-size: 14px;
    }
    .title {
        text-align: center;
        color: #2563eb;
    }
    """
    
    with gr.Blocks(title="OpenSCAD Assistant", theme=gr.themes.Soft(), css=custom_css) as app:
        gr.Markdown("# 🤖 OpenSCAD Design Assistant")
        gr.Markdown("Chat naturally about 3D design with AI models")
        
        # Status indicator
        status = gr.Markdown("✅ **Ready** - Demo mode active")
        
        with gr.Row():
            # Chat interface
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    height=600, 
                    show_label=False, 
                    type='messages',
                    placeholder="The Agent is ready to help you with your 3D design needs..."
                )
                msg = gr.Textbox(
                    placeholder="Try: 'Can you generate a gear with module 4 and 18 teeth?'",
                    show_label=False,
                    scale=4
                )
                with gr.Row():
                    send_btn = gr.Button("Send", variant="primary", scale=1)
                    clear_btn = gr.Button("Clear Chat", variant="secondary", scale=1)
            
            # Preview panel
            with gr.Column(scale=2):
                with gr.Tabs():
                    # 3D Model Tab
                    with gr.TabItem("🎯 3D Viewer"):
                        model_3d = gr.Model3D(
                            label="Generated 3D Model",
                            height=400,
                            display_mode="solid",
                            camera_position=[200, 200, 200]
                        )
                    
                    # 2D Preview Tab
                    with gr.TabItem("🖼️ 2D Preview"):
                        preview_2d = gr.Image(
                            label="2D Preview", 
                            height=400,
                            value=str(PNG_FILE) if PNG_FILE.exists() else None
                        )
                
                # Measurements panel
                with gr.Accordion("📏 Measurements & Info", open=False):
                    measurements_display = gr.Markdown("No measurements available")
                
                # Code panel
                with gr.Accordion("💻 Generated Code", open=False):
                    code_view = gr.Code(
                        language="c", 
                        show_label=False,
                        value=get_scad_code()
                    )
        
        # Event handlers
        def handle_message(message, history):
            """Handle user messages"""
            return demo_assistant.chat(message, history)
        
        def clear_conversation():
            """Clear the conversation"""
            return demo_assistant.clear_chat()
        
        # Wire up events
        msg.submit(
            handle_message,
            [msg, chatbot],
            [chatbot, model_3d, measurements_display, code_view]
        ).then(
            lambda: "",  # Clear input
            outputs=msg
        )
        
        send_btn.click(
            handle_message,
            [msg, chatbot],
            [chatbot, model_3d, measurements_display, code_view]
        ).then(
            lambda: "",  # Clear input
            outputs=msg
        )
        
        clear_btn.click(
            clear_conversation,
            outputs=[chatbot, model_3d, preview_2d, measurements_display, code_view]
        )
        
        # Example prompts
        gr.Examples(
            examples=[
                "Can you generate a gear?",
                "Create a phone stand",
                "Make a custom bracket", 
                "Design a pulley system"
            ],
            inputs=msg,
            label="💡 Example Prompts"
        )
    
    return app

if __name__ == "__main__":
    print("🎬 Starting OpenSCAD Demo App...")
    print("📁 Demo files location:", DEMO_DIR)
    print("📎 STL file:", STL_FILE.exists())
    print("🖼️ PNG file:", PNG_FILE.exists())
    print("💻 SCAD file:", SCAD_FILE.exists())
    
    app = create_demo_app()
    app.launch(
        server_port=7862,  # Different port to avoid conflicts
        share=False,
        show_error=True,
        debug=False
    ) 