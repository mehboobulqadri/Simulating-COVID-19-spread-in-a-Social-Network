import pygame

class TextureManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TextureManager, cls).__new__(cls)
            cls._instance.textures = {}
            cls._instance._generate_textures()
        return cls._instance

    def _generate_textures(self):
        # Generate Person Texture (Soft Circle/Glow)
        self.textures['person_glow'] = self._create_glow_circle(10, (255, 255, 255))
        
        # Generate City Icon (Simple Building shape)
        self.textures['city_icon'] = self._create_city_icon(60, (150, 150, 200))
        
        # Generate Building Textures
        self.textures['building_residential'] = self._create_house_texture(40, (100, 200, 100))
        self.textures['building_workplace'] = self._create_office_texture(40, (100, 100, 200))
        self.textures['building_hospital'] = self._create_hospital_texture(60, (240, 240, 240))
        
        # Generate Ground Textures
        self.textures['ground_grass'] = self._create_noise_texture(100, 100, (30, 60, 30), (40, 70, 40))
        self.textures['ground_pavement'] = self._create_noise_texture(100, 100, (50, 50, 50), (60, 60, 60))

    def _create_house_texture(self, size, color):
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        # Roof
        pygame.draw.polygon(surf, (150, 50, 50), [(0, size//2), (size//2, 0), (size, size//2)])
        # Body
        pygame.draw.rect(surf, color, (5, size//2, size-10, size//2))
        # Door
        pygame.draw.rect(surf, (80, 40, 0), (size//2 - 5, size - 15, 10, 15))
        return surf

    def _create_office_texture(self, size, color):
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        # Body
        pygame.draw.rect(surf, color, (5, 5, size-10, size-5))
        # Windows grid
        win_color = (200, 220, 255)
        for y in range(15, size-10, 8):
            for x in range(10, size-10, 8):
                pygame.draw.rect(surf, win_color, (x, y, 4, 4))
        return surf

    def _create_hospital_texture(self, size, color):
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        # Main Body
        pygame.draw.rect(surf, color, (5, 10, size-10, size-10))
        # Roof accent
        pygame.draw.rect(surf, (200, 200, 200), (2, 5, size-4, 5))
        # Red Cross
        cross_color = (220, 0, 0)
        cx, cy = size//2, size//2 + 5
        w, h = size//3, size//8
        pygame.draw.rect(surf, cross_color, (cx - w//2, cy - h//2, w, h))
        pygame.draw.rect(surf, cross_color, (cx - h//2, cy - w//2, h, w))
        return surf

    def _create_noise_texture(self, w, h, c1, c2):
        surf = pygame.Surface((w, h))
        surf.fill(c1)
        import random
        for _ in range(100):
            x = random.randint(0, w-1)
            y = random.randint(0, h-1)
            pygame.draw.rect(surf, c2, (x, y, 2, 2))
        return surf

    def _create_glow_circle(self, radius, color):
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        # Core
        pygame.draw.circle(surf, color, (radius, radius), radius // 2)
        # Glow (fading out)
        for i in range(radius // 2, radius):
            alpha = int(255 * (1 - (i / radius)))
            pygame.draw.circle(surf, (*color, alpha), (radius, radius), i, 1)
        return surf

    def _create_city_icon(self, size, color):
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        # Main building
        pygame.draw.rect(surf, color, (size//4, size//2, size//2, size//2))
        # Tower
        pygame.draw.rect(surf, color, (size//3, size//4, size//3, size//4))
        # Windows
        win_color = (255, 255, 200)
        pygame.draw.rect(surf, win_color, (size//3 + 2, size//2 + 5, 5, 5))
        pygame.draw.rect(surf, win_color, (size//2 + 2, size//2 + 5, 5, 5))
        return surf

    def get_texture(self, name):
        return self.textures.get(name)
