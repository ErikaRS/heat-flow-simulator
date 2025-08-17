# Heat Flow Simulator

A Python-based heat flow simulator for modeling thermal dynamics in houses. Rooms are modeled as cubes with 10cm³ temperature granularity, simulating heat conduction between adjacent spaces.

## Features

- **Room-Based Modeling**: Define rooms as cubes with integer coordinates and dimensions
- **Hole Connections**: Model doors, windows, and openings between rooms
- **10cm³ Temperature Granularity**: High-resolution thermal modeling
- **Time-Series Simulation**: 1-minute timestep heat conduction simulation
- **SQLite Database**: Persistent storage of temperature data for analysis
- **Text-Based Configuration**: YAML configuration files for easy setup
- **Extensible Architecture**: Designed to support future airflow modeling

## Current Implementation Status

✅ **Project Setup** - Poetry configuration with all dependencies  
✅ **Configuration Models** - Pydantic models for rooms, holes, and validation  
✅ **Database Schema** - SQLite with cells and temperature time-series tables  
🚧 **Grid Builder** - Convert room definitions to 10cm³ cell grid (planned)  
🚧 **Simulation Engine** - Heat conduction finite-difference solver (planned)  
🚧 **CLI Interface** - Command-line interface (planned)

## Installation

Install using Poetry:

```bash
poetry install
```

## Usage

### Command Line Interface

```bash
# View available commands (CLI is currently a basic stub)
python -m src.heat_flow_simulator.cli --help

# Note: Full simulation commands will be available after CLI implementation
```

### Python API

```python
from heat_flow_simulator import SimulationConfig, Simulator

# Load configuration
config = SimulationConfig.from_yaml("config.yaml")

# Run simulation
simulator = Simulator(config)
simulator.run(duration_minutes=60)

# Query results
temps = simulator.get_temperature_history(x=25, y=20, z=13)
```

## Configuration

Create a YAML configuration file to define your house layout:

```yaml
house:
  ambient_temp_c: 5.0
  timestep_s: 60

rooms:
  - id: living
    origin: [0, 0, 0]         # cm coordinates
    dims:   [500, 400, 260]   # width, depth, height in cm
    initial_temp_c: 21

  - id: kitchen
    origin: [500, 0, 0]
    dims:   [300, 400, 260]
    initial_temp_c: 19

holes:
  - id: door_living_kitchen
    origin:     [500, 100, 0] # cm
    size:       [0,  90, 210] # thickness=0 on x-axis
    fixed_axis: x
```

## Development

Install development dependencies:

```bash
poetry install --with dev
```

Run tests:

```bash
poetry run pytest
```

Format code:

```bash
poetry run black .
poetry run ruff check .
```

Type checking:

```bash
poetry run mypy src/
```

## License

MIT License
