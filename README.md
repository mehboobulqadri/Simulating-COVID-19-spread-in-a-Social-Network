# 🦠 Bio-Spatial Epidemic Simulator

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-optimized-brightgreen.svg)

A high-performance, interactive COVID-19 epidemic simulation that models disease spread through realistic social networks and spatial dynamics. Built with Python, NumPy for vectorized calculations, and ModernGL for hardware-accelerated rendering.

## ✨ Key Features

- **🚀 High Performance**: Capable of simulating 1,600+ agents at 50+ FPS using a vectorized NumPy engine and OpenGL rendering.
- **🕸️ Graph-Based Transmission**: Utilizes Watts-Strogatz small-world networks to model realistic social clusters and transmission pathways.
- **🏙️ Spatial Dynamics**: Agents live in a procedurally generated world with cities, districts, homes, workplaces, and daily commuting routines.
- **📊 Real-Time Analytics**:
  - Live statistics dashboard (R-value, active cases, mortality rate).
  - Interactive "God Mode" panel for on-the-fly parameter tuning.
  - Minimap for global situational awareness.
- **🛠️ Control & Intervention**:
  - Implementation of Lockdowns and Quarantines.
  - Vaccination campaigns with adjustable efficacy and rollout speed.
  - Variable simulation speed (1x, 2x, 5x).
- **💾 Data Persistence**: Save/Load simulation states and export data to CSV, JSON, or interactive HTML reports.

## 📦 Installation

1.  **Clone the repository** (if applicable) or download the source.
2.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: Requires `pygame`, `numpy`, `moderngl`, and `networkx`.*

## 🎮 Usage

Run the simulation from the main directory:

```bash
python main.py
```

### ⌨️ Controls

| Category | Key | Action |
| :--- | :---: | :--- |
| **Simulation** | `SPACE` | Pause / Resume |
| | `1` / `2` / `5` | Set Speed (1x, 2x, 5x) |
| | `Ctrl+S` | Quick Save |
| | `Ctrl+L` | Quick Load |
| | `Ctrl+E` | Export Data |
| | `ESC` | Quit |
| **View** | `W/A/S/D` | Pan Camera |
| | `Q` / `E` | Zoom In / Out |
| | `F` | Focus / Frame All |
| | `H` | Toggle HUD / FPS |
| **Interventions** | `G` | Toggle **God Mode** Panel |
| | `L` | Toggle **Lockdown** |
| | `Q` | Toggle **Quarantine** (City-wide) |
| | `R` | Toggle Quarantine Selection Mode |
| **Interaction** | `Click` | Select Agent (view stats) |
| | `T` | Toggle Trace Path for selection |
| | `Shift+Click` | Infect Agents at cursor |

## 🧬 Simulation Mechanics

### The Engine
The core logic resides in `core/numpy_engine.py`. It uses **NumPy** to manage state arrays (positions, health status, timers) for thousands of agents simultaneously, avoiding slow Python loops. This allows for complex "Road Snapping" pathfinding (optional) and dense interactions without frame drops.

### Infection Model
- **States**: Susceptible ➝ Exposed ➝ Infectious ➝ Recovered / Deceased.
- **Transmission**: Occurs via two primary vectors:
    1.  **Spatial Proximity**: Agents physically close to each other.
    2.  **Social Network**: Graph edges connecting agents (family, friends), allowing transmission across distances.

## 📂 Project Structure

```text
├── main.py              # Application Entry Point
├── core/                # Core Simulation Logic
│   ├── numpy_engine.py  # Vectorized Infection & Movement Engine
│   ├── statistics.py    # Analytics & History Tracking
│   └── ...
├── entities/            # Data Attributes
│   ├── person.py        # Agent Definitions
│   └── ...
├── graphics/            # Visuals
│   ├── gl_renderer.py   # ModernGL (OpenGL) Renderer
│   └── ...
├── ui/                  # User Interface
│   ├── control_panel.py # Left Controls
│   ├── god_mode.py      # Parameter Tuning
│   └── ...
└── data/                # Data Handling
    ├── world_generator.py # Procedural World Gen
    └── export.py        # Report Generation
```

## 🔧 Troubleshooting

- **OpenGL Errors**: If you encounter `moderngl` errors, ensure your graphics drivers are up to date. The simulation requires OpenGL 3.3+.
- **Performance**: If FPS is low, ensure "Road Snapping" is disabled in the God Mode panel (it is disabled by default).

## 📄 License

MIT License. Feel free to use and modify for educational or personal projects.
