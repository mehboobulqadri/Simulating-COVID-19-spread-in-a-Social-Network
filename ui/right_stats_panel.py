import pygame
from entities.person import State
from ui.theme import UITheme

class RightStatsPanel:
    def __init__(self, screen_width, screen_height):
        self.width = 320
        self.height = screen_height
        # Animation states - start hidden off-screen
        self.offset_x = screen_width
        self.target_x = screen_width
        self.speed_anim = 0.45  # Softer easing for smoother slide
        self.velocity = 0.0     # For damped spring motion
        
        self.screen_width = screen_width
        self.x = self.offset_x
        self.y = 0
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        
        # Hover detection zone (thin strip on right edge)
        self.hover_zone_width = 18
        self.pinned = False
        # Place pin away from top-right to avoid overlap with God Mode button
        self.pin_rect = pygame.Rect(self.offset_x + 12, 20, 16, 16)
        
        # Dashboard colors
        self.colors = {
            State.SUSCEPTIBLE: (100, 200, 255),
            State.EXPOSED: (255, 255, 100),
            State.INFECTIOUS: (255, 50, 50),
            State.RECOVERED: (50, 200, 50),
            State.DECEASED: (150, 150, 150),
            State.VACCINATED: (200, 100, 255)
        }
        
    def set_world_bounds(self, min_x, min_y, max_x, max_y):
        pass

    def update(self, mouse_pos):
        # Hover detection - show panel when mouse near right edge OR over the panel
        distance_from_right = self.screen_width - mouse_pos[0]
        panel_left = self.offset_x - self.width
        
        # If mouse is near right edge OR over the panel (when it's visible)
        # We want target_x to be screen_width (hidden) or screen_width - width (visible)?
        # Wait, let's check the logic.
        # offset_x starts at screen_width (hidden).
        # x = offset_x - width.
        # So if offset_x = screen_width, x = screen_width - width? No.
        # Let's look at init:
        # self.offset_x = screen_width
        # self.x = self.offset_x - self.width
        # So initially x = 0? No, screen_width - 320. That means it's visible by default?
        # Ah, let's check render.
        # rect = (x, y, width, height).
        
        # If offset_x is screen_width, then x is screen_width - 320. That is ON SCREEN.
        # If we want it hidden, x should be screen_width.
        # So offset_x should be screen_width + width?
        
        # Let's re-read the original code carefully.
        # self.offset_x = screen_width
        # self.x = self.offset_x - self.width
        # If screen_width=1280, width=320. offset_x=1280. x=960. Visible.
        
        # The user says "hovers to the right instead of disappearing to the right".
        # This implies it is visible by default, and when hovered it moves right?
        
        # Let's look at update logic:
        # if distance_from_right < self.hover_zone_width or ... :
        #    self.target_x = self.width  <-- This sets target_x to 320.
        #    If offset_x becomes 320, then x = 320 - 320 = 0. That's the LEFT side of the screen!
        # else:
        #    self.target_x = self.screen_width <-- Sets target_x to 1280.
        #    x = 1280 - 320 = 960. Visible on right.
        
        # So the logic was completely inverted/broken for a right panel.
        # It was treating offset_x as something else.
        
        # Let's fix it.
        # We want:
        # Hidden state: x = screen_width (just off screen).
        # Visible state: x = screen_width - width.
        
        # Let's use 'x' directly as the state variable to be simpler, or stick to offset logic but fix it.
        # Let's stick to 'offset_x' representing the LEFT edge of the panel.
        
        # Init:
        # self.offset_x = screen_width (Hidden)
        
        # Update:
        # if hover:
        #   target_x = screen_width - self.width (Visible)
        # else:
        #   target_x = screen_width (Hidden)
        
        if self.pinned:
            self.target_x = self.screen_width - self.width
        elif distance_from_right < self.hover_zone_width or (mouse_pos[0] > self.offset_x):
            self.target_x = self.screen_width - self.width
        else:
            self.target_x = self.screen_width
        
        # Damped spring animation for a softer overshoot
        delta = self.target_x - self.offset_x
        self.velocity = self.velocity * 0.7 + delta * self.speed_anim
        self.offset_x += self.velocity
        if abs(delta) < 0.5 and abs(self.velocity) < 0.4:
            self.offset_x = self.target_x
            self.velocity = 0.0
        
        # Clamp offset_x
        if self.offset_x < self.screen_width - self.width:
            self.offset_x = self.screen_width - self.width
        if self.offset_x > self.screen_width:
            self.offset_x = self.screen_width
            
        self.x = self.offset_x
        self.rect.x = self.x
        self.pin_rect.x = self.offset_x + 12

    def handle_event(self, event, camera):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.pin_rect.collidepoint(event.pos):
                self.pinned = not self.pinned
                return True
        return False

    def render(self, screen, stats_manager, cities, camera, trace_points=None):
        # Panel background
        UITheme.draw_panel_bg(screen, self.rect)
        
        # Header
        header_font = UITheme.get_font(24, bold=True)
        header = header_font.render("STATISTICS", True, UITheme.ACCENT_COLOR)
        screen.blit(header, (self.x + 20, 25))
        
        # Render dashboard (graph)
        self._render_dashboard(screen, stats_manager, cities)
        
        # Edge indicator (shows when panel is hidden)
        if self.offset_x > self.screen_width - 5:
            indicator_rect = pygame.Rect(self.screen_width - 3, self.height // 2 - 30, 3, 60)
            pygame.draw.rect(screen, UITheme.ACCENT_COLOR, indicator_rect, border_radius=2)

        # Pin toggle
        pin_hover = self.pin_rect.collidepoint(pygame.mouse.get_pos())
        pin_bg = pygame.Color(40, 40, 50, 220)
        pygame.draw.rect(screen, pin_bg, self.pin_rect, border_radius=4)
        pygame.draw.rect(screen, UITheme.ACCENT_COLOR if (self.pinned or pin_hover) else (120, 120, 130), self.pin_rect, 2, border_radius=4)
        cx = self.pin_rect.centerx
        cy = self.pin_rect.centery
        pygame.draw.line(screen, (220, 220, 230), (cx, cy - 4), (cx, cy + 4), 2)
        pygame.draw.line(screen, (220, 220, 230), (cx - 4, cy), (cx + 4, cy), 2)
        if self.pinned:
            pygame.draw.circle(screen, UITheme.ACCENT_COLOR, (cx, cy), 3)

    def _render_dashboard(self, screen, stats_manager, cities):
        graph_y = 70
        graph_h = 220
        graph_w = self.width - 40
        graph_x = self.x + 20
        
        # Background for graph
        graph_rect = pygame.Rect(graph_x, graph_y, graph_w, graph_h)
        s = pygame.Surface((graph_w, graph_h), pygame.SRCALPHA)
        s.fill((20, 20, 30, 200))
        screen.blit(s, (graph_x, graph_y))
        pygame.draw.rect(screen, (80, 80, 100), graph_rect, 1, border_radius=5)
        
        if not stats_manager.time_points or len(stats_manager.time_points) < 2:
            no_data_font = UITheme.get_font(14)
            no_data = no_data_font.render("Collecting data...", True, (150, 150, 150))
            screen.blit(no_data, (graph_x + graph_w // 2 - 60, graph_y + graph_h // 2))
            return
        
        # Normalize values
        max_val = 0
        for s in State:
            if stats_manager.history[s]:
                max_val = max(max_val, max(stats_manager.history[s]))
        
        if max_val == 0:
            max_val = 1
        
        points_count = len(stats_manager.time_points)
        x_step = graph_w / max(1, stats_manager.max_history - 1)
        y_bottom = graph_y + graph_h - 5
        
        # Draw lines
        for state in State:
            points = []
            history = stats_manager.history[state]
            for i, val in enumerate(history):
                px = graph_x + i * x_step
                py = y_bottom - ((val / max_val) * (graph_h - 10))
                points.append((px, py))
            
            if len(points) > 1:
                pygame.draw.lines(screen, self.colors[state], False, points, 2)
        
        # Current stats below graph
        latest = stats_manager.get_latest_counts()
        stats_y = graph_y + graph_h + 15
        
        # Section label
        label_font = UITheme.get_font(12, bold=True)
        label = label_font.render("CURRENT STATUS", True, (150, 150, 160))
        screen.blit(label, (self.x + 20, stats_y))
        stats_y += 25
        
        stat_font = UITheme.get_font(14, bold=True)
        
        # Display key stats
        key_stats = [
            (State.INFECTIOUS, "Infectious"),
            (State.RECOVERED, "Recovered"),
            (State.DECEASED, "Deceased"),
            (State.VACCINATED, "Vaccinated"),
            (State.SUSCEPTIBLE, "Healthy"),
            (State.EXPOSED, "Exposed")
        ]
        
        for state, name in key_stats:
            count = latest.get(state, 0)
            color = self.colors[state]
            
            # Stat box
            stat_rect = pygame.Rect(self.x + 20, stats_y, self.width - 40, 30)
            stat_surf = pygame.Surface((stat_rect.width, stat_rect.height), pygame.SRCALPHA)
            stat_surf.fill((40, 40, 50, 180))
            screen.blit(stat_surf, (stat_rect.x, stat_rect.y))
            pygame.draw.rect(screen, color, stat_rect, 1, border_radius=3)
            
            # Label and value
            text = f"{name}: {count}"
            text_surf = stat_font.render(text, True, color)
            screen.blit(text_surf, (stat_rect.x + 10, stat_rect.y + 7))
            
            stats_y += 35
            
        # Additional Stats (Commuters, Total Agents)
        stats_y += 10
        
        # Calculate total agents and commuters
        total_agents = 0
        total_commuters = 0
        for city in cities:
            for district in city.districts:
                for p in district.people:
                    total_agents += 1
                    home_id = getattr(p, 'home_city_id', None)
                    work_id = getattr(p, 'work_city_id', None)
                    if home_id is not None and work_id is not None and work_id != home_id:
                        total_commuters += 1
        
        # Render Additional Stats
        info_font = UITheme.get_font(14)
        
        # Total Agents
        agents_txt = f"Total Agents: {total_agents}"
        agents_surf = info_font.render(agents_txt, True, (200, 200, 200))
        screen.blit(agents_surf, (self.x + 20, stats_y))
        stats_y += 25
        
        # Commuters
        commuters_txt = f"Commuters: {total_commuters}"
        commuters_surf = info_font.render(commuters_txt, True, (180, 200, 255))
        screen.blit(commuters_surf, (self.x + 20, stats_y))
        stats_y += 25