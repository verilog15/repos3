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

#ifndef MAP_H
#define MAP_H

#include "../../pf_math.h"
#include "../../navigation/public/nav.h" /* dest_id_t */

#include <stdio.h>
#include <stdbool.h>

#include <SDL.h> /* for SDL_RWops */

#define MINIMAP_BORDER_WIDTH    (3.0f)
#define MAX_HEIGHT_LEVEL        (9)
#define MAX_MAP_TEXTURES        (256)

struct pfchunk;
struct pfmap_hdr;
struct map;
struct camera;
struct tile;
struct tile_desc;
struct obb;
enum render_pass;
struct map_resolution;

struct chunkpos{
    int r, c;
};

struct splat{
    unsigned base_mat_idx;
    unsigned accent_mat_idx;
};

struct splatmap{
    struct splat splats[MAX_MAP_TEXTURES];
};

/*###########################################################################*/
/* MAP GENERAL                                                               */
/*###########################################################################*/

/* ------------------------------------------------------------------------
 * Once per frame updates of the private map data.
 * ------------------------------------------------------------------------
 */
void   M_Update(const struct map *map);

/* ------------------------------------------------------------------------
 * This renders all the chunks at once, which is wasteful when there are 
 * many off-screen chunks. Depending on the 'pass' type, this will perform 
 * a different rendering action.
 * ------------------------------------------------------------------------
 */
void   M_RenderEntireMap(const struct map *map, bool shadows, enum render_pass pass);

/* ------------------------------------------------------------------------
 * Get the model matrix for a specific chunk.
 * ------------------------------------------------------------------------
 */
void   M_ModelMatrixForChunk(const struct map *map, struct chunkpos p, mat4x4_t *out);

/* ------------------------------------------------------------------------
 * Renders the chunks of the map that are currently visible by the specified
 * camera using a frustrum-chunk intersection test. Depending on the 'pass'
 * type, this will perform a different action.
 * ------------------------------------------------------------------------
 */
void   M_RenderVisibleMap(const struct map *map, const struct camera *cam, 
                          bool shadows, enum render_pass pass);

/* ------------------------------------------------------------------------
 * Render a layer over the visible map surface showing which regions are 
 * pathable and which are not.
 * ------------------------------------------------------------------------
 */
void   M_RenderVisiblePathableLayer(const struct map *map, const struct camera *cam,
                                    enum nav_layer layer);

/* ------------------------------------------------------------------------
 * Render lines over the map surface showing the boudnaries between different 
 * chunks.
 * ------------------------------------------------------------------------
 */
void   M_RenderChunkBoundaries(const struct map *map, const struct camera *cam);

/* ------------------------------------------------------------------------
 * Render a layer over the visible map surface showing fields which guide
 * units of a particular factions towards their enemies. These fields are
 * used for combat target selection.
 * ------------------------------------------------------------------------
 */
void   M_NavRenderVisibleEnemySeekField(const struct map *map, const struct camera *cam, 
                                        enum nav_layer layer, int faction_id);

/* ------------------------------------------------------------------------
 * Debug rendering of fields that guide units to surround a specific target.
 * ------------------------------------------------------------------------
 */
void   M_NavRenderVisibleSurroundField(const struct map *map, const struct camera *cam, 
                                       enum nav_layer layer, uint32_t uid);

/* ------------------------------------------------------------------------
 * Render a layer over the visible map surface showing which regions are 
 * currently blocked by stationary entities.
 * ------------------------------------------------------------------------
 */
void   M_NavRenderNavigationBlockers(const struct map *map, const struct camera *cam,
                                     enum nav_layer layer);

/* ------------------------------------------------------------------------
 * Render a layer over the visible map surface showing which tiles under
 * an object's OBB can currently be built on. The 'blocked' flag can be used
 * to render all tiles as non-buildable.
 * ------------------------------------------------------------------------
 */
void   M_NavRenderBuildableTiles(const struct map *map, const struct camera *cam, 
                                 const struct obb *obb, enum nav_layer layer, 
                                 bool blocked, bool allow_cliffs);

/* ------------------------------------------------------------------------
 * Render a layer over the visible map surface showing portals between chunks
 * and their status.
 * ------------------------------------------------------------------------
 */
