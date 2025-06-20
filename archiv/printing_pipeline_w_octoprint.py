#!/usr/bin/env python3
"""
G-code Generation Module for OpenSCAD MCP Server
Optimized for macOS with Prusa Core One and OctoPrint integration
"""

import os
import time
import random
import json
import asyncio
import subprocess
import tempfile
import requests
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import logging
from dataclasses import dataclass
import shutil


logger = logging.getLogger(__name__)
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "true").lower() == "true"

@dataclass
class PrinterProfile:
    """Printer configuration for slicing"""
    name: str
    bed_size: Tuple[int, int, int]  # x, y, z in mm
    nozzle_diameter: float
    filament_diameter: float
    max_print_speed: int
    layer_height_min: float
    layer_height_max: float
    extruder_temp_range: Tuple[int, int]
    bed_temp_range: Tuple[int, int]


@dataclass
class SlicingProfile:
    """Slicing parameters for different quality/use cases"""
    name: str
    layer_height: float
    perimeters: int
    top_solid_layers: int
    bottom_solid_layers: int
    infill_percentage: int
    infill_pattern: str
    print_speed: int
    travel_speed: int
    first_layer_speed: int
    supports: bool
    brim_width: float


@dataclass
class VariableDensityConfig:
    """Configuration for variable density printing"""
    center_point: Tuple[float, float]  # x, y coordinates
    inner_radius: float  # mm
    outer_radius: float  # mm
    inner_density: int  # percentage
    outer_density: int  # percentage
    transition_type: str  # "linear", "exponential", "step"


