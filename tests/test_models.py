"""Tests for configuration models."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from pydantic import ValidationError
from heat_flow_simulator.models import Room, Hole, HouseConfig, SimulationConfig


class TestRoom:
    """Tests for Room model."""
    
    def test_valid_room(self):
        """Test creating a valid room."""
        room = Room(
            id="test_room",
            origin_cm=(0, 0, 0),
            dims_cm=(100, 200, 300),
            initial_temp_c=20.0
        )
        assert room.id == "test_room"
        assert room.origin_cm == (0, 0, 0)
        assert room.dims_cm == (100, 200, 300)
        assert room.initial_temp_c == 20.0
    
    def test_negative_coordinates_invalid(self):
        """Test that negative coordinates are invalid."""
        with pytest.raises(ValidationError, match="positive"):
            Room(
                id="test_room",
                origin_cm=(-1, 0, 0),
                dims_cm=(100, 200, 300),
                initial_temp_c=20.0
            )
    
    def test_negative_dimensions_invalid(self):
        """Test that negative dimensions are invalid."""
        with pytest.raises(ValidationError, match="positive"):
            Room(
                id="test_room",
                origin_cm=(0, 0, 0),
                dims_cm=(100, -200, 300),
                initial_temp_c=20.0
            )
    
    def test_get_bounds(self):
        """Test bounds calculation."""
        room = Room(
            id="test_room",
            origin_cm=(10, 20, 30),
            dims_cm=(100, 200, 300),
            initial_temp_c=20.0
        )
        min_bounds, max_bounds = room.get_bounds()
        assert min_bounds == (10, 20, 30)
        assert max_bounds == (110, 220, 330)
    
    def test_overlaps_with(self):
        """Test room overlap detection."""
        room1 = Room(
            id="room1",
            origin_cm=(0, 0, 0),
            dims_cm=(100, 100, 100),
            initial_temp_c=20.0
        )
        room2 = Room(
            id="room2",
            origin_cm=(50, 50, 50),  # Overlaps with room1
            dims_cm=(100, 100, 100),
            initial_temp_c=20.0
        )
        room3 = Room(
            id="room3",
            origin_cm=(200, 200, 200),  # No overlap
            dims_cm=(100, 100, 100),
            initial_temp_c=20.0
        )
        
        assert room1.overlaps_with(room2)
        assert room2.overlaps_with(room1)
        assert not room1.overlaps_with(room3)
        assert not room3.overlaps_with(room1)
    
    def test_is_adjacent_to(self):
        """Test room adjacency detection."""
        room1 = Room(
            id="room1",
            origin_cm=(0, 0, 0),
            dims_cm=(100, 100, 100),
            initial_temp_c=20.0
        )
        room2 = Room(
            id="room2",
            origin_cm=(100, 0, 0),  # Adjacent to room1 (shares face)
            dims_cm=(100, 100, 100),
            initial_temp_c=20.0
        )
        room3 = Room(
            id="room3",
            origin_cm=(200, 200, 200),  # Not adjacent
            dims_cm=(100, 100, 100),
            initial_temp_c=20.0
        )
        
        assert room1.is_adjacent_to(room2)
        assert room2.is_adjacent_to(room1)
        assert not room1.is_adjacent_to(room3)


class TestHole:
    """Tests for Hole model."""
    
    def test_valid_hole_x_axis(self):
        """Test creating a valid hole in x-plane."""
        hole = Hole(
            id="door1",
            origin_cm=(100, 50, 0),
            size_cm=(0, 200, 80),  # Zero thickness in x-direction
            fixed_axis="x"
        )
        assert hole.id == "door1"
        assert hole.fixed_axis == "x"
    
    def test_valid_hole_y_axis(self):
        """Test creating a valid hole in y-plane."""
        hole = Hole(
            id="window1",
            origin_cm=(50, 100, 50),
            size_cm=(150, 0, 100),  # Zero thickness in y-direction
            fixed_axis="y"
        )
        assert hole.fixed_axis == "y"
    
    def test_valid_hole_z_axis(self):
        """Test creating a valid hole in z-plane."""
        hole = Hole(
            id="skylight1",
            origin_cm=(50, 50, 250),
            size_cm=(100, 100, 0),  # Zero thickness in z-direction
            fixed_axis="z"
        )
        assert hole.fixed_axis == "z"
    
    def test_invalid_fixed_axis(self):
        """Test invalid fixed axis."""
        with pytest.raises(ValidationError, match="must be 'x', 'y', or 'z'"):
            Hole(
                id="door1",
                origin_cm=(100, 50, 0),
                size_cm=(0, 200, 80),
                fixed_axis="w"  # Invalid axis
            )
    
    def test_non_zero_fixed_dimension_invalid(self):
        """Test that non-zero dimension on fixed axis is invalid."""
        with pytest.raises(ValidationError, match="must be 0"):
            Hole(
                id="door1",
                origin_cm=(100, 50, 0),
                size_cm=(10, 200, 80),  # Non-zero in x-direction
                fixed_axis="x"
            )
    
    def test_zero_non_fixed_dimension_invalid(self):
        """Test that zero dimension on non-fixed axis is invalid."""
        with pytest.raises(ValidationError, match="must be positive"):
            Hole(
                id="door1",
                origin_cm=(100, 50, 0),
                size_cm=(0, 0, 80),  # Zero in y-direction (not fixed)
                fixed_axis="x"
            )


class TestHouseConfig:
    """Tests for HouseConfig model."""
    
    def test_valid_house_config(self):
        """Test creating a valid house configuration."""
        config = HouseConfig(
            ambient_temp_c=20.0,
            timestep_s=1.0,
            conductivity=0.5,
            rooms=[
                Room(id="room1", origin_cm=(0, 0, 0), dims_cm=(100, 100, 100), initial_temp_c=25.0),
                Room(id="room2", origin_cm=(100, 0, 0), dims_cm=(100, 100, 100), initial_temp_c=20.0)
            ],
            holes=[
                Hole(id="door1", origin_cm=(100, 25, 0), size_cm=(0, 50, 80), fixed_axis="x")
            ]
        )
        assert len(config.rooms) == 2
        assert len(config.holes) == 1
    
    def test_negative_timestep_invalid(self):
        """Test that negative timestep is invalid."""
        with pytest.raises(ValidationError, match="positive"):
            HouseConfig(
                ambient_temp_c=20.0,
                timestep_s=-1.0,  # Invalid
                conductivity=0.5,
                rooms=[Room(id="room1", origin_cm=(0, 0, 0), dims_cm=(100, 100, 100), initial_temp_c=25.0)]
            )
    
    def test_negative_conductivity_invalid(self):
        """Test that negative conductivity is invalid."""
        with pytest.raises(ValidationError, match="positive"):
            HouseConfig(
                ambient_temp_c=20.0,
                timestep_s=1.0,
                conductivity=-0.5,  # Invalid
                rooms=[Room(id="room1", origin_cm=(0, 0, 0), dims_cm=(100, 100, 100), initial_temp_c=25.0)]
            )
    
    def test_duplicate_room_ids_invalid(self):
        """Test that duplicate room IDs are invalid."""
        with pytest.raises(ValidationError, match="unique"):
            HouseConfig(
                ambient_temp_c=20.0,
                rooms=[
                    Room(id="room1", origin_cm=(0, 0, 0), dims_cm=(100, 100, 100), initial_temp_c=25.0),
                    Room(id="room1", origin_cm=(100, 0, 0), dims_cm=(100, 100, 100), initial_temp_c=20.0)  # Duplicate ID
                ]
            )
    
    def test_overlapping_rooms_invalid(self):
        """Test that overlapping rooms are invalid."""
        with pytest.raises(ValidationError, match="overlap"):
            HouseConfig(
                ambient_temp_c=20.0,
                rooms=[
                    Room(id="room1", origin_cm=(0, 0, 0), dims_cm=(100, 100, 100), initial_temp_c=25.0),
                    Room(id="room2", origin_cm=(50, 50, 50), dims_cm=(100, 100, 100), initial_temp_c=20.0)  # Overlaps
                ]
            )


class TestSimulationConfig:
    """Tests for SimulationConfig model."""
    
    def test_valid_simulation_config(self):
        """Test creating a valid simulation configuration."""
        house = HouseConfig(
            ambient_temp_c=20.0,
            rooms=[Room(id="room1", origin_cm=(0, 0, 0), dims_cm=(100, 100, 100), initial_temp_c=25.0)]
        )
        config = SimulationConfig(
            house=house,
            max_iterations=1000,
            convergence_threshold=1e-6,
            output_interval=10
        )
        assert config.max_iterations == 1000
        assert config.convergence_threshold == 1e-6
        assert config.output_interval == 10
    
    def test_negative_max_iterations_invalid(self):
        """Test that negative max_iterations is invalid."""
        house = HouseConfig(
            ambient_temp_c=20.0,
            rooms=[Room(id="room1", origin_cm=(0, 0, 0), dims_cm=(100, 100, 100), initial_temp_c=25.0)]
        )
        with pytest.raises(ValidationError, match="positive"):
            SimulationConfig(
                house=house,
                max_iterations=-100  # Invalid
            )
    
    def test_negative_convergence_threshold_invalid(self):
        """Test that negative convergence threshold is invalid."""
        house = HouseConfig(
            ambient_temp_c=20.0,
            rooms=[Room(id="room1", origin_cm=(0, 0, 0), dims_cm=(100, 100, 100), initial_temp_c=25.0)]
        )
        with pytest.raises(ValidationError, match="positive"):
            SimulationConfig(
                house=house,
                convergence_threshold=-1e-6  # Invalid
            )
    
    def test_zero_output_interval_invalid(self):
        """Test that zero output interval is invalid."""
        house = HouseConfig(
            ambient_temp_c=20.0,
            rooms=[Room(id="room1", origin_cm=(0, 0, 0), dims_cm=(100, 100, 100), initial_temp_c=25.0)]
        )
        with pytest.raises(ValidationError, match="positive"):
            SimulationConfig(
                house=house,
                output_interval=0  # Invalid
            )
