# Heat Flow Simulator Implementation Plan

## Overview

This document outlines the implementation plan for a simple heat flow simulator designed for house thermal modeling. The simulator uses a room-based approach where rooms are modeled as cubes and heat conduction is calculated on a 10cm³ grid resolution.

## Requirements

### Core Requirements
- **Text-based configuration**: YAML configuration files
- **Room modeling**: Cubes with (x,y,z) integer origin points and centimeter dimensions
- **Room adjacency**: Rooms sharing a 2D plane are considered adjacent
- **Hole modeling**: (x,y,z) origin points with two dimensions, one fixed dimension
- **Temperature granularity**: 10x10x10 cm³ units
- **Time resolution**: 1-minute simulation increments
- **No airflow initially**: Architecture must support future airflow addition
- **Database output**: Cell coordinates, timestamps, and temperatures

### Technical Constraints
- All coordinates and dimensions must be integers
- Rooms cannot overlap
- Holes must have exactly one zero dimension matching their fixed axis

## Architecture

### Component Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ CLI / Driver    │───▶│ Config Loader   │───▶│ Validation      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Database        │◀───│ Simulation      │◀───│ Grid Builder    │
│ Persistence     │    │ Engine          │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Layer Responsibilities

1. **CLI / Driver Layer**
   - Entry point and argument parsing
   - Orchestrates: load → build → simulate → persist
   - Progress reporting and error handling

2. **Configuration & Validation Layer**
   - YAML parsing to domain objects
   - Strict validation with Pydantic
   - Geometry validation (overlap, adjacency, constraints)

3. **Grid Builder**
   - Converts room definitions to 10cm³ cell grid
   - Generates cell coordinates and room mappings
   - Creates neighbor adjacency lists (6-face connectivity)
   - Identifies boundary cells (exterior, holes)

4. **Simulation Engine**
   - Finite-difference heat conduction solver
   - 1-minute timesteps with configurable parameters
   - Pluggable physics architecture for future airflow
   - Vectorized operations (NumPy) for performance

5. **Database Persistence**
   - SQLite storage with time-series optimization
   - Bulk insert operations for performance
   - Query interface for analysis and visualization

## Data Models

### Configuration Models
- `Room`: id, origin_cm, dims_cm, initial_temp_c
- `Hole`: id, origin_cm, size_cm, fixed_axis
- `HouseConfig`: ambient_temp_c, timestep_s, conductivity
- `SimulationConfig`: house, rooms, holes, simulation parameters

### Runtime Models
- `Vec3`: (x,y,z) integer coordinates in centimeters
- `CellCoord`: (x,y,z) grid coordinates in 10cm units
- `Grid`: 3D temperature array with neighbor relationships

### Database Schema
- `cells`: id, x, y, z, room_id (static grid)
- `temperatures`: cell_id, timestamp, temp_c (time-series)
- `metadata`: key, value (configuration and simulation metadata)

## Simulation Algorithm

### Heat Conduction (Current Phase)
Uses finite-difference method with explicit time stepping:

```
Fo = α·Δt / Δx²  (Fourier number)
T_new(i) = T_old(i) + Fo * Σ_neighbors (T_old(n) - T_old(i))
```

Where:
- α = thermal diffusivity (k / ρc)
- Δt = 60 seconds (1 minute)
- Δx = 0.10 m (10 cm cell size)

### Boundary Conditions
- **Exterior faces**: Use ambient temperature as virtual neighbor
- **Hole faces**: Natural conduction to adjacent room cells
- **Stability**: Fourier number ≤ 0.167 (automatically satisfied)

### Future Airflow Extension
Architecture includes pluggable `transport_terms` to add convection:
```
dT/dt = conduction_term + airflow_term + radiation_term + ...
```

## Implementation Phases

### ✅ Phase 1: Foundation (Completed)
- [x] Poetry project setup with dependencies
- [x] Pydantic configuration models with validation
- [x] SQLite database schema with time-series support
- [x] Comprehensive test coverage

### 🚧 Phase 2: Core Simulation (In Progress)
- [ ] Grid builder: room → cell discretization
- [ ] Neighbor adjacency calculation
- [ ] Hole boundary identification
- [ ] Basic heat conduction engine

### 📋 Phase 3: CLI & Integration
- [ ] Command-line interface with Click
- [ ] End-to-end simulation workflow
- [ ] Configuration validation and error reporting
- [ ] Performance optimization (NumPy vectorization)

### 📋 Phase 4: Analysis & Tools
- [ ] Temperature history export (CSV)
- [ ] Basic visualization tools
- [ ] Simulation result validation
- [ ] Example configurations and documentation

### 📋 Phase 5: Extensibility
- [ ] Pluggable physics architecture
- [ ] Airflow modeling framework
- [ ] Material property support
- [ ] Advanced boundary conditions

## Technology Stack

- **Language**: Python 3.11+
- **Configuration**: YAML (ruamel.yaml)
- **Data Validation**: Pydantic v2
- **Numerics**: NumPy, SciPy
- **Database**: SQLite with SQLAlchemy
- **CLI**: Click
- **Testing**: pytest
- **Code Quality**: black, ruff, mypy

## File Structure

```
heat-flow-simulator/
├── src/heat_flow_simulator/
│   ├── __init__.py
│   ├── models.py           # ✅ Pydantic configuration models
│   ├── database.py         # ✅ SQLite schema and queries
│   ├── grid.py            # 🚧 Grid builder (planned)
│   ├── simulation.py      # 🚧 Heat conduction engine (planned)
│   └── cli.py             # 📋 Command-line interface (planned)
├── tests/
│   ├── test_models.py     # ✅ Configuration validation tests
│   ├── test_database.py   # ✅ Database operation tests
│   └── ...                # 📋 Additional test modules (planned)
├── examples/
│   └── sample_config.yaml # ✅ Example house configuration
├── docs/
│   └── plan.md            # 📋 This implementation plan
└── pyproject.toml         # ✅ Poetry configuration
```

## Next Steps

1. **Grid Builder Implementation**: Convert room definitions into discretized cell grid
2. **Simulation Engine**: Implement finite-difference heat conduction solver
3. **CLI Development**: Create user-friendly command-line interface
4. **Integration Testing**: End-to-end simulation workflow validation
5. **Performance Optimization**: NumPy vectorization and profiling

## Design Principles

- **Simplicity**: Start with essential features, add complexity incrementally
- **Modularity**: Clear separation between configuration, simulation, and persistence
- **Extensibility**: Architecture supports future physics additions (airflow, radiation)
- **Validation**: Comprehensive input validation to catch errors early
- **Performance**: Designed for NumPy vectorization and efficient database operations
