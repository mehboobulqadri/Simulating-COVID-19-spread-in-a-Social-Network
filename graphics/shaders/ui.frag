#version 330
uniform sampler2D ui_texture;
in vec2 v_uv;
out vec4 f_color;
void main() {
    f_color = texture(ui_texture, v_uv);
}
