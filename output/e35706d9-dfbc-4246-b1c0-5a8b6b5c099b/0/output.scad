// Detailed Planetary Gear System - 20cm outer diameter
use <parameterizable_gears/gears.scad>

$fa = 1;
$fs = 0.4;

// Gear parameters
module_size = 2.0;
pressure_angle = 20;
gear_height = 12;

// Teeth counts for proper meshing
sun_teeth = 18;
planet_teeth = 21;
ring_teeth = sun_teeth + 2 * planet_teeth; // 60 teeth

// Calculate positions
sun_radius = sun_teeth * module_size / 2;
planet_radius = planet_teeth * module_size / 2;
ring_radius = ring_teeth * module_size / 2;
planet_center_distance = sun_radius + planet_radius;

echo("=== Planetary Gear Specifications ===");
echo("Sun gear: ", sun_teeth, " teeth, diameter ", sun_teeth * module_size, "mm");
echo("Planet gears: ", planet_teeth, " teeth, diameter ", planet_teeth * module_size, "mm");
echo("Ring gear: ", ring_teeth, " teeth, inner diameter ", ring_teeth * module_size, "mm");
echo("System outer diameter: 200mm");

// Sun gear (central)
color("royalblue")
translate([0, 0, 0])
zahnrad(modul=module_size, zahnzahl=sun_teeth, breite=gear_height, 
         bohrung=8, eingriffswinkel=pressure_angle);

// Planet gears (3 units)
for(i = [0:2]) {
    angle = i * 120;
    color("lime")
    translate([planet_center_distance * cos(angle), 
               planet_center_distance * sin(angle), 0])
    zahnrad(modul=module_size, zahnzahl=planet_teeth, breite=gear_height,
            bohrung=6, eingriffswinkel=pressure_angle);
}

// Ring gear housing with internal teeth
color("red", 0.8)
difference() {
    // Outer housing - 200mm diameter as specified
    cylinder(h=gear_height, d=200, center=false);
    
    // Internal gear cavity
    translate([0, 0, -1])
    hohlrad(modul=module_size, zahnzahl=ring_teeth, breite=gear_height+2,
            eingriffswinkel=pressure_angle);
}

// Planet carrier
color("silver", 0.6)
translate([0, 0, gear_height + 0.5])
difference() {
    cylinder(h=5, d=planet_center_distance*2 + 25, center=false);
    
    // Central shaft hole
    translate([0, 0, -1])
    cylinder(h=7, d=12, center=false);
    
    // Planet pin holes
    for(i = [0:2]) {
        angle = i * 120;
        translate([planet_center_distance * cos(angle), 
                   planet_center_distance * sin(angle), -1])
        cylinder(h=7, d=8, center=false);
    }
}

// Planet pins
color("darkgray")
for(i = [0:2]) {
    angle = i * 120;
    translate([planet_center_distance * cos(angle), 
               planet_center_distance * sin(angle), 0])
    cylinder(h=gear_height + 6, d=5, center=false);
}

// Central drive shaft
color("darkgray")
translate([0, 0, -3])
cylinder(h=gear_height + 10, d=7, center=false);

// Annotations
color("white")
translate([0, 0, gear_height + 8])
linear_extrude(height=1)
text("Planetary Gear System", size=7, halign="center");

color("white")
translate([85, 0, gear_height + 8])
linear_extrude(height=1)
text("Ø200mm", size=5, halign="center");

// Gear ratio information
color("white")
translate([-90, -80, gear_height + 8])
linear_extrude(height=1)
text(str("Ratio: ", ring_teeth/sun_teeth, ":1"), size=4, halign="left");

// Show gear mesh points
color("yellow")
for(i = [0:2]) {
    angle = i * 120;
    // Sun-Planet mesh point
    mesh_distance = (sun_radius + planet_radius) / 2;
    translate([mesh_distance * cos(angle), mesh_distance * sin(angle), gear_height + 1])
    sphere(d=2);
    
    // Planet-Ring mesh point  
    ring_mesh_distance = (planet_radius + ring_radius) / 2;
    translate([ring_mesh_distance * cos(angle), ring_mesh_distance * sin(angle), gear_height + 1])
    sphere(d=2);
}
