# BOSL2 Gear Overlap Visualization Examples

## Overview

This file contains complete, testable OpenSCAD scripts that demonstrate various techniques for visualizing gear interference and overlapping regions. These examples recreate the BOSL2 wiki visualization techniques and provide debugging tools for gear collision detection.

## Example 1: Basic Intersection Detection

This example shows two gears with their overlapping regions highlighted in red.

```openscad
include <BOSL2/std.scad>
include <BOSL2/gears.scad>
$fa = 1; $fs = 0.4; $fn = 64;

// Gear parameters
teeth1 = 20;
teeth2 = 30; 
circ_pitch = 6;
thickness = 8;

// Calculate center distance (intentionally too close to create overlap)
normal_distance = gear_dist(circ_pitch=circ_pitch, teeth1=teeth1, teeth2=teeth2);
overlap_distance = normal_distance * 0.85; // 15% closer = overlap

// First gear - semi-transparent blue
color("blue", 0.6) 
    spur_gear(circ_pitch=circ_pitch, teeth=teeth1, thickness=thickness, shaft_diam=5);

// Second gear - semi-transparent green, positioned too close
color("green", 0.6)
    translate([overlap_distance, 0, 0])
        spur_gear(circ_pitch=circ_pitch, teeth=teeth2, thickness=thickness, shaft_diam=5);

// Intersection (overlap) - solid red
color("red", 1.0) 
    intersection() {
        spur_gear(circ_pitch=circ_pitch, teeth=teeth1, thickness=thickness, shaft_diam=5);
        translate([overlap_distance, 0, 0])
            spur_gear(circ_pitch=circ_pitch, teeth=teeth2, thickness=thickness, shaft_diam=5);
    }

echo(str("Normal distance: ", normal_distance, "mm"));
echo(str("Overlap distance: ", overlap_distance, "mm"));
echo(str("Interference: ", normal_distance - overlap_distance, "mm"));
```

**Expected Result**: Two semi-transparent gears with red interference regions clearly visible where teeth overlap.

---

## Example 2: Transparency Layering Method

This demonstrates the layered transparency approach for visualizing gear conflicts.

```openscad
include <BOSL2/std.scad>
include <BOSL2/gears.scad>
$fa = 1; $fs = 0.4; $fn = 64;

// Parameters for problematic gear pair
teeth_small = 18;
teeth_ring = 20;
circ_pitch = 5;
thickness = 6;

// Calculate distances
center_dist = gear_dist(circ_pitch=circ_pitch, teeth1=teeth_small, teeth2=0); 

// Small spur gear - transparent yellow
color("gold", 0.5) 
    spur_gear(circ_pitch=circ_pitch, teeth=teeth_small, thickness=thickness, shaft_diam=4);

// Ring gear - transparent blue (this should show interference)
color("blue", 0.5)
    ring_gear(circ_pitch=circ_pitch, teeth=teeth_ring, thickness=thickness, backing=4);

// Show interference between spur gear and ring gear interior
color("red", 0.9) 
    intersection() {
        spur_gear(circ_pitch=circ_pitch, teeth=teeth_small, thickness=thickness, shaft_diam=4);
        ring_gear(circ_pitch=circ_pitch, teeth=teeth_ring, thickness=thickness, backing=4);
    }

// Add text annotation
translate([0, 0, thickness + 2])
    linear_extrude(1)
        text("18T spur vs 20T ring - RED = INTERFERENCE", size=2, halign="center");
```

**Expected Result**: Shows the classic BOSL2 example of a spur gear that doesn't fit inside a ring gear, with red interference regions.

---

## Example 3: Profile Shift Problem Demonstration

Recreates the BOSL2 wiki figure showing profile shift solutions.

