#version 330

in vec2 v_uv;
in vec3 v_color;
in float v_type;

out vec4 f_color;

void main() {
    vec2 center = vec2(0.5, 0.5);
    float dist = distance(v_uv, center);
    float alpha = 1.0;
    
    // Type 0: Circle (Person)
    if (v_type < 0.5) {
        // Soft edge anti-aliasing
        float delta = 0.02; // Fixed softness for now
        alpha = 1.0 - smoothstep(0.5 - delta, 0.5, dist);
    }
    // Type 1: Square (Building)
    else if (v_type < 1.5) {
        // Square with border logic could go here
        // For now, just solid square
        if (v_uv.x < 0.05 || v_uv.x > 0.95 || v_uv.y < 0.05 || v_uv.y > 0.95) {
             // Border
        }
    }
    // Type 2: Ring (City/District)
    else if (v_type < 2.5) {
        float delta = 0.01;
        float outer = 1.0 - smoothstep(0.5 - delta, 0.5, dist);
        float inner = 1.0 - smoothstep(0.4 - delta, 0.4, dist);
        alpha = outer - inner;
    }
    // Type 3: Glow (Soft Light)
    else {
        alpha = 1.0 - smoothstep(0.0, 0.5, dist);
        alpha = pow(alpha, 3.0); // Stronger falloff
    }
    
    if (alpha <= 0.0) discard;
    
    f_color = vec4(v_color, alpha);
}
