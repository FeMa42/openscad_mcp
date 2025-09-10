# Stirnrad mit 20 Zähnen entwerfen
_Exported on 28/08/2025 at 19:44:22 CEST from Cursor (1.5.5)_

---

**User**

Erstelle ein Stirnrad mit 20 Zähnen, Modul 2 und einer Breite von 10 mm.

Erstelle ein Stirnrad mit 20 Zähnen, Modul 2 und einer Breite von 10 mm.

---

**Cursor**

Ich hole mir kurz die korrekten Bibliotheks-/Funktionsnamen für Zahnräder und generiere dann direkt das SCAD samt Vorschau-Render.

Ich rendere jetzt das Stirnrad direkt in OpenSCAD (20 Zähne, Modul 2, Breite 10 mm) und zeige dir die Vorschau.

Ich rendere das gewünschte Stirnrad jetzt mit Modul 2, 20 Zähnen, Breite 10 mm (ohne Bohrung, optimiert=false) zur Vorschau. Anschließend kannst du mir den gewünschten Bohrungsdurchmesser nennen.

Vorschau ist gerendert; hier ist der SCAD‑Code für dein Stirnrad.

```openscad
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

stirnrad(
  modul = 2,
  zahnzahl = 20,
  breite = 10,
  bohrung = 0,          // Wunschdurchmesser eintragen (z.B. 5)
  eingriffswinkel = 20,
  schraegungswinkel = 0,
  optimiert = false
);
```

- **Pitch-Ø**: 40 mm
- **Außen-Ø**: ca. 44 mm

Soll ich eine Bohrung (Durchmesser?) und ggf. Nabe hinzufügen?

```plaintext
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

stirnrad(
  modul = 2,
  zahnzahl = 20,
  breite = 10,
  bohrung = 0,          // Wunschdurchmesser eintragen (z.B. 5)
  eingriffswinkel = 20,
  schraegungswinkel = 0,
  optimiert = false
);
```

---

**User**

Erstelle ein Kegelrad mit 15 Zähnen, Modul 1.5 und einem Winkel von 45 Grad.

---

**Cursor**

Ich rendere jetzt ein Kegelrad mit 15 Zähnen, Modul 1.5 und 45° Kegelwinkel für die Vorschau.

Hier ist das Kegelrad (15 Zähne, Modul 1.5, 45°). `zahnbreite` und `bohrung` kannst du anpassen.

```openscad
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

kegelrad(
  modul = 1.5,
  zahnzahl = 15,
  teilkegelwinkel = 45,
  zahnbreite = 6,   // anpassen
  bohrung = 0,      // z.B. 5
  eingriffswinkel = 20,
  schraegungswinkel = 0
);
```

Möchtest du eine bestimmte Bohrung und Zahnbreite?

```plaintext
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

kegelrad(
  modul = 1.5,
  zahnzahl = 15,
  teilkegelwinkel = 45,
  zahnbreite = 6,   // anpassen
  bohrung = 0,      // z.B. 5
  eingriffswinkel = 20,
  schraegungswinkel = 0
);
```

---

**User**

Erstelle ein schrägverzahntes Zahnrad mit 25 Zähnen, Modul 1.5, Breite 8mm und einem Schrägungswinkel von 15 Grad.

---

**Cursor**

Ich rendere das helical Zahnrad jetzt (25 Zähne, Modul 1.5, Breite 8 mm, Schrägungswinkel 15°) zur Vorschau.

Hier ist dein schrägverzahntes Zahnrad (25 Zähne, Modul 1.5, Breite 8 mm, Schrägungswinkel 15°). Bohrung kannst du eintragen.

```openscad
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

stirnrad(
  modul = 1.5,
  zahnzahl = 25,
  breite = 8,
  bohrung = 0,          // z.B. 5
  eingriffswinkel = 20,
  schraegungswinkel = 15,
  optimiert = false
);
```

- **Teilkreis-Ø**: 37.5 mm
- **Außen-Ø**: ca. 40.5 mm

Soll ich eine Bohrung und ggf. Nabe hinzufügen?

```plaintext
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

stirnrad(
  modul = 1.5,
  zahnzahl = 25,
  breite = 8,
  bohrung = 0,          // z.B. 5
  eingriffswinkel = 20,
  schraegungswinkel = 15,
  optimiert = false
);
```

---

**User**

Erstelle ein Stirnrad (30 Zähne, Modul 1) mit einer zentralen Bohrung von 12 mm.

---

**Cursor**

