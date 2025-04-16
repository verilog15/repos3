/*
 *  This file is part of Permafrost Engine. 
 *  Copyright (C) 2020-2023 Eduard Permyakov 
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

#ifndef RENDER_AL_H
#define RENDER_AL_H

#include <stdio.h>
#include <SDL_rwops.h>

struct pfobj_hdr;
struct map;
struct tile;

/* ---------------------------------------------------------------------------
 * Consumes lines of the stream and uses them to populate a new private context
 * for the model. The context is returned in a malloc'd buffer.
 * ---------------------------------------------------------------------------
 */
void  *R_AL_PrivFromStream(const char *base_path, const struct pfobj_hdr *header, SDL_RWops *stream);

/* ---------------------------------------------------------------------------
 * Dumps private render data in PF Object format.
 * ---------------------------------------------------------------------------
 */
void   R_AL_DumpPrivate(FILE *stream, void *priv_data);

/* ---------------------------------------------------------------------------
 * Gives size (in bytes) of buffer size required for the render private 
 * buffer for a renderable PFChunk.
 * ---------------------------------------------------------------------------
 */
size_t R_AL_PrivBuffSizeForChunk(size_t tiles_width, size_t tiles_height, size_t num_mats);

/* ---------------------------------------------------------------------------
 * Initialize private render buff for a PFChunk of the map. 
 *
 * This function will build the vertices and their vertices from the data
 * already parsed into the 'tiles'.
 * ---------------------------------------------------------------------------
 */
bool   R_AL_InitPrivFromTiles(const struct map *map, int chunk_r, int chunk_c,
                              const struct tile *tiles, size_t width, size_t height,
                              void *priv_buff, const char *basedir);

#endif

