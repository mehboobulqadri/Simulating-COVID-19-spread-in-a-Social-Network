import pygame
import sys
from graphics.optimized_renderer import OptimizedRenderer
from graphics.camera import Camera
from graphics.visual_effects import VisualEffects
from ui.interaction import Interaction
from ui.control_panel import ControlPanel  # NEW: Professional left panel
from ui.right_stats_panel import RightStatsPanel  # NEW: Professional right panel
from ui.god_mode import GodModePanel
from ui.minimap import Minimap
from core.time_engine import TimeEngine
from core.numpy_engine import NumpySimulationEngine
from core.statistics import StatisticsManager
from data.world_generator import WorldGenerator
from data.persistence import PersistenceManager
from data.export import DataExporter
from entities.person import State
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
        
        # Get screen dimensions
        info = pygame.display.Info()
        self.width = info.current_w
        self.height = info.current_h
        
        # Initialize Window - start windowed and resizable for flexibility
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.RESIZABLE)
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
        self.renderer = OptimizedRenderer(self.screen, self.camera)
        self.renderer.set_cities(self.cities)
        self.world_bounds = self._compute_world_bounds(self.cities)
        self.simulation_engine = NumpySimulationEngine(self.cities)
        self.stats_manager = StatisticsManager()
        
        # Initialize Visuals & Interaction
        self.visual_effects = VisualEffects()
        self.interaction = Interaction(self.camera)
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
        # self.control_panel.on_god_mode = self.toggle_god_mode # Removed from control panel
        
        # God mode panel state (if you want to keep the pygame_gui version)
        self.god_mode_active = False
        
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
        print("Exporting simulation data...")
        success = True
        
        # CSV export
        if DataExporter.export_csv("simulation_data.csv", self.stats_manager):
            print("✓ CSV export successful!")
        else:
            success = False
        
        # HTML report export
        if DataExporter.export_html("simulation_report.html", self.stats_manager, self.cities):
            print("✓ HTML report generated!")
        else:
            success = False
        
        # JSON export
        if DataExporter.export_json("simulation_data.json", self.stats_manager, self.cities):
            print("✓ JSON export successful!")
        else:
            success = False
        
        if success:
            print("✓ All exports completed successfully!")
        else:
            print("⚠ Some exports failed")
        
        return success

    def toggle_god_mode(self):
        self.god_mode_panel.toggle()

    def toggle_fullscreen(self):
        """Toggle fullscreen mode (F11)"""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF)
            # Get actual fullscreen dimensions
            info = pygame.display.Info()
            self.width = info.current_w
            self.height = info.current_h
        else:
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.RESIZABLE)
        
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
            self.minimap.rect.x = self.minimap.x
            self.minimap.rect.y = self.minimap.y
            
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
                if event.button == 1:
                    # Check God Mode Button
                    if self.god_btn_rect.collidepoint(event.pos):
                        self.toggle_god_mode()
                        return # Consume click
                
                if event.button == 1 and self.interaction.box_select_active:
                    self.interaction.start_box(mouse_pos)
                elif event.button == 1 and self.interaction.quarantine_selection_mode:
                    # Quarantine selection mode - click to toggle district/building quarantine
                    world_pos = self.camera.screen_to_world(*mouse_pos)
                    for city in self.cities:
                        for district in city.districts:
                            if district.bounds.collidepoint(world_pos):
                                # Toggle quarantine for district
                                district.is_quarantined = not district.is_quarantined
                                if district.is_quarantined:
                                    self.interaction.quarantined_districts.add(district)
                                    print(f"🏥 Quarantined: {district.name}")
                                else:
                                    self.interaction.quarantined_districts.discard(district)
                                    print(f"✅ Released: {district.name}")
                                break
                            
                            # Check buildings
                            for building in district.buildings:
                                if building.bounds.collidepoint(world_pos):
                                    building.is_quarantined = not building.is_quarantined
                                    if building.is_quarantined:
                                        self.interaction.quarantined_buildings.add(building)
                                        print(f"🏥 Quarantined: {building.type.name} building")
                                    else:
                                        self.interaction.quarantined_buildings.discard(building)
                                        print(f"✅ Released: {building.type.name} building")
                                    break
                elif event.button == 1 and (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                    world_pos = self.camera.screen_to_world(*mouse_pos)
                    self._infect_at_point(world_pos, self.infect_radius)
                elif event.button == 1:
                    # Check if click is on UI panels first
                    if not self._is_click_on_panels(mouse_pos):
                        self.interaction.select_entity_at_mouse(self.cities)
                elif event.button == 3:
                    self.interaction.clear_selection()
            
            elif event.type == pygame.MOUSEMOTION:
                self.interaction.update_box(mouse_pos)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and self.interaction.box_select_active:
                    self.interaction.finalize_box_select(self.cities)
            
            elif event.type == pygame.VIDEORESIZE:
                if not self.is_fullscreen:
                    self.handle_window_resize(event.w, event.h)
            
            # Pass events to UI panels (they consume if handled)
            if self.god_mode_panel.handle_event(event):
                continue

            if self.control_panel.handle_event(event):
                continue
            
            if self.stats_panel.handle_event(event, self.camera):
                continue
                
            if self.minimap.handle_event(event, self.camera):
                continue
            
            # Pass event to camera
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
        dt = self.clock.get_time() / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        
        # Update UI panels (for hover detection and animation)
        self.control_panel.update(mouse_pos)
        self.stats_panel.update(mouse_pos)
        
        self.camera.update()
        self.visual_effects.update()
        
        if not self.control_panel.paused:
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
            
            # Record trace point for the currently selected person
            self.interaction.record_trace_point()

    def render(self):
        # 1. Render World
        if self.control_panel.speed > 18.0:
            self.renderer.render(min_detail=True)
        else:
            self.renderer.render()
        
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
        
        # 3. Composite UI onto Screen
        self.renderer.render_overlay(self.ui_surface)
        
        # 4. Render Professional UI Panels (always on top)
        self.control_panel.render(self.screen)
        
        # Render God Mode Button
        # Hover effect
        mx, my = pygame.mouse.get_pos()
        hover = self.god_btn_rect.collidepoint(mx, my)
        color = (180, 140, 0) if not hover else (220, 180, 20)
        pygame.draw.rect(self.screen, color, self.god_btn_rect, border_radius=8)
        pygame.draw.rect(self.screen, (255, 215, 0), self.god_btn_rect, 2, border_radius=8)
        
        font = pygame.font.SysFont("Arial", 16, bold=True)
        text_surf = font.render("GOD MODE", True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.god_btn_rect.center)
        self.screen.blit(text_surf, text_rect)
        
        # Pass trace points to stats panel for minimap visualization
        trace_points = self.interaction.trace_points if (self.interaction.tracing_enabled and self.interaction.trace_points) else None
        
        # Render Minimap
        self.minimap.render(self.screen, self.cities, self.camera, trace_points)

        self.stats_panel.render(self.screen, self.stats_manager, self.cities, self.camera, trace_points)
        
        # Render God Mode Panel
        self.god_mode_panel.render(self.screen)
        
        # 5. Draw box select rectangle if active
        if self.interaction.box_select_active and self.interaction.box_start and self.interaction.box_end:
            x1, y1 = self.interaction.box_start
            x2, y2 = self.interaction.box_end
            rect = pygame.Rect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            pygame.draw.rect(self.screen, (0, 255, 255), rect, 2)
        
        # 6. Swap Buffers
        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_input()
            self.update()
            self.render()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    app = BioSpatialApp()
    app.run()