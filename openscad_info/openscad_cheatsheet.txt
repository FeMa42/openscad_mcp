# OpenSCAD Code Generation Cheat Sheet

## Essential Setup
```openscad
// Quality settings (add at top of file)
$fa = 1;    // minimum angle
$fs = 0.4;  // minimum size
$fn = 50;   // number of fragments (for smoother curves)
```

## Basic Syntax Rules
- Statements end with semicolons `;`
- Code blocks use curly braces `{}`
- Comments: `//` for single line, `/* */` for multi-line
- Variables: `var = value;`
- Conditional: `var = condition ? true_value : false_value;`

## 2D Shapes (Building Blocks)

### Circle
```openscad
circle(r = 10);           // radius
circle(d = 20);           // diameter
```

### Rectangle/Square
```openscad
square(10);               // 10x10 square
square([20, 10]);         // 20x10 rectangle
square([20, 10], center = true);  // centered
```

### Polygon (Custom Shapes)
```openscad
polygon([[0,0], [10,0], [5,10]]);  // triangle
```

### Text
```openscad
text("Hello", size = 10, font = "Arial");
```

## 3D Shapes (Primitives)

### Sphere
```openscad
sphere(r = 10);           // radius
sphere(d = 20);           // diameter
```

### Cube/Box
```openscad
cube(10);                 // 10x10x10 cube
cube([20, 10, 5]);        // 20x10x5 box
cube([20, 10, 5], center = true);  // centered
```

### Cylinder
```openscad
cylinder(h = 20, r = 5);              // height, radius
cylinder(h = 20, d = 10);             // height, diameter
cylinder(h = 20, r1 = 10, r2 = 5);   // cone (different top/bottom radius)
```

## Essential Transformations

### Position (Translate)
```openscad
translate([x, y, z]) object();
translate([10, 5, 0]) cube(5);
```

### Rotation
```openscad
rotate([x, y, z]) object();          // degrees around each axis
rotate([0, 0, 45]) cube(10);         // 45° around Z-axis
rotate(45, [0, 0, 1]) cube(10);      // alternative syntax
```

### Scale
```openscad
scale([x, y, z]) object();
scale([2, 1, 0.5]) cube(10);         // 2x wider, half height
```

### Mirror
```openscad
mirror([1, 0, 0]) object();          // mirror across YZ plane
```

## Boolean Operations (Combining Shapes)

### Union (Add/Combine)
```openscad
union() {
    cube(10);
    translate([5, 5, 5]) sphere(8);
}
// Note: union() is implicit when objects are just listed together
```

### Difference (Subtract)
```openscad
difference() {
    cube(20);                         // main object
    translate([10, 10, -1]) cylinder(h = 22, r = 5);  // hole
}
```

### Intersection (Keep Only Overlap)
```openscad
intersection() {
    cube(20);
    sphere(15);
}
```

## Variables and Lists

### Variables
```openscad
width = 20;
height = 10;
radius = width / 4;

cube([width, height, 5]);
```

### Lists/Arrays
```openscad
dimensions = [20, 10, 5];
cube(dimensions);

points = [[0,0], [10,0], [5,10]];
polygon(points);
```

## Loops and Flow Control

### For Loops
```openscad
// Simple range
for(i = [0:4]) {
    translate([i * 15, 0, 0]) cube(10);
}

// With step
for(i = [0:2:10]) {
    translate([i, 0, 0]) cube(5);
}

// List iteration
for(i = [10, 20, 30]) {
    translate([i, 0, 0]) sphere(5);
}
```

### If Statements
```openscad
for(i = [0:5]) {
    if(i % 2 == 0) {
        translate([i * 10, 0, 0]) cube(5);
    } else {
        translate([i * 10, 0, 0]) sphere(3);
    }
}
```

## Advanced 3D Operations

### Linear Extrude (2D → 3D)
```openscad
linear_extrude(height = 10) {
    circle(r = 5);
}

// With twist
linear_extrude(height = 20, twist = 90) {
    square(10);
}
```

### Rotate Extrude (Lathe Operation)
```openscad
rotate_extrude() {
    translate([10, 0, 0]) circle(r = 3);  // creates torus
}

// Partial rotation
rotate_extrude(angle = 180) {
    translate([10, 0, 0]) square([5, 10]);
}
```

### Hull (Convex Hull)
```openscad
hull() {
    translate([0, 0, 0]) sphere(5);
    translate([20, 20, 10]) sphere(5);
}
```

## Modules (Custom Functions)

### Define Module
```openscad
module my_bracket(width = 20, height = 10, thickness = 2) {
    difference() {
        cube([width, height, thickness]);
        translate([width/2, height/2, -1]) 
            cylinder(h = thickness + 2, r = 3);
    }
}

// Use module
my_bracket(30, 15, 3);
translate([0, 20, 0]) my_bracket();  // uses defaults
```

## Useful Patterns

### Creating Arrays of Objects
```openscad
module screw_hole(x, y) {
    translate([x, y, -1]) cylinder(h = 12, r = 2);
}

difference() {
    cube([50, 30, 10]);
    // Corner holes
    screw_hole(5, 5);
    screw_hole(45, 5);
    screw_hole(5, 25);
    screw_hole(45, 25);
}
```

### Rounded Corners (using hull)
```openscad
module rounded_cube(size, radius) {
    hull() {
        translate([radius, radius, 0]) 
            cylinder(r = radius, h = size[2]);
        translate([size[0] - radius, radius, 0]) 
            cylinder(r = radius, h = size[2]);
        translate([radius, size[1] - radius, 0]) 
            cylinder(r = radius, h = size[2]);
        translate([size[0] - radius, size[1] - radius, 0]) 
            cylinder(r = radius, h = size[2]);
    }
}

rounded_cube([30, 20, 10], 3);
```

## Common Debugging

### Visual Aids
```openscad
// Use # to highlight objects in transparent red
#translate([10, 0, 0]) cube(5);

// Use % to show objects as transparent background
%sphere(20);  // reference sphere

// Use ! to show only this object
!cube(10);
```

### Echo for Debugging
```openscad
radius = 10;
echo("Radius is:", radius);
echo("Circumference is:", 2 * PI * radius);
```

## Best Practices for Code Generation

1. **Always include quality settings** at the top of files
2. **Use meaningful variable names** and organize with modules
3. **Center objects when appropriate** for easier positioning
4. **Use hull()** for organic, flowing shapes
5. **Add small tolerances** (like 0.1mm) for 3D printing clearances
6. **Use difference()** strategically to create holes and cutouts
7. **Leverage loops** for repetitive patterns
8. **Comment complex operations** for clarity

## Quick Reference: Mathematical Functions
- `sin()`, `cos()`, `tan()` - trigonometry
- `sqrt()`, `pow()` - power functions  
- `abs()`, `sign()` - absolute value, sign
- `min()`, `max()` - minimum, maximum
- `len()` - length of list/string
- `PI` - mathematical constant π