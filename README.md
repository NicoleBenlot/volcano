# 🌋 Volcano Simulator

An interactive volcano hazard-mapping simulation for the Philippines, built with [Streamlit](https://streamlit.io) and [Folium](https://python-visualization.github.io/folium/). Explore 25 Philippine volcanoes, model eruption alert levels, earthquake magnitudes, and wind-driven ash plumes over live satellite imagery.

🔗 **Live app:** [volcanosim.streamlit.app](https://volcanosim.streamlit.app) (not volcsim.streamlit.app)

> **Note on the URL:** The app is deployed at `volcanosim.streamlit.app` — the title above reflects where the app actually lives.

## Features

- **🗺 25 Philippine Volcanoes** — Active, Potentially Active, and Inactive markers with predefined locations, colored by status.
- **⚠️ PHIVOLCS-style Alert Levels (0–5)** — Each level scales the hazard radius, grid resolution, and default earthquake magnitude.
- **🌍 Seismic Activity** — Earthquake magnitude slider (M0–M9) that dynamically expands the damage zone and hazard extent.
- **💨 Wind Conditions** — Direction and speed controls drive a continuous, physically-based Gaussian ash plume (symmetric at calm, elongating and shifting downwind as wind increases).
- **🎨 Ash Appearance** — 7 colormaps including a live **Pulse Red** animated effect and adjustable opacity.
- **🗂 Layers** — Toggle Ash Plume, Damage Intensity, and impact ring overlays.
- **🛰 Base Maps** — Google Hybrid/Satellite, Esri World Imagery, and OpenStreetMap layers.
- **📊 Live Statistics** — Hazard zone, damage area, ash-fall area (km²), max downwind reach, and current alert level.

## How It Works

The simulation is driven by two modules:

- **`volc.py`** — Streamlit UI, sidebar controls, Folium map assembly, custom HTML legend/header/stats styling, and JS pulse animation injection.
- **`volcano_models.py`** — `VolcanoSimulation` class: a geographic-aware lat/lon simulation grid with km-based distance fields, colormap utilities, and the physics for damage intensity (inverse-square + exponential falloff) and ash plumes (elongated Gaussian with downwind shift and deterministic turbulence).

## Installation

```bash
git clone <your-repo-url>
cd volcano
pip install -r requirements.txt
```

## Run Locally

```bash
streamlit run volc.py
```

## Deploy to Streamlit Cloud

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Click **New app**, connect the repo, set the main file to `volc.py`, and deploy.

## Requirements

`streamlit`, `folium`, `streamlit-folium`, `numpy`, `matplotlib`, `Pillow`, `scipy`
