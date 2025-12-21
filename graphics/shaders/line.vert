#version 330

in vec2 in_position;
in vec3 in_color;

uniform mat4 projection;
uniform mat4 view;

out vec3 v_color;

void main() {
    v_color = in_color;
    gl_Position = projection * view * vec4(in_position, 0.0, 1.0);
}
