# Library File debug.scad

Helpers to make debugging OpenScad code easier.
To use, add the following lines to the beginning of your file:
```
include <BOSL/constants.scad>
use <BOSL/debug.scad>
```

---

# Table of Contents

1. [Debugging Polyhedrons](#1-debugging-polyhedrons)
    - [`debug_vertices()`](#debug_vertices)
    - [`debug_faces()`](#debug_faces)
    - [`debug_polyhedron()`](#debug_polyhedron)

---

# 1. Debugging Polyhedrons

### debug\_vertices()

**Description**:
Draws all the vertices in an array, at their 3D position, numbered by their
position in the vertex array.  Also draws any children of this module with
transparency.

Argument        | What it does
--------------- | ------------------------------
`vertices`      | Array of point vertices.
`size`          | The size of the text used to label the vertices.
`disabled`      | If true, don't draw numbers, and draw children without transparency.  Default = false.

**Example**:

    verts = [for (z=[-10,10], y=[-10,10], x=[-10,10]) [x,y,z]];
    faces = [[0,1,2], [1,3,2], [0,4,5], [0,5,1], [1,5,7], [1,7,3], [3,7,6], [3,6,2], [2,6,4], [2,4,0], [4,6,7], [4,7,5]];
    debug_vertices(vertices=verts, size=2) {
        polyhedron(points=verts, faces=faces);
    }

![debug\_vertices() Example](images/debug/debug_vertices.png)

---

### debug\_faces()

**Description**:
Draws all the vertices at their 3D position, numbered in blue by their
position in the vertex array.  Each face will have their face number drawn
in red, aligned with the center of face.  All children of this module are drawn
with transparency.

Argument        | What it does
--------------- | ------------------------------
`vertices`      | Array of point vertices.
`faces`         | Array of faces by vertex numbers.
`size`          | The size of the text used to label the faces and vertices.
`disabled`      | If true, don't draw numbers, and draw children without transparency.  Default = false.

**Example**:

    verts = [for (z=[-10,10], y=[-10,10], x=[-10,10]) [x,y,z]];
    faces = [[0,1,2], [1,3,2], [0,4,5], [0,5,1], [1,5,7], [1,7,3], [3,7,6], [3,6,2], [2,6,4], [2,4,0], [4,6,7], [4,7,5]];
    debug_faces(vertices=verts, faces=faces, size=2) {
        polyhedron(points=verts, faces=faces);
    }

![debug\_faces() Example](images/debug/debug_faces.png)

---

### debug\_polyhedron()

**Description**:
A drop-in module to replace `polyhedron()` and help debug vertices and faces.
Draws all the vertices at their 3D position, numbered in blue by their
position in the vertex array.  Each face will have their face number drawn
in red, aligned with the center of face.  All given faces are drawn with
transparency. All children of this module are drawn with transparency.
Works best with Thrown-Together preview mode, to see reversed faces.

Argument        | What it does
--------------- | ------------------------------
`vertices`      | Array of point vertices.
`faces`         | Array of faces by vertex numbers.
`txtsize`       | The size of the text used to label the faces and vertices.
`disabled`      | If true, act exactly like `polyhedron()`.  Default = false.

**Example**:

    verts = [for (z=[-10,10], a=[0:120:359.9]) [10*cos(a),10*sin(a),z]];
    faces = [[0,1,2], [5,4,3], [0,3,4], [0,4,1], [1,4,5], [1,5,2], [2,5,3], [2,3,0]];
    debug_polyhedron(points=verts, faces=faces, txtsize=1);

![debug\_polyhedron() Example](images/debug/debug_polyhedron.png)

---

