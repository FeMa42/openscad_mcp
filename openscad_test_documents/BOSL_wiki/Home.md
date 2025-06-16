## Installation
1. Download the .zip or .tar.gz release file for this library.
2. Unpack it. It should create a BOSL-v1.0 directory with the library files within it.
3. Rename the directory to BOSL.
4. Move the BOSL directory into the apropriate OpenSCAD library directory for your platform:
    - Windows: My Documents\OpenSCAD\libraries\
    - Linux: $HOME/.local/share/OpenSCAD/libraries/
    - Mac OS X: $HOME/Documents/OpenSCAD/libraries/
5. Restart OpenSCAD.

## Belfry OpenScad Library Documentation
The library files are as follows:

### Commonly Used
  - [`transforms.scad`](transforms.scad): The most commonly used transformations, manipulations, and shortcuts are in this file.
  - [`shapes.scad`](shapes.scad): Common useful shapes and structured objects.
  - [`masks.scad`](masks.scad): Shapes that are useful for masking with `difference()` and `intersect()`.
  - [`threading.scad`](threading.scad): Modules to make triangular and trapezoidal threaded rods and nuts.
  - [`paths.scad`](paths.scad): Functions and modules to work with arbitrary 3D paths.
  - [`beziers.scad`](beziers.scad): Functions and modules to work with bezier curves.

### Standard Parts
  - [`involute_gears.scad`](involute_gears.scad): Modules and functions to make involute gears and racks.
  - [`joiners.scad`](joiners.scad): Modules to make joiner shapes for connecting separately printed objects.
  - [`sliders.scad`](sliders.scad): Modules for creating simple sliders and rails.
  - [`metric_screws.scad`](metric_screws.scad): Functions and modules to make metric screws, nuts, and screwholes.
  - [`linear_bearings.scad`](linear_bearings.scad): Modules to make mounts for LMxUU style linear bearings.
  - [`nema_steppers.scad`](nema_steppers.scad): Modules to make mounting holes for NEMA motors.
  - [`phillips_drive.scad`](phillips_drive.scad): Modules to create Phillips screwdriver tips.
  - [`torx_drive.scad`](torx_drive.scad): Functions and Modules to create Torx bit drive holes.
  - [`wiring.scad`](wiring.scad): Modules to render routed bundles of wires.

### Miscellaneous
  - [`constants.scad`](constants.scad): Useful constants for vectors, edges, etc.
  - [`math.scad`](math.scad): Useful helper functions.
  - [`convex_hull.scad`](convex_hull.scad): Functions to create 2D and 3D convex hulls.
  - [`quaternions.scad`](quaternions.scad): Functions to work with quaternion rotations.
  - [`triangulation.scad`](triangulation.scad): Functions to triangulate `polyhedron()` faces that have more than 3 vertices.
  - [`debug.scad`](debug.scad): Modules to help debug creation of beziers, `polygons()`s and `polyhedron()`s

## Terminology
For purposes of these library files, the following terms apply:
- **Left**: Towards X-
- **Right**: Towards X+
- **Front**/**Forward**: Towards Y-
- **Back**/**Behind**: Towards Y+
- **Bottom**/**Down**/**Below**: Towards Z-
- **Top**/**Up**/**Above**: Towards Z+

- **Axis-Negative**: Towards the negative end of the axis the object is oriented on.  IE: X-, Y-, or Z-.
- **Axis-Positive**: Towards the positive end of the axis the object is oriented on.  IE: X+, Y+, or Z+.

## Common Arguments:

Args    | What it is
------- | ----------------------------------------
fillet  | Radius of rounding for interior or exterior edges.
chamfer | Size of chamfers/bevels for interior or exterior edges.
orient  | Axis a part should be oriented along.  Given as an XYZ triplet of rotation angles.  It is recommended that you use the `ORIENT_` constants from `constants.scad`.  Default is usually `ORIENT_Z` for vertical orientation.
align   | Side of the origin that the part should be on.  Given as a vector away from the origin.  It is recommended that you use the `V_` constants from `constants.scad`.  Default is usually `V_ZERO` for centered.



