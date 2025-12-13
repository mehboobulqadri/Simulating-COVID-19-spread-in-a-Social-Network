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

class BioSpatialApp:
    def __init__(self):
        pygame.init()
        self.width = 1280
        self.height = 720
        
        # Initialize Window (Standard Pygame)
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF)
        pygame.display.set_caption("Bio-Spatial Epidemic Simulator (Optimized)")
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.camera = Camera(self.width, self.height)
        self.renderer = OptimizedRenderer(self.screen, self.camera)
        
        # UI Surface for 2D overlay
        self.ui_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Initialize Core Systems
        self.time_engine = TimeEngine()
        self.cities = WorldGenerator.generate_world(num_cities=5)
        self.world_bounds = self._compute_world_bounds(self.cities)
        self.simulation_engine = NumpySimulationEngine(self.cities)
        self.stats_manager = StatisticsManager()
        
        # Initialize Visuals & Interaction
        self.visual_effects = VisualEffects()
        self.interaction = Interaction(self.camera)
        
        # New UI Manager
        self.ui_manager = UIManagerWrapper(self.width, self.height, self.simulation_engine)
        
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
        xs = []
        ys = []
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

    def save_simulation(self):
        print("Saving simulation...")
        if PersistenceManager.save_state("savegame.bio", self.cities, self.time_engine, self.stats_manager):
            print("Save successful!")
        else:
            print("Save failed.")

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
            print("Load successful!")
        else:
            print("Load failed.")

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
            # Run multiple updates based on speed
            steps = int(self.ui_manager.speed)
            for _ in range(steps):
                self.time_engine.update()
                
                # Update all cities (movement, state timers)
                # Note: NumpyEngine handles movement now, so we don't need city.update()
                # UNLESS city.update() does something else?
                # city.update() calls person.update(). NumpyEngine replaces this.
                # So we skip city.update().
                
                # Run simulation logic (infections + movement)
                self.simulation_engine.update(self.time_engine)
                
                # Update stats every 10 ticks (optimization)
                if self.time_engine.ticks % 10 == 0:
                    self.stats_manager.update(self.cities, self.time_engine.current_day + self.time_engine.hour/24)

    def render(self):
        # 1. Render World
        self.renderer.render()

        # Render minimap overlay
        self.minimap.render(self.screen, self.cities, self.camera)
        
        # 2. Render UI (Pygame Surface)
        self.ui_surface.fill((0, 0, 0, 0)) # Clear
        
        # Render UI overlay (Time)
        font = pygame.font.SysFont("Arial", 20)
        time_surf = font.render(self.time_engine.get_time_string(), True, (255, 255, 255))
        self.ui_surface.blit(time_surf, (10, 10))
        
        # 3. Composite UI onto Screen
        self.renderer.render_overlay(self.ui_surface)
        
        # 4. Draw Pygame GUI (Directly to screen)
        self.ui_manager.draw(self.screen)
        
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
