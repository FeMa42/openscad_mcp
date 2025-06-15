// Quality settings for smooth rendering
$fa = 1;
$fs = 0.4;

// Import parameterizable gears library
use <gears.scad>

// Planetary gear system with 5 planet gears
// Standard parameters for a compact planetary system
modul = 2;                  // Module size (tooth pitch)
sun_teeth = 16;             // Sun gear teeth
planet_teeth = 9;           // Planet gear teeth (each of the 5 planets)
number_planets = 5;         // 5 planet gears as requested
width = 8;                  // Gear thickness
rim_width = 4;              // Ring gear rim thickness
bore = 6;                   // Central bore diameter
pressure_angle = 20;        // Standard pressure angle
helix_angle = 0;            // Straight spur gears (no helix)

echo("=== PLANETARY GEAR SYSTEM SPECIFICATIONS ===");
echo("Sun gear teeth:", sun_teeth);
echo("Planet gear teeth:", planet_teeth, "(each of", number_planets, "planets)");
echo("Ring gear teeth:", sun_teeth + 2*planet_teeth, "(calculated automatically)");
echo("Module:", modul, "mm");
echo("Gear ratio (input to output):", (sun_teeth + 2*planet_teeth)/sun_teeth, ":1");

// Color scheme for different components
color("gold") {
    // Complete planetary gear system
    planetary_gear(
        modul = modul,
        sun_teeth = sun_teeth,
        planet_teeth = planet_teeth,
        number_planets = number_planets,
        width = width,
        rim_width = rim_width,
        bore = bore,
        pressure_angle = pressure_angle,
        helix_angle = helix_angle,
        together_built = true,       // Assemble all components together
        optimized = true            // Add lightening holes for better aesthetics
    );
}