class PrusaSlicerManager:
    """Manages PrusaSlicer installation and execution on macOS"""

    def __init__(self, slicer_path: Optional[str] = None):
        self.slicer_path = self._find_prusaslicer_path(slicer_path)
        self.config_dir = Path.home() / "Library/Application Support/PrusaSlicer"
        self.profiles_dir = self.config_dir / "vendor"

        # Prusa Core One profile (updated for 2024 release)
        self.prusa_core_one = PrinterProfile(
            name="Prusa Core One",
            bed_size=(250, 220, 270),  # Core One specifications
            nozzle_diameter=0.4,
            filament_diameter=1.75,
            max_print_speed=200,
            layer_height_min=0.05,
            layer_height_max=0.35,
            extruder_temp_range=(170, 300),
            bed_temp_range=(10, 120)
        )

        # Predefined slicing profiles
        self.slicing_profiles = {
            "fast": SlicingProfile(
                name="Fast Print",
                layer_height=0.3,
                perimeters=2,
                top_solid_layers=3,
                bottom_solid_layers=3,
                infill_percentage=15,
                infill_pattern="grid",
                print_speed=60,
                travel_speed=120,
                first_layer_speed=30,
                supports=False,
                brim_width=0
            ),
            "quality": SlicingProfile(
                name="Quality Print",
                layer_height=0.2,
                perimeters=3,
                top_solid_layers=4,
                bottom_solid_layers=3,
                infill_percentage=20,
                infill_pattern="cubic",
                print_speed=45,
                travel_speed=120,
                first_layer_speed=20,
                supports=True,
                brim_width=2
            ),
            "strong": SlicingProfile(
                name="Strong Print",
                layer_height=0.25,
                perimeters=4,
                top_solid_layers=5,
                bottom_solid_layers=4,
                infill_percentage=40,
                infill_pattern="honeycomb",
                print_speed=40,
                travel_speed=100,
                first_layer_speed=15,
                supports=True,
                brim_width=3
            )
        }

    def _find_prusaslicer_path(self, custom_path: Optional[str] = None) -> str:
        """Find PrusaSlicer executable on macOS"""
        if custom_path and Path(custom_path).exists():
            return custom_path

        # Common PrusaSlicer locations on macOS
        possible_paths = [
            "/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer",
            "/Applications/Original Prusa Drivers/PrusaSlicer.app/Contents/MacOS/PrusaSlicer",
            "/usr/local/bin/prusa-slicer",
            str(Path.home() / "Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer")
        ]

        for path in possible_paths:
            if Path(path).exists():
                logger.info(f"Found PrusaSlicer at: {path}")
                return path

        # Try homebrew installation
        try:
            result = subprocess.run(["which", "prusa-slicer"],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass

        raise FileNotFoundError(
            "PrusaSlicer not found. Install via:\n"
            "1. Download from https://www.prusa3d.com/prusaslicer/\n"
            "2. Or install via Homebrew: brew install --cask prusa-slicer"
        )

    def install_prusa_profiles(self):
        """Ensure Prusa printer profiles are installed"""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True)

        # PrusaSlicer automatically downloads vendor profiles on first run
        # We just need to trigger a config initialization
        try:
            subprocess.run([
                self.slicer_path, "--help"
            ], capture_output=True, timeout=10)
        except subprocess.TimeoutExpired:
            pass  # Normal, just needed to initialize config

    async def slice_stl(self,
                        stl_path: str,
                        output_dir: str,
                        profile: str = "quality",
                        variable_density: Optional[VariableDensityConfig] = None,
                        custom_settings: Optional[Dict] = None) -> str:
        """
        Slice STL file to G-code using PrusaSlicer
        
        Args:
            stl_path: Path to STL file
            output_dir: Directory for output files
            profile: Slicing profile name ("fast", "quality", "strong")
            variable_density: Variable density configuration
            custom_settings: Additional slicer settings
        
        Returns:
            Path to generated G-code file
        """
        if not Path(stl_path).exists():
            raise FileNotFoundError(f"STL file not found: {stl_path}")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        gcode_file = output_path / "output.gcode"

        # Get slicing profile
        if profile not in self.slicing_profiles:
            raise ValueError(
                f"Unknown profile: {profile}. Available: {list(self.slicing_profiles.keys())}")

        slice_profile = self.slicing_profiles[profile]

        # Map our profiles to PrusaSlicer built-in profiles
        prusaslicer_profiles = {
            "fast": {
                "print_profile": "0.20mm SPEED @COREONE HF0.4",
                "material_profile": "Prusament PLA @COREONE HF0.4"
            },
            "quality": {
                "print_profile": "0.20mm STRUCTURAL @COREONE 0.4",
                "material_profile": "Prusament PLA @COREONE"
            },
            "strong": {
                "print_profile": "0.20mm STRUCTURAL @COREONE 0.4",
                "material_profile": "Prusament PLA @COREONE"
            }
        }

        profile_settings = prusaslicer_profiles[profile]

        # Choose appropriate printer profile based on print profile
        if "HF0.4" in profile_settings["print_profile"]:
            printer_profile = "Prusa CORE One HF0.4 nozzle"
        else:
            printer_profile = "Prusa CORE One 0.4 nozzle"

        # Build PrusaSlicer command
        cmd = [
            self.slicer_path,
            "--export-gcode",  # Action: export G-code
            "--printer-profile", printer_profile,  # Printer preset
            # Print preset
            "--print-profile", profile_settings["print_profile"],
            # Material preset
            "--material-profile", profile_settings["material_profile"],
            "--output", str(gcode_file),
            stl_path
        ]

        # Add custom settings if provided
        if custom_settings:
            for key, value in custom_settings.items():
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])

        logger.info(f"Slicing with command: {' '.join(cmd)}")

        # Execute slicing
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown slicing error"
            logger.error(f"Slicing failed: {error_msg}")
            raise RuntimeError(f"PrusaSlicer failed: {error_msg}")

        if not gcode_file.exists():
            raise RuntimeError("G-code file was not generated")

        # Apply variable density post-processing if specified
        if variable_density:
            logger.info("Applying variable density post-processing...")
            gcode_file = GCodePostProcessor.apply_variable_density(
                str(gcode_file), variable_density)

        logger.info(f"G-code generated: {gcode_file}")
        return str(gcode_file)

    def _create_config_file(self, profile: SlicingProfile, custom_settings: Optional[Dict] = None) -> str:
        """Create temporary PrusaSlicer config file"""
        config = {
            # Layer settings
            "layer_height": profile.layer_height,
            "first_layer_height": profile.layer_height * 1.2,

            # Perimeter settings
            "perimeters": profile.perimeters,
            "external_perimeters_first": "0",

            # Infill settings
            "fill_density": f"{profile.infill_percentage}%",
            "fill_pattern": profile.infill_pattern,
            "top_solid_layers": profile.top_solid_layers,
            "bottom_solid_layers": profile.bottom_solid_layers,

            # Speed settings
            "perimeter_speed": profile.print_speed,
            "small_perimeter_speed": profile.print_speed * 0.8,
            "external_perimeter_speed": profile.print_speed * 0.7,
            "infill_speed": profile.print_speed * 1.2,
            "solid_infill_speed": profile.print_speed,
            "top_solid_infill_speed": profile.print_speed * 0.8,
            "travel_speed": profile.travel_speed,
            "first_layer_speed": profile.first_layer_speed,

            # Support settings
            "support_material": "1" if profile.supports else "0",
            "support_material_auto": "1" if profile.supports else "0",

            # Adhesion settings
            "brim_width": profile.brim_width,

            # Quality settings
            "avoid_crossing_perimeters": "1",
            "thin_walls": "1",
            "overhangs": "1",

            # Prusa Core One specific settings
            "printer_model": "CORE_ONE",
            "nozzle_diameter": "0.4",
            "filament_diameter": "1.75",
            "bed_shape": "0x0,250x0,250x220,0x220",

            # Temperature settings (PLA defaults)
            "temperature": "215",
            "first_layer_temperature": "215",
            "bed_temperature": "60",
            "first_layer_bed_temperature": "60"
        }

        # Apply custom settings
        if custom_settings:
            config.update(custom_settings)

        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("[print]\n")
            for key, value in config.items():
                f.write(f"{key} = {value}\n")

            return f.name

    async def _add_variable_density(self, cmd: List[str], stl_path: str,
                                    config: VariableDensityConfig) -> List[str]:
        """Add variable density support using modifier meshes"""
        # For true variable density, we'd need to:
        # 1. Create modifier meshes for different regions
        # 2. Use PrusaSlicer's modifier mesh feature
        # 3. Or post-process the G-code

        # For now, we'll implement post-processing approach
        # This is more universal and doesn't require complex mesh operations

        # The actual implementation would modify the slicing command
        # to include post-processing scripts

        logger.info(
            f"Variable density config: inner={config.inner_density}%, outer={config.outer_density}%")
        return cmd