Ich rendere das Stirnrad jetzt mit Modul 1, 30 Zähnen, Bohrung 12 mm und einer sinnvollen Breite von 6 mm für die Vorschau.

Hier ist dein Stirnrad (30 Zähne, Modul 1, Bohrung 12 mm). Breite aktuell 6 mm – sag Bescheid, falls du eine andere willst.

```openscad
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

stirnrad(
  modul = 1,
  zahnzahl = 30,
  breite = 6,
  bohrung = 12,
  eingriffswinkel = 20,
  schraegungswinkel = 0,
  optimiert = false
);
```

- Teilkreis-Ø: 30 mm
- Außen-Ø: 32 mm
- Bohrung: 12 mm

```plaintext
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

stirnrad(
  modul = 1,
  zahnzahl = 30,
  breite = 6,
  bohrung = 12,
  eingriffswinkel = 20,
  schraegungswinkel = 0,
  optimiert = false
);
```

---

**User**

Ich benötige ein Stirnrad mit 35 Zähnen und einem Außendurchmesser (Kopfkreisdurchmesser) von 74 mm. Die Breite soll 10 mm betragen.

---

**Cursor**

Ich rendere das Stirnrad mit 35 Zähnen so, dass der Außen-Ø 74 mm ergibt. Dafür setze ich das Modul auf 2 und Breite auf 10 mm.

Hier ist dein Stirnrad (35 Zähne, Außen-Ø 74 mm, Breite 10 mm). Modul = 74/(35+2) = 2.

```openscad
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

stirnrad(
  modul = 2,
  zahnzahl = 35,
  breite = 10,
  bohrung = 0,          // gewünschten Durchmesser eintragen (z.B. 8)
  eingriffswinkel = 20,
  schraegungswinkel = 0,
  optimiert = false
);
```

- Teilkreis-Ø: 70 mm
- Außen-Ø: 74 mm

Bohrungsdurchmesser gewünscht?

```plaintext
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

stirnrad(
  modul = 2,
  zahnzahl = 35,
  breite = 10,
  bohrung = 0,          // gewünschten Durchmesser eintragen (z.B. 8)
  eingriffswinkel = 20,
  schraegungswinkel = 0,
  optimiert = false
);
```

---

**User**

rstelle ein Zahnrad, das zu einem existierenden Rad mit Modul 2.5 und 40 Zähnen passt. Das neue Rad soll ein Übersetzungsverhältnis von 1:2 haben.

---

**Cursor**

Ich rendere jetzt das Gegenrad für 1:2 Übersetzung: Modul 2.5, 80 Zähne, Breite 10 mm.

- Das passende Gegenrad für 1:2 zu 40 Zähnen ist: **80 Zähne**, Modul **2.5**, Breite **10 mm**.
- Prüfe, dass der Eingriffswinkel dem vorhandenen Rad entspricht (standard 20°).
- Center Abstand: 2.5*(40+80)/2 = 150 mm.

```openscad
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

stirnrad(
  modul = 2.5,
  zahnzahl = 80,
  breite = 10,
  bohrung = 0,          // gewünschten Durchmesser einsetzen
  eingriffswinkel = 20, // an vorhandenes Rad anpassen
  schraegungswinkel = 0,
  optimiert = false
);
```

Möchtest du eine Bohrung/Nabe (Durchmesser/Dicke)?

```plaintext
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

stirnrad(
  modul = 2.5,
  zahnzahl = 80,
  breite = 10,
  bohrung = 0,          // gewünschten Durchmesser einsetzen
  eingriffswinkel = 20, // an vorhandenes Rad anpassen
  schraegungswinkel = 0,
  optimiert = false
);
```

---

**User**

Konstruiere ein Kegelrad mit Modul 3 und 20 Zähnen, das für eine 90-Grad-Umlenkung mit einem identischen Gegenstück geeignet ist.

---

**Cursor**

Ich rendere jetzt ein Kegelrad mit Modul 3, 20 Zähnen und 45° Teilkegelwinkel (passend für eine 90°-Umlenkung mit identischem Gegenstück).

### Kegelrad für 90°-Umlenkung (identisches Gegenstück)

