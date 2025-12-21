import pygame
import math
from entities.person import State

class HoverRoad:
    """Lightweight wrapper for hover info on roads/highways."""
    def __init__(self, road, city, near_endpoint=False):
        self.road = road
        self.city = city
        self.near_endpoint = near_endpoint

class Interaction:
    def __init__(self, camera):
        self.camera = camera
        self.hovered_entity = None
        self.selected_entity = None
        self.tracing_enabled = True
        self.trace_points = []  # world-space trail for selected person
        self.trace_max_points = 600
        self.person_pick_radius = 10
        # Box selection state (triggered via T)
        self.box_select_active = False
        self.box_start = None
        self.box_end = None
        
        # Quarantine selection mode
        self.quarantine_selection_mode = False
        self.quarantined_districts = set()  # Track quarantined districts
        self.quarantined_buildings = set()  # Track quarantined buildings
        
        self.simulation_engine = None

    def set_simulation_engine(self, engine):
        self.simulation_engine = engine

    def _screen_to_world(self, sx, sy):
        """Convert screen coordinates to world coordinates using camera."""
        wx = (sx - self.camera.width / 2) / self.camera.zoom + self.camera.x
        wy = (sy - self.camera.height / 2) / self.camera.zoom + self.camera.y
        return wx, wy
        
    def handle_input(self, cities):
        mouse_pos = pygame.mouse.get_pos()
        wx, wy = self._screen_to_world(*mouse_pos)
        self.hovered_entity = self._find_entity_at(wx, wy, cities)

    def select_entity_at_mouse(self, cities):
        """Select the entity under the mouse (prefers people)."""
        if not self.tracing_enabled:
            return None
        mouse_pos = pygame.mouse.get_pos()
        wx, wy = self._screen_to_world(*mouse_pos)
        ent = self._find_entity_at(wx, wy, cities)

        # Only track nodes (people); clear otherwise
        if ent and hasattr(ent, 'state'):
            self.selected_entity = ent
            self._reset_trace(ent)
            print(f"Tracing selected: {getattr(ent, 'uid', 'unknown')}")
        else:
            self.selected_entity = None
            self.trace_points = []
            print("Tracing cleared (no person under cursor)")
        return self.selected_entity

    def clear_selection(self):
        self.selected_entity = None
        self.trace_points = []
        print("Tracing cleared")

    def begin_box_select(self):
        """Enter box-select mode and change cursor to crosshair."""
        self.box_select_active = True
        self.box_start = None
        self.box_end = None
        try:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)
        except Exception:
            # Fallback if system cursors unavailable
            pass

    def cancel_box_select(self):
        self.box_select_active = False
        self.box_start = None
        self.box_end = None
        try:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        except Exception:
            pass

    def start_box(self, screen_pos):
        if not self.box_select_active or not self.tracing_enabled:
            return
        self.box_start = screen_pos
        self.box_end = screen_pos

    def update_box(self, screen_pos):
        if not self.box_select_active or self.box_start is None:
            return
        self.box_end = screen_pos

    def finalize_box_select(self, cities):
        """Pick the nearest person inside the drawn rectangle and exit box mode."""
        if not (self.box_select_active and self.box_start and self.box_end and self.tracing_enabled):
            return None

        x1, y1 = self.box_start
        x2, y2 = self.box_end
        rect = pygame.Rect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
        if rect.width < 4 or rect.height < 4:
            # Treat tiny drags as clicks
            self.cancel_box_select()
            return self.select_entity_at_mouse(cities)

        target = None
        best_dist = 1e12
        rect_center = (rect.centerx, rect.centery)

        for city in cities:
            for district in city.districts:
                for person in district.people:
                    sx, sy = self.camera.apply(person.x, person.y)
                    if rect.collidepoint(sx, sy):
                        d2 = (sx - rect_center[0]) ** 2 + (sy - rect_center[1]) ** 2
                        if d2 < best_dist:
                            best_dist = d2
                            target = person

        if target:
            self.selected_entity = target
            self._reset_trace(target)
            print(f"Tracing selected via box: {getattr(target, 'uid', 'unknown')}")
        else:
            self.selected_entity = None
            self.trace_points = []
            print("Tracing cleared (no person in box)")

        self.cancel_box_select()
        return self.selected_entity
        
    def _find_entity_at(self, x, y, cities):
        zoom = self.camera.zoom

        def dist_point_to_seg_sq(px, py, ax, ay, bx, by):
            apx, apy = px - ax, py - ay
            abx, aby = bx - ax, by - ay
            ab_len_sq = abx * abx + aby * aby
            if ab_len_sq == 0:
                return (px - ax) ** 2 + (py - ay) ** 2
            t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab_len_sq))
            proj_x = ax + t * abx
            proj_y = ay + t * aby
            dx = px - proj_x
            dy = py - proj_y
            return dx * dx + dy * dy

        # Prefer nearest person before anything else (so people win over highways/corners)
        best_person = None
        best_dist = 1e12
        pick_r2 = self.person_pick_radius ** 2
        
        if self.simulation_engine:
            # Use engine for fast lookup
            nearby_indices = self.simulation_engine._get_nearby_agents(x, y, pick_r2)
            
            for idx in nearby_indices:
                px, py = self.simulation_engine.pos[idx]
                dist_sq = (px - x)**2 + (py - y)**2
                if dist_sq < pick_r2 and dist_sq < best_dist:
                    best_dist = dist_sq
                    best_person = self.simulation_engine.person_map[idx]
                    # Sync data for this person
                    best_person.x = px
                    best_person.y = py
                    best_person.state = State(self.simulation_engine.state[idx])
                    best_person.variant = self.simulation_engine.variant_names[int(self.simulation_engine.variant_id[idx])]
                    best_person.is_vaccinated = bool(self.simulation_engine.is_vaccinated[idx])
                    best_person.is_asymptomatic = bool(self.simulation_engine.is_asymptomatic[idx])
        else:
            for city in cities:
                for district in city.districts:
                    for person in district.people:
                        dist_sq = (person.x - x) ** 2 + (person.y - y) ** 2
                        if dist_sq < pick_r2 and dist_sq < best_dist:
                            best_person = person
                            best_dist = dist_sq
                            
        if best_person:
            return best_person

        # District or Building under cursor (if no person was closer)
        for city in cities:
            for district in city.districts:
                if district.bounds.collidepoint(x, y):
                    # Try to refine to building
                    for b in district.buildings:
                        if b.bounds.collidepoint(x, y):
                            return b
                    return district

        # Roads and highways (show info even when not over districts)
        road_pick_padding = 12
        for city in cities:
            # Highways first (wider threshold)
            for collection in [getattr(city, 'highways', []), getattr(city, 'roads', [])]:
                for road in collection:
                    ax, ay = road.start
                    bx, by = road.end
                    dist_sq = dist_point_to_seg_sq(x, y, ax, ay, bx, by)
                    threshold = (road.width * 0.5 + road_pick_padding) ** 2

                    if dist_sq < threshold:
                        # Check if we're near an endpoint (intersection/corner)
                        near_endpoint = False
                        end_thresh = (road.width * 0.5 + road_pick_padding) ** 2
                        if (x - ax) ** 2 + (y - ay) ** 2 < end_thresh:
                            near_endpoint = True
                        elif (x - bx) ** 2 + (y - by) ** 2 < end_thresh:
                            near_endpoint = True
                        return HoverRoad(road, city, near_endpoint=near_endpoint)

        # City centers at low zoom
        if zoom < 0.5:
            for city in cities:
                dist_sq = (city.location[0] - x) ** 2 + (city.location[1] - y) ** 2
                if dist_sq < 20 ** 2:
                    return city

        return None

    def get_hover_info(self):
        if not self.hovered_entity:
            return None
            
        info = []
        ent = self.hovered_entity
        
        # Determine type by checking attributes
        if hasattr(ent, 'districts'): # City
            info.append(f"City: {ent.name}")
            info.append(f"Districts: {len(ent.districts)}")
            pop = sum(len(d.people) for d in ent.districts)
            info.append(f"Population: {pop}")
            
        elif hasattr(ent, 'people') and hasattr(ent, 'bounds'): # District
            info.append(f"District: {ent.name}")
            info.append(f"Population: {len(ent.people)}")
            infected = sum(1 for p in ent.people if p.state.name == 'INFECTIOUS')
            info.append(f"Infected: {infected}")
        elif hasattr(ent, 'type') and hasattr(ent, 'bounds'): # Building
            btype = getattr(ent.type, 'name', 'UNKNOWN')
            info.append(f"Building: {btype}")
            
        elif hasattr(ent, 'state'): # Person
            info.append(f"Person: {ent.uid}")
            info.append(f"State: {ent.state.name}")
            if hasattr(ent, 'variant'):
                info.append(f"Variant: {ent.variant}")
            info.append(f"Age: {ent.age}")
            if ent.work_location:
                info.append("Has Job")

        elif isinstance(ent, HoverRoad):
            road = ent.road
            kind = getattr(road, 'kind', 'road')
            label = "Highway" if kind == 'highway' else "Road"
            length = math.hypot(road.end[0] - road.start[0], road.end[1] - road.start[1])
            info.append(f"{label}")
            info.append(f"City: {ent.city.name}")
            info.append(f"Length: {int(length)}")
            info.append(f"Width: {road.width}")
            if ent.near_endpoint:
                info.append("Intersection / Corner")
            
        return info

    def record_trace_point(self):
        """Append current selected person's position to the trace trail."""
        if not (self.tracing_enabled and self.selected_entity):
            return
            
        # If it's a person and we have engine, update pos
        if self.simulation_engine and hasattr(self.selected_entity, 'uid'): # It's a person
             idx = self.simulation_engine.person_to_index.get(self.selected_entity)
             if idx is not None:
                 self.selected_entity.x, self.selected_entity.y = self.simulation_engine.pos[idx]
                 
        if not hasattr(self.selected_entity, 'x'):
            return

        pos = (float(self.selected_entity.x), float(self.selected_entity.y))
        if self.trace_points:
            last = self.trace_points[-1]
            dx = pos[0] - last[0]
            dy = pos[1] - last[1]
            if dx * dx + dy * dy < 1.0:  # avoid noise
                return
        self.trace_points.append(pos)
        if len(self.trace_points) > self.trace_max_points:
            self.trace_points = self.trace_points[-self.trace_max_points:]

    def _reset_trace(self, ent):
        self.trace_points = []
        if ent and hasattr(ent, 'x'):
            self.trace_points.append((float(ent.x), float(ent.y)))
    
    def toggle_quarantine_selection(self):
        """Toggle quarantine selection mode on/off"""
        self.quarantine_selection_mode = not self.quarantine_selection_mode
        if self.quarantine_selection_mode:
            print("🎯 QUARANTINE SELECTION MODE: Click districts/buildings to quarantine them")
        else:
            print("🎯 Quarantine selection mode OFF")
        return self.quarantine_selection_mode
