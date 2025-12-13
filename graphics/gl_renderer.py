import moderngl
import numpy as np
import pygame
from entities.person import State
from entities.building import BuildingType

class GLRenderer:
    def __init__(self, screen, camera):
        self.screen = screen
        self.camera = camera
        
        # Detect existing context or create new
        try:
            self.ctx = moderngl.create_context()
        except moderngl.Error:
            # Fallback if context creation fails (e.g. headless)
            print("Warning: Could not create ModernGL context.")
            self.ctx = None
            return

        # Enable blending for transparency
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        # Load Shaders
        self.prog = self.load_program('sprite')
        
        # Quad Geometry (VBO)
        # x, y (centered at 0,0)
        vertices = np.array([
            -0.5, -0.5,
             0.5, -0.5,
            -0.5,  0.5,
             0.5,  0.5,
        ], dtype='f4')
        
        self.vbo = self.ctx.buffer(vertices)
        
        # Instance Buffer (Dynamic)
        # Format: x, y, size, r, g, b, type
        # Max instances: 100,000
        self.max_instances = 100000
        self.instance_data = np.zeros(self.max_instances * 7, dtype='f4')
        self.instance_vbo = self.ctx.buffer(self.instance_data)
        
        # VAO
        # "2f" for vertices
        # "2f 1f 3f 1f /i" for instances (x,y, size, rgb, type)
        self.vao = self.ctx.vertex_array(
            self.prog,
            [
                (self.vbo, '2f', 'in_vert'),
                (self.instance_vbo, '2f 1f 3f 1f /i', 'in_pos', 'in_size', 'in_color', 'in_type'),
            ]
        )
        
        self.cities = []
        
        # Color Map
        self.colors = {
            State.SUSCEPTIBLE: (0.4, 0.8, 1.0),
            State.EXPOSED: (1.0, 1.0, 0.4),
            State.INFECTIOUS: (1.0, 0.2, 0.2),
            State.RECOVERED: (0.2, 0.8, 0.2),
            State.DECEASED: (0.2, 0.2, 0.2),
            State.VACCINATED: (0.8, 0.4, 1.0)
        }
        
        # Compatibility fields for main.py
        self.visual_effects = None
        self.interaction = None
        self.time_engine = None
        
        # UI Overlay Setup
        self.ui_prog = self.load_program('ui')
        self.quad_fs = self.ctx.buffer(np.array([
            -1.0, -1.0,
             1.0, -1.0,
            -1.0,  1.0,
             1.0,  1.0,
        ], dtype='f4'))
        self.ui_vao = self.ctx.vertex_array(self.ui_prog, [(self.quad_fs, '2f', 'in_vert')])
        self.ui_texture = None

    def load_program(self, name):
        with open(f'bio_spatial/graphics/shaders/{name}.vert') as f:
            vert = f.read()
        with open(f'bio_spatial/graphics/shaders/{name}.frag') as f:
            frag = f.read()
        return self.ctx.program(vertex_shader=vert, fragment_shader=frag)

    def set_world_data(self, cities):
        self.cities = cities
        
    def render_overlay(self, surface):
        if not self.ctx: return
        
        # Create/Update texture from surface
        if self.ui_texture is None or self.ui_texture.size != surface.get_size():
            self.ui_texture = self.ctx.texture(surface.get_size(), 4)
        
        # Pygame surfaces are top-left, OpenGL textures are bottom-left.
        # We flip vertically (True)
        data = pygame.image.tostring(surface, 'RGBA', False) 
        # Wait, if I use False (no flip), it might be upside down in UVs?
        # My shader maps -1..1 to 0..1.
        # Let's try False first.
        
        self.ui_texture.write(data)
        self.ui_texture.use(0)
        
        # Enable blending for UI
        self.ctx.enable(moderngl.BLEND)
        self.ui_vao.render(mode=moderngl.TRIANGLE_STRIP)

    def render(self):
        if not self.ctx: return

        self.ctx.clear(0.1, 0.1, 0.12) # Dark background
        
        # Update Matrices
        proj = self.camera.get_projection_matrix()
        view = self.camera.get_view_matrix()
        
        self.prog['projection'].write(proj.tobytes())
        self.prog['view'].write(view.tobytes())
        
        # Collect Instance Data
        data_list = []
        
        for city in self.cities:
            # Render City Center (Ring)
            cx, cy = city.location
            data_list.extend([cx, cy, 60.0, 0.6, 0.6, 0.6, 2.0])
            
            for district in city.districts:
                # Buildings
                for b in district.buildings:
                    c = b.color
                    data_list.extend([
                        b.bounds.centerx, b.bounds.centery, 
                        b.bounds.width, 
                        c[0]/255, c[1]/255, c[2]/255, 
                        1.0
                    ])
                
                # People
                for p in district.people:
                    c = self.colors.get(p.state, (1,1,1))
                    data_list.extend([
                        p.x, p.y, 
                        4.0, # Size
                        c[0], c[1], c[2], 
                        0.0 # Type 0 = Circle
                    ])
                    
                    # If infectious, add a glow instance
                    if p.state == State.INFECTIOUS:
                         data_list.extend([
                            p.x, p.y, 
                            16.0, # Larger glow
                            c[0], c[1], c[2], 
                            3.0 # Type 3 = Glow
                        ])

        # Particles
        if self.visual_effects:
            for p in self.visual_effects.particles:
                c = p.color
                data_list.extend([
                    p.x, p.y,
                    p.size * 3.0, # Make them visible
                    c[0]/255, c[1]/255, c[2]/255,
                    3.0 # Type 3 = Glow
                ])

        count = len(data_list) // 7
        if count > 0:
            # Update VBO
            if count > self.max_instances:
                count = self.max_instances
                data_list = data_list[:count*7]
                
            self.instance_vbo.write(np.array(data_list, dtype='f4').tobytes())
            self.vao.render(instances=count)
