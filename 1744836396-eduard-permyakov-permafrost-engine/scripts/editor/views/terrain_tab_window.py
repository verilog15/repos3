#
#  This file is part of Permafrost Engine. 
#  Copyright (C) 2018-2023 Eduard Permyakov 
#
#  Permafrost Engine is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Permafrost Engine is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
#  Linking this software statically or dynamically with other modules is making 
#  a combined work based on this software. Thus, the terms and conditions of 
#  the GNU General Public License cover the whole combination. 
#  
#  As a special exception, the copyright holders of Permafrost Engine give 
#  you permission to link Permafrost Engine with independent modules to produce 
#  an executable, regardless of the license terms of these independent 
#  modules, and to copy and distribute the resulting executable under 
#  terms of your choice, provided that you also meet, for each linked 
#  independent module, the terms and conditions of the license of that 
#  module. An independent module is a module which is not derived from 
#  or based on Permafrost Engine. If you modify Permafrost Engine, you may 
#  extend this exception to your version of Permafrost Engine, but you are not 
#  obliged to do so. If you do not wish to do so, delete this exception 
#  statement from your version.
#

import pf
from constants import *
import globals

class Brush(object):
    TEXTURE = 0
    ELEVATION = 1
    SHALLOW_WAT = 2
    DEEP_WAT = 3