```openscad
include <BOSL2/std.scad>
include <BOSL2/gears.scad>
$fa = 1; $fs = 0.4; $fn = 64;

// Problem case parameters
sun_teeth = 5;  // Very few teeth - will need profile shift
ring_teeth = 50;
circ_pitch = 4;
thickness = 8;

// Side-by-side comparison
translate([-30, 0, 0]) {
    // LEFT SIDE: Without profile shift (shows interference)
    
    // Sun gear - transparent orange
    color("orange", 0.6)
        spur_gear(circ_pitch=circ_pitch, teeth=sun_teeth, thickness=thickness, 
                  shaft_diam=3, profile_shift=0);
    
    // Ring gear - transparent gray
    color("gray", 0.6)
        ring_gear(circ_pitch=circ_pitch, teeth=ring_teeth, thickness=thickness, 
                  backing=5, profile_shift=0);
    
    // Show interference
    color("red", 1.0) 
        intersection() {
            spur_gear(circ_pitch=circ_pitch, teeth=sun_teeth, thickness=thickness, 
                      shaft_diam=3, profile_shift=0);
            ring_gear(circ_pitch=circ_pitch, teeth=ring_teeth, thickness=thickness, 
                      backing=5, profile_shift=0);
        }
    
    // Label
    translate([0, -35, 0])
        linear_extrude(1)
            text("WITHOUT\nPROFILE SHIFT", size=3, halign="center");
}

translate([30, 0, 0]) {
    // RIGHT SIDE: With profile shift (no interference)
    
    // Calculate appropriate profile shift
    profile_shift_amount = auto_profile_shift(sun_teeth);
    
    // Sun gear - transparent orange with profile shift
    color("orange", 0.6)
        spur_gear(circ_pitch=circ_pitch, teeth=sun_teeth, thickness=thickness, 
                  shaft_diam=3, profile_shift=profile_shift_amount);
    
    // Ring gear - transparent gray with matching profile shift
    color("gray", 0.6)
        ring_gear(circ_pitch=circ_pitch, teeth=ring_teeth, thickness=thickness, 
                  backing=5, profile_shift=profile_shift_amount);
    
    // Show intersection (should be minimal/none)
    color("red", 1.0) 
        intersection() {
            spur_gear(circ_pitch=circ_pitch, teeth=sun_teeth, thickness=thickness, 
                      shaft_diam=3, profile_shift=profile_shift_amount);
            ring_gear(circ_pitch=circ_pitch, teeth=ring_teeth, thickness=thickness, 
                      backing=5, profile_shift=profile_shift_amount);
        }
    
    // Label
    translate([0, -35, 0])
        linear_extrude(1)
            text("WITH\nPROFILE SHIFT", size=3, halign="center");
}

echo(str("Auto profile shift for ", sun_teeth, " teeth: ", auto_profile_shift(sun_teeth)));
```

**Expected Result**: Side-by-side comparison showing interference on the left (red regions) and proper meshing on the right.

---

## Example 4: Advanced Multi-Gear Assembly Visualization

Shows interference detection in a complex gear train.

```openscad
include <BOSL2/std.scad>
include <BOSL2/gears.scad>
$fa = 1; $fs = 0.4; $fn = 32;

// Multi-gear train with potential interferences
n1 = 12;  // Driver
n2 = 24;  // Intermediate  
n3 = 18;  // Output
circ_pitch = 5;
thickness = 8;

// Calculate distances
d12 = gear_dist(circ_pitch=circ_pitch, teeth1=n1, teeth2=n2);
d23 = gear_dist(circ_pitch=circ_pitch, teeth1=n2, teeth2=n3);

// Intentionally position gears with some interference for demonstration
gear2_pos = [d12 * 0.95, 0, 0];  // 5% too close
gear3_pos = [d12 * 0.95 + d23 * 0.9, 0, 0];  // 10% too close

// Gear 1 - transparent blue
color("blue", 0.5)
    spur_gear(circ_pitch=circ_pitch, teeth=n1, thickness=thickness, shaft_diam=4);

// Gear 2 - transparent green
color("green", 0.5)
    translate(gear2_pos)
        spur_gear(circ_pitch=circ_pitch, teeth=n2, thickness=thickness, shaft_diam=4);

// Gear 3 - transparent orange
color("orange", 0.5)
    translate(gear3_pos)
        spur_gear(circ_pitch=circ_pitch, teeth=n3, thickness=thickness, shaft_diam=4);

// Interference 1-2
color("red", 1.0)
    intersection() {
        spur_gear(circ_pitch=circ_pitch, teeth=n1, thickness=thickness, shaft_diam=4);
        translate(gear2_pos)
            spur_gear(circ_pitch=circ_pitch, teeth=n2, thickness=thickness, shaft_diam=4);
    }

// Interference 2-3
color("red", 1.0)
    intersection() {
        translate(gear2_pos)
            spur_gear(circ_pitch=circ_pitch, teeth=n2, thickness=thickness, shaft_diam=4);
        translate(gear3_pos)
            spur_gear(circ_pitch=circ_pitch, teeth=n3, thickness=thickness, shaft_diam=4);
    }

// Status indicators
translate([0, -25, 0]) {
    color("red") cube([5, 5, 2]);
    translate([7, 0, 0])
        linear_extrude(1)
            text("= INTERFERENCE", size=2);
}
```

