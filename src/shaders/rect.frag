#version 330
in vec2 v_uv;
in vec2 v_local_pos;
out vec4 f_color;

uniform vec4 u_color;
uniform vec2 u_rect_size;
uniform float u_radius;

void main() {
    // If radius is 0, just draw the whole quad (optimization)
    if (u_radius <= 0.0) {
        f_color = u_color;
        return;
    }
    
    // Define the corner bounding boxes (rect size minus radius on both sides)
    vec2 half_size = u_rect_size * 0.5;
    vec2 box_size = u_rect_size - u_radius * 2.0;

    // P is the current pixel position relative to the center of the rectangle
    vec2 P = v_local_pos - half_size;

    // Q is the distance from the center of the rectangle to the edges
    // We use max(abs(P) - box_size * 0.5, 0.0) to find the distance
    // only outside the inner rounded box.
    vec2 Q = abs(P) - half_size + u_radius;

    // If Q.x < 0 or Q.y < 0, the pixel is in the central, non-rounded area.
    // If both are > 0, we are in a corner area.
    
    // Distance (d) from the pixel P to the rounded box's edge
    float d = length(max(Q, 0.0)) + min(max(Q.x, Q.y), 0.0);

    // If the distance (d) is greater than the radius, the pixel is outside the rounded shape.
    if (d > u_radius) {
        discard;
    }

    // Optional: Smooth blending for anti-aliasing (smooth step from radius to radius + 1)
    float alpha = 1.0 - smoothstep(u_radius, u_radius + 1.0, d);
    f_color = vec4(u_color.rgb, u_color.a * alpha);
    
    //f_color = u_color;
}