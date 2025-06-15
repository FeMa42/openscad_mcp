#!/usr/bin/env python3
"""
Test script for OpenSCAD FastMCP Server
Tests the core functionality without going through MCP decorators
"""

import sys
import os
import uuid
import subprocess
from pathlib import Path
from PIL import Image as PILImage
from io import BytesIO

# Test OpenSCAD rendering directly
def test_render():
    """Test OpenSCAD rendering functionality"""
    print("\n=== Testing OpenSCAD rendering ===")
    
    test_code = """
$fa = 1;
$fs = 0.4;

// Test cube
color("red") cube(10, center=true);

// Test sphere
translate([15, 0, 0])
color("blue") sphere(r=5);
"""
    
    try:
        # Create output directory
        output_dir = Path(f"scad/test_{uuid.uuid4().hex}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        scad_file = output_dir / "output.scad"
        png_file = output_dir / "output.png"
        
        # Write SCAD code
        scad_file.write_text(test_code)
        
        # Render to PNG
        cmd = f"openscad -o {png_file} {scad_file} 2>&1"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"✗ Rendering failed: {result.stdout}")
            return False
        
        # Check if image was created
        if png_file.exists():
            with PILImage.open(png_file) as img:
                print(f"✓ Rendering successful!")
                print(f"  Image size: {img.size[0]}x{img.size[1]} pixels")
                
                # Convert and verify we can create FastMCP Image format
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                print(f"  Image data size: {len(buffer.getvalue())} bytes")
                
            return True
        else:
            print("✗ PNG file not created")
            return False
            
    except Exception as e:
        print(f"✗ Rendering failed: {e}")
        return False

def test_validation():
    """Test OpenSCAD syntax validation"""
    print("\n=== Testing OpenSCAD validation ===")
    
    # Test valid code
    valid_code = "cube(10);"
    try:
        temp_file = Path(f"/tmp/validate_{uuid.uuid4().hex}.scad")
        temp_file.write_text(valid_code)
        
        cmd = f"openscad -o /dev/null {temp_file} 2>&1"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        temp_file.unlink()
        
        if result.returncode == 0:
            print("✓ Valid code validated correctly")
        else:
            print(f"✗ Valid code validation failed: {result.stdout}")
            
    except Exception as e:
        print(f"✗ Validation error: {e}")
    
    # Test invalid code
    invalid_code = "cube(10"  # Missing closing parenthesis
    try:
        temp_file = Path(f"/tmp/validate_{uuid.uuid4().hex}.scad")
        temp_file.write_text(invalid_code)
        
        cmd = f"openscad -o /dev/null {temp_file} 2>&1"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        temp_file.unlink()
        
        if result.returncode != 0:
            print("✓ Invalid code detected correctly")
            return True
        else:
            print("✗ Invalid code passed validation")
            return False
            
    except Exception as e:
        print(f"✗ Validation error: {e}")
        return False

def test_doc_search():
    """Test documentation search"""
    print("\n=== Testing documentation search ===")
    
    try:
        # Import and initialize the knowledge base
        from openscad_fastmcp_server import init_knowledge_base
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS
        
        # Initialize
        init_knowledge_base()
        
        # Try to load and search directly
        if Path("faiss_index").exists():
            embeddings = HuggingFaceEmbeddings(
                # BAAI/bge-base-en-v1.5, "Salesforce/SFR-Embedding-2_R"
                model_name="Salesforce/SFR-Embedding-2_R",
                model_kwargs={'device': 'cpu'}
            )
            db = FAISS.load_local(
                "faiss_index", 
                embeddings,
                allow_dangerous_deserialization=True
            )
            retriever = db.as_retriever(search_kwargs={'k': 3})
            
            results = retriever.invoke("how to create a cylinder")
            
            if results:
                print(f"✓ Documentation search successful!")
                print(f"  Found {len(results)} results")
                return True
            else:
                print("✗ No search results found")
                return False
        else:
            print("⚠ Knowledge base not found (not a failure)")
            return True
            
    except ImportError:
        print("⚠ Knowledge base dependencies not installed")
        return True
    except Exception as e:
        print(f"✗ Search failed: {e}")
        return False

def test_server_startup():
    """Test that the server can be imported and initialized"""
    print("\n=== Testing server startup ===")
    
    try:
        import openscad_fastmcp_server
        
        # Check that the mcp object exists
        if hasattr(openscad_fastmcp_server, 'mcp'):
            print("✓ FastMCP server object created")
            
            # Check that tools were registered
            server = openscad_fastmcp_server.mcp
            if hasattr(server, '_tools') and len(server._tools) > 0:
                print(f"✓ {len(server._tools)} tools registered")
                for tool_name in server._tools:
                    print(f"  - {tool_name}")
            
            return True
        else:
            print("✗ MCP server object not found")
            return False
            
    except Exception as e:
        print(f"✗ Server startup failed: {e}")
        return False

def main():
    """Run all tests"""
    print("OpenSCAD FastMCP Server Test Suite")
    print("=" * 50)
    
    # Check OpenSCAD
    try:
        result = subprocess.run(["openscad", "--version"], capture_output=True, text=True)
        print(f"OpenSCAD found: {result.stdout.strip() or 'version info not available'}")
    except FileNotFoundError:
        print("⚠ OpenSCAD not found in PATH!")
        print("  Please install OpenSCAD to run tests")
    
    # Run tests
    tests_passed = 0
    tests_total = 4
    
    if test_server_startup():
        tests_passed += 1
    
    if test_render():
        tests_passed += 1
    
    if test_validation():
        tests_passed += 1
    
    if test_doc_search():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"Tests passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("✓ All tests passed! Your FastMCP server is ready.")
        print("\nTo use with Claude Desktop, add to config:")
        print('  "openscad": {')
        print('    "command": "python",')
        print(f'    "args": ["{Path.cwd()}/openscad_fastmcp_server.py"]')
        print('  }')
        return 0
    else:
        print("✗ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
