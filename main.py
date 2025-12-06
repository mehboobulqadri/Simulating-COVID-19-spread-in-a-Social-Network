import pygame
import sys
from graphics.renderer import Renderer
from graphics.camera import Camera
from graphics.visual_effects import VisualEffects
from ui.interaction import Interaction
from ui.control_panel import ControlPanel
from ui.dashboard import Dashboard
from core.time_engine import TimeEngine
from core.simulation_engine import SimulationEngine
from core.statistics import StatisticsManager
from data.world_generator import WorldGenerator
from data.persistence import PersistenceManager
from data.export import DataExporter
from entities.person import State
import random

class BioSpatialApp:
    def __init__(self):
        pygame.init()
        self.width = 1280
        self.height = 720
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Bio-Spatial Epidemic Simulator")
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.camera = Camera(self.width, self.height)
        self.renderer = Renderer(self.screen, self.camera)
        
        # Initialize Core Systems
        self.time_engine = TimeEngine()
        self.cities = WorldGenerator.generate_world(num_cities=5)
        self.simulation_engine = SimulationEngine(self.cities)
        self.stats_manager = StatisticsManager()
        
        # Initialize Visuals & Interaction
        self.visual_effects = VisualEffects()
        self.interaction = Interaction(self.camera)
        self.control_panel = ControlPanel(self.width, self.height)
        self.dashboard = Dashboard(self.width, self.height)
        
        # Connect systems
        self.renderer.visual_effects = self.visual_effects
        self.renderer.interaction = self.interaction
        
        # Connect Control Panel Callbacks
        self.control_panel.on_save = self.save_simulation
        self.control_panel.on_load = self.load_simulation
        self.control_panel.on_export = self.export_data
        
        # Infect patient zero
        self._infect_patient_zero()
        
        # Pass data to renderer
        self.renderer.set_world_data(self.cities)

    def _infect_patient_zero(self):
        # Find a random person and infect them
        all_people = []
        for city in self.cities:
            for district in city.districts:
                all_people.extend(district.people)
        
        if all_people:
            patient_zero = random.choice(all_people)
            patient_zero.state = State.INFECTIOUS
            patient_zero.infection_timer = 1000
            self.visual_effects.add_infection_effect(patient_zero.x, patient_zero.y)
            print(f"Patient Zero infected in {patient_zero.district.name}")

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
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
            
            # Pass event to control panel first
            if self.control_panel.handle_event(event):
                continue
            
            # Pass event to camera
            self.camera.handle_event(event)
        
        # Handle continuous input (keys held down)
        self.camera.handle_input()
        
        # Handle Interaction (Hover)
        self.interaction.handle_input(self.cities)

    def update(self):
        self.camera.update()
        self.visual_effects.update()
        
        if not self.control_panel.paused:
            # Run multiple updates based on speed
            steps = int(self.control_panel.speed)
            for _ in range(steps):
                self.time_engine.update()
                
                # Update all cities (movement, state timers)
                for city in self.cities:
                    city.update(self.time_engine)
                    
                # Run simulation logic (infections)
                self.simulation_engine.update()
                
                # Update stats every 10 ticks (optimization)
                if self.time_engine.ticks % 10 == 0:
                    self.stats_manager.update(self.cities, self.time_engine.current_day + self.time_engine.hour/24)

    def render(self):
        self.screen.fill((30, 30, 30))  # Dark background
        self.renderer.render()
        
        # Render UI overlay (Time)
        font = pygame.font.SysFont("Arial", 20)
        time_surf = font.render(self.time_engine.get_time_string(), True, (255, 255, 255))
        self.screen.blit(time_surf, (10, 10))
        
        # Render Control Panel
        self.control_panel.render(self.screen)
        
        # Render Dashboard
        self.dashboard.render(self.screen, self.stats_manager)
        
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
