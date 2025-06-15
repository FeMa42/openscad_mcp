// Raspberry Pi 3 Model B Enclosure Box - Open Top Case (Fixed)
// Quality settings
$fa = 1;
$fs = 0.4;

// Raspberry Pi 3 Model B dimensions (in mm)
pi_length = 85.6;
pi_width = 56.5;
pi_height = 17; // including components
board_thickness = 1.6;

// Box parameters
wall_thickness = 2;
clearance = 1.5; // clearance around the board
lid_height = 3;

// Case dimensions - NO ceiling, completely open at top
case_height = pi_height + clearance + 3; // Extra height for easy access
external_height = case_height + wall_thickness; // Just bottom + walls

// Internal dimensions
internal_length = pi_length + 2 * clearance;
internal_width = pi_width + 2 * clearance;

// External dimensions
external_length = internal_length + 2 * wall_thickness;
external_width = internal_width + 2 * wall_thickness;

// Mounting holes for Pi (relative to corner)
mounting_holes = [
    [3.5, 3.5],     // corner hole
    [61.5, 3.5],    // near USB ports
    [3.5, 52.5],    // near GPIO
    [61.5, 52.5]    // diagonal corner
];

module main_box() {
    difference() {
        // Start with solid cube
        cube([external_length, external_width, external_height]);
        
        // CUT AWAY THE TOP - this creates the open top
        translate([-1, -1, external_height - lid_height])
            cube([external_length + 2, external_width + 2, lid_height + 1]);
        
        // Inner cavity
        translate([wall_thickness, wall_thickness, wall_thickness])
            cube([internal_length, internal_width, case_height]);
        
        // Port cutouts - Based on Pi 3 specifications
        translate([wall_thickness + clearance, wall_thickness + clearance, wall_thickness]) {
            
            // USB ports (right side) - 4x USB 2.0 ports
            translate([69, 9, 0])
                cube([wall_thickness + 2, 13, 6]); // USB port 1
            translate([69, 24, 0])
                cube([wall_thickness + 2, 13, 6]); // USB port 2
            translate([69, 9, 6])
                cube([wall_thickness + 2, 13, 6]); // USB port 3 (stacked)
            translate([69, 24, 6])
                cube([wall_thickness + 2, 13, 6]); // USB port 4 (stacked)
            
            // Ethernet port (right side)
            translate([54, 10.25, 0])
                cube([wall_thickness + 2, 16, 13.5]);
        }
        
        // Front side ports
        translate([wall_thickness + clearance, 0, wall_thickness]) {
            // HDMI port
            translate([32, -1, 0])
                cube([15, wall_thickness + 2, 6]);
            
            // 3.5mm Audio jack
            translate([53.5, -1, 0])
                cube([7, wall_thickness + 2, 6]);
            
            // Micro USB power port
            translate([10.6, -1, 0])
                cube([8, wall_thickness + 2, 3]);
        }
        
        // Left side - MicroSD card slot
        translate([0, wall_thickness + clearance, wall_thickness]) {
            translate([-1, 22, 0])
                cube([wall_thickness + 2, 11.5, 3]);
        }
        
        // Back side - GPIO access
        translate([wall_thickness + clearance, wall_thickness + internal_width, wall_thickness]) {
            translate([1, -1, pi_height - 8.5])
                cube([52, wall_thickness + 2, 8.5]); // GPIO header clearance
        }
        
        // CSI Camera connector access
        translate([wall_thickness + clearance, wall_thickness + internal_width, wall_thickness]) {
            translate([45, -1, pi_height - 5])
                cube([22, wall_thickness + 2, 3]);
        }
        
        // DSI Display connector access  
        translate([0, wall_thickness + clearance, wall_thickness]) {
            translate([-1, 3, pi_height - 5])
                cube([wall_thickness + 2, 22, 3]);
        }
    }
    
    // Mounting posts for Pi - these sit on the bottom of the case
    translate([wall_thickness + clearance, wall_thickness + clearance, wall_thickness]) {
        for (hole = mounting_holes) {
            translate([hole[0], hole[1], 0]) {
                difference() {
                    cylinder(h = 3, d = 6);
                    cylinder(h = 3.1, d = 2.7); // M2.5 screw hole
                }
            }
        }
    }
}

// Completely separate lid piece
module lid() {
    translate([external_length + 10, 0, 0]) {
        difference() {
            union() {
                // Solid lid base
                cube([external_length, external_width, lid_height]);
                
                // Lid rim that fits inside the case for secure fit
                translate([wall_thickness + 0.2, wall_thickness + 0.2, -1.5])
                    cube([internal_length - 0.4, internal_width - 0.4, 1.5]);
            }
            
            // GPIO access hole
            translate([wall_thickness + clearance + 1, wall_thickness + clearance + 7, -0.1])
                cube([52, 5, lid_height + 0.2]);
            
            // Lid ventilation holes
            for (i = [0:6]) {
                for (j = [0:4]) {
                    translate([wall_thickness + 8 + i * 9, wall_thickness + 6 + j * 9, -0.1])
                        cylinder(h = lid_height + 0.2, d = 2.5);
                }
            }
            
            // Status LED viewing hole
            translate([wall_thickness + clearance + 8, wall_thickness + clearance + 5, -0.1])
                cylinder(h = lid_height + 0.2, d = 4);
            
            // Text on lid
            translate([external_length/2, external_width/2, lid_height - 0.5])
                linear_extrude(height = 0.6)
                    text("Raspberry Pi 3", size = 5, halign = "center", valign = "center");
        }
    }
}

// Assembly - show both pieces separately
main_box();
lid();