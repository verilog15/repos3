/*
 *  This file is part of Permafrost Engine. 
 *  Copyright (C) 2018-2023 Eduard Permyakov 
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

#ifndef SELECTION_H
#define SELECTION_H

#include "public/game.h"
#include "../lib/public/vec.h"
#include "../entity.h"

#include <stdbool.h>

struct obb;
struct camera;
struct SDL_RWops;

VEC_TYPE(obb, struct obb)
VEC_PROTOTYPES(extern, obb, struct obb)

extern const vec3_t g_seltype_color_map[];

bool G_Sel_Init(void);
void G_Sel_Shutdown(void);
void G_Sel_Update(struct camera *cam, const vec_entity_t *visible, const vec_obb_t *visible_obbs);
bool G_Sel_SaveState(struct SDL_RWops *stream);
bool G_Sel_LoadState(struct SDL_RWops *stream);
void G_Sel_MarkHoveredDirty(void);
bool G_Sel_IsSelected(uint32_t uid);

#endif
