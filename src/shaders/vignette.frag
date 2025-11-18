#version 330
in vec2 v_uv;
out vec4 f_color;
uniform float intensity;

void main() {
    // center UV 0.5,0.5
    float d = distance(v_uv, vec2(0.5, 0.5));

    // smooth falloff
    float vig = smoothstep(0.4, 0.85, d);

    float dark = vig * intensity;
    f_color = vec4(0.0, 0.0, 0.0, dark);
}