```openscad
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

// Einzelrad (45° Teilkegelwinkel für 90°-Achsen)
kegelrad(
  modul = 3,
  zahnzahl = 20,
  teilkegelwinkel = 45,
  zahnbreite = 10,
  bohrung = 0,
  eingriffswinkel = 20,
  schraegungswinkel = 0
);

// Alternativ: direkt als Paar (beide 20 Zähne, 90° Achsen)
kegelradpaar(
  modul = 3,
  zahnzahl_rad = 20,
  zahnzahl_ritzel = 20,
  achsenwinkel = 90,
  zahnbreite = 10,
  bohrung_rad = 0,
  bohrung_ritzel = 0,
  eingriffswinkel = 20,
  schraegungswinkel = 0,
  zusammen_gebaut = true
);
```

- Anpassbar: `bohrung` bzw. `bohrung_rad/bohrung_ritzel`.

```plaintext
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

// Einzelrad (45° Teilkegelwinkel für 90°-Achsen)
kegelrad(
  modul = 3,
  zahnzahl = 20,
  teilkegelwinkel = 45,
  zahnbreite = 10,
  bohrung = 0,
  eingriffswinkel = 20,
  schraegungswinkel = 0
);

// Alternativ: direkt als Paar (beide 20 Zähne, 90° Achsen)
kegelradpaar(
  modul = 3,
  zahnzahl_rad = 20,
  zahnzahl_ritzel = 20,
  achsenwinkel = 90,
  zahnbreite = 10,
  bohrung_rad = 0,
  bohrung_ritzel = 0,
  eingriffswinkel = 20,
  schraegungswinkel = 0,
  zusammen_gebaut = true
);
```

---

**User**

Erstelle eine Zahnstange (Rack) der Länge 100mm, die zu einem Stirnrad mit Modul 2 passt.

---

**Cursor**

Ich rendere jetzt eine Zahnstange mit Modul 2 und Länge 100 mm (Standard: Höhe 8 mm, Breite 10 mm, Eingriffswinkel 20°) zur Vorschau.

Hier ist deine Zahnstange (Länge 100 mm) passend zu Modul 2.

```openscad
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

zahnstange(
  modul = 2,
  laenge = 100,
  hoehe = 8,     // Höhe bis zur Wälzgeraden
  breite = 10,   // Zahnbreite (Tiefe)
  eingriffswinkel = 20,
  schraegungswinkel = 0
);
```

Möchtest du andere Werte für `hoehe` oder `breite`?- I generated the rack preview and provided the exact SCAD you can paste.

```plaintext
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

zahnstange(
  modul = 2,
  laenge = 100,
  hoehe = 8,     // Höhe bis zur Wälzgeraden
  breite = 10,   // Zahnbreite (Tiefe)
  eingriffswinkel = 20,
  schraegungswinkel = 0
);
```

---

**User**

Konstruiere ein einfaches Stirnradgetriebe (Modul 2). Das Antriebsrad hat 18 Zähne, das Abtriebsrad 36 Zähne. Positioniere sie so, dass sie korrekt ineinandergreifen.

---

**Cursor**

Ich rendere das Getriebe mit korrekt berechnetem Achsabstand von 54 mm und meshe die Räder über eine passende Winkelversetzung.

- Achsabstand: 54 mm. Übersetzung: 18:36 = 1:2.

```openscad
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

m = 2;
z1 = 18;           // Antrieb
z2 = 36;           // Abtrieb
a  = m*(z1+z2)/2;  // 54 mm
width = 8;
bore  = 0;         // ggf. Bohrungen eintragen

// Antriebsrad
color("gold")
stirnrad(modul=m, zahnzahl=z1, breite=width, bohrung=bore, eingriffswinkel=20, schraegungswinkel=0, optimiert=false);

// Abtriebsrad, korrekt ausgerichtet
color("orange")
translate([a,0,0])
  rotate([0,0,180/z2])
    stirnrad(modul=m, zahnzahl=z2, breite=width, bohrung=bore, eingriffswinkel=20, schraegungswinkel=0, optimiert=false);
```

```plaintext
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

m = 2;
z1 = 18;           // Antrieb
z2 = 36;           // Abtrieb
a  = m*(z1+z2)/2;  // 54 mm
width = 8;
bore  = 0;         // ggf. Bohrungen eintragen

// Antriebsrad
color("gold")
stirnrad(modul=m, zahnzahl=z1, breite=width, bohrung=bore, eingriffswinkel=20, schraegungswinkel=0, optimiert=false);

// Abtriebsrad, korrekt ausgerichtet
color("orange")
translate([a,0,0])
  rotate([0,0,180/z2])
    stirnrad(modul=m, zahnzahl=z2, breite=width, bohrung=bore, eingriffswinkel=20, schraegungswinkel=0, optimiert=false);
```

