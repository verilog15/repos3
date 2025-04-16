/* 
 *  This file is part of Permafrost Engine. 
 *  Copyright (C) 2019-2023 Eduard Permyakov 
 *
 *  Permafrost Engine is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  Permafrost Engine is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 * 
 *  Linking this software statically or dynamically with other modules is making 
 *  a combined work based on this software. Thus, the terms and conditions of 
 *  the GNU General Public License cover the whole combination. 
 *  
 *  As a special exception, the copyright holders of Permafrost Engine give 
 *  you permission to link Permafrost Engine with independent modules to produce 
 *  an executable, regardless of the license terms of these independent 
 *  modules, and to copy and distribute the resulting executable under 
 *  terms of your choice, provided that you also meet, for each linked 
 *  independent module, the terms and conditions of the license of that 
 *  module. An independent module is a module which is not derived from 
 *  or based on Permafrost Engine. If you modify Permafrost Engine, you may 
 *  extend this exception to your version of Permafrost Engine, but you are not 
 *  obliged to do so. If you do not wish to do so, delete this exception 
 *  statement from your version.
 *
 */

#version 330 core

#define WAVE_STRENGTH   (0.005)
#define WATER_TINT_CLR  vec4(0.0, 0.3, 0.5, 0.1)

#define SPECULAR_STRENGTH  0.15
#define SPECULAR_SHININESS 0.8

#define BOUNDARY_THRESH 0.00025

#define X_COORDS_PER_TILE  8 
#define Z_COORDS_PER_TILE  8 

#define STATE_UNEXPLORED 0
#define STATE_IN_FOG     1
#define STATE_VISIBLE    2

/*****************************************************************************/
/* INPUTS                                                                    */
/*****************************************************************************/

in VertexToFrag {
    vec4 clip_space_pos;
    vec3 world_pos;
    vec2 uv;
    vec3 view_dir;
    vec3 light_dir;
}from_vertex;

/*****************************************************************************/
/* OUTPUTS                                                                   */
/*****************************************************************************/

out vec4 o_frag_color;

/*****************************************************************************/
/* UNIFORMS                                                                  */
/*****************************************************************************/

uniform sampler2D water_dudv_map;
uniform sampler2D water_normal_map;
uniform sampler2D refraction_tex;
uniform sampler2D reflection_tex;
uniform sampler2D refraction_depth;

uniform float water_move_factor;
uniform float cam_near;
uniform float cam_far;

uniform vec3 light_color;

uniform vec2 water_tiling;

uniform usamplerBuffer visbuff;
uniform int visbuff_offset;

uniform ivec4 map_resolution;
uniform vec2 map_pos;

/*****************************************************************************/
/* PROGRAM                                                                   */
/*****************************************************************************/

/*
 * x = chunk_r
 * y = chunk_c
 * z = tile_r
 * a = tile_c
 */
ivec4 tile_desc_at(vec3 ws_pos)
{
    int chunk_w = map_resolution[0];
    int chunk_h = map_resolution[1];
    int tile_w = map_resolution[2];
    int tile_h = map_resolution[3];
    int tiles_per_chunk = tile_w * tile_h;

    int chunk_x_dist = tile_w * X_COORDS_PER_TILE;
    int chunk_z_dist = tile_h * Z_COORDS_PER_TILE;

    int chunk_r = int(abs(map_pos.y - ws_pos.z) / chunk_z_dist);
    int chunk_c = int(abs(map_pos.x - ws_pos.x) / chunk_x_dist);

    int chunk_base_x = int(map_pos.x - (chunk_c * chunk_x_dist));
    int chunk_base_z = int(map_pos.y + (chunk_r * chunk_z_dist));

    int tile_c = int(abs(chunk_base_x - ws_pos.x) / X_COORDS_PER_TILE);
    int tile_r = int(abs(chunk_base_z - ws_pos.z) / Z_COORDS_PER_TILE);

    return ivec4(chunk_r, chunk_c, tile_r, tile_c);
}