void   M_NavRenderNavigationPortals(const struct map *map, const struct camera *cam,
                                    enum nav_layer layer);

/* ------------------------------------------------------------------------
 * Debug rendering to show the global island ID over every navigation tile.
 * ------------------------------------------------------------------------
 */
void   M_NavRenderNavigationIslandIDs(const struct map *map, const struct camera *cam,
                                      enum nav_layer layer);

/* ------------------------------------------------------------------------
 * Debug rendering to show the local island ID over every navigation tile.
 * ------------------------------------------------------------------------
 */
void   M_NavRenderNavigationLocalIslandIDs(const struct map *map, const struct camera *cam,
                                           enum nav_layer layer);

/* ------------------------------------------------------------------------
 * Centers the map at the worldspace origin.
 * ------------------------------------------------------------------------
 */
void   M_CenterAtOrigin     (struct map *map);

/* ------------------------------------------------------------------------
 * Sets an XZ bounding box for the camera such that the XZ coordinate of 
 * the intersection of the camera ray with the ground plane is always 
 * within the map area.
 * ------------------------------------------------------------------------
 */
void   M_RestrictRTSCamToMap(const struct map *map, struct camera *cam);

/* ------------------------------------------------------------------------
 * Install event handlers which will keep up-to-date state of the currently
 * hovered over tile.
 * ------------------------------------------------------------------------
 */
int    M_Raycast_Install(struct map *map, struct camera *cam);

/* ------------------------------------------------------------------------
 * Uninstall handlers installed by 'M_Raycast_Install'
 * ------------------------------------------------------------------------
 */
void   M_Raycast_Uninstall(void);

/* ------------------------------------------------------------------------
 * Determines how many tiles around the selected tile are highlighted during
 * rendering. 0 (default) means no tile is highlighted; 1 = single tile is 
 * highlighted; 3 = 3x3 grid is highlighted; etc.
 * ------------------------------------------------------------------------
 */
void   M_Raycast_SetHighlightSize(size_t size);
size_t M_Raycast_GetHighlightSize(void);

/* ------------------------------------------------------------------------
 * If returning true, the height of the map under the mouse cursor will be
 * written to 'out'. Otherwise, the mouse cursor is not over the map surface.
 * ------------------------------------------------------------------------
 */
bool   M_Raycast_MouseIntersecCoord(vec3_t *out);

/* ------------------------------------------------------------------------
 * If returning true, the height of the map under the ray originating at 
 * the camera position and facing in the same direction as the camera is 
 * written to 'out'.
 * ------------------------------------------------------------------------
 */
bool   M_Raycast_CameraIntersecCoord(const struct camera *cam, vec3_t *out);

/* ------------------------------------------------------------------------
 * Utility function to convert an XZ worldspace coordinate to one in the 
 * range (-1, -1) in the 'top left' corner to (1, 1) in the 'bottom right' 
 * corner for square maps, with (0, 0) being in the exact center of the map. 
 * Coordinates outside the map bounds will be ouside this range. Note that 
 * for non-square maps, the proportion of the width to the height is kept 
 * the same, meaning that the shorter dimension will not span the entire 
 * range of [-1, 1]
 * ------------------------------------------------------------------------
 */
vec2_t M_WorldCoordsToNormMapCoords(const struct map *map, vec2_t xz);

/* ------------------------------------------------------------------------
 * Returns true if the XZ coordinate is within the map bounds.
 * ------------------------------------------------------------------------
 */
bool   M_PointInsideMap(const struct map *map, vec2_t xz);

/* ------------------------------------------------------------------------
 * Returns true if the XZ coordinate is over water.
 * ------------------------------------------------------------------------
 */
bool   M_PointOverWater(const struct map *map, vec2_t pos);

/* ------------------------------------------------------------------------
 * Returns true if the XZ coordinate is over land.
 * ------------------------------------------------------------------------
 */
bool   M_PointOverLand(const struct map *map, vec2_t pos);

/* ------------------------------------------------------------------------
 * Returns true if the tile has at least one adjacent tile over water.
 * ------------------------------------------------------------------------
 */
bool   M_TileAdjacentToWater(const struct map *map, const struct tile_desc *td);