**Expected Result**: Three-gear assembly with red interference regions showing where gears are positioned too close.

---

## Example 5: Debugging Helper Functions

Reusable modules for interference checking.

```openscad
include <BOSL2/std.scad>
include <BOSL2/gears.scad>
$fa = 1; $fs = 0.4; $fn = 64;

// Helper module: Check interference between two gears
module gear_interference_check(
    teeth1, teeth2,
    circ_pitch,
    thickness,
    position1 = [0,0,0],
    position2 = [0,0,0],
    show_gears = true,
    gear1_color = "blue",
    gear2_color = "green",
    interference_color = "red"
) {
    if (show_gears) {
        // Show semi-transparent gears
        color(gear1_color, 0.6) 
            translate(position1)
                spur_gear(circ_pitch=circ_pitch, teeth=teeth1, thickness=thickness, shaft_diam=5);
        
        color(gear2_color, 0.6)
            translate(position2)
                spur_gear(circ_pitch=circ_pitch, teeth=teeth2, thickness=thickness, shaft_diam=5);
    }
    
    // Always show interference
    color(interference_color, 1.0)
        intersection() {
            translate(position1)
                spur_gear(circ_pitch=circ_pitch, teeth=teeth1, thickness=thickness, shaft_diam=5);
            translate(position2)
                spur_gear(circ_pitch=circ_pitch, teeth=teeth2, thickness=thickness, shaft_diam=5);
        }
}

// Helper module: Calculate and display interference info
module gear_analysis(teeth1, teeth2, circ_pitch, actual_distance) {
    correct_distance = gear_dist(circ_pitch=circ_pitch, teeth1=teeth1, teeth2=teeth2);
    interference = correct_distance - actual_distance;
    
    echo(str("Gear Analysis:"));
    echo(str("  Teeth: ", teeth1, " vs ", teeth2));
    echo(str("  Correct distance: ", correct_distance, "mm"));
    echo(str("  Actual distance: ", actual_distance, "mm"));
    echo(str("  Interference: ", interference, "mm"));
    echo(str("  Status: ", interference > 0 ? "OVERLAPPING" : "PROPERLY SPACED"));
}

// Example usage of helper functions
teeth_a = 16;
teeth_b = 24;
pitch = 5;
thick = 8;

// Test with overlapping gears
test_distance = 15;  // Too close
gear_analysis(teeth_a, teeth_b, pitch, test_distance);

gear_interference_check(
    teeth1 = teeth_a,
    teeth2 = teeth_b, 
    circ_pitch = pitch,
    thickness = thick,
    position1 = [0, 0, 0],
    position2 = [test_distance, 0, 0]
);

// Add measurement indicators
color("black") {
    translate([test_distance/2, -15, 0])
        cylinder(h=1, r=0.5);
    translate([test_distance/2, -18, 0])
        linear_extrude(1)
            text(str(test_distance, "mm"), size=2, halign="center");
}
```

**Expected Result**: Reusable debugging tools that can be applied to any gear pair, with automatic interference calculation and console output.

---

## Usage Instructions

1. **Copy any complete example** into a new OpenSCAD file
2. **Ensure BOSL2 is installed** and accessible  
3. **Render with F5** (preview) to see the visualization
4. **Check console output** for numerical analysis
5. **Modify parameters** to test different scenarios

## Key Techniques Demonstrated

- **`intersection()`** - Find overlapping regions between gears
- **`color(name, alpha)`** - Create transparency effects  
- **Layered visualization** - Combine transparent gears with solid interference regions
- **Console analysis** - Use `echo()` for numerical feedback
- **Modular debugging** - Create reusable interference checking tools

## Testing Recommendations

- Start with **Example 1** for basic functionality
- Use **Example 5 helper functions** for systematic testing
- Modify distances and tooth counts to explore different interference scenarios
- Try with real gear parameters from your projects