class TerrainTabWindow(pf.Window):

    def __init__(self):
        vresx, vresy = (1920, 1080)
        super(TerrainTabWindow, self).__init__("TerrainTab", 
            (0, UI_TAB_BAR_HEIGHT + 1, UI_LEFT_PANE_WIDTH, vresy - UI_TAB_BAR_HEIGHT - 1), pf.NK_WINDOW_BORDER, (vresx, vresy),
            resize_mask = pf.ANCHOR_X_LEFT | pf.ANCHOR_Y_TOP | pf.ANCHOR_Y_BOT)

        self.selected_mat_idx = 0
        self.brush_size_idx = 0
        self.brush_type_idx = 0
        self.edges_type_idx = 0
        self.selected_tile = None
        self.heights = [h for h in range(0, 10)]
        self.selected_height_idx = 0
        self.blend_textures = True
        self.blend_normals = True
        self.selected_side_mat_idx = 1

    def update(self):

        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Selected Tile:", (255, 255, 255))

        self.layout_row_dynamic(30, 1)
        label = str(self.selected_tile) if self.selected_tile is None \
            else "Chunk: {0} Tile: {1}".format(self.selected_tile[0], self.selected_tile[1])
        self.label_colored_wrap(label, (200, 200, 0))

        # Blend options
        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Blending Options:", (255, 255, 255))

        old_blend_textures = self.blend_textures
        self.layout_row_dynamic(20, 1)
        self.blend_textures = self.checkbox("Blend Textures", self.blend_textures)
        if old_blend_textures != self.blend_textures:
            pf.global_event(EVENT_TERRAIN_TEX_BLEND_CHANGED, self.blend_textures)

        old_blend_normals = self.blend_normals
        self.layout_row_dynamic(20, 1)
        self.blend_normals = self.checkbox("Blend Normals", self.blend_normals)
        if old_blend_normals != self.blend_normals:
            pf.global_event(EVENT_TERRAIN_NORMAL_BLEND_CHANGED, self.blend_normals)
        self.layout_row_dynamic(10, 1)

        # Brush size
        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Brush Size:", (255, 255, 255))

        old_brush_size_idx = self.brush_size_idx
        self.layout_row_dynamic(20, 2)
        if self.option_label("Small", self.brush_size_idx == 0):
            self.brush_size_idx = 0
        if self.option_label("Large", self.brush_size_idx == 1):
            self.brush_size_idx = 1
        self.layout_row_dynamic(10, 1)

        if self.brush_size_idx != old_brush_size_idx:
            pf.global_event(EVENT_TERRAIN_BRUSH_SIZE_CHANGED, self.brush_size_idx)

        # Brush type
        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Brush Type:", (255, 255, 255))

        old_brush_type_idx = self.brush_type_idx
        self.layout_row_dynamic(20, 1)
        if self.option_label("Texture", self.brush_type_idx == Brush.TEXTURE):
            self.brush_type_idx = Brush.TEXTURE
        self.layout_row_dynamic(20, 1)
        if self.option_label("Elevation", self.brush_type_idx == Brush.ELEVATION):
            self.brush_type_idx = Brush.ELEVATION
        self.layout_row_dynamic(20, 1)
        if self.option_label("Shallow Water", self.brush_type_idx == Brush.SHALLOW_WAT):
            self.brush_type_idx = Brush.SHALLOW_WAT
        self.layout_row_dynamic(20, 1)
        if self.option_label("Deep Water", self.brush_type_idx == Brush.DEEP_WAT):
            self.brush_type_idx = Brush.DEEP_WAT
        self.layout_row_dynamic(10, 1)

        if self.brush_type_idx != old_brush_type_idx:
            pf.global_event(EVENT_TERRAIN_BRUSH_TYPE_CHANGED, self.brush_type_idx)

        if self.brush_type_idx == Brush.TEXTURE:
            # Texture
            self.layout_row_dynamic(20, 1)
            self.label_colored_wrap("Texture:", (255, 255, 255))

            def textures_group():
                self.layout_row_static(25, UI_LEFT_PANE_WIDTH-60, 1)
                for i in range(0, len(globals.active_map.materials)):
                    old = self.selected_mat_idx
                    on = self.selectable_label(globals.active_map.materials[i].name, 
                        pf.NK_TEXT_ALIGN_LEFT, i == self.selected_mat_idx)
                    if on: 
                        self.selected_mat_idx = i
                    if self.selected_mat_idx != old:
                        pf.global_event(EVENT_TEXTURE_SELECTION_CHANGED, i)

            self.layout_row_static(400, UI_LEFT_PANE_WIDTH-30, 1)
            self.group("Texture:", pf.NK_WINDOW_BORDER, textures_group)
        else:
            # Elevation
            self.layout_row_dynamic(20, 1)
            self.label_colored_wrap("Edges:", (255, 255, 255))

            old_edges_type_idx = self.edges_type_idx
            self.layout_row_dynamic(20, 2)
            if self.option_label("Smooth", self.edges_type_idx == 0):
                self.edges_type_idx = 0
            if self.option_label("Hard", self.edges_type_idx == 1):
                self.edges_type_idx = 1
            self.layout_row_dynamic(10, 1)

            if old_edges_type_idx != self.edges_type_idx:
                pf.global_event(EVENT_TERRAIN_EDGE_TYPE_CHANGED, self.edges_type_idx)

            if self.brush_type_idx == Brush.ELEVATION:            

                self.layout_row_dynamic(20, 1)
                self.label_colored_wrap("Height:", (255, 255, 255))

                self.layout_row_static(25, UI_LEFT_PANE_WIDTH - 30, 1)
                old_height_idx = self.selected_height_idx
                self.selected_height_idx = self.combo_box([str(h) for h in self.heights], self.selected_height_idx, 25, (UI_LEFT_PANE_WIDTH - 30, 200))
                if old_height_idx != self.selected_height_idx:
                    pf.global_event(EVENT_HEIGHT_SELECTION_CHANGED, self.heights[self.selected_height_idx])
                self.layout_row_dynamic(10, 1)

            self.layout_row_dynamic(20, 1)
            self.label_colored_wrap("Side Texture:", (255, 255, 255))

            self.layout_row_static(25, UI_LEFT_PANE_WIDTH - 30, 1)
            old_side_mat_idx = self.selected_side_mat_idx
            self.selected_side_mat_idx = self.combo_box([mat.name for mat in globals.active_map.materials], self.selected_side_mat_idx, 25, (UI_LEFT_PANE_WIDTH - 30, 200))
            if old_side_mat_idx != self.selected_side_mat_idx:
                pf.global_event(EVENT_SIDE_MAT_SEL_CHANGED, globals.active_map.materials[self.selected_side_mat_idx])

