#!/usr/bin/env python3
"""
Test the multi-view rendering system with a simple cube
Tests core functionality by directly calling OpenSCAD without MCP decorators
"""
import sys
import os
import uuid 
import subprocess
from pathlib import Path
from PIL import Image as PILImage
from io import BytesIO

# Add the current directory to the path
sys.path.insert(0, str(Path.cwd()))

# Import what we need from the server
from openscad_fastmcp_server import PREDEFINED_VIEWS, OUTPUT_DIR, generation_id, current_views_session, fix_library_includes

# Set OpenSCAD executable path
OPENSCAD_EXECUTABLE = os.environ.get('OPENSCAD_EXECUTABLE', 'openscad')

def test_multiview_core_logic():
    """Test the multi-view rendering logic without MCP wrapper"""
    print("🧪 Testing Multi-View Rendering System")
    print("=" * 50)
    
    # Simple test OpenSCAD code
    test_code = """
// Simple test cube with quality settings
$fa=1; $fs=0.4;

// Create a simple cube with some features for better view testing
cube([20, 15, 10], center=true);
translate([10, 0, 5])
    cylinder(d=5, h=20, center=true);
"""
    
    print(f"📝 Test OpenSCAD Code:")
    print(test_code)
    print()
    
    try:
        # Test 1: Manual multi-view rendering (mimic the core logic)
        print("🎬 Step 1: Testing multi-view rendering core logic...")
        
        # Use test-specific generation ID to avoid conflicts
        test_generation_id = f"test_{uuid.uuid4().hex[:8]}"
        iteration = 0
        
        # Create directories  
        output_dir = Path(OUTPUT_DIR) / test_generation_id / str(iteration)
        views_dir = output_dir / "views"
        views_dir.mkdir(parents=True, exist_ok=True)

        scad_file = output_dir / "multi_views.scad"
        
        # Write SCAD code (with library fixing)
        fixed_code = fix_library_includes(test_code)
        scad_file.write_text(fixed_code)
        print(f"   Created SCAD file: {scad_file}")

        # Store test session information
        session_key = f"{test_generation_id}_{iteration}"
        current_views_session[session_key] = {
            'scad_file': str(scad_file),
            'views_dir': str(views_dir), 
            'available_views': {},
            'code': fixed_code
        }

        # Test rendering a few key views
        test_views = ['isometric', 'front', 'top']
        rendered_views = {}
        
        for view_id in test_views:
            if view_id not in PREDEFINED_VIEWS:
                continue
                
            view_info = PREDEFINED_VIEWS[view_id]
            view_file = views_dir / f"{view_id}.png"
            
            print(f"   Rendering {view_info['name']} ({view_id})...")
            
            # Build OpenSCAD command with specific camera
            cmd = [
                OPENSCAD_EXECUTABLE,
                '-o', str(view_file),
                '--camera', view_info['camera'],
                str(scad_file)
            ]

            # Execute rendering
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"   ⚠️ Failed to render {view_id}: {result.stderr}")
                continue
                
            # Check if file was created
            if not view_file.exists():
                print(f"   ⚠️ View file not created: {view_file}")
                continue
                
            # Store view info in session
            current_views_session[session_key]['available_views'][view_id] = {
                'name': view_info['name'],
                'description': view_info['description'], 
                'file_path': str(view_file),
                'default': view_info['default']
            }
            
            rendered_views[view_id] = view_file
            print(f"   ✅ Rendered {view_info['name']}: {view_file}")
        
        print(f"   Successfully rendered {len(rendered_views)} views")
        print()
        
        # Test 2: View retrieval simulation
        print("🔍 Step 2: Testing view file retrieval...")
        
        for view_id, view_file in rendered_views.items():
            try:
                # Test loading the image file
                with PILImage.open(view_file) as img:
                    # Basic image validation
                    if img.size[0] > 0 and img.size[1] > 0:
                        print(f"   ✅ {view_id}: {img.size[0]}x{img.size[1]} pixels, mode: {img.mode}")
                    else:
                        print(f"   ❌ {view_id}: Invalid image size")
                        
            except Exception as e:
                print(f"   ❌ Failed to load {view_id}: {e}")
        
        print()
        
        # Test 3: Session management
        print("📋 Step 3: Testing session management...")
        
        if session_key in current_views_session:
            session = current_views_session[session_key]
            available_views = session['available_views']
            
            print(f"   ✅ Session stored: {session_key}")
            print(f"   ✅ Available views: {len(available_views)}")
            
            for view_id, view_info in available_views.items():
                marker = " (default)" if view_info['default'] else ""
                print(f"      - {view_id}: {view_info['name']}{marker}")
        else:
            print(f"   ❌ Session not found: {session_key}")
            
        print()
        print("🎉 Core multi-view rendering logic test completed!")
        
        return len(rendered_views) > 0
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Check OpenSCAD availability
    try:
        result = subprocess.run([OPENSCAD_EXECUTABLE, "--version"], capture_output=True, text=True)
        print(f"OpenSCAD found: {result.stdout.strip() or 'version info not available'}")
        print()
    except FileNotFoundError:
        print("⚠️ OpenSCAD not found in PATH!")
        print("  Please install OpenSCAD to run tests")
        print("  macOS: brew install --cask openscad")
        sys.exit(1)
    
    success = test_multiview_core_logic()
    if success:
        print("\n✅ Multi-view system test PASSED")
        sys.exit(0)
    else:
        print("\n❌ Multi-view system test FAILED")
        sys.exit(1)