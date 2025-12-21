import pygame
import sys
import os

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass

from graphics.gl_renderer import GLRenderer
from graphics.camera import Camera
from graphics.visual_effects import VisualEffects
from ui.interaction import Interaction
from ui.control_panel import ControlPanel  # NEW: Professional left panel
from ui.right_stats_panel import RightStatsPanel  # NEW: Professional right panel
from ui.god_mode import GodModePanel
from ui.minimap import Minimap
from ui.theme import UITheme
from core.time_engine import TimeEngine
from core.numpy_engine import NumpySimulationEngine
from core.statistics import StatisticsManager
from data.world_generator import WorldGenerator
from data.persistence import PersistenceManager
from data.export import DataExporter
from entities.person import State
from datetime import datetime
import random
import math

class BioSpatialApp:
    def __init__(self):
        # Fix for high DPI displays on Windows
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass

        pygame.init()
        # Request an OpenGL 3.3 core profile context before creating the window.
        # Without this on macOS, ModernGL fails to create a usable context and the screen stays black.
        try:
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
            pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
        except Exception:
            pass
        
        # Get screen dimensions
        info = pygame.display.Info()
        self.width = info.current_w
        self.height = info.current_h
        
        # Initialize Window - start windowed and resizable for flexibility
        # Enable OpenGL context for ModernGL
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE)
        pygame.display.set_caption("Bio-Spatial Epidemic Simulator")
        
        self.clock = pygame.time.Clock()
        self.running = True
        self.is_fullscreen = False
        self.show_fps = True
        
        self.camera = Camera(self.width, self.height)
        
        # UI Surface for 2D overlay
        self.ui_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Ensure wheel events are delivered (trackpad/scroll)
        try:
            pygame.event.set_allowed([pygame.MOUSEWHEEL, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.KEYDOWN, pygame.QUIT, pygame.VIDEORESIZE])
        except Exception:
            pass

        # Initialize Core Systems
        self.time_engine = TimeEngine()
        self.cities = WorldGenerator.generate_world(num_cities=5)
        
        # Initialize renderer AFTER cities are generated
        self.renderer = GLRenderer(self.screen, self.camera)
        self.renderer.set_cities(self.cities)
        self.world_bounds = self._compute_world_bounds(self.cities)
        self.simulation_engine = NumpySimulationEngine(self.cities)
        self.renderer.set_simulation_engine(self.simulation_engine)
        self.stats_manager = StatisticsManager()
        
        # Initialize Visuals & Interaction
        self.visual_effects = VisualEffects()
        self.interaction = Interaction(self.camera)
        self.interaction.set_simulation_engine(self.simulation_engine)
        self.interaction.tracing_enabled = True
        
        # Fonts
        self.font_main = pygame.font.SysFont("Arial", 20)
        
        # Infect mode state
        self.infect_mode = False
        self.infect_radius = 75
        
        # NEW: Professional UI Panels (replace old UI)
        self.control_panel = ControlPanel(self.width, self.height)
        self.stats_panel = RightStatsPanel(self.width, self.height)
        self.god_mode_panel = GodModePanel(self.width, self.height, self.simulation_engine)
        self.minimap = Minimap(self.width, self.height)
        
        # God Mode Button (Top Right)
        self.god_btn_rect = pygame.Rect(self.width - 140, 10, 120, 40)
        
        # Setup callbacks for control panel
        self.control_panel.on_save = self.save_simulation
        self.control_panel.on_load = self.load_simulation
        self.control_panel.on_export = self.export_data
        self.control_panel.on_report = self.generate_report
        # self.control_panel.on_god_mode = self.toggle_god_mode # Removed from control panel
        
        # God mode panel state (if you want to keep the pygame_gui version)
        self.god_mode_active = False
        
        # Main window drag state
        self.main_window_dragging = False
        self.main_window_drag_start = (0, 0)
        
        # Set world bounds for minimap in stats panel
        if self.world_bounds:
            min_x, min_y, max_x, max_y = self.world_bounds
            self.stats_panel.set_world_bounds(min_x, min_y, max_x, max_y)
            self.minimap.set_world_bounds(min_x, min_y, max_x, max_y)
            self.camera.frame_bounds(min_x, min_y, max_x, max_y)
        
        # Connect systems
        self.renderer.visual_effects = self.visual_effects
        self.renderer.interaction = self.interaction
        self.renderer.time_engine = self.time_engine
        
        # Infect patient zero
        self._infect_patient_zero()
        
        # Pass data to renderer
        self.renderer.set_world_data(self.cities)

        # HUD cache
        self._hud_cache = None
        self._hud_cache_tick = -1

    def _compute_world_bounds(self, cities):
        xs, ys = [], []
        for city in cities:
            for district in city.districts:
                r = district.bounds
                xs.extend([r.left, r.right])
                ys.extend([r.top, r.bottom])
        if not xs or not ys:
            return None
        return (min(xs), min(ys), max(xs), max(ys))

    def _infect_patient_zero(self):
        pos = self.simulation_engine.infect_random_person()
        if pos is not None:
            self.visual_effects.add_infection_effect(pos[0], pos[1])
            print(f"Patient Zero infected at {pos}")
    
    def _infect_at_point(self, world_pos, radius=75):
        """Infect all agents within a circular zone at the given point"""
        infected_count = 0
        zone_x, zone_y = world_pos
        
        # Check all agents in the numpy engine
        for idx in range(self.simulation_engine.num_people):
            agent_x, agent_y = self.simulation_engine.pos[idx]
            dist_sq = (agent_x - zone_x) ** 2 + (agent_y - zone_y) ** 2
            
            if dist_sq < radius ** 2:
                # Only infect susceptible agents
                if self.simulation_engine.state[idx] == State.SUSCEPTIBLE.value:
                    variant_idx = int(self.simulation_engine.active_variant)
                    self.simulation_engine._apply_exposure(idx, variant_idx)
                    infected_count += 1
                    self.visual_effects.add_infection_effect(agent_x, agent_y)
        
        if infected_count > 0:
            print(f"✓ Infected {infected_count} agents at ({zone_x:.0f}, {zone_y:.0f})")
        else:
            print(f"⚠ No susceptible agents in radius at ({zone_x:.0f}, {zone_y:.0f})")
        
        return infected_count

    def save_simulation(self):
        print("Saving simulation...")
        if PersistenceManager.save_state("savegame.bio", self.cities, self.time_engine, self.stats_manager):
            print("✓ Save successful!")
            return True
        else:
            print("✗ Save failed.")
            return False

    def load_simulation(self):
        print("Loading simulation...")
        data = PersistenceManager.load_state("savegame.bio")
        if data:
            self.cities = data['cities']
            self.time_engine.ticks = data['time']['ticks']
            self.time_engine.current_day = data['time']['current_day']
            self.stats_manager.history = data['stats']['history']
            self.stats_manager.time_points = data['stats']['time_points']
            
            # Reconnect references
            self.simulation_engine.cities = self.cities
            self.renderer.set_world_data(self.cities)
            print("✓ Load successful!")
            return True
        else:
            print("✗ Load failed.")
            return False

    def export_data(self):
        """Export simulation data to CSV/JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"data/exports/simulation_{timestamp}"
        
        # Ensure export directory exists
        import os
        if not os.path.exists("data/exports"):
            os.makedirs("data/exports")
            
        print("Exporting simulation data...")
        csv_success = DataExporter.export_csv(f"{filename_base}.csv", self.stats_manager)
        html_success = DataExporter.export_html(f"{filename_base}.html", self.stats_manager, self.renderer.cities)
        json_success = DataExporter.export_json(f"{filename_base}.json", self.stats_manager, self.renderer.cities)
        
        if csv_success:
            print("✓ CSV export successful!")
        if html_success:
            print("✓ HTML export generated!")
        if json_success:
            print("✓ JSON export successful!")
            
        if not (csv_success and html_success and json_success):
            print("⚠ Some exports failed")

    def generate_report(self):
        """Generate comprehensive report in multiple formats"""
        # Warning if simulation is running
        force_generate = False
        
        # Simple console confirmation for now (could be GUI dialog later)
        # Using a non-blocking check approach or blocking dialog
        
        print("\n--- REPORT GENERATION ---")
        if not self.control_panel.paused:
            print("⚠ WARNING: Simulation is still running!")
            print("The report will only contain data up to the current moment.")
            print("It is recommended to PAUSE or wait for completion.")
            
            # Auto-pause for generation safety
            was_paused = self.control_panel.paused
            self.control_panel.paused = True
            
            # In a GUI app, we'd show a dialog here. 
            # For now we'll proceed but notify the user in console.
            print(">> Generating incomplete report snapshot...")
        else:
            was_paused = True # Already paused
            print("Generating full report...")
            
        output_dir = "data/reports"
        success = DataExporter.generate_comprehensive_report(output_dir, self.stats_manager)
        
        if success:
            print(f"✓ Report generated successfully in {output_dir}/")
            # Windows notification or sound could go here
        else:
            print("❌ Report generation failed. Check console for details.")
            
            print("❌ Report generation failed. Check console for details.")
            
        # Restore pause state if we auto-paused
        if not was_paused:
            self.control_panel.paused = False
            
        print("-------------------------\n")
        
        return success

    def toggle_god_mode(self):
        self.god_mode_panel.toggle()

    def toggle_fullscreen(self):
        """Toggle fullscreen mode (F11)"""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.OPENGL)
            # Get actual fullscreen dimensions
            info = pygame.display.Info()
            self.width = info.current_w
            self.height = info.current_h
        else:
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE)
        
        self.handle_window_resize(self.width, self.height)
        pygame.display.set_caption("Bio-Spatial Epidemic Simulator")
    
    def handle_window_resize(self, new_width, new_height):
        """Handle window resize event"""
        if new_width > 0 and new_height > 0:
            self.width = new_width
            self.height = new_height
            self.camera.width = new_width
            self.camera.height = new_height
            self.ui_surface = pygame.Surface((new_width, new_height), pygame.SRCALPHA)
            self.renderer.screen = self.screen
            
            # Update panel dimensions
            self.control_panel.height = new_height
            self.control_panel.rect.height = new_height
            self.stats_panel.height = new_height
            self.stats_panel.rect.height = new_height
            self.stats_panel.screen_width = new_width
            
            # Update minimap position
            self.minimap.x = new_width - self.minimap.size - 10
            self.minimap.y = new_height - self.minimap.size - 10
            self.minimap.rect = pygame.Rect(self.minimap.x, self.minimap.y, self.minimap.size, self.minimap.size)
            
            # Update God Mode Button
            self.god_btn_rect.x = new_width - 140
            
            # Update God Mode Panel position (center it)
            self.god_mode_panel.center_on_screen(new_width, new_height)

    def handle_input(self):
        dt = self.clock.get_time() / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_f:
                    if self.world_bounds:
                        min_x, min_y, max_x, max_y = self.world_bounds
                        self.camera.frame_bounds(min_x, min_y, max_x, max_y)
                elif event.key == pygame.K_g:
                    self.toggle_god_mode()
                elif event.key == pygame.K_l and not (event.mod & pygame.KMOD_CTRL):
                    # L key for Lockdown (unless Ctrl+L for Load)
                    self.simulation_engine.toggle_lockdown()
                elif event.key == pygame.K_q and not (event.mod & pygame.KMOD_CTRL):
                    # Q key for Quarantine
                    self.simulation_engine.toggle_quarantine()
                elif event.key == pygame.K_r and not (event.mod & pygame.KMOD_CTRL):
                    # R key for Quarantine selection (Right-click areas)
                    self.interaction.toggle_quarantine_selection()
                elif event.key == pygame.K_v:
                    # Cycle active variant for new infections
                    self.simulation_engine.cycle_variant()
                elif event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key == pygame.K_SPACE:
                    self.control_panel.toggle_pause()
                elif event.key == pygame.K_1:
                    self.control_panel.set_speed(1.0)
                elif event.key == pygame.K_2:
                    self.control_panel.set_speed(2.0)
                elif event.key == pygame.K_5:
                    self.control_panel.set_speed(5.0)
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    new_speed = min(self.control_panel.speed + 1.0, 20.0)
                    self.control_panel.set_speed(new_speed)
                elif event.key == pygame.K_MINUS:
                    new_speed = max(self.control_panel.speed - 1.0, 0.5)
                    self.control_panel.set_speed(new_speed)
                elif event.key == pygame.K_h:
                    self.show_fps = not self.show_fps
                elif event.key == pygame.K_t:
                    self.interaction.tracing_enabled = True
                    self.interaction.begin_box_select()
                # Save/Load shortcuts with Ctrl modifier
                elif event.key == pygame.K_s and (event.mod & pygame.KMOD_CTRL):
                    self.save_simulation()
                elif event.key == pygame.K_l and (event.mod & pygame.KMOD_CTRL):
                    self.load_simulation()
                elif event.key == pygame.K_e and (event.mod & pygame.KMOD_CTRL):
                    self.export_data()
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                
                if event.button == 1:
                    # Check God Mode Button
                    if self.god_btn_rect.collidepoint(event.pos):
                        self.toggle_god_mode()
                        continue  # Consume click
                    
                    # Start dragging if not on UI panels
                    if not self._is_click_on_panels(mouse_pos):
                        self.main_window_dragging = True
                        self.main_window_drag_start = mouse_pos
                
                # Handle special mode clicks (these prevent camera drag)
                if event.button == 1 and self.interaction.box_select_active:
                    self.interaction.start_box(mouse_pos)
                    continue
                elif event.button == 1 and self.interaction.quarantine_selection_mode:
                    # Quarantine selection mode - click to toggle district/building quarantine
                    world_pos = self.camera.screen_to_world(*mouse_pos)
                    for city in self.cities:
                        for district in city.districts:
                            if district.bounds.collidepoint(world_pos):
                                # Toggle quarantine for district
                                district.is_quarantined = not district.is_quarantined
                                if district.is_quarantined:
                                    # Quarantine everyone in the district immediately
                                    self.simulation_engine.set_quarantine_for_people(
                                        district.people,
                                        active=True,
                                        location=(district.bounds.centerx, district.bounds.centery)
                                    )
                                    self.interaction.quarantined_districts.add(district)
                                    print(f"🏥 Quarantined: {district.name}")
                                else:
                                    self.simulation_engine.set_quarantine_for_people(district.people, active=False)
                                    self.interaction.quarantined_districts.discard(district)
                                    print(f"✅ Released: {district.name}")
                                continue
                            
                            # Check buildings
                            for building in district.buildings:
                                if building.bounds.collidepoint(world_pos):
                                    building.is_quarantined = not building.is_quarantined
                                    if building.is_quarantined:
                                        # Quarantine only people that belong to this building (home/work/school match)
                                        # People store home/work/school locations; filter by bounding box membership.
                                        people = [
                                            p for p in district.people
                                            if building.bounds.collidepoint(*p.home_location)
                                            or building.bounds.collidepoint(*getattr(p, 'work_location', p.home_location))
                                            or building.bounds.collidepoint(*getattr(p, 'school_location', p.home_location))
                                        ]
                                        self.simulation_engine.set_quarantine_for_people(
                                            people,
                                            active=True,
                                            location=(building.bounds.centerx, building.bounds.centery)
                                        )
                                        self.interaction.quarantined_buildings.add(building)
                                        print(f"🏥 Quarantined: {building.type.name} building")
                                    else:
                                        people = [
                                            p for p in district.people
                                            if building.bounds.collidepoint(*p.home_location)
                                            or building.bounds.collidepoint(*getattr(p, 'work_location', p.home_location))
                                            or building.bounds.collidepoint(*getattr(p, 'school_location', p.home_location))
                                        ]
                                        self.simulation_engine.set_quarantine_for_people(people, active=False)
                                        self.interaction.quarantined_buildings.discard(building)
                                        print(f"✅ Released: {building.type.name} building")
                                    continue
                elif event.button == 1 and (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                    world_pos = self.camera.screen_to_world(*mouse_pos)
                    self._infect_at_point(world_pos, self.infect_radius)
                    continue
                elif event.button == 1 and self.god_mode_panel.visible and not self._is_click_on_panels(mouse_pos):
                    world_pos = self.camera.screen_to_world(*mouse_pos)
                    self._infect_at_point(world_pos, self.infect_radius)
                    continue
                
                # Right click clears selection
                if event.button == 3:
                    self.interaction.clear_selection()
            
            elif event.type == pygame.MOUSEMOTION:
                mouse_pos = pygame.mouse.get_pos()
                self.interaction.update_box(mouse_pos)
                
                # Handle main window drag
                if self.main_window_dragging:
                    dx = event.pos[0] - self.main_window_drag_start[0]
                    dy = event.pos[1] - self.main_window_drag_start[1]
                    
                    # Pan camera (inverse of mouse movement)
                    pan_x = dx / self.camera.zoom
                    pan_y = dy / self.camera.zoom
                    
                    self.camera.x -= pan_x
                    self.camera.y -= pan_y
                    self.camera.target_x -= pan_x
                    self.camera.target_y -= pan_y
                    
                    self.main_window_drag_start = event.pos
            
            elif event.type == pygame.MOUSEBUTTONUP:
                mouse_pos = pygame.mouse.get_pos()
                
                if event.button == 1:
                    self.main_window_dragging = False
                
                if event.button == 1 and self.interaction.box_select_active:
                    self.interaction.finalize_box_select(self.cities)
                elif event.button == 1 and not self.camera.did_drag:
                    # Only select entity if we didn't actually drag
                    # and not in any special modes
                    if (not self.interaction.box_select_active and 
                        not self.interaction.quarantine_selection_mode and
                        not (pygame.key.get_mods() & pygame.KMOD_SHIFT) and
                        not self._is_click_on_panels(mouse_pos)):
                        self.interaction.select_entity_at_mouse(self.cities)
            
            elif event.type == pygame.VIDEORESIZE:
                if not self.is_fullscreen:
                    self.handle_window_resize(event.w, event.h)
            
            # Pass events to UI panels first (they consume if handled)
            if self.minimap.handle_event(event, self.camera):
                continue
                
            if self.god_mode_panel.handle_event(event):
                continue

            if self.control_panel.handle_event(event):
                continue
            
            if self.stats_panel.handle_event(event, self.camera):
                continue
            
            # Pass events to camera for drag/zoom (only if panels didn't consume)
            self.camera.handle_event(event)
        
        # Handle continuous input (keys held down)
        self.camera.handle_input()
        
        # Handle Interaction (Hover)
        self.interaction.handle_input(self.cities)

    def _is_click_on_panels(self, mouse_pos):
        """Check if mouse click is on any UI panel"""
        mx, my = mouse_pos
        
        # Check control panel (left side)
        if self.control_panel.rect.collidepoint(mx, my):
            return True
        
        # Check stats panel (right side)
        if self.stats_panel.rect.collidepoint(mx, my):
            return True
            
        # Check minimap
        if self.minimap.rect.collidepoint(mx, my):
            return True
            
        # Check god mode panel
        if self.god_mode_panel.visible and self.god_mode_panel.rect.collidepoint(mx, my):
            return True
        
        return False


    def update(self):
        import time
        dt = self.clock.get_time() / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        
        t0 = time.perf_counter()
        # Update UI panels (for hover detection and animation)
        self.control_panel.update(mouse_pos)
        self.stats_panel.update(mouse_pos)
        ui_time = (time.perf_counter() - t0) * 1000
        
        t1 = time.perf_counter()
        self.camera.update()
        self.visual_effects.update()
        cam_vfx_time = (time.perf_counter() - t1) * 1000
        
        sim_time = 0
        if not self.control_panel.paused:
            t2 = time.perf_counter()
            # Run multiple updates based on speed
            speed_factor = self.control_panel.speed
            steps = max(1, int(math.ceil(speed_factor)))
            steps = min(steps, 4)
            
            for _ in range(steps):
                self.time_engine.update()
                
                # Run simulation logic (infections + movement)
                self.simulation_engine.update(self.time_engine, dt)
                
                # Update vaccination efficacy decay
                self.simulation_engine.update_vaccination_efficacy(days=1/20)
                
                # Update stats every 20 ticks
                if self.time_engine.ticks % 20 == 0:
                    self.stats_manager.update(
                        self.cities, 
                        self.time_engine.current_day + self.time_engine.hour/24, 
                        engine=self.simulation_engine
                    )
            sim_time = (time.perf_counter() - t2) * 1000
            
            # Record trace point for the currently selected person
            self.interaction.record_trace_point()
        
        # Store timing info
        if not hasattr(self, '_update_times'):
            self._update_times = []
        self._update_times.append((ui_time, cam_vfx_time, sim_time))

    def render(self):
        import time
        # 1. Render World
        t0 = time.perf_counter()
        if self.control_panel.speed > 18.0:
            self.renderer.render(min_detail=True)
        else:
            self.renderer.render()
        render_time = (time.perf_counter() - t0) * 1000
        
        # 2. Render UI Overlay (Time, FPS, Tracing info)
        self.ui_surface.fill((0, 0, 0, 0))
        
        # Time display (top-left, but below where panels might slide)
        time_surf = self.font_main.render(self.time_engine.get_time_string(), True, (255, 255, 255))
        self.ui_surface.blit(time_surf, (self.width // 2 - 100, 10))
        
        # FPS counter
        if self.show_fps:
            fps = self.clock.get_fps()
            if fps > 45:
                fps_color = (0, 255, 0)
            elif fps > 30:
                fps_color = (255, 255, 0)
            else:
                fps_color = (255, 0, 0)
            fps_surf = self.font_main.render(f"FPS: {fps:.1f}", True, fps_color)
            self.ui_surface.blit(fps_surf, (self.width // 2 - 100, 40))
        
        # Tracing status
        if self.interaction.tracing_enabled and self.interaction.selected_entity:
            selected = self.interaction.selected_entity
            state = getattr(selected, 'state', None)
            state_name = getattr(state, 'name', 'Unknown')
            # Clarify infectious state with symptom visibility
            if state == State.INFECTIOUS:
                if getattr(selected, 'is_asymptomatic', False):
                    state_name = "INFECTIOUS (ASYMPTOMATIC)"
                else:
                    state_name = "INFECTIOUS (SYMPTOMATIC)"
            variant = getattr(selected, 'variant', 'base')
            trace_txt = f"Tracing: {getattr(selected, 'uid', 'unknown')} ({state_name}, variant: {variant})"
            trace_surf = self.font_main.render(trace_txt, True, (0, 240, 255))
            self.ui_surface.blit(trace_surf, (self.width // 2 - 150, 70))
        
        # Lockdown status indicator
        if self.simulation_engine.lockdown_active:
            lockdown_font = pygame.font.SysFont("Arial", 18, bold=True)
            lockdown_txt = "🔒 LOCKDOWN ACTIVE"
            lockdown_surf = lockdown_font.render(lockdown_txt, True, (255, 100, 100))
            lockdown_rect = lockdown_surf.get_rect(center=(self.width // 2, 70))
            # Background for visibility
            bg_rect = lockdown_rect.inflate(20, 10)
            pygame.draw.rect(self.ui_surface, (40, 0, 0, 200), bg_rect, border_radius=5)
            pygame.draw.rect(self.ui_surface, (255, 100, 100), bg_rect, 2, border_radius=5)
            self.ui_surface.blit(lockdown_surf, lockdown_rect)
        
        # Quarantine status indicator
        if self.simulation_engine.quarantine_active:
            quarantine_font = pygame.font.SysFont("Arial", 18, bold=True)
            quarantine_txt = "🏥 QUARANTINE ACTIVE"
            quarantine_surf = quarantine_font.render(quarantine_txt, True, (100, 200, 255))
            # Position below lockdown if both active, otherwise at top
            y_pos = 100 if self.simulation_engine.lockdown_active else 70
            quarantine_rect = quarantine_surf.get_rect(center=(self.width // 2, y_pos))
            # Background for visibility
            bg_rect = quarantine_rect.inflate(20, 10)
            pygame.draw.rect(self.ui_surface, (0, 20, 40, 200), bg_rect, border_radius=5)
            pygame.draw.rect(self.ui_surface, (100, 200, 255), bg_rect, 2, border_radius=5)
            self.ui_surface.blit(quarantine_surf, quarantine_rect)
        
        # Quarantine selection mode indicator
        if self.interaction.quarantine_selection_mode:
            qsel_font = pygame.font.SysFont("Arial", 16, bold=True)
            qsel_txt = "🎯 CLICK TO QUARANTINE AREAS"
            qsel_surf = qsel_font.render(qsel_txt, True, (255, 200, 0))
            y_pos = 130 if (self.simulation_engine.lockdown_active or self.simulation_engine.quarantine_active) else 70
            qsel_rect = qsel_surf.get_rect(center=(self.width // 2, y_pos))
            # Background for visibility
            bg_rect = qsel_rect.inflate(20, 10)
            pygame.draw.rect(self.ui_surface, (60, 40, 0, 200), bg_rect, border_radius=5)
            pygame.draw.rect(self.ui_surface, (255, 200, 0), bg_rect, 2, border_radius=5)
            self.ui_surface.blit(qsel_surf, qsel_rect)

        # Keyboard shortcuts help (bottom center)
        help_font = pygame.font.SysFont("Arial", 14)
        shortcuts = [
            "SPACE: Pause/Play | 1/2/5: Speed | T: Trace | F: Frame | L: Lockdown | Q: Quarantine",
            "R: Quarantine Select | SHIFT+Click: Infect | H: FPS | Ctrl+S: Save | Ctrl+L: Load"
        ]
        y_offset = self.height - 50
        for text in shortcuts:
            help_surf = help_font.render(text, True, (180, 180, 180))
            help_rect = help_surf.get_rect(center=(self.width // 2, y_offset))
            self.ui_surface.blit(help_surf, help_rect)
            y_offset += 20
        
        # 3. Render Professional UI Panels to ui_surface (not screen)
        self.control_panel.render(self.ui_surface)
        
        # Render God Mode Button to ui_surface
        mx, my = pygame.mouse.get_pos()
        hover = self.god_btn_rect.collidepoint(mx, my)
        color = (180, 140, 0) if not hover else (220, 180, 20)
        pygame.draw.rect(self.ui_surface, color, self.god_btn_rect, border_radius=8)
        pygame.draw.rect(self.ui_surface, (255, 215, 0), self.god_btn_rect, 2, border_radius=8)
        
        font = pygame.font.SysFont("Arial", 16, bold=True)
        text_surf = font.render("GOD MODE", True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.god_btn_rect.center)
        self.ui_surface.blit(text_surf, text_rect)
        
        # Pass trace points to stats panel for minimap visualization
        trace_points = self.interaction.trace_points if (self.interaction.tracing_enabled and self.interaction.trace_points) else None
        
        # Render Minimap to ui_surface
        self.minimap.render(self.ui_surface, self.cities, self.camera, trace_points, self.simulation_engine)

        self.stats_panel.render(self.ui_surface, self.stats_manager, self.cities, self.camera, trace_points)
        
        # Quarantine highlights in world space
        self._render_quarantine_highlights(self.ui_surface)

        # Always-visible overlays (legend)
        self._render_state_legend(self.ui_surface)

        # Render God Mode Panel to ui_surface
        self.god_mode_panel.render(self.ui_surface)

        # Hover info card (entities/buildings/districts/roads)
        hover_info = self.interaction.get_hover_info()
        if hover_info:
            self._render_hover_info(self.ui_surface, hover_info, pygame.mouse.get_pos())
        
        # Draw box select rectangle to ui_surface if active
        if self.interaction.box_select_active and self.interaction.box_start and self.interaction.box_end:
            x1, y1 = self.interaction.box_start
            x2, y2 = self.interaction.box_end
            rect = pygame.Rect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            pygame.draw.rect(self.ui_surface, (0, 255, 255), rect, 2)
        
        # 4. Composite all UI onto OpenGL screen
        t1 = time.perf_counter()
        self.renderer.render_overlay(self.ui_surface)
        overlay_time = (time.perf_counter() - t1) * 1000
        
        # 6. Swap Buffers
        t2 = time.perf_counter()
        pygame.display.flip()
        flip_time = (time.perf_counter() - t2) * 1000
        
        # Store timing info for logging
        if not hasattr(self, '_render_times'):
            self._render_times = []
        self._render_times.append((render_time, overlay_time, flip_time))

    def _render_state_legend(self, surface):
        legend = [
            ((100, 200, 255), "Susceptible"),
            ((255, 255, 100), "Exposed"),
            ((255, 50, 50), "Infectious"),
            ((50, 200, 50), "Recovered"),
            ((150, 150, 150), "Deceased"),
            ((200, 100, 255), "Vaccinated"),
        ]
        padding = 10
        x = 12
        font = UITheme.get_font(12)
        line_h = 18
        width = max(font.size(text)[0] for _, text in legend) + 34
        height = line_h * len(legend) + padding * 2
        y = self.height - height - 12  # Position at bottom-left
        rect = pygame.Rect(x, y, width, height)

        bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        bg.fill((18, 22, 30, 220))
        surface.blit(bg, rect.topleft)
        pygame.draw.rect(surface, UITheme.BORDER_COLOR, rect, 1, border_radius=8)

        cy = rect.y + padding
        for color, label in legend:
            pygame.draw.rect(surface, color, (rect.x + 8, cy + 2, 12, 12), border_radius=2)
            text_surf = font.render(label, True, UITheme.TEXT_COLOR)
            surface.blit(text_surf, (rect.x + 26, cy - 1))
            cy += line_h

    def _render_quarantine_highlights(self, surface):
        # Fill and stroke colors for quarantined selections
        fill_q = (120, 200, 255, 60)
        stroke_q = (120, 200, 255)
        fill_hover = (255, 210, 100, 40)
        stroke_hover = (255, 200, 80)

        def rect_to_poly(rect):
            tl = self.camera.apply(rect.left, rect.top)
            tr = self.camera.apply(rect.right, rect.top)
            br = self.camera.apply(rect.right, rect.bottom)
            bl = self.camera.apply(rect.left, rect.bottom)
            return [tl, tr, br, bl]

        # Draw quarantined areas
        for district in getattr(self.interaction, 'quarantined_districts', []):
            poly = rect_to_poly(district.bounds)
            pygame.draw.polygon(surface, fill_q, poly)
            pygame.draw.polygon(surface, stroke_q, poly, width=2)

        for building in getattr(self.interaction, 'quarantined_buildings', []):
            poly = rect_to_poly(building.bounds)
            pygame.draw.polygon(surface, fill_q, poly)
            pygame.draw.polygon(surface, stroke_q, poly, width=2)

        # Highlight hovered target while in selection mode
        if self.interaction.quarantine_selection_mode and self.interaction.hovered_entity:
            ent = self.interaction.hovered_entity
            if hasattr(ent, 'bounds'):
                poly = rect_to_poly(ent.bounds)
                pygame.draw.polygon(surface, fill_hover, poly)
                pygame.draw.polygon(surface, stroke_hover, poly, width=2)

    def _render_hud_summary(self, surface):
        # Update cached values every 20 ticks to keep overhead low
        if self.time_engine.ticks != self._hud_cache_tick and self.time_engine.ticks % 20 == 0:
            latest = self.stats_manager.get_latest_counts()
            total_agents = 0
            total_commuters = 0
            for city in self.cities:
                for district in city.districts:
                    for p in district.people:
                        total_agents += 1
                        home_id = getattr(p, 'home_city_id', None)
                        work_id = getattr(p, 'work_city_id', None)
                        if home_id is not None and work_id is not None and work_id != home_id:
                            total_commuters += 1
            metrics = self.stats_manager.get_advanced_metrics()
            self._hud_cache = {
                'latest': latest,
                'total_agents': total_agents,
                'commuters': total_commuters,
                'r_value': metrics.get('r_value', 0.0),
                'doubling': metrics.get('doubling_time', float('inf')),
            }
            self._hud_cache_tick = self.time_engine.ticks

        if not self._hud_cache:
            return

        hud = self._hud_cache
        x = self.width - 260
        y = 60  # Leave room for God Mode button
        w = 248
        h = 140
        rect = pygame.Rect(x, y, w, h)

        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((20, 24, 32, 220))
        surface.blit(bg, (x, y))
        pygame.draw.rect(surface, UITheme.BORDER_COLOR, rect, 1, border_radius=10)

        font_title = UITheme.get_font(14, bold=True)
        font_val = UITheme.get_font(14)
        surface.blit(font_title.render("OVERVIEW", True, UITheme.ACCENT_COLOR), (x + 12, y + 10))

        lines = [
            ("Total Agents", hud['total_agents']),
            ("Commuters", hud['commuters']),
            ("Exposed", hud['latest'].get(State.EXPOSED, 0)),
            ("Infectious", hud['latest'].get(State.INFECTIOUS, 0)),
            ("R", f"{hud['r_value']:.2f}"),
        ]

        cy = y + 34
        for label, val in lines:
            text = f"{label}: {val}"
            surface.blit(font_val.render(text, True, UITheme.TEXT_COLOR), (x + 12, cy))
            cy += 22

    def _render_hover_info(self, surface, lines, mouse_pos):
        """Draw a small hover info card near the cursor."""
        if not lines:
            return
        # Layout
        font_title = UITheme.get_font(14, bold=True)
        font_body = UITheme.get_font(12)
        max_width = 0
        line_surfs = []
        for i, txt in enumerate(lines):
            font = font_title if i == 0 else font_body
            surf = font.render(str(txt), True, UITheme.TEXT_COLOR)
            line_surfs.append(surf)
            max_width = max(max_width, surf.get_width())
        padding = 12
        line_height = max(s.get_height() for s in line_surfs)
        card_width = max_width + padding * 2
        card_height = line_height * len(line_surfs) + padding * 2

        # Position near cursor with clamp to screen
        mx, my = mouse_pos
        x = mx + 18
        y = my + 18
        screen_w, screen_h = surface.get_size()
        if x + card_width > screen_w:
            x = max(10, mx - card_width - 18)
        if y + card_height > screen_h:
            y = max(10, my - card_height - 18)

        rect = pygame.Rect(x, y, card_width, card_height)

        # Background with slight gradient and border
        bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        bg.fill((18, 22, 30, 230))
        surface.blit(bg, rect.topleft)
        pygame.draw.rect(surface, UITheme.BORDER_COLOR, rect, 1, border_radius=8)

        # Accent stripe
        stripe_rect = pygame.Rect(rect.x, rect.y, 4, rect.height)
        pygame.draw.rect(surface, UITheme.ACCENT_COLOR, stripe_rect, border_radius=3)

        # Text
        cy = rect.y + padding
        for i, surf in enumerate(line_surfs):
            surface.blit(surf, (rect.x + padding + 6, cy))
            cy += surf.get_height()

    def run(self):
        import time
        fps_log_interval = 60  # Log FPS every 60 frames
        frame_count = 0
        fps_samples = []
        
        while self.running:
            self.handle_input()
            self.update()
            self.render()
            self.clock.tick(60)
            
            # Log FPS periodically
            frame_count += 1
            if frame_count % fps_log_interval == 0:
                fps = self.clock.get_fps()
                fps_samples.append(fps)
                
                # Calculate average render times
                if self._render_times:
                    avg_render = sum(t[0] for t in self._render_times) / len(self._render_times)
                    avg_overlay = sum(t[1] for t in self._render_times) / len(self._render_times)
                    avg_flip = sum(t[2] for t in self._render_times) / len(self._render_times)
                    self._render_times = []
                else:
                    avg_render = avg_overlay = avg_flip = 0
                
                # Calculate average update times
                if self._update_times:
                    avg_ui = sum(t[0] for t in self._update_times) / len(self._update_times)
                    avg_cam = sum(t[1] for t in self._update_times) / len(self._update_times)
                    avg_sim = sum(t[2] for t in self._update_times) / len(self._update_times)
                    self._update_times = []
                else:
                    avg_ui = avg_cam = avg_sim = 0
                
                if frame_count == fps_log_interval:
                    print(f"\n[OpenGL Renderer Performance]")
                print(f"Frame {frame_count}: {fps:.1f} FPS")
                print(f"  Render: {avg_render:.2f}ms | Overlay: {avg_overlay:.2f}ms | Flip: {avg_flip:.2f}ms")
                print(f"  UI: {avg_ui:.2f}ms | Cam/VFX: {avg_cam:.2f}ms | Simulation: {avg_sim:.2f}ms")
                print(f"  Total measured: {avg_render+avg_overlay+avg_flip+avg_ui+avg_cam+avg_sim:.2f}ms")
                
                # Log average after 5 samples
                if len(fps_samples) >= 5:
                    avg_fps = sum(fps_samples) / len(fps_samples)
                    print(f"Average FPS (last {len(fps_samples)} samples): {avg_fps:.1f}")
                    fps_samples = []  # Reset

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    app = BioSpatialApp()
    app.run()