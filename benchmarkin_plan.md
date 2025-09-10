### 1\. Experimental Setup and Prerequisites

Before starting the experiments, ensure the infrastructure is stable and reproducible.

#### 1.1. OpenSCAD MCP Server Validation

Ensure your MCP server is robust and exposes the necessary tools. The agent relies entirely on these tools for interaction.

* `list_openscad_libraries()`: Must return the available libraries and, crucially, the detailed documentation (function signatures and descriptions) for the `parameterizable_gears` library. The VLM needs to know which functions (e.g., `stirnrad`, `kegelrad`) and parameters (e.g., `modul`, `zaehnezahl`) exist.
* `render_scad(code: str)`: Must execute the OpenSCAD code and return:
  * **Success:** A high-quality PNG rendering (Use a fixed isometric view and resolution, e.g., 1024x1024, for consistency).
  * **Failure:** The compilation/syntax error log from OpenSCAD.

#### 1.2. Agent Harness and Configuration

You need a Python script (the "Harness") to manage the experiment loop, call VLM APIs, interact with the MCP server, and log results.

* **Models:** Claude 3.5 Sonnet, Claude 3.5 Opus, GPT-4o, Gemini 1.5 Pro, Gemini 1.5 Flash.
* **Parameters:** Set the temperature low (e.g., T=0.1) for reproducibility.
* **Maximum Iterations (k):** Set `k=5`. This allows sufficient opportunity for self-correction.
* **System Prompt:** Develop a standardized system prompt that enforces the agent's persona ("Bibliotheken zuerst, parametrisch immer"), explains the available MCP tools, and instructs the agent on the iterative workflow (Think -\> Plan -\> Execute -\> Observe/Critique -\> Correct).

### 2\. Benchmark Dataset Design (The GearSet Benchmark)

The benchmark should test tool selection, parameter mapping, reasoning/calculation, and spatial arrangement. We will define 12 standardized prompts (4 per level).

#### Level 1: Direct Parameter Mapping (Einfach)

Tests the ability to read documentation and correctly assign explicit values.

* **L1.1 (Stirnrad):** Erstelle ein Stirnrad mit 20 Zähnen, Modul 2 und einer Breite von 10 mm.
* **L1.2 (Kegelrad):** Erstelle ein Kegelrad mit 15 Zähnen, Modul 1.5, einem Winkel von 45 Grad und einer Breite von 10 mm.
* **L1.3 (schrägverzahntes Zahnrad):** Erstelle ein schrägverzahntes Zahnrad mit 25 Zähnen, Modul 1.5, Breite 8mm und einem Schrägungswinkel von 15 Grad.

#### Level 2: Implicit Parameters and Calculation (Mittel)

Tests the ability to derive required parameters from given constraints.

* **L2.1 (Modul Berechnung):** Ich benötige ein Stirnrad mit 35 Zähnen und einem Außendurchmesser (Kopfkreisdurchmesser) von 74 mm. Die Breite soll 10 mm betragen.
    - Challenge: Agent must calculate Modul ≈ 2.
* **L2.2 (Achsabstand Berechnung):** Konstruiere zwei Stirnräder mit Modul 1.5 und einem Übersetzungsverhältnis von 1:3. Der Achsabstand muss exakt 60 mm betragen.
    - Challenge: Solve system of equations: z2 = 3 *z1 AND 60 = 1.5* (z1 + z2) / 2. (Solution: z1=20, z2=60).
* **L2.3 (Planetengetriebe):** Erstelle ein Planetengetriebe mit Modul 1. Das Sonnenrad hat 24 Zähne und das Hohlrad hat 56 Zähne. Wähle eine passende Anzahl von Planetenrädern (N), sodass das System symmetrisch aufgebaut ist und funktioniert.
    - Challenge: Calculate planet teeth (z_p = (56-24)/2 = 16). Crucially, check the assembly condition: (z_s + z_r) / N must be an integer. (24+56)/N = 80/N. The agent must choose a valid N (e.g., N=4 or N=5).