/* ------------------------------------------------------------------------
 * Returns true if the tile has at least one adjacent tile over land.
 * ------------------------------------------------------------------------
 */
bool   M_TileAdjacentToLand(const struct map *map, const struct tile_desc *td);

/* ------------------------------------------------------------------------
 * Returns true if any of the tiles under the object are adjacent to water
 * or land.
 * ------------------------------------------------------------------------
 */
bool   M_ObjectAdjacentToWater(const struct map *map, const struct obb *obb);
bool   M_ObjectAdjacentToLand(const struct map *map, const struct obb *obb);

/* ------------------------------------------------------------------------
 * Returns an XZ coordinate that is contained within the map bounds. The 
 * 'xz' arg is truncated if it's outside the map range, or unchanged otherwise.
 * ------------------------------------------------------------------------
 */
vec2_t M_ClampedMapCoordinate(const struct map *map, vec2_t xz);

/* ------------------------------------------------------------------------
 * Returns the Y coordinate for an XZ point on the map's surface.
 * ------------------------------------------------------------------------
 */
float  M_HeightAtPoint(const struct map *map, vec2_t xz);

/* ------------------------------------------------------------------------
 * Sets 'out to a tile descriptor for an XZ point on a the map. 'out' is valid
 * if the function returns true.
 * ------------------------------------------------------------------------
 */
bool   M_DescForPoint2D(const struct map *map, vec2_t point_xz, struct tile_desc *out);

/* ------------------------------------------------------------------------
 * Returns the material index for a particular texture, or '-1' if it is 
 * not found.
 * ------------------------------------------------------------------------
 */
int    M_MaterialIndexForTexture(const struct map *map, const char *texture);

/* ------------------------------------------------------------------------
 * Make an impassable region in the navigation data, making it not possible 
 * for pathable units to pass through the region underneath the OBB.
 * ------------------------------------------------------------------------
 */
void   M_NavCutoutStaticObject(const struct map *map, const struct obb *obb);

/* ------------------------------------------------------------------------
 * Update navigation private data after changes to the cost field.
 * (ex. to remove a path in case it was blocked off by a placed object)
 * ------------------------------------------------------------------------
 */
void   M_NavUpdatePortals(const struct map *map);

/* ------------------------------------------------------------------------
 * Update navigation private data (regarding which tile is reachanble from
 * which other tiles) after changes to the cost field.
 * ------------------------------------------------------------------------
 */
void   M_NavUpdateIslandsField(const struct map *map);

/* ------------------------------------------------------------------------
 * Makes a path request to the navigation subsystem, causing the required
 * flowfields to be generated and cached. Returns true if a successful path
 * has been made, false otherwise.
 * ------------------------------------------------------------------------
 */
bool   M_NavRequestPath(const struct map *map, vec2_t xz_src, vec2_t xz_dest, 
                        enum nav_layer layer, dest_id_t *out_dest_id);

/* ------------------------------------------------------------------------
 * Render the flow field that will steer entities towards a particular 
 * destination over the map surface.
 * Also render the LOS field of tiles directly visible from the destination.
 * ------------------------------------------------------------------------
 */
void   M_NavRenderVisiblePathFlowField(const struct map *map, const struct camera *cam, 
                                       dest_id_t id);
/* ------------------------------------------------------------------------
 * Render the vision information for a particular faction. Every tile is 
 * color-coded based on the vision the specified faction has of it. 
 * (black = unexplored, green = visible, yellow = in fog of war)
 * ------------------------------------------------------------------------
 */
void   M_RenderChunkVisibility(const struct map *map, const struct camera *cam, 
                               int faction_id);

/* ------------------------------------------------------------------------
 * Returns the desired velocity vector for moving with the flow field 
 * to the specified destination.
 * ------------------------------------------------------------------------
 */
vec2_t M_NavDesiredPointSeekVelocity(const struct map *map, dest_id_t id, 
                                     vec2_t curr_pos, vec2_t xz_dest);

/* ------------------------------------------------------------------------
 * Returns the desired velocity vector for moving with the flow field 
 * for approaching enemies of a particular faction.
 * ------------------------------------------------------------------------
 */
