"""Configuration models for heat flow simulator."""

from typing import List, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator
import numpy as np

# Type aliases for coordinates
Vec3 = Tuple[int, int, int]  # (x, y, z) coordinates in centimeters
CellCoord = Tuple[int, int, int]  # Grid cell coordinates


class Room(BaseModel):
    """Model representing a room in the house."""
    id: str = Field(..., description="Unique identifier for the room")
    origin_cm: Vec3 = Field(..., description="Bottom-left-front corner in cm")
    dims_cm: Vec3 = Field(..., description="Dimensions (width, height, depth) in cm")
    initial_temp_c: float = Field(..., description="Initial temperature in Celsius")
    
    @field_validator('origin_cm', 'dims_cm')
    @classmethod
    def validate_positive_coordinates(cls, v: Vec3) -> Vec3:
        """Ensure all coordinate components are positive integers."""
        if any(coord < 0 for coord in v):
            raise ValueError("All coordinates and dimensions must be positive")
        return v
    
    def get_bounds(self) -> Tuple[Vec3, Vec3]:
        """Get the min and max bounds of the room."""
        x, y, z = self.origin_cm
        w, h, d = self.dims_cm
        min_bounds = self.origin_cm
        max_bounds = (x + w, y + h, z + d)
        return min_bounds, max_bounds
    
    def overlaps_with(self, other: 'Room') -> bool:
        """Check if this room overlaps with another room."""
        self_min, self_max = self.get_bounds()
        other_min, other_max = other.get_bounds()
        
        # Check for overlap in all three dimensions
        for i in range(3):
            if self_max[i] <= other_min[i] or other_max[i] <= self_min[i]:
                return False
        return True
    
    def is_adjacent_to(self, other: 'Room') -> bool:
        """Check if this room is adjacent to another room (shares a face)."""
        self_min, self_max = self.get_bounds()
        other_min, other_max = other.get_bounds()
        
        # Count dimensions where rooms touch
        touching_faces = 0
        overlapping_dims = 0
        
        for i in range(3):
            if self_max[i] == other_min[i] or other_max[i] == self_min[i]:
                touching_faces += 1
            elif not (self_max[i] <= other_min[i] or other_max[i] <= self_min[i]):
                overlapping_dims += 1
        
        # Adjacent if touching in one dimension and overlapping in the other two
        return touching_faces == 1 and overlapping_dims == 2


class Hole(BaseModel):
    """Model representing a hole (door/window) between rooms."""
    id: str = Field(..., description="Unique identifier for the hole")
    origin_cm: Vec3 = Field(..., description="Bottom-left corner of hole in cm")
    size_cm: Vec3 = Field(..., description="Hole dimensions in cm")
    fixed_axis: str = Field(..., description="Axis perpendicular to hole ('x', 'y', or 'z')")
    
    @field_validator('fixed_axis')
    @classmethod
    def validate_fixed_axis(cls, v: str) -> str:
        """Ensure fixed_axis is valid."""
        if v not in ['x', 'y', 'z']:
            raise ValueError("fixed_axis must be 'x', 'y', or 'z'")
        return v
    
    @model_validator(mode='after')
    def validate_hole_dimensions(self):
        """Ensure hole has exactly one zero dimension matching fixed_axis."""
        axis_map = {'x': 0, 'y': 1, 'z': 2}
        fixed_dim = axis_map[self.fixed_axis]
        
        # Check that the fixed axis dimension is zero (hole has no thickness)
        if self.size_cm[fixed_dim] != 0:
            raise ValueError(f"Hole dimension for fixed_axis '{self.fixed_axis}' must be 0")
        
        # Check that other dimensions are positive
        for i, dim in enumerate(self.size_cm):
            if i != fixed_dim and dim <= 0:
                raise ValueError("Hole dimensions (except fixed axis) must be positive")
        
        return self


class HouseConfig(BaseModel):
    """Configuration for the house structure."""
    ambient_temp_c: float = Field(..., description="Ambient temperature outside the house")
    timestep_s: float = Field(default=1.0, description="Simulation timestep in seconds")
    rooms: List[Room] = Field(..., description="List of rooms in the house")
    holes: List[Hole] = Field(default_factory=list, description="List of holes between rooms")
    
    @field_validator('timestep_s')
    @classmethod
    def validate_positive_values(cls, v: float) -> float:
        """Ensure timestep is positive."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v
    
    @model_validator(mode='after')
    def validate_room_ids_unique(self):
        """Ensure all room IDs are unique."""
        room_ids = [room.id for room in self.rooms]
        if len(room_ids) != len(set(room_ids)):
            raise ValueError("Room IDs must be unique")
        return self
    
    @model_validator(mode='after')
    def validate_no_room_overlaps(self):
        """Ensure no rooms overlap."""
        for i, room1 in enumerate(self.rooms):
            for room2 in self.rooms[i + 1:]:
                if room1.overlaps_with(room2):
                    raise ValueError(f"Rooms '{room1.id}' and '{room2.id}' overlap")
        return self


class SimulationConfig(BaseModel):
    """Top-level simulation configuration."""
    house: HouseConfig = Field(..., description="House configuration")
    max_iterations: int = Field(default=1000, description="Maximum simulation iterations")
    convergence_threshold: float = Field(default=1e-6, description="Temperature change threshold for convergence")
    output_interval: int = Field(default=10, description="Steps between output snapshots")
    
    @field_validator('max_iterations', 'output_interval')
    @classmethod
    def validate_positive_integers(cls, v: int) -> int:
        """Ensure positive integer values."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v
    
    @field_validator('convergence_threshold')
    @classmethod
    def validate_positive_threshold(cls, v: float) -> float:
        """Ensure convergence threshold is positive."""
        if v <= 0:
            raise ValueError("Convergence threshold must be positive")
        return v