class GCodePostProcessor:
    """Post-process G-code for variable density and optimization"""

    @staticmethod
    def apply_variable_density(gcode_path: str, config: VariableDensityConfig) -> str:
        """Apply variable density to existing G-code"""
        with open(gcode_path, 'r') as f:
            lines = f.readlines()

        modified_lines = []
        current_x, current_y = 0.0, 0.0
        in_infill = False

        for line in lines:
            # Track position
            if 'X' in line:
                try:
                    current_x = float(line.split('X')[1].split()[0])
                except:
                    pass
            if 'Y' in line:
                try:
                    current_y = float(line.split('Y')[1].split()[0])
                except:
                    pass

            # Detect infill sections
            if ';TYPE:Internal infill' in line:
                in_infill = True
            elif ';TYPE:' in line and 'infill' not in line.lower():
                in_infill = False

            # Modify extrusion rate for infill based on distance from center
            if in_infill and 'E' in line and 'G1' in line:
                distance = ((current_x - config.center_point[0])**2 +
                            (current_y - config.center_point[1])**2)**0.5

                # Calculate density multiplier
                if distance <= config.inner_radius:
                    multiplier = config.inner_density / 100.0
                elif distance >= config.outer_radius:
                    multiplier = config.outer_density / 100.0
                else:
                    # Linear interpolation in transition zone
                    ratio = (distance - config.inner_radius) / \
                        (config.outer_radius - config.inner_radius)
                    multiplier = (config.inner_density +
                                  ratio * (config.outer_density - config.inner_density)) / 100.0

                # Modify E value
                if 'E' in line:
                    try:
                        e_start = line.find('E') + 1
                        e_end = line.find(' ', e_start)
                        if e_end == -1:
                            e_end = len(line.rstrip())

                        e_value = float(line[e_start:e_end])
                        new_e_value = e_value * multiplier

                        modified_line = line[:e_start] + \
                            f"{new_e_value:.5f}" + line[e_end:]
                        line = modified_line
                    except:
                        pass  # Keep original line if parsing fails

            modified_lines.append(line)

        # Write modified G-code
        output_path = gcode_path.replace('.gcode', '_variable_density.gcode')
        with open(output_path, 'w') as f:
            f.writelines(modified_lines)

        return output_path


class OctoPrintManager:
    """Manage OctoPrint integration for automatic printing"""

    def __init__(self, host: str, api_key: str, port: int = 80):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.base_url = f"http://{host}:{port}/api"
        self.headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }

    def check_connection(self) -> bool:
        """Test OctoPrint connection"""
        try:
            response = requests.get(
                f"{self.base_url}/connection", headers=self.headers, timeout=5)
            return response.status_code == 200
        except:
            return False

    def upload_gcode(self, gcode_path: str, filename: Optional[str] = None) -> str:
        """Upload G-code file to OctoPrint"""
        if not filename:
            filename = Path(gcode_path).name

        with open(gcode_path, 'rb') as f:
            files = {'file': (filename, f, 'text/plain')}
            # Remove Content-Type for file upload
            headers = {"X-Api-Key": self.api_key}

            response = requests.post(
                f"{self.base_url}/files/local",
                files=files,
                headers=headers
            )

        if response.status_code == 201:
            return response.json()['files']['local']['name']
        else:
            raise RuntimeError(f"Upload failed: {response.text}")

    def start_print(self, filename: str) -> bool:
        """Start printing uploaded file"""
        data = {
            "command": "select",
            "path": filename,
            "print": True
        }

        response = requests.post(
            f"{self.base_url}/files/local/{filename}",
            json=data,
            headers=self.headers
        )

        return response.status_code == 204