vec2_t M_NavDesiredEnemySeekVelocity(const struct map *map, enum nav_layer layer, 
                                     vec2_t curr_pos, int faction_id);

/* ------------------------------------------------------------------------
 * Returns the desired velocity vector for getting as close as possible
 * to a specific entity. This only works when we are within a chunk-sized
 * box centered at the target entity position. Until then, use a point path.
 * ------------------------------------------------------------------------
 */
vec2_t M_NavDesiredSurroundVelocity(const struct map *map, enum nav_layer layer, 
                                    vec2_t curr_pos, const uint32_t uid, int faction_id);

/* ------------------------------------------------------------------------
 * Returns true if the specified coordinate is in direct line of sight of 
 * the specified destination.
 * ------------------------------------------------------------------------
 */
bool   M_NavHasDestLOS(const struct map *map, dest_id_t id, vec2_t curr_pos);

/* ------------------------------------------------------------------------
 * Returns true if the particular entity is in direct line of sight of the 
 * specified position.
 * ------------------------------------------------------------------------
 */
bool   M_NavHasEntityLOS(const struct map *map, enum nav_layer layer, 
                         vec2_t xz_pos, const uint32_t uid);

/* ------------------------------------------------------------------------
 * Returns true if the specified positions is pathable (i.e. a unit is 
 * allowed to stand on this region of the map)
 * ------------------------------------------------------------------------
 */
bool   M_NavPositionPathable(const struct map *map, enum nav_layer layer, 
                             vec2_t xz_pos);

/* ------------------------------------------------------------------------
 * Returns true if the specified positions is blocked (i.e. a unit or entity
 * is currently occupying this tile, causing it to temporarily become non-traversable)
 * ------------------------------------------------------------------------
 */
bool   M_NavPositionBlocked(const struct map *map, enum nav_layer layer, 
                            vec2_t xz_pos);

/* ------------------------------------------------------------------------
 * Returns the closest position to the destination that is pathable to from
 * the (valid) source position. In the best case, this is the destination
 * itself.
 * ------------------------------------------------------------------------
 */
vec2_t M_NavClosestReachableDest(const struct map *map, enum nav_layer layer, 
                                 vec2_t xz_src, vec2_t xz_dst);

/* ------------------------------------------------------------------------
 * If true is returned, 'out' is set to the worldspace XZ position of the 
 * closest reachable point on the map that is adjacent to the specified entity.
 * For 'static' entities, the tiles under the OBB are used, else the tiles
 * under the selection circle are used.
 * ------------------------------------------------------------------------
 */
bool   M_NavClosestReachableAdjacentPos(const struct map *map, enum nav_layer layer, 
                                        vec2_t xz_src, const uint32_t target_uid, 
                                        vec2_t *out);

/* ------------------------------------------------------------------------
 * Will return the XZ map position that the entity at the source location
 * should travel to in order to get in range of the target position using
 * the shortest path.
 * ------------------------------------------------------------------------
 */
vec2_t M_NavClosestReachableInRange(const struct map *map, enum nav_layer layer,
                                    vec2_t xz_src, vec2_t xz_target, float range);

/* ------------------------------------------------------------------------
 * Will write the XZ map position of the closest currently pathable location
 * to the source to out, if it exists.
 * ------------------------------------------------------------------------
 */
bool M_NavClosestPathable(const struct map *map, enum nav_layer layer, 
                          vec2_t xz_src, vec2_t *out);

/* ------------------------------------------------------------------------
 * Returns the closest position to 'pos' that is adjacent to a land tile.
 * ------------------------------------------------------------------------
 */
vec2_t M_NavClosestPointAdjacentToLand(const struct map *map, vec2_t pos);

/* ------------------------------------------------------------------------
 * Returns the closest position to 'pos' that is adjacent to a land tile
 * having the same global "island ID" as the tile under the 'island_pos'
 * location.
 * ------------------------------------------------------------------------
 */
vec2_t M_NavClosestPointAdjacentToIsland(const struct map *map, vec2_t pos,
                                         vec2_t island_pos, enum nav_layer layer);

/* ------------------------------------------------------------------------
 * Returns true if the two locations can currently be reached from one another.
 * ------------------------------------------------------------------------
 */
