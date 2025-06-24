# Variable-Density Reinforcement in G-code (PrusaSlicer)

## 1. Goal

Enable the MCP server to generate G-code that **reinforces the outer regions** of a printed part (e.g. gear teeth) while keeping the inner core light.  
Initial MVP: radial strategy – *r < R_inner ➜ low infill*, *r > R_outer ➜ high infill*, smooth transition in between.

## 2. What PrusaSlicer Already Offers

| Feature | CLI Support | Notes |
|---------|-------------|-------|
| **Modifier meshes** (a.k.a. "parts" / *STL modifiers*) | `--modifier <file>` & per-modifier config keys | Official, robust. Any closed mesh can override settings such as `fill_density`, `fill_pattern`, `perimeters`, `speed` … |
| **Variable layer height / adaptive infill** | `--adaptive-layer-height` | Orthogonal to radial density, not sufficient alone. |
| **Per-object settings in 3MF** | Prepare 3MF scene, slice headless | More flexible but heavier to generate. |
| **Post-processing scripts** | `--post-process <script>` | Runs after slicing; can mutate G-code – we already use this (see `GCodePostProcessor.apply_variable_density`). |

Sources: PrusaSlicer help, CLI `--help`, and the official *First print* guide [link](https://help.prusa3d.com/article/first-print-with-prusaslicer_1753).

## 3. Implementation Strategies

### A. Modifier-Mesh Method (Preferred)
1. **Generate a ring (or any shape) STL** that covers the regions to reinforce.  
   *For a gear*: difference of two cylinders → hollow ring over teeth.
2. Call PrusaSlicer headless:
   ```bash
   prusa-slicer input.stl \
       --modifier outer_ring.stl \
       --fill-density 70% \           # for the modifier only
       --fill-density 20% --object input.stl \  # default
       --merge --output output.gcode
   ```
   `--modifier` automatically applies to overlapping volume. CLI accepts multiple modifiers.
3. Pros
   * Native, keeps PrusaSlicer's path planning (no E-value hacks).
   * Works with supports, sequential printing, etc.
4. Cons
   * We must create/clean temporary STLs per print.

### B. Post-Process Method (Fallback)
Keep `GCodePostProcessor.apply_variable_density` but improve:
* Detect infill moves via `;TYPE:Internal infill` (already used).
* Use extrusion width to scale *flow* instead of raw *E*, to stay consistent with volumetric flow.
* Pros: single G-code file, no extra meshes.
* Cons: breaks Prusa preview, risk of under/over-extrusion.

## 4. Proposed Pipeline Changes

1. **Extend `VariableDensityConfig`**
   ```python
   class VariableDensityConfig:
       center_point: Tuple[float, float]
       inner_radius: float
       outer_radius: float
       inner_density: int  # %
       outer_density: int  # %
       method: Literal["modifier", "post"] = "modifier"
   ```

2. **Generate Modifier STL (if method=="modifier")**
   * Use `trimesh` or OpenSCAD CLI to create a ring:
     ```openscad
     difference() {
       cylinder(h=part_height, r=outer_radius);
       cylinder(h=part_height+1, r=inner_radius);
     }
     ```
   * Export to temp file.

3. **Update `PrusaSlicerManager.slice_stl`**
   * Build CLI with `--modifier` and per-modifier density keys:  
     `--modifier ring.stl --modifier-fill-density 70%` (actual CLI syntax: `--modifier ring.stl --fill-density 70%` immediately after).  
   * Keep base object density from profile.

4. **Fallback to Post-Process**
   * If `method=="post"` or CLI fails (old PrusaSlicer), call improved `apply_variable_density()`.

5. **API Surface**
   * `generate_gcode()` gains `method="modifier"` | `"post"`.
   * Chat agent can propose prompts like:  
     *"Make inner 15 % and outer 60 % infill, method modifier."*

6. **Testing**
   * Unit test: slice a 40 mm test cylinder with 20/60 % settings, parse resulting G-code & verify density difference via `;INFILL_BODY` area.
   * Visual test: open in PrusaSlicer preview, observe orange (dense) ring.

## 5. Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| CLI syntax differences across versions | Detect `prusa-slicer --version`; adjust flags accordingly. |
| Modifier mesh Z-height mismatch | Use model's bounding box height ±1 mm. |
| Users specify complex shapes (non-radial) | MVP is radial; future: accept user-supplied modifier STLs. |
| Post-process may break volumetric flow | Keep modifier as default; document fallback. |

## 6. Milestones
1. **PoC**: Manual ring STL, slice via CLI → see dense ring preview.
2. **Automated STL generation** inside `PrusaSlicerManager`.
3. **Config wiring** from `generate_gcode()` tool & UI.
4. **Fallback post-process** hardening.
5. **Docs & examples** – update README and add chat prompt examples.

---
*After agreement on this plan we can start coding (estimated 2–3 sessions).* 