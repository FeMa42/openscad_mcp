# OpenSCAD Assistant Demo App

This is a **fake/demo version** of the OpenSCAD Assistant designed for video recording and demonstrations. It provides all the visual elements of the real app without any actual AI or processing dependencies.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the demo app
python demo_app.py
```

The app will be available at: `http://localhost:7862`

## 🎯 Demo Flow

The app responds to messages in a predefined sequence:

1. **First message** (any input) → Gear generation response with technical details
2. **Second message** (any input) → G-code generation and print start response  
3. **Subsequent messages** → Generic demo capabilities response

## 💡 Suggested Demo Script

For the most realistic demo video:

### Script:
```
1. Type: "Can you generate a gear with the following Specifications:
         Module m = 4 (tooth size parameter)
         Number of teeth z = 18
         Face width b = 25mm (axial length of teeth)
         Bore for shaft or clamping element: 30mm
         A hub diameter of 0mm."
   → Shows gear generation response + 3D model
   
2. Type: "Please generate the gcode and start the printing process"  
   → Shows printing optimization response
```

### Changing the conversation:

To change the conversation you can edit the answers in the `demo_app.py` file.