bool M_NavLocationsReachable(const struct map *map, enum nav_layer layer, 
                             vec2_t a, vec2_t b);

/* ------------------------------------------------------------------------
 * Change the blocker reference count for the navigation tile under the
 * specified position. Flow fields will steer around tiles with a blocker 
 * count of greater than 0.
 * ------------------------------------------------------------------------
 */
void   M_NavBlockersIncref(vec2_t xz_pos, float range, int faction_id, 
                           uint32_t flags, const struct map *map);
void   M_NavBlockersDecref(vec2_t xz_pos, float range, int faction_id, 
                           uint32_t flags, const struct map *map);

void   M_NavBlockersIncrefOBB(const struct map *map, int faction_id, 
                              uint32_t flags, const struct obb *obb);
void   M_NavBlockersDecrefOBB(const struct map *map, int faction_id, 
                              uint32_t flags, const struct obb *obb);

/* ------------------------------------------------------------------------
 * Wrapper around navigation APIs.
 * ------------------------------------------------------------------------
 */
uint32_t M_NavDestIDForPos(const struct map *map, vec2_t xz_pos, enum nav_layer layer);
uint32_t M_NavDestIDForPosAttacking(const struct map *map, vec2_t xz_pos, 
                                    enum nav_layer layer, int faction_id);
void     M_NavGetResolution(const struct map *map, struct map_resolution *out);
bool     M_NavObjectBuildable(const struct map *map, enum nav_layer layer, 
                              bool allow_shore, const struct obb *obb);
bool     M_NavIsMaximallyClose(const struct map *map, enum nav_layer layer, 
                               vec2_t xz_pos, vec2_t xz_dest, float tolerance);
bool     M_NavIsAdjacentToImpassable(const struct map *map, enum nav_layer layer, vec2_t xz_pos);
void     M_NavCopyIslandsFieldView(const struct map *map, vec2_t center,
                                   int nrows, int ncols, enum nav_layer layer, uint16_t *out_field);
void     M_NavCellArrivalFieldCreate(const struct map *map, size_t rdim, size_t cdim, 
                                     enum nav_layer layer, uint16_t enemies,
                                     struct tile_desc target, struct tile_desc center,
                                     uint8_t *out, void *workspace, size_t workspace_size);
void     M_NavCellArrivalFieldUpdateToNearestPathable(const struct map *map, 
                                  size_t rdim, size_t cdim, enum nav_layer layer, uint16_t enemies,
                                  struct tile_desc start, struct tile_desc center, 
                                  uint8_t *inout, void *workspace, size_t workspace_size);
bool     M_NavIsAdjacentToIsland(const struct map *map, enum nav_layer layer, vec2_t xz_pos, 
                                 float radius, vec2_t island_pos);
bool     M_NavIsAdjacentToIslandOBB(const struct map *map, enum nav_layer layer, 
                                    const struct obb *obb, vec2_t island_pos);

/* ------------------------------------------------------------------------
 * Request an asynchronous computation of a field.
 * ------------------------------------------------------------------------
 */

void M_NavRequestAsyncEnemySeekField(const struct map *map, enum nav_layer layer, 
                                     vec2_t curr_pos, int faction_id);
void M_NavRequestAsyncSurroundField(const struct map *map, enum nav_layer layer, 
                                    vec2_t curr_pos, uint32_t ent, int faction_id);

/* ------------------------------------------------------------------------
 * Returns true if the tiles under the entity selection cirlce overlap or 
 * share an edge with any of the tiles under the target entity.
 * For 'static' enties, the OBB is used. Else, the selection circle is used.
 * ------------------------------------------------------------------------
 */
bool     M_NavObjAdjacent(const struct map *map, const uint32_t uid, 
                         const uint32_t target_uid);

/* ------------------------------------------------------------------------
 * Like M_NavObjAdjacent, but allowing passsing all the required state
 * as arguments.
 * ------------------------------------------------------------------------
 */
bool     M_NavObjAdjacentToStaticWith(const struct map *map, vec2_t xz_pos, float radius, 
                                      const struct obb *stat);
