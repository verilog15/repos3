/*
 *  This file is part of Permafrost Engine. 
 *  Copyright (C) 2021-2023 Eduard Permyakov 
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

#ifndef PHYS_H
#define PHYS_H

struct obb;
struct SDL_RWops;

#include "../../pf_math.h"

#include <stdint.h>
#include <stdbool.h>


#define PROJ_ONLY_HIT_COMBATABLE   (1 << 0)
#define PROJ_ONLY_HIT_ENEMIES      (1 << 1)

struct proj_hit{
    uint32_t ent_uid;
    uint32_t proj_uid;
    uint32_t parent_uid;
    uint32_t cookie;
};

struct proj_desc{
    const char *basedir;
    const char *pfobj;
    vec3_t      scale;
    float       speed;
};

bool     P_Projectile_Init(void);
void     P_Projectile_Shutdown(void);

uint32_t P_Projectile_Add(vec3_t origin, vec3_t velocity, uint32_t ent_parent, int faction_id, 
                          uint32_t cookie, int flags, struct proj_desc pd);
void     P_Projectile_Update(void);
bool     P_Projectile_VelocityForTarget(vec3_t src, vec3_t dst, float init_speed, vec3_t *out);

bool     P_Projectile_SaveState(struct SDL_RWops *stream);
bool     P_Projectile_LoadState(struct SDL_RWops *stream);
void     P_Projectile_ClearState(void);

#endif

