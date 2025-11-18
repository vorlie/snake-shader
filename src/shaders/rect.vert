#version 330
in vec2 in_pos;
in vec2 in_uv;

out vec2 v_uv; // Normalized UV (0..1)
out vec2 v_local_pos; // Local pixel position (0..size)

uniform vec2 u_screen;
uniform vec2 u_rect_pos; // Pixel coordinates of the top-left corner
uniform vec2 u_rect_size; // Pixel size of the rectangle

void main() {
    v_uv = in_uv;
    
    // Calculate local pixel position: (in_pos - u_rect_pos)
    // Note: in_pos is already derived from the quad array (x, y, x+w, y+h)
    v_local_pos = vec2(in_pos.x - u_rect_pos.x, u_rect_pos.y + u_rect_size.y - in_pos.y);
    
    // Convert from pixel coords to clip space
    vec2 p = (in_pos / u_screen) * 2.0 - 1.0;
    gl_Position = vec4(p.x, -p.y, 0.0, 1.0); // flip Y
}