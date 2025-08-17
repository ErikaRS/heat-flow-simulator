"""SQLite database models and utilities for heat flow simulator."""

import datetime
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path

from sqlalchemy import (
    create_engine, Column, Integer, Float, String, DateTime, ForeignKey, 
    UniqueConstraint, Index, func, and_, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.engine import Engine

Base = declarative_base()


class SimulationRun(Base):
    """Represents a simulation run with its configuration and metadata."""
    
    __tablename__ = 'simulation_runs'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    config_json = Column(Text, nullable=False)  # Serialized configuration
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default='created')  # created, running, completed, failed
    
    # Relationships
    cells = relationship("Cell", back_populates="simulation_run", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_run_name', 'name'),
        Index('idx_run_status', 'status'),
        Index('idx_run_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<SimulationRun(id={self.id}, name={self.name}, status={self.status})>"


class Cell(Base):
    """Represents a 3D cell in the simulation grid."""
    
    __tablename__ = 'cells'
    
    id = Column(Integer, primary_key=True)
    simulation_run_id = Column(Integer, ForeignKey('simulation_runs.id'), nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False) 
    z = Column(Integer, nullable=False)
    room_id = Column(String(50), nullable=True)
    
    # Relationships
    simulation_run = relationship("SimulationRun", back_populates="cells")
    temperatures = relationship("Temperature", back_populates="cell", cascade="all, delete-orphan")
    
    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint('simulation_run_id', 'x', 'y', 'z', name='unique_coordinates_per_run'),
        Index('idx_cell_coordinates', 'x', 'y', 'z'),
        Index('idx_cell_room', 'room_id'),
        Index('idx_cell_run', 'simulation_run_id'),
    )
    
    def __repr__(self):
        return f"<Cell(id={self.id}, run={self.simulation_run_id}, x={self.x}, y={self.y}, z={self.z}, room={self.room_id})>"


class Temperature(Base):
    """Temperature readings for cells at specific timestamps."""
    
    __tablename__ = 'temperatures'
    
    cell_id = Column(Integer, ForeignKey('cells.id'), primary_key=True)
    timestamp = Column(DateTime, primary_key=True, default=datetime.datetime.utcnow)
    temp_c = Column(Float, nullable=False)
    
    # Relationships
    cell = relationship("Cell", back_populates="temperatures")
    
    # Indexes
    __table_args__ = (
        Index('idx_temperature_timestamp', 'timestamp'),
        Index('idx_temperature_cell_time', 'cell_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<Temperature(cell_id={self.cell_id}, timestamp={self.timestamp}, temp={self.temp_c}°C)>"


class Metadata(Base):
    """Key-value store for simulation configuration and metadata."""
    
    __tablename__ = 'metadata'
    
    key = Column(String(255), primary_key=True)
    value = Column(String(1000), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<Metadata(key={self.key}, value={self.value})>"


class DatabaseManager:
    """Manages database connection, initialization, and common operations."""
    
    def __init__(self, db_path: str = "heat_flow.db"):
        self.db_path = Path(db_path)
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
    
    def initialize(self, echo: bool = False) -> None:
        """Initialize database connection and create tables."""
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=echo,
            connect_args={"check_same_thread": False}
        )
        
        # Create all tables
        Base.metadata.create_all(bind=self.engine)
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a database session."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.SessionLocal()
    
    def close(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()


class HeatFlowQueries:
    """Query interface for heat flow simulation data."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_simulation_run(self, name: str, config_json: str, description: Optional[str] = None) -> SimulationRun:
        """Create a new simulation run."""
        with self.db_manager.get_session() as session:
            run = SimulationRun(name=name, description=description, config_json=config_json)
            session.add(run)
            session.commit()
            session.refresh(run)
            return run
    
    def get_simulation_run(self, run_id: int) -> Optional[SimulationRun]:
        """Get simulation run by ID."""
        with self.db_manager.get_session() as session:
            return session.query(SimulationRun).filter_by(id=run_id).first()
    
    def get_simulation_runs(self) -> List[SimulationRun]:
        """Get all simulation runs."""
        with self.db_manager.get_session() as session:
            return session.query(SimulationRun).order_by(SimulationRun.created_at.desc()).all()
    
    def update_simulation_run_status(self, run_id: int, status: str) -> None:
        """Update simulation run status."""
        with self.db_manager.get_session() as session:
            run = session.query(SimulationRun).filter_by(id=run_id).first()
            if run:
                run.status = status
                if status == 'completed':
                    run.completed_at = datetime.datetime.utcnow()
                session.commit()
    
    def get_or_create_cell(self, simulation_run_id: int, x: int, y: int, z: int, room_id: Optional[str] = None) -> Cell:
        """Get existing cell or create new one at coordinates for a specific simulation run."""
        with self.db_manager.get_session() as session:
            cell = session.query(Cell).filter_by(
                simulation_run_id=simulation_run_id, x=x, y=y, z=z
            ).first()
            if not cell:
                cell = Cell(simulation_run_id=simulation_run_id, x=x, y=y, z=z, room_id=room_id)
                session.add(cell)
                session.commit()
                session.refresh(cell)
            return cell
    
    def record_temperature(self, simulation_run_id: int, x: int, y: int, z: int, temp_c: float, 
                          timestamp: Optional[datetime.datetime] = None) -> None:
        """Record temperature for a cell at given coordinates in a specific simulation run."""
        with self.db_manager.get_session() as session:
            cell = self.get_or_create_cell(simulation_run_id, x, y, z)
            
            if timestamp is None:
                timestamp = datetime.datetime.utcnow()
            
            # Check if temperature already exists for this cell and timestamp
            existing = session.query(Temperature).filter_by(
                cell_id=cell.id, timestamp=timestamp
            ).first()
            
            if existing:
                existing.temp_c = temp_c
            else:
                temp_record = Temperature(cell_id=cell.id, timestamp=timestamp, temp_c=temp_c)
                session.add(temp_record)
            
            session.commit()
    
    def get_temperature_history(self, simulation_run_id: int, x: int, y: int, z: int, 
                               start_time: Optional[datetime.datetime] = None,
                               end_time: Optional[datetime.datetime] = None) -> List[Temperature]:
        """Get temperature history for a specific cell in a simulation run."""
        with self.db_manager.get_session() as session:
            cell = session.query(Cell).filter_by(
                simulation_run_id=simulation_run_id, x=x, y=y, z=z
            ).first()
            if not cell:
                return []
            
            query = session.query(Temperature).filter_by(cell_id=cell.id)
            
            if start_time:
                query = query.filter(Temperature.timestamp >= start_time)
            if end_time:
                query = query.filter(Temperature.timestamp <= end_time)
            
            return query.order_by(Temperature.timestamp).all()
    
    def get_temperatures_at_timestamp(self, simulation_run_id: int, timestamp: datetime.datetime, 
                                     tolerance_seconds: int = 0) -> List[Tuple[Cell, Temperature]]:
        """Get all cells and their temperatures at a specific timestamp for a simulation run."""
        with self.db_manager.get_session() as session:
            base_query = session.query(Cell, Temperature).join(Temperature).filter(
                Cell.simulation_run_id == simulation_run_id
            )
            
            if tolerance_seconds == 0:
                # Exact timestamp match
                results = base_query.filter(Temperature.timestamp == timestamp).all()
            else:
                # Within tolerance window
                start_time = timestamp - datetime.timedelta(seconds=tolerance_seconds)
                end_time = timestamp + datetime.timedelta(seconds=tolerance_seconds)
                
                results = base_query.filter(
                    and_(
                        Temperature.timestamp >= start_time,
                        Temperature.timestamp <= end_time
                    )
                ).all()
            
            return results
    
    def get_temperature_range(self, simulation_run_id: int, start_time: datetime.datetime, 
                            end_time: datetime.datetime) -> Dict[str, Any]:
        """Get temperature statistics across a time period for a simulation run."""
        with self.db_manager.get_session() as session:
            result = session.query(
                func.min(Temperature.temp_c).label('min_temp'),
                func.max(Temperature.temp_c).label('max_temp'),
                func.avg(Temperature.temp_c).label('avg_temp'),
                func.count(Temperature.temp_c).label('reading_count')
            ).join(Cell).filter(
                and_(
                    Cell.simulation_run_id == simulation_run_id,
                    Temperature.timestamp >= start_time,
                    Temperature.timestamp <= end_time
                )
            ).first()
            
            return {
                'min_temperature': result.min_temp,
                'max_temperature': result.max_temp,
                'average_temperature': result.avg_temp,
                'reading_count': result.reading_count,
                'start_time': start_time,
                'end_time': end_time
            }
    
    def get_cell_count(self, simulation_run_id: Optional[int] = None) -> int:
        """Get total number of cells, optionally filtered by simulation run."""
        with self.db_manager.get_session() as session:
            query = session.query(Cell)
            if simulation_run_id is not None:
                query = query.filter_by(simulation_run_id=simulation_run_id)
            return query.count()
    
    def get_temperature_count(self, simulation_run_id: Optional[int] = None) -> int:
        """Get total number of temperature readings, optionally filtered by simulation run."""
        with self.db_manager.get_session() as session:
            query = session.query(Temperature)
            if simulation_run_id is not None:
                query = query.join(Cell).filter(Cell.simulation_run_id == simulation_run_id)
            return query.count()
    
    def set_metadata(self, key: str, value: str) -> None:
        """Set or update metadata value."""
        with self.db_manager.get_session() as session:
            metadata = session.query(Metadata).filter_by(key=key).first()
            if metadata:
                metadata.value = value
                metadata.updated_at = datetime.datetime.utcnow()
            else:
                metadata = Metadata(key=key, value=value)
                session.add(metadata)
            session.commit()
    
    def get_metadata(self, key: str) -> Optional[str]:
        """Get metadata value by key."""
        with self.db_manager.get_session() as session:
            metadata = session.query(Metadata).filter_by(key=key).first()
            return metadata.value if metadata else None
    
    def clear_simulation_run(self, simulation_run_id: int) -> None:
        """Clear data for a specific simulation run."""
        with self.db_manager.get_session() as session:
            # Delete temperatures first (foreign key constraint)
            session.query(Temperature).join(Cell).filter(
                Cell.simulation_run_id == simulation_run_id
            ).delete(synchronize_session=False)
            
            # Delete cells for this run
            session.query(Cell).filter_by(simulation_run_id=simulation_run_id).delete()
            
            # Delete the simulation run itself
            session.query(SimulationRun).filter_by(id=simulation_run_id).delete()
            session.commit()
    
    def clear_all_data(self) -> None:
        """Clear all simulation data (for testing/reset)."""
        with self.db_manager.get_session() as session:
            session.query(Temperature).delete()
            session.query(Cell).delete()
            session.query(SimulationRun).delete()
            session.query(Metadata).delete()
            session.commit()


def create_database(db_path: str = "heat_flow.db", echo: bool = False) -> DatabaseManager:
    """Create and initialize database."""
    db_manager = DatabaseManager(db_path)
    db_manager.initialize(echo=echo)
    return db_manager
