import pygame
import random

class Particle:
    def __init__(self, x, y, color, life):
        self.x = x
        self.y = y
        self.color = color
        self.life = life
        self.max_life = life
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(-1, 1)
        self.size = random.randint(2, 4)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size = max(0, self.size - 0.05)

    def is_dead(self):
        return self.life <= 0

class VisualEffects:
    def __init__(self):
        self.particles = []

    def add_infection_effect(self, x, y):
        # Spawn a burst of red particles
        for _ in range(5):
            self.particles.append(Particle(x, y, (255, 50, 50), random.randint(20, 40)))

    def update(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if not p.is_dead()]

    def render(self, screen, camera):
        for p in self.particles:
            px, py = camera.apply(p.x, p.y)
            # Fade out alpha
            alpha = int(255 * (p.life / p.max_life))
            surf = pygame.Surface((int(p.size)*2, int(p.size)*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p.color, alpha), (int(p.size), int(p.size)), int(p.size))
            screen.blit(surf, (px - int(p.size), py - int(p.size)))
