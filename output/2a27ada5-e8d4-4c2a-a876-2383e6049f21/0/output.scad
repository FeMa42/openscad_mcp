// Quality settings for smooth rendering
$fa = 0.5;
$fs = 0.1;

// Gear parameters
teeth = 20;
outer_radius = 40;  // mm
thickness = 5;      // mm
pressure_angle = 20; // degrees

// Calculate standard gear dimensions
module_size = (2 * outer_radius) / (teeth + 2); // 3.636mm
pitch_radius = module_size * teeth / 2;          // 36.36mm
root_radius = pitch_radius - 1.25 * module_size; // 31.82mm
base_radius = pitch_radius * cos(pressure_angle); // 34.15mm

echo("Gear specifications:");
echo("- Module:", module_size, "mm");
echo("- Pitch radius:", pitch_radius, "mm");
echo("- Root radius:", root_radius, "mm");
echo("- Actual tooth depth:", outer_radius - root_radius, "mm");

// Metallic steel finish
color([0.7, 0.75, 0.8]) 
difference() {
    // Main gear body with involute teeth
    linear_extrude(height = thickness, center = true) {
        gear_profile(teeth, outer_radius, pitch_radius, root_radius, pressure_angle);
    }
    
    // Hexagonal bore (10mm across flats)
    translate([0, 0, 0])
    linear_extrude(height = thickness + 2, center = true) {
        circle(d = 11.55, $fn = 6); // Hexagon with ~10mm across flats
    }
    
    // Optional: Add some lightening holes for realism
    for (angle = [0:45:315]) {
        rotate([0, 0, angle])
        translate([pitch_radius * 0.7, 0, 0])
        cylinder(h = thickness + 1, d = 4, center = true);
    }
}

// Main gear profile with involute teeth
module gear_profile(num_teeth, outer_r, pitch_r, root_r, press_angle) {
    tooth_angle = 360 / num_teeth;
    
    union() {
        // Root circle
        circle(r = root_r);
        
        // Generate all teeth
        for (i = [0:num_teeth-1]) {
            rotate([0, 0, i * tooth_angle]) {
                involute_tooth(outer_r, pitch_r, root_r, tooth_angle, press_angle);
            }
        }
    }
}

// Accurate involute tooth profile
module involute_tooth(outer_r, pitch_r, root_r, tooth_angle, press_angle) {
    // Calculate tooth dimensions
    circular_pitch = PI * 2 * pitch_r / teeth;
    tooth_thickness = circular_pitch / 2;
    tooth_half_angle = tooth_thickness / (2 * pitch_r) * 180/PI;
    
    // Create involute tooth shape
    intersection() {
        // Tooth sector
        pie_slice(outer_r, -tooth_half_angle * 0.8, tooth_half_angle * 0.8);
        
        // Tooth profile polygon (approximating involute)
        polygon([
            [root_r, -tooth_half_angle * root_r * PI/180 * 1.3],
            [pitch_r, -tooth_half_angle * pitch_r * PI/180],
            [outer_r, -tooth_half_angle * outer_r * PI/180 * 0.6],
            [outer_r, tooth_half_angle * outer_r * PI/180 * 0.6],
            [pitch_r, tooth_half_angle * pitch_r * PI/180],
            [root_r, tooth_half_angle * root_r * PI/180 * 1.3]
        ]);
    }
}

// Helper module for pie slice
module pie_slice(radius, start_angle, end_angle) {
    intersection() {
        circle(r = radius);
        polygon([
            [0, 0],
            [radius * cos(start_angle), radius * sin(start_angle)],
            for (a = [start_angle:1:end_angle]) [radius * cos(a), radius * sin(a)],
            [radius * cos(end_angle), radius * sin(end_angle)]
        ]);
    }
}