ivec4 tile_relative_desc(ivec4 desc, int dr, int dc)
{
    ivec4 ret = desc;

    if(desc.z + dr >= map_resolution.z)
        ret.x += 1;
    else if(desc.z + dr < 0)
        ret.x += -1;

    if(desc.a + dc >= map_resolution.a)
        ret.y += 1;
    else if(desc.a + dc < 0)
        ret.y += -1;

    ret.x = clamp(ret.x, 0, map_resolution.x-1);
    ret.y = clamp(ret.y, 0, map_resolution.y-1);

    ret.z = int(mod(ret.z + dr, map_resolution.z));
    ret.a = int(mod(ret.a + dc, map_resolution.a));

    return ret;
}

int visbuff_idx(ivec4 td)
{
    int chunk_w = map_resolution[0];
    int tile_w = map_resolution[2];
    int tile_h = map_resolution[3];
    int tiles_per_chunk = tile_w * tile_h;

    return visbuff_offset + (td.x * tiles_per_chunk * chunk_w) 
                          + (td.y * tiles_per_chunk) 
                          + (td.z * tile_w) 
                          + td.a;
}

float tf_for_state(uint state)
{
    if(state == uint(STATE_UNEXPLORED))
        return 0.0;
    else if(state == uint(STATE_IN_FOG))
        return 0.5;
    return 1.0;
}

/* (0,0) is in the bottom-left corner, and (1,1) is in the top right corner */
float bilinear_interp_unit_square(float tl, float tr, float bl, float br, vec2 coord)
{
    return bl * (1.0 - coord.x) * (1.0 - coord.y) 
         + br * (coord.x) * (1.0 - coord.y)
         + tl * (1.0 - coord.x) * (coord.y)
         + tr * (coord.x) * (coord.y);
}

vec2 local_uv(vec2 global_uv)
{
    float x_per_chunk = 1.0 / map_resolution.x;
    float z_per_chunk = 1.0 / map_resolution.y;
    float x_per_tile = x_per_chunk / map_resolution.z;
    float z_per_tile = z_per_chunk / map_resolution.a;

    /* convert to range [0, 1] for the entire map */
    global_uv /= -water_tiling;

    /* Convert to tile-local, in range: [0, *_per_tile]  */
    global_uv.x = mod(global_uv.x, x_per_tile);
    global_uv.y = mod(global_uv.y, z_per_tile);

    /* Normalize */
    global_uv.x /= x_per_tile;
    global_uv.y /= z_per_tile;

    return global_uv;
}

/* The tint factor is in the range of [0,1]. It is a color multiplier based on 
 * the fog-of-war state of the current and adjacent tiles. */
float tint_factor(ivec4 td, vec2 uv)
{
    float c  = tf_for_state(texelFetch(visbuff, visbuff_idx(td)).r);
    float tl = tf_for_state(texelFetch(visbuff, visbuff_idx(tile_relative_desc(td, -1, -1))).r);
    float tr = tf_for_state(texelFetch(visbuff, visbuff_idx(tile_relative_desc(td, -1, +1))).r);
    float l  = tf_for_state(texelFetch(visbuff, visbuff_idx(tile_relative_desc(td,  0, -1))).r);
    float r  = tf_for_state(texelFetch(visbuff, visbuff_idx(tile_relative_desc(td,  0, +1))).r);
    float bl = tf_for_state(texelFetch(visbuff, visbuff_idx(tile_relative_desc(td, +1, -1))).r);
    float br = tf_for_state(texelFetch(visbuff, visbuff_idx(tile_relative_desc(td, +1, +1))).r);
    float t  = tf_for_state(texelFetch(visbuff, visbuff_idx(tile_relative_desc(td, -1,  0))).r);
    float b  = tf_for_state(texelFetch(visbuff, visbuff_idx(tile_relative_desc(td, +1,  0))).r);

    float tl_corner = (c + t + l + tl) / 4.0;
    float tr_corner = (c + t + r + tr) / 4.0;
    float bl_corner = (c + l + b + bl) / 4.0;
    float br_corner = (c + r + b + br) / 4.0;

    return bilinear_interp_unit_square(tl_corner, tr_corner, bl_corner, br_corner, local_uv(uv));
}