---

**User**

Konstruiere ein Zahnradpaar für eine 90-Grad-Umlenkung (Kegelräder). Das Antriebsrad hat 15 Zähne, das Abtriebsrad 30. Beide haben Modul 1.5. Richte sie korrekt zueinander aus.

---

**Cursor**

Ich rendere das Kegelradpaar jetzt mit Modul 1.5, Zähnezahlen 15/30, Achsenwinkel 90°, korrekt zusammengebaut.

Hier ist das korrekt ausgerichtete Kegelradpaar (Modul 1.5, 15/30 Zähne, 90° Achsen).

```openscad
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

kegelradpaar(
  modul = 1.5,
  zahnzahl_rad = 30,      // Abtrieb
  zahnzahl_ritzel = 15,   // Antrieb
  achsenwinkel = 90,
  zahnbreite = 6,
  bohrung_rad = 0,        // gewünschte Bohrungen einsetzen
  bohrung_ritzel = 0,
  eingriffswinkel = 20,
  schraegungswinkel = 0,
  zusammen_gebaut = true
);
```

Bohrungsdurchmesser/Dicke der Räder gewünscht?

```plaintext
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

kegelradpaar(
  modul = 1.5,
  zahnzahl_rad = 30,      // Abtrieb
  zahnzahl_ritzel = 15,   // Antrieb
  achsenwinkel = 90,
  zahnbreite = 6,
  bohrung_rad = 0,        // gewünschte Bohrungen einsetzen
  bohrung_ritzel = 0,
  eingriffswinkel = 20,
  schraegungswinkel = 0,
  zusammen_gebaut = true
);
```

---

**User**

Generiere ein Zahnrad mit Fischgrätverzahnung (herringbone gear) mit Modul 1 und 30 Zähnen, Breite 20mm.

---

**Cursor**

Ich rendere jetzt das Fischgrät‑Zahnrad (Modul 1, 30 Zähne, Breite 20 mm, Schrägungswinkel 20°) zur Vorschau und gebe dir danach den SCAD‑Code.

Rendering brach nach 60 s ab – ich gebe dir den SCAD‑Code direkt zum lokalen Rendern.

```openscad
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

pfeilrad(
  modul = 1,
  zahnzahl = 30,
  breite = 20,          // Gesamtbreite (wird intern halbiert)
  bohrung = 0,          // z.B. 5
  nabendicke = 0,
  nabendurchmesser = 0,
  eingriffswinkel = 20,
  schraegungswinkel = 20, // typischer Wert; anpassen falls gewünscht
  optimiert = false
);
```

- Teilkreis-Ø ≈ 30 mm, Außen-Ø ≈ 32 mm. Bohrung/Nabe gewünscht?

```plaintext
$fa = 1;
$fs = 0.4;

use <parameterizable_gears/gears.scad>

pfeilrad(
  modul = 1,
  zahnzahl = 30,
  breite = 20,          // Gesamtbreite (wird intern halbiert)
  bohrung = 0,          // z.B. 5
  nabendicke = 0,
  nabendurchmesser = 0,
  eingriffswinkel = 20,
  schraegungswinkel = 20, // typischer Wert; anpassen falls gewünscht
  optimiert = false
);
```

---

**User**

versuche es erneut. Du kannst bis zu 5 iterationen nutzen um ein Ergebnis zu generieren

---

**Cursor**

Ich versuche das Fischgrät‑Zahnrad erneut zu rendern und senke die Tessellation ($fn, $fa, $fs) für schnellere Berechnung. Wenn es erneut scheitert, passe ich die Qualität weiter an (bis zu 5 Versuche).

Funktioniert – hier ist das gerenderte Fischgrät‑Zahnrad. SCAD‑Code mit moderaten Qualitätssettings:

```openscad
$fa = 8;
$fs = 1.2;
$fn = 48;

use <parameterizable_gears/gears.scad>

pfeilrad(
  modul = 1,
  zahnzahl = 30,
  breite = 20,
  bohrung = 0,            // ggf. Bohrung eintragen
  nabendicke = 0,
  nabendurchmesser = 0,
  eingriffswinkel = 20,
  schraegungswinkel = 20, // anpassen (15–30° üblich)
  optimiert = false
);
```

Möchtest du eine Bohrung oder eine Nabe hinzufügen?

