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

#ifndef FIELD_H
#define FIELD_H

#include "public/nav.h"
#include "nav_data.h"
#include "../pf_math.h"
#include "../map/public/tile.h"
#include <stdbool.h>

typedef uint64_t ff_id_t;
struct nav_private;

struct LOS_field{
    struct coord chunk;
    struct{
        uint8_t visible : 1;
        uint8_t wavefront_blocked : 1;
    }field[FIELD_RES_R][FIELD_RES_C];
};

struct enemies_desc{
    int          faction_id;
    vec3_t       map_pos;
    struct coord chunk;
};

struct entity_desc{
    uint32_t     target;
    vec3_t       map_pos;
};

struct portal_desc{
    const struct portal *port;
    uint16_t             port_iid;
    const struct portal *next;
    uint16_t             next_iid;
};

struct field_target{
    enum{
        TARGET_PORTAL,
        TARGET_TILE,
        TARGET_ENEMIES,
        /* Guide to the closest eligible portal. Each set bit represents
         * that the portal at that index is 'eligible'. */
        TARGET_PORTALMASK,
        TARGET_ENTITY,
    }type;
    union{
        struct portal_desc   pd;
        struct coord         tile;
        struct enemies_desc  enemies;
        uint64_t             portalmask;
        struct entity_desc   ent;
    };
};

struct flow_field{
    struct coord chunk;
    struct field_target target;
    struct{
        uint8_t dir_idx : 4;
    }field[FIELD_RES_R][FIELD_RES_C];
};

/* ------------------------------------------------------------------------
 * Get the unique flow field ID for the specified parameters.
 * ------------------------------------------------------------------------
 */
ff_id_t        N_FlowFieldID(struct coord        chunk, 
                             struct field_target target, 
                             enum nav_layer      layer);

/* ------------------------------------------------------------------------
 * Extract the navigation layer from the previously generated flow field ID.
 * ------------------------------------------------------------------------
 */
enum nav_layer N_FlowFieldLayer(ff_id_t id);

/* ------------------------------------------------------------------------
 * Extract the field target type from the previously generated flow field ID.
 * ------------------------------------------------------------------------
 */
int            N_FlowFieldTargetType(ff_id_t id);

/* ------------------------------------------------------------------------
 * Initialize the field to have a 'FD_NONE' direction at every tile. Regions
 * of the field can then be made to guide towards specifid targets with 
 * subsequent calls to the 'Update' family of functions.
 * ------------------------------------------------------------------------
 */
void    N_FlowFieldInit(struct coord       chunk_coord, 
                        struct flow_field *out);

/* ------------------------------------------------------------------------
 * Populate the flow field with directions leading units in the field towards
 * the target. If faction_id is not FACTION_ID_NONE, then tiles blocked by
 * enemy factions will not be considered obstacles.
 * ------------------------------------------------------------------------
 */
void    N_FlowFieldUpdate(struct coord              chunk_coord, 
                          const struct nav_private *priv, 
                          int                       faction_id,
                          enum nav_layer            layer, 
                          struct field_target       target, 
                          struct flow_field        *inout_flow);

/* ------------------------------------------------------------------------
 * Update all tiles with a specific local island ID from the
 * 'local_islands' field for the chunk. The new directions will guide to
 * the closest possible tiles to the original field target. In the case
 * that the original field target tiles all are all on the same local
 * island (local_iid), the field will remain unchanged.
 * ------------------------------------------------------------------------
 */
void    N_FlowFieldUpdateIslandToNearest(uint16_t                  local_iid, 
                                         const struct nav_private *priv,
                                         enum nav_layer            layer, 
                                         int                       faction_id, 
                                         struct flow_field        *inout_flow);

/* ------------------------------------------------------------------------
 * Update all tiles for for the 'impassable island' that start is a part of
 * (i.e. the start tile and all impassable tiles that are connected to it via
 * other impassable tiles) to guide to the closest passable tiles on the same 
 * chunk. This can be used to guide entities back to a passable tile if they 
 * somehow end up on an impassable one.
 * ------------------------------------------------------------------------
 */
void N_FlowFieldUpdateToNearestPathable(const struct nav_private *priv, 
                                        enum nav_layer            layer,
                                        struct coord              chunk,
                                        struct coord              start, 
                                        int                       faction_id, 
                                        struct flow_field        *inout_flow);

/* ------------------------------------------------------------------------
 * Create a line of sight field, indicating which tiles in this chunk are 
 * directly visible from the 'target' tile. If the 'target' tile is not in
 * the current chunk, the previous LOS field along the path must be 
 * supplied in the 'prev_los' argument, so that the visibility information
 * can be carried accross the chunk border. This means that the LOS fields 
 * must be generated starting at the destination chunk (where 'prev_los' is 
 * NULL) and and moving backwards along the path back to the 'source' chunk.
 * ------------------------------------------------------------------------
 */
void    N_LOSFieldCreate(dest_id_t                 id, 
                         struct coord              chunk_coord, 
                         struct tile_desc          target,
                         const struct nav_private *priv, 
                         vec3_t                    map_pos, 
                         struct LOS_field         *out_los, 
                         const struct LOS_field   *prev_los);

#endif

