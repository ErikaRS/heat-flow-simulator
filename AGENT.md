# Agent Instructions for Heat Flow Simulator

## Project Overview
Heat flow simulator for houses using room-cube modeling with 10cm³ temperature granularity.

## Key Commands

### Testing
```bash
python -m pytest tests/
```

### Code Quality
```bash
python -m black src/ tests/
python -m ruff check src/ tests/
python -m mypy src/
```

### Running CLI
```bash
python -m src.heat_flow_simulator.cli --help
python -m src.heat_flow_simulator.cli --version
```

### Project Structure
```
src/heat_flow_simulator/
├── __init__.py
├── models.py          # ✅ Pydantic config models
├── database.py        # ✅ SQLite schema & queries  
├── cli.py            # ✅ Basic CLI stub
├── grid.py           # 🚧 Grid builder (next)
└── simulation.py     # 🚧 Heat conduction engine (next)

tests/
├── test_models.py    # ✅ Config validation tests
├── test_database.py  # ✅ Database operation tests
└── ...               # 🚧 Additional tests

examples/
└── sample_config.yaml # ✅ Example house config

docs/
└── plan.md           # ✅ Implementation plan
```

## Implementation Status
- ✅ Project setup (Poetry, dependencies)
- ✅ Configuration models (Pydantic with validation)
- ✅ Database schema (SQLite with time-series)
- 🚧 Grid builder (discretize rooms → 10cm³ cells)
- 🚧 Simulation engine (finite-difference heat conduction)
- 🚧 Full CLI implementation

## Code Conventions
- Python 3.11+ with type hints
- Pydantic for data validation
- SQLAlchemy for database operations
- Click for CLI framework
- pytest for testing
- Black + Ruff for formatting/linting

## Architecture Notes
- Room coordinates: integer centimeters
- Cell grid: 10cm³ units (divide by 10)
- Temperature simulation: 1-minute timesteps
- Database: separate cells (static) and temperatures (time-series) tables
- Extensible design for future airflow modeling

## Current TODO Items
1. Grid builder implementation
2. Heat conduction simulation engine
3. Complete CLI with run/export commands
4. Performance optimization (NumPy vectorization)
