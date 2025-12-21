import moderngl
import numpy as np
import pygame
from entities.person import State
from entities.building import BuildingType

class GLRenderer:
    def __init__(self, screen, camera):
        self.screen = screen
        self.camera = camera
        self.width = camera.width
        self.height = camera.height
        
        # Detect existing context or create new
        try:
            self.ctx = moderngl.create_context()
            print(f"✓ OpenGL context created: {self.ctx.info['GL_RENDERER']}")
        except Exception as e:
            # Fallback if context creation fails (e.g. headless)
            print(f"Warning: Could not create ModernGL context: {e}")
            self.ctx = None
            return

        # Enable blending for transparency
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        # Create framebuffer for off-screen rendering
        self.fbo_texture = self.ctx.texture((self.width, self.height), 4)
        self.fbo = self.ctx.framebuffer(color_attachments=[self.fbo_texture])
        
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
        
        # Pre-allocate reusable instance buffer (avoid per-frame allocations)
        self.instance_buffer_2d = np.zeros((self.max_instances, 7), dtype=np.float32)
        
        # Pre-compute state color mapping (vectorized lookup table)
        self.state_colors = np.array([
            [0.4, 0.8, 1.0],  # 0: SUSCEPTIBLE
            [1.0, 1.0, 0.4],  # 1: EXPOSED
            [1.0, 0.2, 0.2],  # 2: INFECTIOUS
            [0.2, 0.8, 0.2],  # 3: RECOVERED
            [0.2, 0.2, 0.2],  # 4: DECEASED
            [0.8, 0.4, 1.0],  # 5: VACCINATED
        ], dtype=np.float32)
        
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
        self.simulation_engine = None
        
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
        
        # Line Rendering Setup (for roads/highways)
        self.line_prog = self.load_program('line')
        self.max_line_vertices = 20000
        self.line_vbo = self.ctx.buffer(reserve=self.max_line_vertices * 5 * 4)  # x, y, r, g, b per vertex
        self.line_vao = self.ctx.vertex_array(
            self.line_prog,
            [(self.line_vbo, '2f 3f', 'in_position', 'in_color')]
        )

    def load_program(self, name):
        with open(f'graphics/shaders/{name}.vert') as f:
            vert = f.read()
        with open(f'graphics/shaders/{name}.frag') as f:
            frag = f.read()
        return self.ctx.program(vertex_shader=vert, fragment_shader=frag)

    def set_world_data(self, cities):
        self.cities = cities
    
    def set_simulation_engine(self, engine):
        self.simulation_engine = engine
    
    def set_cities(self, cities):
        self.cities = cities
        
    def render_overlay(self, surface):
        """Render a pygame surface as an OpenGL overlay"""
        if not self.ctx: return
        
        # Create/Update texture from surface
        if self.ui_texture is None or self.ui_texture.size != surface.get_size():
            self.ui_texture = self.ctx.texture(surface.get_size(), 4)
        
        # Convert pygame surface to RGBA bytes
        # Pygame surfaces are top-left origin, OpenGL is bottom-left
        # We need to flip the data vertically
        data = pygame.image.tostring(surface, 'RGBA', True)  # True = flip vertically
        
        self.ui_texture.write(data)
        self.ui_texture.use(0)
        
        # Enable blending for UI transparency
        self.ctx.enable(moderngl.BLEND)
        self.ui_prog['ui_texture'].value = 0
        self.ui_vao.render(mode=moderngl.TRIANGLE_STRIP)

    def render(self, min_detail=False):
        if not self.ctx: return

        self.ctx.clear(0.1, 0.1, 0.12) # Dark background
        
        # Update Matrices
        proj = self.camera.get_projection_matrix()
        view = self.camera.get_view_matrix()
        
        self.prog['projection'].write(proj.tobytes())
        self.prog['view'].write(view.tobytes())
        
        # Render roads/highways first (underneath everything)
        if not min_detail:
            self._render_roads(proj, view)
        
        # Render trace path for selected person (on top of roads, under agents)
        if not min_detail and self.interaction:
            self._render_trace_path(proj, view)
        
        # Render using numpy arrays directly (GPU-optimized)
        if self.simulation_engine is not None:
            self._render_from_numpy(min_detail=min_detail)
        else:
            # Fallback to Python object iteration (slow)
            self._render_from_objects(min_detail=min_detail)
    
    def _render_roads(self, proj, view):
        """Render roads and highways as lines"""
        
        # 1. Render City Roads (Width 2.0)
        road_vertices = []
        road_color = [0.16, 0.16, 0.18]  # (40, 40, 45) / 255
        
        for city in self.cities:
            if hasattr(city, 'roads'):
                for road in city.roads:
                    road_vertices.extend([
                        road.start[0], road.start[1], *road_color,
                        road.end[0], road.end[1], *road_color
                    ])
                    
        if road_vertices:
            self._draw_lines(road_vertices, 2.0, proj, view)

        # 2. Render Highways (Width 5.0)
        highway_vertices = []
        highway_color = [0.47, 0.47, 0.27]  # (120, 120, 70) / 255
        
        for city in self.cities:
            if hasattr(city, 'highways'):
                for highway in city.highways:
                    highway_vertices.extend([
                        highway.start[0], highway.start[1], *highway_color,
                        highway.end[0], highway.end[1], *highway_color
                    ])

        if highway_vertices:
            self._draw_lines(highway_vertices, 5.0, proj, view)

    def _draw_lines(self, vertices, width, proj, view):
        vertex_count = len(vertices) // 5
        if vertex_count > self.max_line_vertices:
            vertex_count = self.max_line_vertices
            vertices = vertices[:vertex_count * 5]
        
        line_data = np.array(vertices, dtype='f4')
        self.line_vbo.write(line_data.tobytes())
        
        self.ctx.line_width = width
        self.line_prog['projection'].write(proj.tobytes())
        self.line_prog['view'].write(view.tobytes())
        self.line_vao.render(mode=moderngl.LINES, vertices=vertex_count)
    
    def _render_trace_path(self, proj, view):
        """Render the trace path for selected person"""
        if not self.interaction or not self.interaction.tracing_enabled:
            return
        
        trace_points = getattr(self.interaction, 'trace_points', [])
        if not trace_points or len(trace_points) < 2:
            return
        
        # Build line segments from trace points
        line_vertices = []
        trace_color = [0.0, 0.94, 1.0]  # Cyan (0, 240, 255) / 255
        
        for i in range(len(trace_points) - 1):
            p1 = trace_points[i]
            p2 = trace_points[i + 1]
            line_vertices.extend([
                p1[0], p1[1], *trace_color,
                p2[0], p2[1], *trace_color
            ])
        
        if line_vertices:
            vertex_count = len(line_vertices) // 5
            if vertex_count > self.max_line_vertices:
                vertex_count = self.max_line_vertices
                line_vertices = line_vertices[:vertex_count * 5]
            
            line_data = np.array(line_vertices, dtype='f4')
            self.line_vbo.write(line_data.tobytes())
            
            # Set line width and render
            self.ctx.line_width = 3.0
            self.line_prog['projection'].write(proj.tobytes())
            self.line_prog['view'].write(view.tobytes())
            self.line_vao.render(mode=moderngl.LINES, vertices=vertex_count)
    
    def _render_from_numpy(self, min_detail=False):
        """Fast rendering path using numpy arrays directly"""
        num_agents = self.simulation_engine.num_people
        
        # Reuse pre-allocated buffer (avoid per-frame allocations)
        instance_data = self.instance_buffer_2d
        idx = 0
        
        # Render all agents in one batch
        if idx + num_agents <= self.max_instances:
            instance_data[idx:idx+num_agents, 0:2] = self.simulation_engine.pos  # x, y
            instance_data[idx:idx+num_agents, 2] = 4.0  # size
            instance_data[idx:idx+num_agents, 3:6] = self.state_colors[self.simulation_engine.state]  # rgb
            instance_data[idx:idx+num_agents, 6] = 0.0  # type (circle)
            idx += num_agents
            
            # Add glows for infectious agents (skip in min_detail mode)
            if not min_detail:
                infectious_mask = self.simulation_engine.state == State.INFECTIOUS.value
                infectious_count = np.sum(infectious_mask)
                if infectious_count > 0 and idx + infectious_count <= self.max_instances:
                    infectious_pos = self.simulation_engine.pos[infectious_mask]
                    instance_data[idx:idx+infectious_count, 0:2] = infectious_pos
                    instance_data[idx:idx+infectious_count, 2] = 16.0  # glow size
                    instance_data[idx:idx+infectious_count, 3:6] = [1.0, 0.2, 0.2]  # red
                    instance_data[idx:idx+infectious_count, 6] = 3.0  # type (glow)
                    idx += infectious_count
        
        # Render buildings (batch process from cities)
        for city in self.cities:
            for district in city.districts:
                for b in district.buildings:
                    if idx >= self.max_instances:
                        break
                    c = b.color
                    instance_data[idx] = [
                        b.bounds.centerx, b.bounds.centery,
                        b.bounds.width,
                        c[0]/255.0, c[1]/255.0, c[2]/255.0,
                        1.0  # type (square)
                    ]
                    idx += 1
        
        # Particles (skip in min_detail mode)
        if not min_detail and self.visual_effects:
            for p in self.visual_effects.particles:
                if idx >= self.max_instances:
                    break
                c = p.color
                instance_data[idx] = [
                    p.x, p.y,
                    p.size * 3.0,
                    c[0]/255.0, c[1]/255.0, c[2]/255.0,
                    3.0  # type (glow)
                ]
                idx += 1
        
        # Upload to GPU and render
        if idx > 0:
            # Clamp to max instances
            if idx > self.max_instances:
                idx = self.max_instances
            self.instance_vbo.write(instance_data[:idx].tobytes())
            self.vao.render(mode=moderngl.TRIANGLE_STRIP, instances=idx)
    
    def _render_from_objects(self, min_detail=False):
        """Fallback slow rendering path using Python object iteration"""
        data_list = []
        
        for city in self.cities:
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
            self.vao.render(mode=moderngl.TRIANGLE_STRIP, instances=count)
