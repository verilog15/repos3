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

#ifndef A_STAR_H
#define A_STAR_H

#include "nav_data.h"
#include "public/nav.h"
#include "../lib/public/vec.h"
#include "../map/public/tile.h"

#include <stdbool.h>


struct nav_private;

/* 
 * Say we have the following scenario: there are 3 chunks in a column
 * linked by portals. The middle chunk has some temporary blockers such
 * that it is being divided into 2 islands. We wish to find the list of 
 * portals we need to traverse to get from the top to the bottom.
 *
 *   +----------+
 *   |AAAAAAAAAA| (portal A)
 *   +----------+
 *   |0000000000|
 *   |0000000000|
 *   |0000000000| (chunk 1) - [1 local island]
 *   |0000000000|
 *   |0000000000|
 *   +----------+
 *   |BBBBBBBBBB| (portal B)
 *   +----------+
 *   |1111^0000^|
 *   |1111^0000^|
 *   |1111^0000^| (chunk 2) - [2 local islands]
 *   |1111^^^^^^|
 *   |1111111111|
 *   +----------+
 *   |CCCCCCCCCC| (portal C)
 *   +----------+
 *   |0000000000|
 *   |0000000000|
 *   |0000000000| (chunk 3) - [1 local island]
 *   |0000000000|
 *   |0000000000|
 *   +----------+
 *   |DDDDDDDDDD| (portal D)
 *   +----------+
 *   |0000000000|
 *   ............
 *
 * Obviously, this is the list of portals: A -> B -> C -> D
 * However, this information on its' own is not enough. Looking at
 * this example, it can be seen that the blockers are really dividing 
 * portal B into two portals - the left side and the right side. If 
 * we enter from the right side, we will get trapped in an enclave.
 *
 * As such, we need additional information along with which portals
 * to enter: the local island at which we can enter it on.
 *
 * Using this, the new path now looks like the following series of 'hops':
 * (A, 0) -> (B, 1) -> (C, 0) -> (D, 0)
 */
struct portal_hop{
    const struct portal *portal;
    uint16_t liid;
};

VEC_TYPE(coord, struct coord)
VEC_IMPL(static inline, coord, struct coord)

VEC_TYPE(portal, struct portal_hop)
VEC_IMPL(static inline, portal, struct portal_hop)


/* ------------------------------------------------------------------------
 * Finds the shortest path in a rectangular cost field. Returns true if a 
 * path is found, false otherwise. If returning true, 'out_path' holds the
 * tiles to be traversed, in order.
 * ------------------------------------------------------------------------
 */
bool AStar_GridPath(struct coord start, struct coord finish, struct coord chunk,
                    const uint8_t cost_field[FIELD_RES_R][FIELD_RES_C], 
                    enum nav_layer layer, vec_coord_t *out_path, float *out_cost);

/* ------------------------------------------------------------------------
 * Finds the shortest path between a tile and a node in a portal graph. Returns 
 * true if a path is found, false otherwise. If returning true, 'out_path' holds 
 * the portal nodes to be traversed, in order.
 * ------------------------------------------------------------------------
 */
bool AStar_PortalGraphPath(struct tile_desc start_tile, struct tile_desc end_tile, 
                           const struct portal *finish, const struct nav_private *priv, 
                           enum nav_layer layer, vec_portal_t *out_path, float *out_cost);

#endif

