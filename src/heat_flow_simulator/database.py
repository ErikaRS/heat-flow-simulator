"""SQLite database models and utilities for heat flow simulator."""

import datetime
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path

from sqlalchemy import (
    create_engine, Column, Integer, Float, String, DateTime, ForeignKey, 
    UniqueConstraint, Index, func, and_
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.engine import Engine

Base = declarative_base()


class Cell(Base):
    """Represents a 3D cell in the simulation grid."""
    
    __tablename__ = 'cells'
    
    id = Column(Integer, primary_key=True)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False) 
    z = Column(Integer, nullable=False)
    room_id = Column(String(50), nullable=True)
    
    # Relationships
    temperatures = relationship("Temperature", back_populates="cell", cascade="all, delete-orphan")
    
    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint('x', 'y', 'z', name='unique_coordinates'),
        Index('idx_cell_coordinates', 'x', 'y', 'z'),
        Index('idx_cell_room', 'room_id'),
    )
    
    def __repr__(self):
        return f"<Cell(id={self.id}, x={self.x}, y={self.y}, z={self.z}, room={self.room_id})>"


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
    
    def get_or_create_cell(self, x: int, y: int, z: int, room_id: Optional[str] = None) -> Cell:
        """Get existing cell or create new one at coordinates."""
        with self.db_manager.get_session() as session:
            cell = session.query(Cell).filter_by(x=x, y=y, z=z).first()
            if not cell:
                cell = Cell(x=x, y=y, z=z, room_id=room_id)
                session.add(cell)
                session.commit()
                session.refresh(cell)
            return cell
    
    def record_temperature(self, x: int, y: int, z: int, temp_c: float, 
                          timestamp: Optional[datetime.datetime] = None) -> None:
        """Record temperature for a cell at given coordinates."""
        with self.db_manager.get_session() as session:
            cell = self.get_or_create_cell(x, y, z)
            
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
    
    def get_temperature_history(self, x: int, y: int, z: int, 
                               start_time: Optional[datetime.datetime] = None,
                               end_time: Optional[datetime.datetime] = None) -> List[Temperature]:
        """Get temperature history for a specific cell."""
        with self.db_manager.get_session() as session:
            cell = session.query(Cell).filter_by(x=x, y=y, z=z).first()
            if not cell:
                return []
            
            query = session.query(Temperature).filter_by(cell_id=cell.id)
            
            if start_time:
                query = query.filter(Temperature.timestamp >= start_time)
            if end_time:
                query = query.filter(Temperature.timestamp <= end_time)
            
            return query.order_by(Temperature.timestamp).all()
    
    def get_temperatures_at_timestamp(self, timestamp: datetime.datetime, 
                                    tolerance_seconds: int = 0) -> List[Tuple[Cell, Temperature]]:
        """Get all cells and their temperatures at a specific timestamp."""
        with self.db_manager.get_session() as session:
            if tolerance_seconds == 0:
                # Exact timestamp match
                results = session.query(Cell, Temperature).join(Temperature).filter(
                    Temperature.timestamp == timestamp
                ).all()
            else:
                # Within tolerance window
                start_time = timestamp - datetime.timedelta(seconds=tolerance_seconds)
                end_time = timestamp + datetime.timedelta(seconds=tolerance_seconds)
                
                results = session.query(Cell, Temperature).join(Temperature).filter(
                    and_(
                        Temperature.timestamp >= start_time,
                        Temperature.timestamp <= end_time
                    )
                ).all()
            
            return results
    
    def get_temperature_range(self, start_time: datetime.datetime, 
                            end_time: datetime.datetime) -> Dict[str, Any]:
        """Get temperature statistics across a time period."""
        with self.db_manager.get_session() as session:
            result = session.query(
                func.min(Temperature.temp_c).label('min_temp'),
                func.max(Temperature.temp_c).label('max_temp'),
                func.avg(Temperature.temp_c).label('avg_temp'),
                func.count(Temperature.temp_c).label('reading_count')
            ).filter(
                and_(
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
    
    def get_cell_count(self) -> int:
        """Get total number of cells."""
        with self.db_manager.get_session() as session:
            return session.query(Cell).count()
    
    def get_temperature_count(self) -> int:
        """Get total number of temperature readings."""
        with self.db_manager.get_session() as session:
            return session.query(Temperature).count()
    
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
    
    def clear_all_data(self) -> None:
        """Clear all simulation data (for testing/reset)."""
        with self.db_manager.get_session() as session:
            session.query(Temperature).delete()
            session.query(Cell).delete()
            session.query(Metadata).delete()
            session.commit()


def create_database(db_path: str = "heat_flow.db", echo: bool = False) -> DatabaseManager:
    """Create and initialize database."""
    db_manager = DatabaseManager(db_path)
    db_manager.initialize(echo=echo)
    return db_manager
