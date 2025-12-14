import pygame
import sys
from  graphics.optimized_renderer import OptimizedRenderer
from  graphics.camera import Camera
from  graphics.visual_effects import VisualEffects
from  ui.interaction import Interaction
from  ui.ui_manager import UIManagerWrapper
from  ui.dashboard import Dashboard
from  ui.minimap import Minimap
from  core.time_engine import TimeEngine
from  core.numpy_engine import NumpySimulationEngine
from  core.statistics import StatisticsManager
from  data.world_generator import WorldGenerator
from  data.persistence import PersistenceManager
from  data.export import DataExporter
from  entities.person import State
import random
import math

class BioSpatialApp:
    def __init__(self):
        pygame.init()
        # Increase main app window size
        self.width = 1600
        self.height = 900
        
        # Initialize Window (Standard Pygame) - RESIZABLE flag for window resizing
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.RESIZABLE)
        pygame.display.set_caption("Bio-Spatial Epidemic Simulator (Optimized)")
        
        self.clock = pygame.time.Clock()
        self.running = True
        self.is_fullscreen = False  # Track fullscreen state
        self.show_fps = True  # Toggle FPS display
        
        self.camera = Camera(self.width, self.height)
        
        # UI Surface for 2D overlay
        self.ui_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Initialize Core Systems
        self.time_engine = TimeEngine()
        self.cities = WorldGenerator.generate_world(num_cities=5)
        
        # Initialize renderer AFTER cities are generated (needs them for commuter count)
        self.renderer = OptimizedRenderer(self.screen, self.camera)
        self.renderer.set_cities(self.cities)  # Set cities and compute commuter stats
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
        self.infect_radius = 75  # Radius for infection zone

        # New UI Manager
        self.ui_manager = UIManagerWrapper(self.width, self.height, self.simulation_engine)
        # Ensure God Mode panel is visible by default
        self.ui_manager.toggle_god_mode()
        
        self.minimap = Minimap(self.width, self.height)
        if self.world_bounds:
            min_x, min_y, max_x, max_y = self.world_bounds
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
                    self.simulation_engine.state[idx] = State.EXPOSED.value
                    self.simulation_engine.timer[idx] = 100
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
        # Export multiple formats
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

    def toggle_fullscreen(self):
        """Toggle fullscreen mode (F11)"""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF)
        else:
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.RESIZABLE)
        pygame.display.set_caption("Bio-Spatial Epidemic Simulator (Optimized)")
    
    def handle_window_resize(self, new_width, new_height):
        """Handle window resize event"""
        if new_width > 0 and new_height > 0:
            self.width = new_width
            self.height = new_height
            self.camera.width = new_width
            self.camera.height = new_height
            self.ui_surface = pygame.Surface((new_width, new_height), pygame.SRCALPHA)
            self.renderer.screen = self.screen
            # Update minimap position and size on window resize
            self.minimap.size = 200  # Keep consistent size
            self.minimap.x = new_width - self.minimap.size - 10
            self.minimap.y = new_height - self.minimap.size - 10
            self.minimap.rect = pygame.Rect(self.minimap.x, self.minimap.y, self.minimap.size, self.minimap.size)
            # Update UI manager dimensions
            self.ui_manager.width = new_width
            self.ui_manager.height = new_height

    def export_data(self):
        print("Exporting data...")
        if DataExporter.export_csv("simulation_data.csv", self.stats_manager):
            print("Export successful!")
        else:
            print("Export failed.")

    def handle_input(self):
        dt = self.clock.get_time() / 1000.0
        
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
                    # Toggle God Mode window via keyboard
                    self.ui_manager.toggle_god_mode()
                elif event.key == pygame.K_F11:
                    # Toggle fullscreen (F11)
                    self.toggle_fullscreen()
                elif event.key == pygame.K_SPACE:
                    # Toggle pause (Space)
                    self.ui_manager.toggle_pause()
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    # Increase speed (+)
                    new_speed = self.ui_manager.speed + 1.0
                    self.ui_manager.sim_speed_slider.set_current_value(min(new_speed, 20.0))
                elif event.key == pygame.K_MINUS:
                    # Decrease speed (-)
                    new_speed = self.ui_manager.speed - 1.0
                    self.ui_manager.sim_speed_slider.set_current_value(max(new_speed, 0.5))
                elif event.key == pygame.K_h:
                    # Toggle FPS display (H)
                    self.show_fps = not self.show_fps
                elif event.key == pygame.K_t:
                    # Enter box-select tracing mode
                    self.interaction.tracing_enabled = True
                    self.interaction.begin_box_select()
                # Save/Load shortcuts with Ctrl modifier
                elif event.key == pygame.K_s and (event.mod & pygame.KMOD_CTRL):
                    # Save (Ctrl+S)
                    self.save_simulation()
                elif event.key == pygame.K_l and (event.mod & pygame.KMOD_CTRL):
                    # Load (Ctrl+L)
                    self.load_simulation()
                elif event.key == pygame.K_e and (event.mod & pygame.KMOD_CTRL):
                    # Export (Ctrl+E)
                    self.export_data()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and self.interaction.box_select_active:
                    self.interaction.start_box(pygame.mouse.get_pos())
                elif event.button == 1 and (pygame.key.get_mods() & pygame.KMOD_SHIFT):  # Left click + Shift
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    world_pos = self.camera.screen_to_world(mouse_x, mouse_y)
                    self._infect_at_point(world_pos, self.infect_radius)
                elif event.button == 1:
                    self.interaction.select_entity_at_mouse(self.cities)
                elif event.button == 3:
                    self.interaction.clear_selection()
            elif event.type == pygame.MOUSEMOTION:
                self.interaction.update_box(pygame.mouse.get_pos())
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and self.interaction.box_select_active:
                    self.interaction.finalize_box_select(self.cities)
            elif event.type == pygame.VIDEORESIZE:
                # Handle window resize
                if not self.is_fullscreen:
                    self.handle_window_resize(event.w, event.h)
            
            # Pass event to UI Manager
            self.ui_manager.handle_event(event)
                
            # Pass event to Minimap
            if self.minimap.handle_event(event, self.camera):
                continue
            
            # Pass event to camera
            self.camera.handle_event(event)
        
        # Handle continuous input (keys held down)
        self.camera.handle_input()
        
        # Handle Interaction (Hover)
        self.interaction.handle_input(self.cities)

    def update(self):
        dt = self.clock.get_time() / 1000.0
        self.ui_manager.update(dt, self.stats_manager)
        
        self.camera.update()
        self.visual_effects.update()
        
        if not self.ui_manager.paused:
            # Run multiple updates based on speed with an upper cap to reduce lag
            speed_factor = self.ui_manager.speed
            # Keep logic updates modest to avoid heavy CPU when speed is high
            steps = max(1, int(math.ceil(speed_factor)))
            steps = min(steps, 4)
            for _ in range(steps):
                self.time_engine.update()
                
                # Update all cities (movement, state timers)
                # Note: NumpyEngine handles movement now, so we don't need city.update()
                # UNLESS city.update() does something else?
                # city.update() calls person.update(). NumpyEngine replaces this.
                # So we skip city.update().
                
                # Run simulation logic (infections + movement) with dt for smooth motion
                self.simulation_engine.update(self.time_engine, dt)
                
                # Update vaccination efficacy decay
                self.simulation_engine.update_vaccination_efficacy(days=1/20)  # Update proportionally per tick
                
                # Update stats every 20 ticks (optimization: reduced from 10 for better performance)
                if self.time_engine.ticks % 20 == 0:
                    self.stats_manager.update(self.cities, self.time_engine.current_day + self.time_engine.hour/24, engine=self.simulation_engine)

            # Record trace point for the currently selected person
            self.interaction.record_trace_point()


    def render(self):
        # 1. Render World
        # Keep full detail until extreme speeds (only use min_detail above 18.0 speed)
        # This preserves visual clarity at normal playing speeds
        if self.ui_manager.speed > 18.0:
            self.renderer.render(min_detail=True)
        else:
            self.renderer.render()

        # Minimap overlay: Always render; include trace polyline when active
        trace_pts = self.interaction.trace_points if (self.interaction.tracing_enabled and self.interaction.trace_points) else None
        self.minimap.render(self.screen, self.cities, self.camera, trace_pts)
        
        # 2. Render UI (Pygame Surface)
        self.ui_surface.fill((0, 0, 0, 0)) # Clear
        
        # Render UI overlay (Time)
        time_surf = self.font_main.render(self.time_engine.get_time_string(), True, (255, 255, 255))
        self.ui_surface.blit(time_surf, (10, 10))
        
        # Render FPS counter if enabled (H key to toggle)
        if self.show_fps:
            fps = self.clock.get_fps()
            # Color code: green >45, yellow >30, red <30
            if fps > 45:
                fps_color = (0, 255, 0)  # Green
            elif fps > 30:
                fps_color = (255, 255, 0)  # Yellow
            else:
                fps_color = (255, 0, 0)  # Red
            fps_surf = self.font_main.render(f"FPS: {fps:.1f}", True, fps_color)
            self.ui_surface.blit(fps_surf, (10, 40))

        # Render tracing status
        if self.interaction.tracing_enabled and self.interaction.selected_entity:
            state_name = getattr(getattr(self.interaction.selected_entity, 'state', None), 'name', 'Unknown')
            trace_txt = f"Tracing: {getattr(self.interaction.selected_entity, 'uid', 'unknown')} ({state_name})"
            trace_surf = self.font_main.render(trace_txt, True, (0, 240, 255))
            self.ui_surface.blit(trace_surf, (10, 70))
        
        # Render drag-to-infect visual feedback
        # 3. Composite UI onto Screen
        self.renderer.render_overlay(self.ui_surface)
        
        # 4. Draw Pygame GUI (Directly to screen)
        self.ui_manager.manager.draw_ui(self.screen)
        
        # 5. Swap Buffers
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