class DummyOctoPrintManager:
    """Dummy OctoPrint manager for development testing"""

    def __init__(self, host: str, api_key: str, port: int = 80):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.base_url = f"http://{host}:{port}/api"

        # Simulate various connection states for testing
        self.connection_success_rate = 0.95  # 95% success rate
        self.upload_delay = 2.0  # Simulate upload time

    def check_connection(self) -> bool:
        """Simulate connection check with occasional failures"""
        if DEVELOPMENT_MODE:
            # Simulate network delay
            time.sleep(0.5)
            return random.random() < self.connection_success_rate
        else:
            # Real implementation would go here
            return False

    def upload_gcode(self, gcode_path: str, filename: Optional[str] = None) -> str:
        """Simulate G-code upload with realistic behavior"""
        if not filename:
            filename = Path(gcode_path).name

        if DEVELOPMENT_MODE:
            # Check if file actually exists
            if not Path(gcode_path).exists():
                raise RuntimeError(f"G-code file not found: {gcode_path}")

            # Simulate upload time based on file size
            file_size = Path(gcode_path).stat().st_size
            upload_time = min(file_size / (1024 * 1024) * 2,
                              10)  # 2 seconds per MB, max 10s
            time.sleep(upload_time)

            # Simulate occasional upload failures
            if random.random() < 0.05:  # 5% failure rate
                raise RuntimeError("Upload failed: Network timeout")

            # Generate realistic filename
            return f"openscad_model_{int(time.time())}.gcode"
        else:
            # Real implementation would go here
            raise RuntimeError(
                "Real OctoPrint integration not implemented yet")

    def start_print(self, filename: str) -> bool:
        """Simulate print start with validation"""
        if DEVELOPMENT_MODE:
            # Simulate printer state checks
            time.sleep(1.0)

            # Simulate various failure conditions
            failure_scenarios = [
                (0.02, "Printer not connected"),
                (0.01, "Print bed not heated"),
                (0.01, "Filament not detected"),
                (0.005, "Previous print not cleared")
            ]

            for probability, error in failure_scenarios:
                if random.random() < probability:
                    raise RuntimeError(f"Cannot start print: {error}")

            return True
        else:
            # Real implementation would go here
            raise RuntimeError(
                "Real OctoPrint integration not implemented yet")


class PrintingPipeline:
    """Complete printing pipeline from STL to print job"""

    def __init__(self,
                 slicer_path: Optional[str] = None,
                 octoprint_host: Optional[str] = None,
                 octoprint_api_key: Optional[str] = None):
        self.slicer = PrusaSlicerManager(slicer_path)
        self.octoprint = None

        if octoprint_host and octoprint_api_key:
            if DEVELOPMENT_MODE:
                self.octoprint = DummyOctoPrintManager(
                    octoprint_host, octoprint_api_key)
            else:
                self.octoprint = OctoPrintManager(
                    octoprint_host, octoprint_api_key)

    async def process_and_print(self,
                                stl_path: str,
                                output_dir: str,
                                profile: str = "quality",
                                variable_density: Optional[VariableDensityConfig] = None,
                                auto_start_print: bool = False,
                                custom_settings: Optional[Dict] = None) -> Dict:
        """
        Complete pipeline: STL → G-code → OctoPrint
        
        Returns:
            Dictionary with processing results and file paths
        """
        results = {
            "stl_path": stl_path,
            "profile": profile,
            "success": False,
            "development_mode": DEVELOPMENT_MODE
        }

        try:
            # Step 1: Slice to G-code
            logger.info("Starting slicing process...")
            gcode_path = await self.slicer.slice_stl(
                stl_path=stl_path,
                output_dir=output_dir,
                profile=profile,
                variable_density=variable_density,
                custom_settings=custom_settings
            )
            results["gcode_path"] = gcode_path

            # Step 2: Apply variable density post-processing if needed
            if variable_density:
                logger.info("Applying variable density post-processing...")
                gcode_path = GCodePostProcessor.apply_variable_density(
                    gcode_path, variable_density)
                results["processed_gcode_path"] = gcode_path

            # Step 3: OctoPrint integration (real or dummy)
            if self.octoprint:
                logger.info("Checking OctoPrint connection...")
                if not self.octoprint.check_connection():
                    raise RuntimeError("Cannot connect to OctoPrint")

                logger.info("Uploading to OctoPrint...")
                uploaded_filename = self.octoprint.upload_gcode(gcode_path)
                results["uploaded_filename"] = uploaded_filename

                # Step 4: Start print if requested
                if auto_start_print:
                    logger.info("Starting print job...")
                    print_started = self.octoprint.start_print(
                        uploaded_filename)
                    results["print_started"] = print_started
            elif auto_start_print:
                # Fallback for when OctoPrint is not configured
                logger.warning(
                    "OctoPrint not configured, cannot auto-start print")
                results["warning"] = "Auto-print requested but OctoPrint not configured"

            results["success"] = True
            logger.info("Pipeline completed successfully")

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            results["error"] = str(e)
            raise

        return results

