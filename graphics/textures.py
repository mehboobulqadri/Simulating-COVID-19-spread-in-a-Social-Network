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
        
        # Generate District Texture (Semi-transparent block)
        # We'll handle district coloring dynamically, but maybe a pattern?

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
