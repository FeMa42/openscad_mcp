#!/usr/bin/env python3
"""
Verify the MCP server is properly configured
"""

import subprocess
import sys
import json
import time
from pathlib import Path

def check_stdout_clean():
    """Check that the server doesn't pollute stdout"""
    print("Checking stdout cleanliness...")
    
    # Run server and capture stdout/stderr separately
    proc = subprocess.Popen(
        [sys.executable, "openscad_fastmcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give it a moment to start
    time.sleep(1)
    
    # Terminate without sending any input
    proc.terminate()
    stdout, stderr = proc.communicate()
    
    # Check stdout - should be empty or only JSON
    if stdout.strip():
        # Try to parse as JSON to see if it's valid
        try:
            for line in stdout.strip().split('\n'):
                if line:
                    json.loads(line)
            print("✓ stdout contains only valid JSON")
        except json.JSONDecodeError:
            print(f"✗ stdout contains non-JSON data: {stdout[:100]}...")
            return False
    else:
        print("✓ stdout is clean (no output without input)")
    
    # Check stderr has the expected logs
    if "Starting OpenSCAD FastMCP Server" in stderr:
        print("✓ Logging goes to stderr correctly")
    else:
        print("✗ Expected logs not found in stderr")
        return False
    
    return True

def check_environment():
    """Check environment setup"""
    print("\nChecking environment...")
    
    # Check OpenSCAD
    try:
        result = subprocess.run(
            ["openscad", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓ OpenSCAD is installed")
        else:
            print("✗ OpenSCAD not working properly")
            return False
    except FileNotFoundError:
        print("✗ OpenSCAD not found in PATH")
        return False
    
    # Check output directory
    import os
    output_dir = os.environ.get('OPENSCAD_OUTPUT_DIR', 'scad_output')
    print(f"✓ Output directory: {output_dir}")
    
    # Check FAISS index
    faiss_path = os.environ.get('FAISS_INDEX_PATH', 'faiss_index')
    if Path(faiss_path).exists():
        print(f"✓ FAISS index found: {faiss_path}")
    else:
        print(f"⚠ FAISS index not found: {faiss_path} (doc search won't work)")
    
    return True

def test_basic_protocol():
    """Test basic JSON-RPC communication"""
    print("\nTesting basic protocol...")
    
    # Start server
    proc = subprocess.Popen(
        [sys.executable, "openscad_fastmcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0"
                }
            }
        }
        
        proc.stdin.write(json.dumps(init_request) + '\n')
        proc.stdin.flush()
        
        # Read response
        response_line = proc.stdout.readline()
        if response_line:
            response = json.loads(response_line)
            if "result" in response and "serverInfo" in response["result"]:
                print(f"✓ Server responded: {response['result']['serverInfo']['name']}")
                return True
            else:
                print(f"✗ Invalid response: {response}")
                return False
        else:
            print("✗ No response from server")
            return False
            
    finally:
        proc.terminate()
        proc.wait()

def main():
    """Run all checks"""
    print("MCP Server Verification")
    print("=" * 50)
    
    checks = [
        ("Environment", check_environment),
        ("stdout cleanliness", check_stdout_clean),
        ("Basic protocol", test_basic_protocol)
    ]
    
    passed = 0
    for name, check_func in checks:
        try:
            if check_func():
                passed += 1
            else:
                print(f"⚠ {name} check failed")
        except Exception as e:
            print(f"✗ {name} check error: {e}")
    
    print("\n" + "=" * 50)
    print(f"Passed {passed}/{len(checks)} checks")
    
    if passed == len(checks):
        print("\n✓ Server is properly configured!")
        print("\nYou can now:")
        print("1. Configure Claude Desktop with the server path")
        print("2. Set OPENSCAD_OUTPUT_DIR if you want a custom output location")
        print("3. Test with: 'Create a red cube using OpenSCAD'")
    else:
        print("\n⚠ Some checks failed. Please review the issues above.")
    
    return 0 if passed == len(checks) else 1

if __name__ == "__main__":
    sys.exit(main())
