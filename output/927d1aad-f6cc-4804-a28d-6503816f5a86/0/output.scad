// Two meshing gears - small red and large green
// Quality settings
$fa = 1;
$fs = 0.4;

// Import BOSL involute gear library
include <BOSL/constants.scad>
use <BOSL/involute_gears.scad>

// Gear specifications
small_teeth = 12;
large_teeth = 24;
mm_per_tooth = 8;  // Same for both gears to mesh properly
thickness = 6;     // Thickness for both gears
pressure_angle = 20;

// Calculate gear dimensions
small_pitch_radius = mm_per_tooth * small_teeth / (2 * PI);
large_pitch_radius = mm_per_tooth * large_teeth / (2 * PI);
center_distance = small_pitch_radius + large_pitch_radius;

echo("=== GEAR PAIR SPECIFICATIONS ===");
echo("Small gear - Teeth:", small_teeth, "Pitch radius:", small_pitch_radius, "mm");
echo("Large gear - Teeth:", large_teeth, "Pitch radius:", large_pitch_radius, "mm");
echo("Center distance:", center_distance, "mm");
echo("Gear ratio:", large_teeth/small_teeth, ":1");

// Small red gear (left side)
translate([-center_distance/2, 0, 0]) {
    color("red")
    gear(
        mm_per_tooth = mm_per_tooth,
        number_of_teeth = small_teeth,
        thickness = thickness,
        hole_diameter = 8,  // Central bore
        pressure_angle = pressure_angle,
        clearance = 0.1,
        backlash = 0.05
    );
}

// Large green gear (right side) - rotated for proper meshing
translate([center_distance/2, 0, 0]) {
    rotate([0, 0, 180/large_teeth]) {  // Offset for proper tooth-to-gap meshing
        color("green")
        gear(
            mm_per_tooth = mm_per_tooth,
            number_of_teeth = large_teeth,
            thickness = thickness,
            hole_diameter = 12,  // Central bore
            pressure_angle = pressure_angle,
            clearance = 0.1,
            backlash = 0.05
        );
    }
}