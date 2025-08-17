"""Tests for the database module."""

import datetime
import tempfile
import pytest
from pathlib import Path

from heat_flow_simulator.database import (
    DatabaseManager, HeatFlowQueries, Cell, Temperature, Metadata,
    create_database
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db_manager = create_database(db_path)
    yield db_manager, HeatFlowQueries(db_manager)
    
    db_manager.close()
    Path(db_path).unlink()


class TestDatabaseManager:
    """Test database manager functionality."""
    
    def test_initialize_creates_tables(self, temp_db):
        """Test that initialization creates all required tables."""
        db_manager, queries = temp_db
        
        with db_manager.get_session() as session:
            # Check that tables exist by querying them
            assert session.query(Cell).count() == 0
            assert session.query(Temperature).count() == 0
            assert session.query(Metadata).count() == 0
    
    def test_get_session_without_init_raises_error(self):
        """Test that getting session without initialization raises error."""
        db_manager = DatabaseManager(":memory:")
        
        with pytest.raises(RuntimeError, match="Database not initialized"):
            db_manager.get_session()


class TestCellOperations:
    """Test cell CRUD operations."""
    
    def test_get_or_create_cell_creates_new(self, temp_db):
        """Test creating a new cell."""
        db_manager, queries = temp_db
        
        cell = queries.get_or_create_cell(1, 2, 3, "living_room")
        
        assert cell.x == 1
        assert cell.y == 2
        assert cell.z == 3
        assert cell.room_id == "living_room"
        assert cell.id is not None
    
    def test_get_or_create_cell_returns_existing(self, temp_db):
        """Test retrieving existing cell."""
        db_manager, queries = temp_db
        
        # Create first cell
        cell1 = queries.get_or_create_cell(1, 2, 3)
        cell1_id = cell1.id
        
        # Get same cell again
        cell2 = queries.get_or_create_cell(1, 2, 3)
        
        assert cell1.id == cell2.id
        assert cell1_id == cell2.id
    
    def test_unique_coordinates_constraint(self, temp_db):
        """Test that cells with duplicate coordinates are not allowed."""
        db_manager, queries = temp_db
        
        # Create cell
        cell1 = queries.get_or_create_cell(5, 5, 5)
        
        # Try to get same coordinates - should return existing cell
        cell2 = queries.get_or_create_cell(5, 5, 5, "different_room")
        
        assert cell1.id == cell2.id
        # Room ID should remain as originally set
        assert cell1.room_id == cell2.room_id


class TestTemperatureOperations:
    """Test temperature recording and retrieval."""
    
    def test_record_temperature(self, temp_db):
        """Test recording temperature for a cell."""
        db_manager, queries = temp_db
        
        timestamp = datetime.datetime(2024, 1, 1, 12, 0, 0)
        queries.record_temperature(1, 1, 1, 20.5, timestamp)
        
        # Verify temperature was recorded
        history = queries.get_temperature_history(1, 1, 1)
        assert len(history) == 1
        assert history[0].temp_c == 20.5
        assert history[0].timestamp == timestamp
    
    def test_record_temperature_updates_existing(self, temp_db):
        """Test that recording temperature updates existing record."""
        db_manager, queries = temp_db
        
        timestamp = datetime.datetime(2024, 1, 1, 12, 0, 0)
        
        # Record initial temperature
        queries.record_temperature(2, 2, 2, 18.0, timestamp)
        
        # Record new temperature at same timestamp
        queries.record_temperature(2, 2, 2, 22.0, timestamp)
        
        # Should only have one record with updated temperature
        history = queries.get_temperature_history(2, 2, 2)
        assert len(history) == 1
        assert history[0].temp_c == 22.0
    
    def test_get_temperature_history_with_time_range(self, temp_db):
        """Test retrieving temperature history with time filtering."""
        db_manager, queries = temp_db
        
        # Record multiple temperatures
        base_time = datetime.datetime(2024, 1, 1, 12, 0, 0)
        for i in range(5):
            timestamp = base_time + datetime.timedelta(hours=i)
            queries.record_temperature(3, 3, 3, 20.0 + i, timestamp)
        
        # Get history for middle 3 hours
        start_time = base_time + datetime.timedelta(hours=1)
        end_time = base_time + datetime.timedelta(hours=3)
        
        history = queries.get_temperature_history(3, 3, 3, start_time, end_time)
        
        assert len(history) == 3
        assert history[0].temp_c == 21.0  # Hour 1
        assert history[-1].temp_c == 23.0  # Hour 3
    
    def test_get_temperature_history_nonexistent_cell(self, temp_db):
        """Test getting history for non-existent cell returns empty list."""
        db_manager, queries = temp_db
        
        history = queries.get_temperature_history(999, 999, 999)
        assert history == []


class TestTimestampQueries:
    """Test timestamp-based queries."""
    
    def test_get_temperatures_at_timestamp_exact(self, temp_db):
        """Test getting all temperatures at exact timestamp."""
        db_manager, queries = temp_db
        
        timestamp = datetime.datetime(2024, 1, 1, 15, 30, 0)
        
        # Record temperatures for multiple cells at same time
        queries.record_temperature(1, 1, 1, 18.0, timestamp)
        queries.record_temperature(2, 2, 2, 22.0, timestamp)
        queries.record_temperature(3, 3, 3, 25.0, timestamp)
        
        results = queries.get_temperatures_at_timestamp(timestamp)
        
        assert len(results) == 3
        temps = [temp.temp_c for cell, temp in results]
        assert 18.0 in temps
        assert 22.0 in temps
        assert 25.0 in temps
    
    def test_get_temperatures_at_timestamp_with_tolerance(self, temp_db):
        """Test getting temperatures within tolerance window."""
        db_manager, queries = temp_db
        
        base_time = datetime.datetime(2024, 1, 1, 15, 30, 0)
        
        # Record temperatures at slightly different times
        queries.record_temperature(1, 1, 1, 18.0, base_time - datetime.timedelta(seconds=5))
        queries.record_temperature(2, 2, 2, 22.0, base_time)
        queries.record_temperature(3, 3, 3, 25.0, base_time + datetime.timedelta(seconds=3))
        queries.record_temperature(4, 4, 4, 30.0, base_time + datetime.timedelta(seconds=15))
        
        # Query with 10-second tolerance
        results = queries.get_temperatures_at_timestamp(base_time, tolerance_seconds=10)
        
        assert len(results) == 3  # Should exclude the one 15 seconds away
        temps = [temp.temp_c for cell, temp in results]
        assert 30.0 not in temps  # This one should be excluded


class TestTemperatureRangeQueries:
    """Test temperature range and statistics queries."""
    
    def test_get_temperature_range(self, temp_db):
        """Test getting temperature statistics over time period."""
        db_manager, queries = temp_db
        
        base_time = datetime.datetime(2024, 1, 1, 12, 0, 0)
        temperatures = [15.0, 20.0, 25.0, 30.0, 35.0]
        
        # Record temperatures over 5 hours
        for i, temp in enumerate(temperatures):
            timestamp = base_time + datetime.timedelta(hours=i)
            queries.record_temperature(1, 1, 1, temp, timestamp)
        
        start_time = base_time
        end_time = base_time + datetime.timedelta(hours=4)
        
        stats = queries.get_temperature_range(start_time, end_time)
        
        assert stats['min_temperature'] == 15.0
        assert stats['max_temperature'] == 35.0
        assert stats['average_temperature'] == 25.0
        assert stats['reading_count'] == 5
        assert stats['start_time'] == start_time
        assert stats['end_time'] == end_time


class TestMetadataOperations:
    """Test metadata storage and retrieval."""
    
    def test_set_and_get_metadata(self, temp_db):
        """Test setting and getting metadata values."""
        db_manager, queries = temp_db
        
        queries.set_metadata("config_hash", "abc123")
        queries.set_metadata("simulation_version", "1.0.0")
        
        assert queries.get_metadata("config_hash") == "abc123"
        assert queries.get_metadata("simulation_version") == "1.0.0"
        assert queries.get_metadata("nonexistent") is None
    
    def test_update_metadata(self, temp_db):
        """Test updating existing metadata."""
        db_manager, queries = temp_db
        
        # Set initial value
        queries.set_metadata("test_key", "initial_value")
        assert queries.get_metadata("test_key") == "initial_value"
        
        # Update value
        queries.set_metadata("test_key", "updated_value")
        assert queries.get_metadata("test_key") == "updated_value"


class TestUtilityMethods:
    """Test utility and counting methods."""
    
    def test_get_counts(self, temp_db):
        """Test getting cell and temperature counts."""
        db_manager, queries = temp_db
        
        # Initially empty
        assert queries.get_cell_count() == 0
        assert queries.get_temperature_count() == 0
        
        # Add some data
        timestamp = datetime.datetime.now()
        queries.record_temperature(1, 1, 1, 20.0, timestamp)
        queries.record_temperature(2, 2, 2, 25.0, timestamp)
        
        assert queries.get_cell_count() == 2
        assert queries.get_temperature_count() == 2
    
    def test_clear_all_data(self, temp_db):
        """Test clearing all simulation data."""
        db_manager, queries = temp_db
        
        # Add some data
        queries.record_temperature(1, 1, 1, 20.0)
        queries.set_metadata("test", "value")
        
        assert queries.get_cell_count() > 0
        assert queries.get_temperature_count() > 0
        assert queries.get_metadata("test") is not None
        
        # Clear all data
        queries.clear_all_data()
        
        assert queries.get_cell_count() == 0
        assert queries.get_temperature_count() == 0
        assert queries.get_metadata("test") is None


class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    def test_complete_simulation_workflow(self, temp_db):
        """Test a complete simulation data workflow."""
        db_manager, queries = temp_db
        
        # Set simulation metadata
        queries.set_metadata("config_hash", "sim_abc123")
        queries.set_metadata("grid_size", "10x10x5")
        
        # Simulate recording temperature data over time
        base_time = datetime.datetime(2024, 1, 1, 0, 0, 0)
        
        # Record initial temperatures for a 3x3x1 grid
        for x in range(3):
            for y in range(3):
                for t in range(5):  # 5 time steps
                    timestamp = base_time + datetime.timedelta(minutes=t*10)
                    # Simulate cooling over time
                    temp = 100.0 - (t * 5) + (x + y) * 2
                    queries.record_temperature(x, y, 0, temp, timestamp)
        
        # Verify data integrity
        assert queries.get_cell_count() == 9  # 3x3 grid
        assert queries.get_temperature_count() == 45  # 9 cells * 5 timesteps
        
        # Check temperature history for center cell
        history = queries.get_temperature_history(1, 1, 0)
        assert len(history) == 5
        assert history[0].temp_c == 104.0  # Initial temp for (1,1)
        assert history[-1].temp_c == 84.0   # Final temp for (1,1)
        
        # Check snapshot at specific time
        snapshot_time = base_time + datetime.timedelta(minutes=20)  # t=2
        snapshot = queries.get_temperatures_at_timestamp(snapshot_time)
        assert len(snapshot) == 9
        
        # Check temperature range statistics
        start_time = base_time
        end_time = base_time + datetime.timedelta(minutes=40)
        stats = queries.get_temperature_range(start_time, end_time)
        
        assert stats['reading_count'] == 45
        assert stats['min_temperature'] == 80.0  # Corner cell (0,0) at t=4
        assert stats['max_temperature'] == 108.0  # Corner cell (2,2) at t=0
        
        # Verify metadata
        assert queries.get_metadata("config_hash") == "sim_abc123"
        assert queries.get_metadata("grid_size") == "10x10x5"