```plaintext
$fa = 8;
$fs = 1.2;
$fn = 48;

use <parameterizable_gears/gears.scad>

pfeilrad(
  modul = 1,
  zahnzahl = 30,
  breite = 20,
  bohrung = 0,            // ggf. Bohrung eintragen
  nabendicke = 0,
  nabendurchmesser = 0,
  eingriffswinkel = 20,
  schraegungswinkel = 20, // anpassen (15–30° üblich)
  optimiert = false
);
```

---

**User**

Erstelle ein einfaches Planetengetriebe mit einem Sonnenrad (20 Zähne) und drei Planetenrädern (10 Zähne). Modul 1.

---

**Cursor**

Ich rendere jetzt das Planetengetriebe (m=1, Sonne 20Z, 3×Planeten 10Z, korrektes Hohlrad wird berechnet) für die Vorschau.

Ich versuche eine leichtere Planetensatz-Variante mit Stirn- statt Pfeilverzahnung zu rendern (Ring als `hohlrad`, Sonne/Planeten als `stirnrad`) und reduziere die Qualitätseinstellungen für schnelle Vorschau. Jetzt rendere ich.

```plaintext
$fa=8; $fs=1.2; $fn=48;
use <parameterizable_gears/gears.scad>

m = 1;
z_s = 20;
z_p = 10;
z_r = z_s + 2*z_p; // 40
width = 5; // or set it to 5 since the user didn't specify.

r_s = m*z_s/2;
r_p = m*z_p/2;
r_center = r_s + r_p;

color("gold") hohlrad(... randbreite = 3 ...);
color("orange") stirnrad(...s);
for (i=[0:2]) translate([...]) rotate([...]) stirnrad(...)
```

Ich habe das Planetenset erfolgreich gerendert; hier ist der SCAD‑Code für Sonne, 3 Planeten und Hohlrad (m=1), korrekt positioniert.

```openscad
$fa = 10;
$fs = 1.6;
$fn = 40;

use <parameterizable_gears/gears.scad>

m = 1;
z_s = 20;                 // Sonne
z_p = 10;                 // Planet
z_r = z_s + 2*z_p;        // Hohlrad = 40
width = 5;                // Zahnbreite (anpassen)
bore  = 0;                // ggf. Bohrungen setzen

r_s = m*z_s/2;            // 10
r_p = m*z_p/2;            // 5
r_center = r_s + r_p;     // 15 mm Planetenradius zur Mitte

// Hohlrad (Ring)
color("gold")
hohlrad(modul=m, zahnzahl=z_r, breite=width, randbreite=3, eingriffswinkel=20, schraegungswinkel=0);

// Sonnenrad
color("orange")
stirnrad(modul=m, zahnzahl=z_s, breite=width, bohrung=bore, eingriffswinkel=20, schraegungswinkel=0, optimiert=false);

// Drei Planeten bei 120°-Abständen
for (n = [0:2])
  color("khaki")
  translate([r_center*cos(120*n), r_center*sin(120*n), 0])
    rotate([0,0,180/z_p])
      stirnrad(modul=m, zahnzahl=z_p, breite=width, bohrung=bore, eingriffswinkel=20, schraegungswinkel=0, optimiert=false);
```

- Sonne 20Z, Planeten 10Z, Hohlrad 40Z; Planetenmitte bei 15 mm.

```plaintext
$fa = 10;
$fs = 1.6;
$fn = 40;

use <parameterizable_gears/gears.scad>

m = 1;
z_s = 20;                 // Sonne
z_p = 10;                 // Planet
z_r = z_s + 2*z_p;        // Hohlrad = 40
width = 5;                // Zahnbreite (anpassen)
bore  = 0;                // ggf. Bohrungen setzen

r_s = m*z_s/2;            // 10
r_p = m*z_p/2;            // 5
r_center = r_s + r_p;     // 15 mm Planetenradius zur Mitte

// Hohlrad (Ring)
color("gold")
hohlrad(modul=m, zahnzahl=z_r, breite=width, randbreite=3, eingriffswinkel=20, schraegungswinkel=0);

// Sonnenrad
color("orange")
stirnrad(modul=m, zahnzahl=z_s, breite=width, bohrung=bore, eingriffswinkel=20, schraegungswinkel=0, optimiert=false);

// Drei Planeten bei 120°-Abständen
for (n = [0:2])
  color("khaki")
  translate([r_center*cos(120*n), r_center*sin(120*n), 0])
    rotate([0,0,180/z_p])
      stirnrad(modul=m, zahnzahl=z_p, breite=width, bohrung=bore, eingriffswinkel=20, schraegungswinkel=0, optimiert=false);
```