# Integration function for MCP server


async def generate_and_print_gcode(
    stl_path: str,
    output_dir: str,
    strengthen_radius: float = 50.0,
    inner_density: int = 15,
    outer_density: int = 60,
    profile: str = "quality",
    auto_print: bool = False
) -> str:
    """
    Generate G-code with enhanced status reporting for development
    """

    # Get center point of the model (simplified - assumes center of bed)
    center_point = (125.0, 110.0)  # Center of Prusa Core One bed

    # Create variable density configuration
    variable_density = VariableDensityConfig(
        center_point=center_point,
        inner_radius=strengthen_radius * 0.9,
        outer_radius=strengthen_radius * 1.1,
        inner_density=inner_density,
        outer_density=outer_density,
        transition_type="linear"
    )

    # Initialize pipeline with environment-based OctoPrint config
    pipeline = PrintingPipeline(
        octoprint_host=os.getenv("OCTOPRINT_HOST", "octopi.local"),
        octoprint_api_key=os.getenv("OCTOPRINT_API_KEY", "demo-key")
    )

    try:
        results = await pipeline.process_and_print(
            stl_path=stl_path,
            output_dir=output_dir,
            profile=profile,
            variable_density=variable_density,
            auto_start_print=auto_print
        )

        # Enhanced status message with development indicators
        status = f"✅ G-code generation successful!\n"

        if results.get("development_mode"):
            status += f"🧪 Development Mode: OctoPrint simulation active\n"

        status += f"\n📁 **Files:**\n"
        status += f"   STL: {results['stl_path']}\n"
        status += f"   G-code: {results['gcode_path']}\n"

        if "processed_gcode_path" in results:
            status += f"   Variable density G-code: {results['processed_gcode_path']}\n"

        status += f"\n🔧 **Print Settings:**\n"
        status += f"   Profile: {results['profile']}\n"
        status += f"   Variable density strategy:\n"
        status += f"      - Inner zone (r<{strengthen_radius*0.9:.1f}mm): {inner_density}% infill\n"
        status += f"      - Transition zone ({strengthen_radius*0.9:.1f}-{strengthen_radius*1.1:.1f}mm): gradient\n"
        status += f"      - Outer zone (r>{strengthen_radius*1.1:.1f}mm): {outer_density}% infill\n"

        if "uploaded_filename" in results:
            printer_emoji = "🖨️" if results.get("development_mode") else "☁️"
            status += f"\n{printer_emoji} **OctoPrint:**\n"
            status += f"   Uploaded: {results['uploaded_filename']}\n"

            if results.get("print_started"):
                status += f"   🚀 Print job started automatically\n"
                if results.get("development_mode"):
                    status += f"   📝 Note: Simulated print start (development mode)\n"

        if "warning" in results:
            status += f"\n⚠️ Warning: {results['warning']}\n"

        # Add file size information
        gcode_path = results.get(
            "processed_gcode_path", results.get("gcode_path"))
        if gcode_path and Path(gcode_path).exists():
            file_size = Path(gcode_path).stat().st_size
            status += f"\n📊 **G-code Stats:**\n"
            status += f"   File size: {file_size / 1024:.1f} KB\n"

            # Estimate print time (rough calculation)
            estimated_time = file_size / (1024 * 100)  # Very rough estimate
            status += f"   Estimated print time: ~{estimated_time:.1f} hours\n"

        return status

    except Exception as e:
        error_status = f"❌ G-code generation failed: {str(e)}\n"
        if DEVELOPMENT_MODE:
            error_status += f"\n🧪 Development mode error - check implementation\n"
        return error_status
