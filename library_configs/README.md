# OpenSCAD Library Configurations

This directory contains JSON configuration files for OpenSCAD libraries used by the MCP server.

## How it works

The MCP server automatically loads all `.json` files from this directory to provide detailed information about OpenSCAD libraries, including usage examples, common modules, and documentation links.

## Configuration File Format

Each library should have its own JSON file named `LibraryName.json` with the following structure:

```json
{
  "name": "LibraryName",
  "description": "Brief description of what the library does",
  "main_files": ["main.scad", "shapes.scad", "utils.scad"],
  "usage": "// Example usage code:\nuse <LibraryName/main.scad>\n\n// Create something:\nsome_function();",
  "common_modules": [
    "category: module1(), module2()",
    "shapes: circle_thing(), square_thing()"
  ],
  "documentation_url": "https://github.com/author/library",
  "license": "MIT"
}
```

### Required Fields

- `name`: Library name (should match the directory name in OpenSCAD libraries)
- `description`: Brief description of the library
- `main_files`: Array of main SCAD files to include/use
- `usage`: Example code showing how to use the library

### Optional Fields

- `common_modules`: Array of strings describing common modules/functions
- `documentation_url`: Link to documentation
- `license`: Library license

## Adding New Libraries

1. Create a new `.json` file in this directory
2. Use the format above as a template
3. Fill in the appropriate information
4. Restart the MCP server to load the new configuration

## Current Libraries

The following libraries have configurations:

- **BOSL**: Belfry OpenSCAD Library - tools, shapes, and helpers
- **BOSL2**: Belfry OpenScad Library v2 - enhanced version
- **BOLTS**: Open Library for Technical Specifications - standard parts
- **MCAD**: OpenSCAD Parametric CAD Library - mechanical parts
- **dotSCAD**: Mathematical operations and transforms
- **constructive**: Complex mechanical parts with stamping approach
- **parameterizable_gears**: Comprehensive gear generation
- **pathbuilder**: Complex 2D shapes with SVG syntax
- **UB**: Full 3D printing workflow solution
- **Round-Anything**: Radii and fillets utilities
- **scad-utils**: Functional programming utilities

## Environment Variables

- `LIBRARY_CONFIGS_DIR`: Override config directory (default: `library_configs`)
- `OPENSCAD_USER_LIBRARY_PATH`: OpenSCAD libraries directory (default: `~/Documents/OpenSCAD/libraries`) 