float linearize_depth(float z)
{
    return 2.0 * cam_near * cam_far / (cam_far + cam_near - (2.0 * z - 1.0) * (cam_far - cam_near));
}

/* The refraction texture is rendered at a lower resoulution than the scene in which the 
 * water quad is rendered and textured. Thus, when we use projective texturing to texture 
 * the water quad with the refraction texture, there may be some aliasing aftifacts at 
 * the very edges of the water. There will sometimes be a single pixel-wide line where the 
 * water plane meets the ground that isn't properly textured. We use the depth buffer to 
 * discard these disconinuous pixels at the edges. 
 */
bool should_discard(vec2 ndc_pos)
{
    float depth = linearize_depth(texture(refraction_depth, ndc_pos).r);
    float top = linearize_depth(texture(refraction_depth, vec2(ndc_pos.x, ndc_pos.y + BOUNDARY_THRESH)).r);
    float bot = linearize_depth(texture(refraction_depth, vec2(ndc_pos.x, ndc_pos.y - BOUNDARY_THRESH)).r);
    float left = linearize_depth(texture(refraction_depth, vec2(ndc_pos.x - BOUNDARY_THRESH, ndc_pos.y)).r);
    float right = linearize_depth(texture(refraction_depth, vec2(ndc_pos.x + BOUNDARY_THRESH, ndc_pos.y - BOUNDARY_THRESH)).r);
    if(abs(depth - top) > 5.0)
        return true;
    if(abs(depth - bot) > 5.0)
        return true;
    if(abs(depth - left) > 5.0)
        return true;
    if(abs(depth - right) > 5.0)
        return true;
    return false;
}

void main()
{
    ivec4 td = tile_desc_at(from_vertex.world_pos);
    float tf = tint_factor(td, from_vertex.uv);

    if(tf == 0.0) {
        o_frag_color = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }

    vec2 ndc_pos = (from_vertex.clip_space_pos.xy / from_vertex.clip_space_pos.w)/2.0 + 0.5;

    if(should_discard(ndc_pos))
        discard;

    float ground_dist = linearize_depth(texture(refraction_depth, ndc_pos).r);
    float water_dist = linearize_depth(gl_FragCoord.z);
    float water_depth = ground_dist - water_dist;
    float depth_damping_factor = clamp(water_depth/2.5, 0.0, 1.0);

    vec2 distorted_uv = vec2(from_vertex.uv.x + water_move_factor, from_vertex.uv.y);
    distorted_uv = texture(water_dudv_map, distorted_uv).rg * 0.1;
    distorted_uv = from_vertex.uv + vec2(distorted_uv.x, distorted_uv.y + water_move_factor);
    vec2 tot_dist = (texture(water_dudv_map, distorted_uv).rg * 2.0 - 1.0) * WAVE_STRENGTH;

    vec2 refract_uv = clamp(ndc_pos + tot_dist, 0.001, 0.999);
    vec4 refract_clr = texture(refraction_tex, refract_uv);

    vec2 reflect_uv = vec2(ndc_pos.x, -ndc_pos.y) + tot_dist;
    reflect_uv.x = clamp(reflect_uv.x, 0.001, 0.999);
    reflect_uv.y = clamp(reflect_uv.y, -0.999, -0.001);
    vec4 reflect_clr = texture(reflection_tex, reflect_uv);

    vec4 norm_map_clr = texture(water_normal_map, distorted_uv);
    vec3 normal = vec3(norm_map_clr.r * 2.0 - 1.0, norm_map_clr.b, norm_map_clr.g * 2.0 - 1.0);

    vec3 reflect_dir = reflect(-from_vertex.light_dir, normal);
    float spec = pow(max(dot(from_vertex.view_dir, reflect_dir), 0.0), SPECULAR_SHININESS);
    vec3 specular = SPECULAR_STRENGTH * spec * light_color;

    o_frag_color = mix(refract_clr, reflect_clr, 0.5);
    o_frag_color = mix(o_frag_color, WATER_TINT_CLR, 0.1) + vec4(specular, 0.0);
    o_frag_color.a = depth_damping_factor;

    o_frag_color *= tf;
}