* **L2.4 (Kegelradpaar):** Konstruiere ein Kegelradpaar (Modul 1.5, 15 und 30 Zähne) für eine 90-Grad-Umlenkung. Das Antriebsrad hat 15 Zähne, das Abtriebsrad 30. Beide haben Modul 1.5. Richte sie korrekt zueinander aus.
    - Challenge: The agent must either call the kegelradpaar function or use the kegelrad function twice.

#### Level 3: Multi-part Assembly and Spatial Reasoning (Schwer)

Tests the ability to generate multiple components and arrange them correctly in 3D space.

* **L3.1 (schrägverzahntes Zahnradpaar):** Konstruiere ein Paar schrägverzahnter Stirnräder (Helical Gears) mit Modul 2 und je 20 Zähnen. Der Schrägungswinkel soll 15 Grad betragen. Positioniere sie korrekt auf parallelen Achsen, sodass sie ineinandergreifen.
    - Challenge: The agent must realize that helical gears on parallel shafts must have opposite helix angles (one 15°, one -15°) to mesh correctly. It also requires calculating center distance and rotational alignment.
* **L3.2 (zweistufiges Getriebe):** Konstruiere ein zweistufiges Getriebe (Compound Gear Train). Stufe 1: 10 Zähne auf 30 Zähne. Stufe 2: 15 Zähne auf 45 Zähne. Modul 1. Die Zahnräder 30Z und 15Z sitzen fest auf derselben Zwischenwelle. Richte alle vier Räder korrekt aus.
    - Challenge: Complex spatial reasoning. Requires calculating two center distances and ensuring the middle two gears are coaxial and translated axially (e.g., along the Z-axis) to mesh with their respective partners.
* **L3.3 (Zahnstangengetriebe):** Erstelle ein Zahnstangengetriebe. Das Ritzel (Pinion) hat 15 Zähne, Modul 2. Die Zahnstange ist 150mm lang. Positioniere das Ritzel so, dass es mittig auf der Zahnstange sitzt und korrekt eingreift (nicht überlappt und nicht zu weit entfernt ist).
    - Challenge: Requires calculating the pitch radius and translating the pinion vertically by that exact amount relative to the rack. Highly dependent on visual feedback for fine-tuning the meshing.

#### 2.3. Ground Truth Definition

For every prompt, manually define:

1. **Target Parameters:** The exact parameters required (e.g., L2.1: Modul=2, Zähne=35, Breite=10).
2. **Target Code:** The ideal OpenSCAD script using the library.

### 3\. Evaluation Metrics

We will use the following quantitative metrics:

1. **Success Rate (SR@k):** The primary metric. The percentage of tasks successfully completed within `k=5` iterations. Success means the final code produces a model that matches the ground truth parameters and spatial arrangement.
2. **Parameter Accuracy (PA):** For successful tasks, the accuracy of the parameters used in the final OpenSCAD code compared to the ground truth.
3. **Code Validity Rate (CVR):** The percentage of all generated OpenSCAD snippets (across all iterations) that are syntactically correct and executable without error.
4. **Average Iterations to Success (AIS):** For successful tasks, the average number of iterations required. Lower is better (Efficiency).
5. **Self-Correction Ability (SCA):** The percentage of tasks where the agent failed on the first attempt (SR@1=Fail) but succeeded by the final attempt (SR@5=Success). This highlights the value of the visual feedback loop.

### 4\. Step-by-Step Experimental Procedure

The procedure will be automated by the Agent Harness:

```python
# Pseudocode for the Experimental Procedure
For each MODEL in [GPT-4o, Claude-Opus, Claude-Sonnet, Gemini-Pro, Gemini-Flash]:
  For each PROMPT in GearSet_Benchmark:
    Initialize_Agent(System_Prompt, PROMPT)
    Success = False
    Log = []

    For ITERATION in 1 to 5:
      # 1. VLM Reasoning and Tool Call
      Agent_Response = VLM_Call(History)
      Tool_Call = Parse_Tool_Call(Agent_Response) # e.g., render_scad(code)

      # 2. MCP Execution
      (Status, Output, ErrorMessage) = Execute_MCP_Tool(Tool_Call)
      # Status: Success, Syntax_Error, Runtime_Error
      # Output: Image path or Library documentation

      # 3. Logging
      Log.append({Iteration, Tool_Call, Status, Output, ErrorMessage})

      # 4. Verification (Manual or Automated Parameter Check)
      Is_Correct = Verify_Result(Tool_Call.code, PROMPT.GroundTruth)

      # 5. Decision and Feedback
      If Is_Correct:
        Success = True
        Break
      Else:
        # Append Observation (Image/Error) and Critique prompt to history
        Append_to_History(Observation, "Analyze the output against the requirements. If incorrect, correct the code.")

    # Final Evaluation for the prompt
    Calculate_Metrics(Success, Log)
```

### 5\. Data Logging and Reporting

#### 5.1. Data Logging

Log every interaction in a structured JSON format for reproducibility and analysis.

```json
{
  "run_id": "uuid",
  "model": "GPT-4o",
  "prompt_id": "L2.1",
  "ground_truth_params": {"modul": 2, "zaehnezahl": 35, "breite": 10},
  "iterations": [
    {
      "iteration_id": 1,
      "agent_thought": "The user wants a gear with D=74 and Z=35. I calculate M = D/(Z+2) = 74/37 approx 2.",
      "generated_code": "use <...>; stirnrad(modul=1.5, zaehnezahl=35, breite=10);",
      "execution_status": "Success",
      "rendered_image_path": "runs/uuid/iter1.png",
      "agent_critique": "I used M=1.5 initially. The rendered gear looks slightly smaller than expected. I will correct M to 2."
    },
    {
      "iteration_id": 2,
      // ... details of the successful iteration
    }
  ],
  "results": {"SR": 1, "PA": 1.0, "AIS": 2, "SCA": 1}
}
```

#### 5.2. Reporting in the Paper

The results should clearly compare the models and highlight the effectiveness of the self-correction mechanism.

**Tabelle 1: Gesamtleistung der VLMs im GearSet-Benchmark**

A comprehensive table summarizing the results across all tasks.

| Modell | SR@1 (%) $\\uparrow$ | SR@5 (%) $\\uparrow$ | SCA (%) $\\uparrow$ | CVR (%) $\\uparrow$ | PA (%) $\\uparrow$ | AIS $\\downarrow$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| GPT-4o | 66.7 | 88.9 | 22.2 | 95.5 | 98.0 | 1.45 |
| Claude 3.5 Opus | 77.8 | 100.0 | 22.2 | 98.2 | 100.0 | 1.22 |
| Claude 3.5 Sonnet| 55.6 | 77.8 | 22.2 | 92.1 | 90.5 | 1.80 |
| Gemini 1.5 Pro | ... | ... | ... | ... | ... | ... |
| Gemini 1.5 Flash | ... | ... | ... | ... | ... | ... |
*(Table values are illustrative examples)*

**Abbildung 2: Erfolgsrate nach Schwierigkeitsgrad**

A grouped bar chart showing how the SR@5 changes as complexity increases (X-Axis: Easy, Medium, Hard; Y-Axis: SR@5; Groups: Models).

**Abbildung 3: Qualitative Analyse der Selbstkorrektur**

A figure demonstrating the visual feedback loop (e.g., for L3.1 where the initial placement was wrong). Show: (a) Iteration 1 (Code and incorrect rendering), (b) VLM's critique, (c) Iteration 2 (Corrected code and rendering).

**Diskussion der Fehlermodi**

Analyze the logs and categorize the reasons for failure (e.g., Mathematical Errors, Spatial Reasoning Failure, Syntactic Hallucination, Ineffective Self-Correction).