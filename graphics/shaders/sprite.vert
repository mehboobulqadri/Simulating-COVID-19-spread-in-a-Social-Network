#version 330

// Per-vertex inputs (The Quad)
in vec2 in_vert;

// Per-instance inputs
in vec2 in_pos;
in float in_size;
in vec3 in_color;
in float in_type;

uniform mat4 projection;
uniform mat4 view;

out vec2 v_uv;
out vec3 v_color;
out float v_type;

void main() {
    v_uv = in_vert + 0.5; // Map -0.5..0.5 to 0.0..1.0
    v_color = in_color;
    v_type = in_type;
    
    // Scale the quad
    vec2 scaled_pos = in_vert * in_size;
    
    // Translate to world position
    vec2 world_pos = scaled_pos + in_pos;
    
    gl_Position = projection * view * vec4(world_pos, 0.0, 1.0);
}
