// Quality settings
$fa = 1;
$fs = 0.4;
$fn = 64;

// Gear parameters
small_teeth = 12;
large_teeth = 24;
module_size = 3.2;
pressure_angle = 20;

// Calculate proper gear dimensions
small_pitch_radius = module_size * small_teeth / 2;
large_pitch_radius = module_size * large_teeth / 2;
center_distance = small_pitch_radius + large_pitch_radius;

// Tooth proportions
addendum = module_size;
dedendum = module_size * 1.25;

small_outer_radius = small_pitch_radius + addendum;
small_root_radius = small_pitch_radius - dedendum;
large_outer_radius = large_pitch_radius + addendum;
large_root_radius = large_pitch_radius - dedendum;

// Generate involute-like tooth profile points
function gear_tooth_points(num_teeth, pitch_radius, outer_radius, root_radius) =
    let(
        tooth_angle = 360 / num_teeth,
        half_tooth_angle = tooth_angle / 4,
        // Create curved tooth profile approximating involute
        root_half_width = tooth_angle / 3,
        pitch_half_width = tooth_angle / 4.5,
        tip_half_width = tooth_angle / 6
    )
    [
        // Left side of tooth (root to tip)
        [root_radius * cos(-root_half_width), root_radius * sin(-root_half_width)],
        [(root_radius + pitch_radius)/2 * cos(-pitch_half_width * 1.2), 
         (root_radius + pitch_radius)/2 * sin(-pitch_half_width * 1.2)],
        [pitch_radius * cos(-pitch_half_width), pitch_radius * sin(-pitch_half_width)],
        [(pitch_radius + outer_radius)/2 * cos(-tip_half_width * 1.2), 
         (pitch_radius + outer_radius)/2 * sin(-tip_half_width * 1.2)],
        [outer_radius * cos(-tip_half_width), outer_radius * sin(-tip_half_width)],
        
        // Tip curve
        [outer_radius * cos(0), outer_radius * sin(0)],
        
        // Right side of tooth (tip to root)
        [outer_radius * cos(tip_half_width), outer_radius * sin(tip_half_width)],
        [(pitch_radius + outer_radius)/2 * cos(tip_half_width * 1.2), 
         (pitch_radius + outer_radius)/2 * sin(tip_half_width * 1.2)],
        [pitch_radius * cos(pitch_half_width), pitch_radius * sin(pitch_half_width)],
        [(root_radius + pitch_radius)/2 * cos(pitch_half_width * 1.2), 
         (root_radius + pitch_radius)/2 * sin(pitch_half_width * 1.2)],
        [root_radius * cos(root_half_width), root_radius * sin(root_half_width)]
    ];

// Create involute gear with proper tooth profile
module involute_gear_accurate(num_teeth, pitch_radius, outer_radius, root_radius, bore_radius, gear_color) {
    color(gear_color) {
        difference() {
            union() {
                // Root circle
                circle(r = root_radius);
                
                // Add each tooth with proper involute-like profile
                for (i = [0:num_teeth-1]) {
                    rotate([0, 0, i * 360/num_teeth]) {
                        tooth_points = gear_tooth_points(num_teeth, pitch_radius, outer_radius, root_radius);
                        polygon(tooth_points);
                    }
                }
            }
            
            // Central bore
            circle(r = bore_radius);
        }
    }
}

// Small red gear
translate([-center_distance/2, 0, 0]) {
    involute_gear_accurate(
        num_teeth = small_teeth,
        pitch_radius = small_pitch_radius,
        outer_radius = small_outer_radius,
        root_radius = small_root_radius,
        bore_radius = 4,
        gear_color = "red"
    );
}

// Large green gear - positioned to mesh properly
translate([center_distance/2, 0, 0]) {
    rotate([0, 0, 180/large_teeth]) { // Offset for proper tooth-to-space meshing
        involute_gear_accurate(
            num_teeth = large_teeth,
            pitch_radius = large_pitch_radius,
            outer_radius = large_outer_radius,
            root_radius = large_root_radius,
            bore_radius = 6,
            gear_color = "green"
        );
    }
}