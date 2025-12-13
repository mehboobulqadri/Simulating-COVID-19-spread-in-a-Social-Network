import numpy as np
import math

class SimplePathfinder:
    """Simple grid-based pathfinding that snaps agents to roads"""
    
    @staticmethod
    def snap_to_road(pos, cities, road_snap_distance=20):
        """
        Snap a position to the nearest road if within snap distance
        Returns: (snapped_x, snapped_y, is_on_road)
        """
        x, y = pos
        min_dist = float('inf')
        snap_x, snap_y = x, y
        
        for city in cities:
            # Check city roads (grid)
            if hasattr(city, 'roads'):
                for road in city.roads:
                    # Find closest point on road segment
                    closest = SimplePathfinder._closest_point_on_segment(
                        (x, y), road.start, road.end
                    )
                    dist = math.hypot(closest[0] - x, closest[1] - y)
                    
                    if dist < min_dist and dist < road_snap_distance:
                        min_dist = dist
                        snap_x, snap_y = closest
            
            # Check highways between cities
            if hasattr(city, 'highways'):
                for road in city.highways:
                    closest = SimplePathfinder._closest_point_on_segment(
                        (x, y), road.start, road.end
                    )
                    dist = math.hypot(closest[0] - x, closest[1] - y)
                    
                    if dist < min_dist and dist < road_snap_distance:
                        min_dist = dist
                        snap_x, snap_y = closest
        
        is_on_road = min_dist < road_snap_distance
        return (snap_x, snap_y, is_on_road)
    
    @staticmethod
    def _closest_point_on_segment(point, seg_start, seg_end):
        """Find closest point on line segment to given point"""
        px, py = point
        sx, sy = seg_start
        ex, ey = seg_end
        
        # Vector from start to end
        dx = ex - sx
        dy = ey - sy
        
        # Handle zero-length segment
        if dx == 0 and dy == 0:
            return seg_start
        
        # Project point onto line segment
        t = ((px - sx) * dx + (py - sy) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))  # Clamp to segment
        
        return (sx + t * dx, sy + t * dy)
    
    @staticmethod
    def get_road_path(start, end, cities):
        """
        Simple pathfinding along roads
        Returns list of waypoints from start to end following roads
        """
        # For now, use direct path with road snapping
        # More sophisticated A* can be added later
        
        # Generate intermediate points
        waypoints = []
        steps = 10
        
        for i in range(steps + 1):
            t = i / steps
            x = start[0] + t * (end[0] - start[0])
            y = start[1] + t * (end[1] - start[1])
            
            # Snap to nearest road
            snap_x, snap_y, is_on_road = SimplePathfinder.snap_to_road(
                (x, y), cities, road_snap_distance=30
            )
            
            if is_on_road:
                waypoints.append((snap_x, snap_y))
            else:
                waypoints.append((x, y))
        
        return waypoints if waypoints else [start, end]
