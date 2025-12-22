#version 330
in vec2 in_vert;
out vec2 v_uv;
void main() {
    v_uv = (in_vert + 1.0) / 2.0;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
