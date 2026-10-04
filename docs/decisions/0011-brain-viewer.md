---
status: accepted
date: 2026-10-03
decision-makers: Tyler Banks
---

# 3D brain view: BrainGlobe meshes as glTF at deploy time, drawn with React Three Fiber

## Context and Problem Statement

The plan's explorer leads with a 3D brain whose connections are drawn between real region meshes (plan: Anatomical view). The meshes come from the Allen mouse atlas, whose content can't be committed (ADR 0005). How do the meshes reach the site, and what draws them?

## Considered Options

* Convert the pinned atlas's meshes to glTF in the build, at deploy time, and draw them with React Three Fiber and drei
* Commit converted meshes to the repository
* Embed an existing viewer (Neuroglancer, brainrender's web export)

## Decision Outcome

Chosen option: "glTF at deploy time, React Three Fiber", the plan's own building blocks (plan: Proven building blocks), with nothing restricted in the repository.

* **Export:** `python -m build --meshes DIR` (`build/meshes.py`) reads the pinned BrainGlobe atlas (it stops if BrainGlobe serves another version) and writes `DIR/<atlas>/`: `root.glb`, one `<structure>.glb` per region named by a connection, and `index.json` with each region's acronym, name and centroid. It uses trimesh, and fast-simplification for the quadric decimation: at most 20,000 triangles for the brain outline and 4,000 per region (about 9 MB for 202 regions, each fetched only when drawn). Atlases with no connections are not exported.
* **Coordinates:** millimetres from the centre of the atlas volume, x towards the animal's right, y up, z posterior: a right-handed frame for three.js. The atlas's third axis runs from the animal's left to its right, as in Allen's own data: right-hemisphere injections (`hemisphere_id` 2) sit at large values, although BrainGlobe labels the atlas "asr". The conversion is then a rotation, so triangles keep their winding. Arcs meet a region at the centre of its right-hemisphere surface, where Allen injects (corrected after the final review: the first version followed BrainGlobe's label and mirrored the brain).
* **Deploy:** the database job writes the meshes and passes them to the site job as a one-day workflow artifact; the site job puts them in `site/public/brain/` before `vercel build`. They are served with the site, credited in its footer, and never committed or dumped.
* **Page:** `/brain`, a client-only component (`next/dynamic` with `ssr: false`) using three, `@react-three/fiber` and `@react-three/drei`. Arcs run from each injected amygdala region to its targets, wider for denser projections and dashed when every claim is `proposed`; each opens its evidence. A side list holds the same connections for keyboard and screen-reader use, and the Explore table remains the 2D equivalent.
* **Network view:** a toggle on the same page swaps the 3D scene for a force-directed graph of the same connections (`react-force-graph-2d`, the plan's network library), loaded only when chosen. Both views share the injected region, density filter and selection, so choosing a region in one highlights it in the other (plan: linked views).

### Consequences

* Good, because meshes always match the pinned atlas and the connections just loaded, and the repository stays free of Allen content.
* Good, because the stack is the plan's, with no custom WebGL.
* Bad, because each deploy downloads about 200 meshes from BrainGlobe's S3 (about a minute); an outage stops the deploy and the previous site stays live.
* Neutral: CI's build doesn't export meshes; unit tests cover the conversion with fake atlases, and the deploy is the integration test.