bool     M_NavObjAdjacentToDynamicWith(const struct map *map, vec2_t xz_pos_a, float radius_a,
                                       vec2_t xz_pos_b, float radius_b);

/* ------------------------------------------------------------------------
 * Sets 'out' to pointer to 'struct tile' for the specified descriptor. 
 * Returns 'true' on success, 'false' on failure.
 * ------------------------------------------------------------------------
 */
bool   M_TileForDesc(const struct map *map, struct tile_desc desc, struct tile **out);

/* ------------------------------------------------------------------------
 * Get the resolution (chunks, tiles) of the specified map.
 * ------------------------------------------------------------------------
 */
void   M_GetResolution(const struct map *map, struct map_resolution *out);

/* ------------------------------------------------------------------------
 * Enable or disable rendering shadows on the map.
 * ------------------------------------------------------------------------
 */
void   M_SetShadowsEnabled(struct map *map, bool on);

/* ------------------------------------------------------------------------
 * Returns the center point of the map, in world space.
 * ------------------------------------------------------------------------
 */
vec3_t M_GetCenterPos(const struct map *map);

/* ------------------------------------------------------------------------
 * Returns the position of the top-left corner of the amp, in world space.
 * ------------------------------------------------------------------------
 */
vec3_t M_GetPos(const struct map *map);


/*###########################################################################*/
/* MINIMAP                                                                   */
/*###########################################################################*/

/* ------------------------------------------------------------------------
 * Creates a minimap texture from the map to be rendered later.
 * ------------------------------------------------------------------------
 */
bool   M_InitMinimap     (struct map *map, vec2_t center_pos);

/* ------------------------------------------------------------------------
 * Update a chunk-sized region of the minimap texture with the most 
 * up-to-date vertex data.
 * ------------------------------------------------------------------------
 */
bool   M_UpdateMinimapChunk(const struct map *map, int chunk_r, int chunk_c);

/* ------------------------------------------------------------------------
 * Frees the resources allocated by 'M_InitMinimap'.
 * ------------------------------------------------------------------------
 */
void   M_FreeMinimap     (struct map *map);

/* ------------------------------------------------------------------------
 * Sets the virtual resolution. This determines how the other minimap 
 * coordinates get mapped to the viewport.
 * ------------------------------------------------------------------------
 */
void   M_SetMinimapVres(struct map *map, vec2_t vres);
/* ------------------------------------------------------------------------
 * This returns the bounds for the current aspect ratio based on the 
 * resize mask.
 * ------------------------------------------------------------------------
 */
void   M_GetMinimapAdjVres(const struct map *map, vec2_t *out_vres);

/* ------------------------------------------------------------------------
 * The minimap position, in virtual screen coordinates.
 * ------------------------------------------------------------------------
 */
void   M_GetMinimapPos   (const struct map *map, vec2_t *out_center_pos);
void   M_SetMinimapPos   (struct map *map, vec2_t center_pos);

/* ------------------------------------------------------------------------
 * The minimap size, in virtual screen coordinates.
 * ------------------------------------------------------------------------
 */
int    M_GetMinimapSize(const struct map *map);
void   M_SetMinimapSize(struct map *map, int side_len);

/* ------------------------------------------------------------------------
 * Controls the minimap bounds as the screen resizes. See ui.h
 * ------------------------------------------------------------------------
 */
void   M_SetMinimapResizeMask(struct map *map, int resize_mask);

/* ------------------------------------------------------------------------
 * Render the minimap at the location specified by 'M_SetMinimapPos' and 
 * draw a box around the area visible by the specified camera.
 * ------------------------------------------------------------------------
 */
void   M_RenderMinimap   (const struct map *map, const struct camera *cam);

/* ------------------------------------------------------------------------
 * Render a coloroed box for every specified unit in the minimap region.
 * ------------------------------------------------------------------------
 */
void   M_RenderMinimapUnits(const struct map *map, size_t nunits, 
                            vec2_t *posbuff, vec3_t *colorbuff);

/* ------------------------------------------------------------------------
 * Render the minimap at the location specified by 'M_SetMinimapPos'.
 * ------------------------------------------------------------------------
 */
bool   M_MouseOverMinimap(const struct map *map);

/* ------------------------------------------------------------------------
 * Returns false if none of the chunks visible by the camera have water tiles.
 * This can allow us to skip rendering the water altogether in some cases.
 * ------------------------------------------------------------------------
 */
bool   M_WaterMaybeVisible(const struct map *map, const struct camera *cam);

/* ------------------------------------------------------------------------
 * Add/remove secondary (splat) materials that are blended together with
 * some existing material.
 * ------------------------------------------------------------------------
 */
bool   M_AddSplat(struct map *map, int base_mat_idx, int accent_mat_idx);
bool   M_RemoveSplat(struct map *map, int base_mat_idx, int accent_mat_idx);

/* ------------------------------------------------------------------------
 * Returns true if the mouse is over a valid map location on the minimap.
 * In this case, 'out' is set to the worldspace coordinate of the position
 * over the map surface.
 * ------------------------------------------------------------------------
 */
bool   M_MinimapMouseMapCoords(const struct map *map, vec3_t *out);

/* ------------------------------------------------------------------------
 * Access the (RGBA) color of the minimap border.
 * ------------------------------------------------------------------------
 */
vec4_t M_MinimapGetBorderClr(void);
void   M_MinimapSetBorderClr(vec4_t clr);
void   M_MinimapClearBorderClr(void);


/*###########################################################################*/
/* MAP ASSET LOADING                                                         */
/*###########################################################################*/

/* ------------------------------------------------------------------------
 * Initialize private map data ('outmap', which is allocated by the calleer) 
 * from PFMAP stream.
 * ------------------------------------------------------------------------
 */
bool   M_AL_InitMapFromStream(const struct pfmap_hdr *header, const char *basedir,
                              SDL_RWops *stream, void *outmap, bool update_navgrid);

/* ------------------------------------------------------------------------
 * Returns the size, in bytes, needed to store the private map data
 * based on the header contents.
 * ------------------------------------------------------------------------
 */
size_t M_AL_BuffSizeFromHeader(const struct pfmap_hdr *header);

/* ------------------------------------------------------------------------
 * Writes the map in PFMap format.
 * ------------------------------------------------------------------------
 */
void   M_AL_DumpMap(FILE *stream, const struct map *map);

/* ------------------------------------------------------------------------
 * Cleans up resource allocations done during map initialization.
 * ------------------------------------------------------------------------
 */
void   M_AL_FreePrivate(struct map *map);

/* ------------------------------------------------------------------------
 * Updates the material list for the map, parsed from a PFMAP materials 
 * section string.
 * ------------------------------------------------------------------------
 */
bool   M_AL_UpdateChunkMats(const struct map *map, int chunk_r, int chunk_c, 
                            const char *mats_string);

bool   M_AL_UpdateTile(struct map *map, const struct tile_desc *desc, 
                       const struct tile *tile);

/* ------------------------------------------------------------------------
 * The size (in bytes) needed to store a shallow copy of the map.
 * ------------------------------------------------------------------------
 */
size_t M_AL_ShallowCopySize(size_t nrows, size_t ncols);

/* ------------------------------------------------------------------------
 * Copy map data to 'dst' buffer, which must have at least 'M_AL_ShallowCopySize'
 * bytes free. Handles to contexts/resources of other subsystems (ex. navigation 
 * and rendering data) are copied weakly.
 * ------------------------------------------------------------------------
 */
void   M_AL_ShallowCopy(struct map *dst, const struct map *src);

/* ------------------------------------------------------------------------
 * Makes a copy of the map, also copying cost field, blocked fields and
 * faction refcounts from the navigation data.
 * ------------------------------------------------------------------------
 */
struct map *M_AL_CopyWithFields(const struct map *src);
void        M_AL_FreeCopyWithFields(struct map *map);

/* ------------------------------------------------------------------------
 * Write the map contents to the stream in PFMap format.
 * ------------------------------------------------------------------------
 */
bool   M_AL_WritePFMap(const struct map *map, SDL_RWops *stream);

/* ------------------------------------------------------------------------
 * Manage memory pools used for 'deep' copies of the map.
 * ------------------------------------------------------------------------
 */
void   M_InitCopyPools(const struct map *map);
void   M_DestroyCopyPools(void);


#endif
