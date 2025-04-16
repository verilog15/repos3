/*
 *  This file is part of Permafrost Engine. 
 *  Copyright (C) 2024 Eduard Permyakov 
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

#include "garrison.h"
#include "game_private.h"
#include "fog_of_war.h"
#include "selection.h"
#include "movement.h"
#include "position.h"
#include "../main.h"
#include "../ui.h"
#include "../entity.h"
#include "../event.h"
#include "../sched.h"
#include "../task.h"
#include "../lib/public/khash.h"
#include "../lib/public/vec.h"
#include "../lib/public/attr.h"
#include "../lib/public/pf_nuklear.h"
#include "../lib/public/pf_string.h"

#include <assert.h>

#define EVICT_DELAY_MS          (1000)
#define GARRISON_THRESHOLD_DIST (25.0f)
#define GARRISON_BUFFER_DIST    (15.0f)
#define GARRISON_WAIT_TICKS     (5)
#define GARRISONABLE_WAIT_TICKS (10)
#define EPSILON                 (1.0f/1024)

#define CHK_TRUE_RET(_pred)             \
    do{                                 \
        if(!(_pred))                    \
            return false;               \
    }while(0)

enum unit_state{
    STATE_NOT_GARRISONED,
    STATE_MOVING_TO_GARRISONABLE,
    STATE_AWAITING_PICKUP,
    STATE_GARRISONED
};

enum holder_state{
    STATE_IDLE,
    STATE_MOVING_TO_PICKUP_POINT,
    STATE_MOVING_TO_DROPOFF_POINT
};

struct garrison_state{
    int             capacity_consumed;
    uint32_t        target;
    bool            target_rendevouz_issued;
    enum unit_state state;
    int             wait_ticks;
};

struct garrisonable_state{
    enum holder_state state;
    vec2_t            evict_target;
    /* The point the unit will go to in order to go in order to get into the transport */
    vec2_t            rendevouz_point_unit;
    /* The point the transport will go to in order to pickup the unit(s) */
    vec2_t            rendevouz_point_transport;
    int               wait_ticks;
    int               capacity;
    int               current;
    vec_entity_t      garrisoned;
};

struct evict_work{
    uint32_t      uid;
    vec2_t        target;
    uint32_t      tid;
};

KHASH_MAP_INIT_INT(garrison, struct garrison_state)
KHASH_MAP_INIT_INT(garrisonable, struct garrisonable_state)

VEC_TYPE(evict, struct evict_work)
VEC_IMPL(static inline, evict, struct evict_work)

/*****************************************************************************/
/* STATIC VARIABLES                                                          */
/*****************************************************************************/

static const struct map      *s_map;
static khash_t(garrison)     *s_garrison_state_table;
static khash_t(garrisonable) *s_garrisonable_state_table;
static bool                   s_evict_on_lclick = false;
static vec_evict_t            s_evicting;

static char                   s_garrison_icon_path[512] = {0};
static struct nk_style_item   s_bg_style = {0};
static struct nk_color        s_font_clr = {0};
static bool                   s_show_ui = true;

/*****************************************************************************/
/* STATIC FUNCTIONS                                                          */
/*****************************************************************************/

/* gu - garrison unit 
 * gb - garrisonable building
 */

static struct garrison_state *gu_state_get(uint32_t uid)
{
    khiter_t k = kh_get(garrison, s_garrison_state_table, uid);
    if(k == kh_end(s_garrison_state_table))
        return NULL;

    return &kh_value(s_garrison_state_table, k);
}

static bool gu_state_set(uint32_t uid, struct garrison_state gus)
{
    int status;
    khiter_t k = kh_put(garrison, s_garrison_state_table, uid, &status);
    if(status == -1 || status == 0)
        return false;
    kh_value(s_garrison_state_table, k) = gus;
    return true;
}

static void gu_state_remove(uint32_t uid)
{
    khiter_t k = kh_get(garrison, s_garrison_state_table, uid);
    if(k != kh_end(s_garrison_state_table))
        kh_del(garrison, s_garrison_state_table, k);
}

static struct garrisonable_state *gb_state_get(uint32_t uid)
{
    khiter_t k = kh_get(garrisonable, s_garrisonable_state_table, uid);
    if(k == kh_end(s_garrisonable_state_table))
        return NULL;

    return &kh_value(s_garrisonable_state_table, k);
}

static bool gb_state_set(uint32_t uid, struct garrisonable_state gus)
{
    int status;
    khiter_t k = kh_put(garrisonable, s_garrisonable_state_table, uid, &status);
    if(status == -1 || status == 0)
        return false;
    kh_value(s_garrisonable_state_table, k) = gus;
    return true;
}

static void gb_state_remove(uint32_t uid)
{
    khiter_t k = kh_get(garrisonable, s_garrisonable_state_table, uid);
    if(k != kh_end(s_garrisonable_state_table)) {
        struct garrisonable_state *gbs = &kh_value(s_garrisonable_state_table, k);
        vec_entity_destroy(&gbs->garrisoned);
        kh_del(garrisonable, s_garrisonable_state_table, k);
    }
}

static void on_update_ui(void *user, void *event)
{
    if(!s_show_ui)
        return;

    uint32_t uid;
    struct garrisonable_state gbs;
    struct nk_context *ctx = UI_GetContext();

    nk_style_push_style_item(ctx, &ctx->style.window.fixed_background, s_bg_style);

    kh_foreach(s_garrisonable_state_table, uid, gbs, {

        struct obb obb;
        Entity_CurrentOBB(uid, &obb, true);
        if(!G_Fog_ObjExplored(G_GetPlayerControlledFactions(), uid, &obb))
            continue;

        char name[256];
        pf_snprintf(name, sizeof(name), "__garrisonable__.%x", uid);

        const vec2_t vres = (vec2_t){1920, 1080};
        const vec2_t adj_vres = UI_ArAdjustedVRes(vres);

        vec2_t ss_pos = Entity_TopScreenPos(uid, adj_vres.x, adj_vres.y);
        const int width = 100;
        const int height = 32;
        const vec2_t pos = (vec2_t){ss_pos.x - width/2, ss_pos.y + 20};
        const int flags = NK_WINDOW_NOT_INTERACTIVE | NK_WINDOW_BACKGROUND | NK_WINDOW_NO_SCROLLBAR;

        struct rect adj_bounds = UI_BoundsForAspectRatio(
            (struct rect){pos.x, pos.y, width, height}, 
            vres, adj_vres, ANCHOR_DEFAULT
        );

        if(nk_begin_with_vres(ctx, name, 
            (struct nk_rect){adj_bounds.x, adj_bounds.y, adj_bounds.w, adj_bounds.h}, 
            flags, (struct nk_vec2i){adj_vres.x, adj_vres.y})) {

            char text[32];
            pf_snprintf(text, sizeof(text), "%d / %d", gbs.current, gbs.capacity);

            nk_layout_row_begin(ctx, NK_STATIC, 24, 3);
            nk_layout_row_push(ctx, 24);
            nk_image_texpath(ctx, s_garrison_icon_path);

            nk_layout_row_push(ctx, 2);
            nk_spacing(ctx, 1);

            nk_layout_row_push(ctx, 72);
            nk_label_colored(ctx, text, NK_TEXT_ALIGN_LEFT | NK_TEXT_ALIGN_MIDDLE, s_font_clr);
        }
        nk_end(ctx);
    });
    nk_style_pop_style_item(ctx);
}

static void filter_selection_garrison(const vec_entity_t *in_sel, vec_entity_t *out_sel)
{
    vec_entity_init(out_sel);
    for(int i = 0; i < vec_size(in_sel); i++) {

        uint32_t uid = vec_AT(in_sel, i);
        uint32_t flags = G_FlagsGet(uid);
        if(!(flags & ENTITY_FLAG_GARRISON))
            continue;
        vec_entity_push(out_sel, uid);
    }
}

static void garrison_selection(void)
{
    enum selection_type sel_type;
    const vec_entity_t *sel = G_Sel_Get(&sel_type);
    uint32_t target = G_Sel_GetHovered();

    if(sel_type != SELECTION_TYPE_PLAYER)
        return;

    vec_entity_t filtered;
    filter_selection_garrison(sel, &filtered);

    for(int i = 0; i < vec_size(&filtered); i++) {

        uint32_t curr = vec_AT(&filtered, i);
        G_Garrison_Enter(target, curr);
    }

    if(vec_size(&filtered) > 0) {
        Entity_Ping(target);
    }
    vec_entity_destroy(&filtered);
}

static void try_evict(vec2_t target)
{
    enum selection_type sel_type;
    const vec_entity_t *sel = G_Sel_Get(&sel_type);

    if(sel_type != SELECTION_TYPE_PLAYER)
        return;

    for(int i = 0; i < vec_size(sel); i++) {

        uint32_t curr = vec_AT(sel, i);
        uint32_t flags = G_FlagsGet(curr);
        if(!(flags & ENTITY_FLAG_GARRISONABLE))
            continue;
        G_Garrison_EvictAll(curr, target);
    }
}

static void on_mousedown(void *user, void *event)
{
    SDL_MouseButtonEvent *mouse_event = &(((SDL_Event*)event)->button);

    bool targeting = G_Garrison_InTargetMode();
    bool right = (mouse_event->button == SDL_BUTTON_RIGHT);
    bool left = (mouse_event->button == SDL_BUTTON_LEFT);
    bool evict = s_evict_on_lclick && left;
    s_evict_on_lclick = false;

    if(G_MouseOverMinimap())
        return;

    if(S_UI_MouseOverWindow(mouse_event->x, mouse_event->y))
        return;

    if(right && targeting)
        return;

    if(left && !targeting)
        return;

    int action = G_CurrContextualAction();
    if(right && (action != CTX_ACTION_GARRISON))
        return;

    if(right) {
        garrison_selection(); 
        return;
    }

    vec3_t mouse_coord;
    if(!M_MinimapMouseMapCoords(s_map, &mouse_coord)
    && !M_Raycast_MouseIntersecCoord(&mouse_coord))
        return;
    try_evict((vec2_t){mouse_coord.x, mouse_coord.z});
}

static bool can_garrison(uint32_t uid, uint32_t target)
{
    struct garrison_state *gus = gu_state_get(uid);
    struct garrisonable_state *gbs = gb_state_get(target);
    assert(gus && gbs);
    int capacity_left = gbs->capacity - gbs->current;
    return (capacity_left >= gus->capacity_consumed);
}

static void do_garrison(uint32_t uid, uint32_t target)
{
    struct garrison_state *gus = gu_state_get(uid);
    struct garrisonable_state *gbs = gb_state_get(target);
    assert(gus && gbs);

    /* Add the unit to the garrisonable's units */
    gbs->current += gus->capacity_consumed;
    vec_entity_push(&gbs->garrisoned, uid);

    /* Remove the garrisoned unit from the game simulation */
    G_Sel_Remove(uid);
    gus->state = STATE_GARRISONED;
    uint32_t flags = G_FlagsGet(uid);
    flags |= ENTITY_FLAG_GARRISONED;
    G_FlagsSet(uid, flags);
    G_Move_Unblock(uid);
    G_Pos_Garrison(uid);
}

static bool adjacent(uint32_t unit, uint32_t garrisonable)
{
    uint32_t flags = G_FlagsGet(garrisonable);
    float unit_radius = G_GetSelectionRadius(unit);
    float garrisonable_radius = G_GetSelectionRadius(garrisonable);
    vec2_t unit_pos = G_Pos_GetXZ(unit);
    vec2_t garrisonable_pos = G_Pos_GetXZ(garrisonable);

    if(flags & ENTITY_FLAG_MOVABLE) {
        return M_NavObjAdjacentToDynamicWith(s_map, unit_pos, 
            unit_radius, garrisonable_pos, 
            garrisonable_radius + GARRISON_THRESHOLD_DIST);
    }else{
        struct obb obb;
        Entity_CurrentOBB(garrisonable, &obb, true);
        return M_NavObjAdjacentToStaticWith(s_map, unit_pos, 
            unit_radius + GARRISON_THRESHOLD_DIST, &obb);
    }
}

static void on_20hz_tick(void *user, void *event)
{
    uint32_t uid;

    /* Process GARRISON entities */
    struct garrison_state *gu_state;
    kh_foreach_val_ptr(s_garrison_state_table, uid, gu_state, {
        switch(gu_state->state) {
        case STATE_GARRISONED:
        case STATE_NOT_GARRISONED:
            assert(!gu_state->target_rendevouz_issued);
            break;
        case STATE_MOVING_TO_GARRISONABLE: {
            if(G_Move_Still(uid)) {
                if(!G_EntityExists(gu_state->target) || G_EntityIsZombie(gu_state->target)) {
                    gu_state->target_rendevouz_issued = false;
                    gu_state->state = STATE_NOT_GARRISONED;
                    break;
                }
                float target_radius = G_GetSelectionRadius(uid);
                float garrison_thresh = target_radius * 1.5f;

                vec2_t ent_pos = G_Pos_GetXZ(uid);
                float ent_radius = G_GetSelectionRadius(uid);
                vec2_t target_pos = G_Pos_GetXZ(gu_state->target);
                enum nav_layer unit_layer = Entity_NavLayer(uid);
                enum nav_layer target_layer = Entity_NavLayer(gu_state->target);

                if(adjacent(uid, gu_state->target) && gu_state->wait_ticks > 0) {

                    if(!can_garrison(uid, gu_state->target)) {
                        gu_state->target_rendevouz_issued = false;
                        gu_state->state = STATE_NOT_GARRISONED;
                        break;
                    }
                    do_garrison(uid, gu_state->target); 
                    gu_state->wait_ticks = 0;
                    gu_state->target_rendevouz_issued = false;
                    gu_state->state = STATE_GARRISONED;
                    break;
                }

                struct garrisonable_state *target_state = gb_state_get(gu_state->target);
                /* We were not able to reach the garrisonable target 
                 */
                if(!target_state) {
                    gu_state->wait_ticks = 0;
                    gu_state->target_rendevouz_issued = false;
                    gu_state = STATE_NOT_GARRISONED;
                    break;
                }
                if(target_state->state == STATE_MOVING_TO_PICKUP_POINT) {
                    gu_state->wait_ticks = 0;
                    gu_state->state = STATE_AWAITING_PICKUP;
                    break;
                }
                /* Wait a few ticks to allow any transient conditions 
                 * to settle and avoid any ping-pong behaviour.
                 */
                gu_state->wait_ticks++;
                if(gu_state->wait_ticks < GARRISON_WAIT_TICKS)
                    break;

                /* The transport is stopped, possibly due to a new command
                 * from the player.
                 */
                if(target_state->state == STATE_IDLE) {
                    /* If it is reachable, retry going to its' location 
                     */
                    if(M_NavIsAdjacentToIsland(s_map, unit_layer, target_pos, 
                        garrison_thresh + GARRISON_THRESHOLD_DIST, ent_pos)) {
                        gu_state->wait_ticks = 0;
                        G_Garrison_Enter(gu_state->target, uid);
                        break;
                    }
                }
                /* Otherwise, call it quits.
                 */
                gu_state->wait_ticks = 0;
                gu_state->target_rendevouz_issued = false;
                gu_state->state = STATE_NOT_GARRISONED;
            }
            break;
        }
        case STATE_AWAITING_PICKUP: {
            struct garrisonable_state *target_state = gb_state_get(gu_state->target);
            if(!target_state) {
                gu_state->target_rendevouz_issued = false;
                gu_state->state = STATE_NOT_GARRISONED;
                break;
            }
            if(target_state->state == STATE_IDLE) {
                gu_state->state = STATE_MOVING_TO_GARRISONABLE;
                break;
            }
            break;
        }
        default: assert(0);
        }
    });

    /* Process GARRISONABLE entities */
    struct garrisonable_state *gb_state;
    kh_foreach_val_ptr(s_garrisonable_state_table, uid, gb_state, {

        enum nav_layer garrisonable_layer = Entity_NavLayer(uid);
        float garrisonable_radius = G_GetSelectionRadius(uid);
        vec2_t garrisonable_pos = G_Pos_GetXZ(uid);

        switch(gb_state->state) {
        case STATE_IDLE:
            break;
        case STATE_MOVING_TO_PICKUP_POINT: {

            vec2_t delta;
            PFM_Vec2_Sub(&gb_state->rendevouz_point_transport, &garrisonable_pos, &delta);
            const float tolerance = garrisonable_radius * 1.5f;

            if(G_Move_Still(uid)) {

                if(M_NavIsMaximallyClose(s_map, garrisonable_layer, garrisonable_pos, 
                    gb_state->rendevouz_point_transport, tolerance)
                    || PFM_Vec2_Len(&delta) <= tolerance){
                    gb_state->state = STATE_IDLE;
                    gb_state->wait_ticks = 0;
                    break;
                }
                gb_state->wait_ticks++;
                if(gb_state->wait_ticks == GARRISONABLE_WAIT_TICKS) {
                    G_Move_SetDest(uid, gb_state->rendevouz_point_transport, false);
                }
            }
            break;
        }
        case STATE_MOVING_TO_DROPOFF_POINT: {

            uint32_t garrisonable_flags = G_FlagsGet(uid);
            enum nav_layer garrisonable_layer = Entity_NavLayer(uid);
            float garrisonable_radius = G_GetSelectionRadius(uid);
            vec2_t garrisonable_pos = G_Pos_GetXZ(uid);

            uint32_t first = vec_AT(&gb_state->garrisoned, 0);
            enum nav_layer target_layer = Entity_NavLayer(first);

            vec2_t delta;
            PFM_Vec2_Sub(&gb_state->rendevouz_point_transport, &garrisonable_pos, &delta);
            const float tolerance = garrisonable_radius * 1.5f;

            if(G_Move_Still(uid)) {

                if((garrisonable_flags & ENTITY_FLAG_AIR)
                && (M_NavIsMaximallyClose(s_map, garrisonable_layer, garrisonable_pos,
                    gb_state->evict_target, tolerance + GARRISON_BUFFER_DIST)
                    || PFM_Vec2_Len(&delta) < tolerance + GARRISON_BUFFER_DIST)) {

                    gb_state->state = STATE_IDLE;
                    gb_state->wait_ticks = 0;
                    G_Garrison_EvictAll(uid, gb_state->evict_target);
                    break;
                }

                if((garrisonable_flags & ENTITY_FLAG_WATER)
                && M_NavIsAdjacentToIsland(s_map, target_layer, garrisonable_pos,
                    tolerance + GARRISON_BUFFER_DIST, gb_state->evict_target)){

                    gb_state->state = STATE_IDLE;
                    gb_state->wait_ticks = 0;
                    G_Garrison_EvictAll(uid, gb_state->evict_target);
                    break;
                }
                gb_state->wait_ticks++;
                if(gb_state->wait_ticks == GARRISONABLE_WAIT_TICKS) {
                    /* Retry */
                    gb_state->wait_ticks = 0;
                    G_Move_SetDest(uid, gb_state->evict_target, false);
                }
            }
            break;
        }
        default: assert(0);
        }
    });
}

static bool compare_uids(uint32_t *a, uint32_t *b)
{
    return *a == *b;
}

static bool compare_evict_work(struct evict_work *a, struct evict_work *b)
{
    return a->uid == b->uid;
}

static struct result evict_task(void *arg)
{
    ASSERT_IN_MAIN_THREAD();

    struct evict_work *work = arg;
    struct garrisonable_state *gbs = gb_state_get(work->uid);
    if(!gbs)
        goto out;

    vec_evict_push(&s_evicting, *work);

    struct garrisonable_state copy = *gbs;
    for(int i = 0; i < vec_size(&copy.garrisoned); i++) {
        uint32_t curr = vec_AT(&copy.garrisoned, i);
        G_Garrison_Evict(work->uid, curr, work->target);
        Task_Sleep(EVICT_DELAY_MS);
    }

    int idx = vec_evict_indexof(&s_evicting, *work, compare_evict_work);
    if(idx != -1) {
        vec_evict_del(&s_evicting, idx);
    }

out:
    free(arg);
    return NULL_RESULT;
}

static bool transport_move(uint32_t garrisonable, vec2_t target)
{
    struct garrisonable_state *gbs = gb_state_get(garrisonable);
    if(!gbs)
        return false;

    if(vec_size(&gbs->garrisoned) == 0)
        return false;

    uint32_t first = vec_AT(&gbs->garrisoned, 0);
    enum nav_layer target_layer = Entity_NavLayer(first);
    enum nav_layer transport_layer = Entity_NavLayer(garrisonable);

    vec2_t garrisonable_pos = G_Pos_GetXZ(garrisonable);
    float garrisonable_radius = G_GetSelectionRadius(garrisonable);
    uint32_t garrisonable_flags = G_FlagsGet(garrisonable);
    uint32_t unit_flags = G_FlagsGet(first);

    /* For water/air transports, the transport should first 
     * come adjacent to the targeted "island" and only subsequently
     * evict the units.
     */
    bool water_transport_should_rendevouz = 
         ((garrisonable_flags & (ENTITY_FLAG_WATER | ENTITY_FLAG_MOVABLE)) == (ENTITY_FLAG_WATER | ENTITY_FLAG_MOVABLE))
     &&  !(unit_flags & ENTITY_FLAG_WATER);

    bool air_transport_should_rendevouz = 
         ((garrisonable_flags & (ENTITY_FLAG_AIR | ENTITY_FLAG_MOVABLE)) == (ENTITY_FLAG_AIR | ENTITY_FLAG_MOVABLE))
     &&  !(unit_flags & ENTITY_FLAG_AIR);

    vec2_t delta;
    PFM_Vec2_Sub(&target, &garrisonable_pos, &delta);
    float distance = PFM_Vec2_Len(&delta);
    float tolerance = garrisonable_radius * 1.5f;

    if((water_transport_should_rendevouz
        && !M_NavIsAdjacentToIsland(s_map, target_layer, garrisonable_pos, tolerance, target)) 
    || (air_transport_should_rendevouz
        && (!M_NavIsMaximallyClose(s_map, transport_layer, garrisonable_pos, target, tolerance)
            && distance > tolerance))) {

        if(gbs->state == STATE_MOVING_TO_DROPOFF_POINT) {

            vec2_t delta;
            PFM_Vec2_Sub(&gbs->evict_target, &target, &delta);
            if(PFM_Vec2_Len(&delta) < EPSILON)
                return false;
        }

        gbs->state = STATE_MOVING_TO_DROPOFF_POINT;
        gbs->evict_target = target;

        G_StopEntity(garrisonable, true, false);
        G_Move_SetDest(garrisonable, target, false);
        return true;
    }
    return false;
}

static bool save_color(struct nk_color clr, SDL_RWops *stream)
{
    struct attr clr_r = (struct attr){
        .type = TYPE_INT,
        .val.as_int = clr.r
    };
    CHK_TRUE_RET(Attr_Write(stream, &clr_r, "clr_r"));

    struct attr clr_g = (struct attr){
        .type = TYPE_INT,
        .val.as_int = clr.g
    };
    CHK_TRUE_RET(Attr_Write(stream, &clr_g, "clr_g"));

    struct attr clr_b = (struct attr){
        .type = TYPE_INT,
        .val.as_int = clr.b
    };
    CHK_TRUE_RET(Attr_Write(stream, &clr_b, "clr_b"));

    struct attr clr_a = (struct attr){
        .type = TYPE_INT,
        .val.as_int = clr.a
    };
    CHK_TRUE_RET(Attr_Write(stream, &clr_a, "clr_a"));

    return true;
}

static bool load_color(struct nk_color *out, SDL_RWops *stream)
{
    struct attr attr;

    CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
    CHK_TRUE_RET(attr.type == TYPE_INT);
    out->r = attr.val.as_int;

    CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
    CHK_TRUE_RET(attr.type == TYPE_INT);
    out->g = attr.val.as_int;

    CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
    CHK_TRUE_RET(attr.type == TYPE_INT);
    out->b = attr.val.as_int;

    CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
    CHK_TRUE_RET(attr.type == TYPE_INT);
    out->a = attr.val.as_int;

    return true;
}

/*****************************************************************************/
/* EXTERN FUNCTIONS                                                          */
/*****************************************************************************/

bool G_Garrison_Init(const struct map *map)
{
    if((s_garrison_state_table = kh_init(garrison)) == NULL)
        goto fail_garrison;
    if((s_garrisonable_state_table = kh_init(garrisonable)) == NULL)
        goto fail_garrisonable;
    vec_evict_init(&s_evicting);

    struct nk_context ctx;
    nk_style_default(&ctx);
    s_bg_style = ctx.style.window.fixed_background;
    s_font_clr = ctx.style.text.color;

    E_Global_Register(EVENT_UPDATE_UI, on_update_ui, NULL, 
        G_RUNNING | G_PAUSED_UI_RUNNING | G_PAUSED_FULL);
    E_Global_Register(SDL_MOUSEBUTTONDOWN, on_mousedown, NULL, G_RUNNING);
    E_Global_Register(EVENT_20HZ_TICK, on_20hz_tick, NULL, G_RUNNING);

    s_map = map;
    return true;

fail_garrisonable:
    kh_destroy(garrison, s_garrison_state_table);
fail_garrison:
    return false;
}

void G_Garrison_Shutdown(void)
{
    E_Global_Unregister(EVENT_20HZ_TICK, on_20hz_tick);
    E_Global_Unregister(SDL_MOUSEBUTTONDOWN, on_mousedown);
    E_Global_Unregister(EVENT_UPDATE_UI, on_update_ui);
    vec_evict_destroy(&s_evicting);
    kh_destroy(garrisonable, s_garrisonable_state_table);
    kh_destroy(garrison, s_garrison_state_table);
}

bool G_Garrison_AddGarrison(uint32_t uid)
{
    struct garrison_state gus;
    gus.capacity_consumed = 1;
    gus.target = NULL_UID;
    gus.target_rendevouz_issued = false;
    gus.state = STATE_NOT_GARRISONED;
    gus.wait_ticks = 0;
    return gu_state_set(uid, gus);
}

void G_Garrison_RemoveGarrison(uint32_t uid)
{
    gu_state_remove(uid);
}

bool G_Garrison_AddGarrisonable(uint32_t uid)
{
    struct garrisonable_state gbs;
    gbs.state = STATE_IDLE;
    gbs.wait_ticks = 0;
    gbs.capacity = 0;
    gbs.current = 0;
    vec_entity_init(&gbs.garrisoned);
    return gb_state_set(uid, gbs);
}

void G_Garrison_RemoveGarrisonable(uint32_t uid)
{
    gb_state_remove(uid);
}

void G_Garrison_SetCapacityConsumed(uint32_t uid, int capacity)
{
    struct garrison_state *gus = gu_state_get(uid);
    assert(gus);
    gus->capacity_consumed = capacity;
}

int G_Garrison_GetCapacityConsumed(uint32_t uid)
{
    struct garrison_state *gus = gu_state_get(uid);
    assert(gus);
    return gus->capacity_consumed;
}

void G_Garrison_SetGarrisonableCapacity(uint32_t uid, int capacity)
{
    struct garrisonable_state *gbs = gb_state_get(uid);
    assert(gbs);
    gbs->capacity = capacity;
}

int G_Garrison_GetGarrisonableCapacity(uint32_t uid)
{
    struct garrisonable_state *gbs = gb_state_get(uid);
    assert(gbs);
    return gbs->capacity;
}

int G_Garrison_GetCurrentGarrisoned(uint32_t uid)
{
    struct garrisonable_state *gbs = gb_state_get(uid);
    assert(gbs);
    return gbs->current;
}

bool G_Garrison_Enter(uint32_t garrisonable, uint32_t unit)
{
    /* In cases where land units are ordered inside a water-based transport, the 
     * transport should "automatically" go to the shore to pick up the units
     */
    struct garrisonable_state *gbs = gb_state_get(garrisonable);
    struct garrison_state *gus = gu_state_get(unit);
    assert(gbs && gus);

    vec2_t unit_pos = G_Pos_GetXZ(unit);
    enum nav_layer unit_layer = Entity_NavLayer(unit);
    uint32_t unit_flags = G_FlagsGet(unit);

    uint32_t garrisonable_flags = G_FlagsGet(garrisonable);
    vec2_t garrisonable_pos = G_Pos_GetXZ(garrisonable);
    enum nav_layer garrisonable_layer = Entity_NavLayer(garrisonable);
    float garrisonable_radius = G_GetSelectionRadius(garrisonable);

    bool has_rendevouz_point = false;
    vec2_t rendevouz_point;
    vec2_t rendevouz_point_transport;

    bool water_transport_should_rendevouz = 
         ((garrisonable_flags & (ENTITY_FLAG_WATER | ENTITY_FLAG_MOVABLE)) == (ENTITY_FLAG_WATER | ENTITY_FLAG_MOVABLE))
     &&  !(unit_flags & ENTITY_FLAG_WATER);

    bool air_transport_should_rendevouz = 
         ((garrisonable_flags & (ENTITY_FLAG_AIR | ENTITY_FLAG_MOVABLE)) == (ENTITY_FLAG_AIR | ENTITY_FLAG_MOVABLE))
     &&  !(unit_flags & ENTITY_FLAG_AIR);

    if(water_transport_should_rendevouz || air_transport_should_rendevouz) {

        if(M_NavIsAdjacentToIsland(s_map, unit_layer, garrisonable_pos,
            garrisonable_radius * 1.5f, unit_pos)) {

            G_StopEntity(garrisonable, true, false);

        }else if(gbs->state == STATE_MOVING_TO_PICKUP_POINT) {

            rendevouz_point = gbs->rendevouz_point_unit;
            rendevouz_point_transport = gbs->rendevouz_point_transport;
            has_rendevouz_point = true;
        }else{

            rendevouz_point = M_NavClosestPointAdjacentToIsland(s_map, 
                garrisonable_pos, unit_pos, unit_layer);
            rendevouz_point_transport = M_NavClosestReachableDest(s_map, garrisonable_layer, 
                garrisonable_pos, rendevouz_point);

            vec2_t delta;
            PFM_Vec2_Sub(&rendevouz_point_transport, &garrisonable_pos, &delta);
            const float tolerance = garrisonable_radius * 1.5f;

            if(!M_NavIsMaximallyClose(s_map, garrisonable_layer, garrisonable_pos, 
                rendevouz_point_transport, tolerance)
                && (PFM_Vec2_Len(&delta) > tolerance)){
                has_rendevouz_point = true;
            }
        }
    }

    if(has_rendevouz_point && !gus->target_rendevouz_issued) {
        G_StopEntity(garrisonable, true, false);
        G_Move_SetDest(garrisonable, rendevouz_point, false);

        gbs->state = STATE_MOVING_TO_PICKUP_POINT;
        gbs->rendevouz_point_unit = rendevouz_point;
        gbs->rendevouz_point_transport = rendevouz_point_transport;
    }

    gus->target = garrisonable;
    gus->target_rendevouz_issued = true;
    gus->state = STATE_MOVING_TO_GARRISONABLE;

    vec2_t unit_target_pos = garrisonable_pos;
    if(has_rendevouz_point) {
        unit_target_pos = rendevouz_point;
    }

    G_StopEntity(unit, false, false);
    if(M_NavLocationsReachable(s_map, unit_layer, unit_pos, garrisonable_pos)) {
        G_Move_SetSurroundEntity(unit, garrisonable);
    }else{
        G_Move_SetDest(unit, unit_target_pos, false);
    }
    return true;
}

bool G_Garrison_Evict(uint32_t garrisonable, uint32_t unit, vec2_t target)
{
    struct garrison_state *gus = gu_state_get(unit);
    if(!gus)
        return false;

    struct garrisonable_state *gbs = gb_state_get(garrisonable);
    if(!gbs)
        return false;

    int idx = vec_entity_indexof(&gbs->garrisoned, unit, compare_uids);
    if(idx == -1)
        return false;

    enum nav_layer target_layer = Entity_NavLayer(unit);
    vec2_t garrisonable_pos = G_Pos_GetXZ(garrisonable);
    float garrisonable_radius = G_GetSelectionRadius(garrisonable);
    uint32_t garrisonable_flags = G_FlagsGet(garrisonable);
    uint32_t unit_flags = G_FlagsGet(unit);

    vec2_t closest;
    if(!M_NavClosestPathable(s_map, target_layer, garrisonable_pos, &closest))
        return false;

    /* Check if we are able to evict the unit */
    if(garrisonable_flags & ENTITY_FLAG_BUILDING) {

        struct obb obb;
        Entity_CurrentOBB(garrisonable, &obb, true);
        if(!M_NavObjAdjacentToStaticWith(s_map, closest, GARRISON_THRESHOLD_DIST, &obb))
            return false;
    }else{

        vec2_t delta;
        PFM_Vec2_Sub(&closest, &garrisonable_pos, &delta);
        float distance = PFM_Vec2_Len(&delta);

        float garrisonable_radius = G_GetSelectionRadius(garrisonable);
        float unit_radius = G_GetSelectionRadius(unit);
        float threshold = garrisonable_radius + unit_radius + GARRISON_THRESHOLD_DIST;
        if(distance > threshold)
            return false;
    }

    /* Now it is certain that eviction can take place */
    int capacity_consumed = gus->capacity_consumed;
    vec_entity_del(&gbs->garrisoned, idx);
    gbs->current -= capacity_consumed;

    /* Place the evicted unit at the closest location and issue it a move order */
    uint32_t flags = G_FlagsGet(unit);
    flags &= ~ENTITY_FLAG_GARRISONED;
    G_FlagsSet(unit, flags);

    vec3_t pos = (vec3_t){
        closest.x,
        M_HeightAtPoint(s_map, closest),
        closest.z
    };

    G_Pos_Ungarrison(unit, pos);
    G_Move_BlockAt(unit, pos);
    G_Move_SetDest(unit, target, false);

    return true;
}

bool G_Garrison_EvictAll(uint32_t garrisonable, vec2_t target)
{
    if(transport_move(garrisonable, target))
        return true;
    struct evict_work *work = malloc(sizeof(struct evict_work));
    if(!work)
        return false;
    work->uid = garrisonable;
    work->target = target;
    work->tid = Sched_Create(16, evict_task, work, NULL, TASK_MAIN_THREAD_PINNED | TASK_BIG_STACK);
    if(work->tid == NULL_TID) {
        free(work);
        return false;
    }
    Sched_RunSync(work->tid);
    return true;
}

void G_Garrison_SetFontColor(const struct nk_color *clr)
{
    s_font_clr = *clr;
}

void G_Garrison_SetIcon(const char *path)
{
    size_t len = strlen(path) + 1;
    size_t buffsize = sizeof(s_garrison_icon_path);
    size_t copysize = len < buffsize ? len : buffsize;
    pf_strlcpy(s_garrison_icon_path, path, copysize);
}

void G_Garrison_SetBackgroundStyle(const struct nk_style_item *item)
{
    s_bg_style = *item;
}

void G_Garrison_SetShowUI(bool show)
{
    s_show_ui = show;
}

int G_Garrison_CurrContextualAction(void)
{
    uint32_t hovered = G_Sel_GetHovered();
    if(!G_EntityExists(hovered))
        return CTX_ACTION_NONE;

    if(M_MouseOverMinimap(s_map))
        return CTX_ACTION_NONE;

    if(!(G_FlagsGet(hovered) & ENTITY_FLAG_GARRISONABLE))
        return CTX_ACTION_NONE;

    int mouse_x, mouse_y;
    SDL_GetMouseState(&mouse_x, &mouse_y);
    if(S_UI_MouseOverWindow(mouse_x, mouse_y))
        return CTX_ACTION_NONE;

    enum selection_type sel_type;
    const vec_entity_t *sel = G_Sel_Get(&sel_type);

    vec_entity_t filtered;
    filter_selection_garrison(sel, &filtered);

    if(vec_size(&filtered) == 0 || sel_type != SELECTION_TYPE_PLAYER) {
        vec_entity_destroy(&filtered);
        return CTX_ACTION_NONE;
    }

    uint32_t first = vec_AT(&filtered, 0);
    if(G_GetFactionID(hovered) != G_GetFactionID(first)) {
        vec_entity_destroy(&filtered);
        return CTX_ACTION_NONE;
    }

    vec_entity_destroy(&filtered);
    return CTX_ACTION_GARRISON;
}

bool G_Garrison_InTargetMode(void)
{
    return s_evict_on_lclick;
}

void G_Garrison_SetEvictOnLeftClick(void)
{
    s_evict_on_lclick = true;
}

void G_Garrison_Stop(uint32_t uid)
{
    ASSERT_IN_MAIN_THREAD();

    uint32_t flags = G_FlagsGet(uid);
    if(flags & ENTITY_FLAG_GARRISON) {
        struct garrison_state *gus = gu_state_get(uid);
        assert(gus);
        if(gus->state != STATE_GARRISONED) {
            gus->target_rendevouz_issued = false;
            gus->state = STATE_NOT_GARRISONED;
            gus->wait_ticks = 0;
        }
    }
    if(flags & ENTITY_FLAG_GARRISONABLE) {
        struct garrisonable_state *gbs = gb_state_get(uid);
        assert(gbs);
        gbs->state = STATE_IDLE;
        gbs->wait_ticks = 0;
    }
}

void G_Garrison_GetUnits(uint32_t uid, vec_entity_t *out)
{
    struct garrisonable_state *gbs = gb_state_get(uid);
    assert(gbs);
    vec_entity_copy(out, &gbs->garrisoned);
}

void G_Garrison_ClearGarrison(uint32_t uid)
{
    struct garrisonable_state *gbs = gb_state_get(uid);
    assert(gbs);
    vec_entity_reset(&gbs->garrisoned);
}

bool G_Garrison_SaveState(struct SDL_RWops *stream)
{
    struct attr num_ents = (struct attr){
        .type = TYPE_INT,
        .val.as_int = kh_size(s_garrison_state_table)
    };
    CHK_TRUE_RET(Attr_Write(stream, &num_ents, "num_ents"));
    Sched_TryYield();

    uint32_t key;
    struct garrison_state curr_gus;
    struct garrisonable_state curr_gbs;

    kh_foreach(s_garrison_state_table, key, curr_gus, {

        struct attr uid = (struct attr){
            .type = TYPE_INT,
            .val.as_int = key
        };
        CHK_TRUE_RET(Attr_Write(stream, &uid, "uid"));

        struct attr cap_consumed = (struct attr){
            .type = TYPE_INT,
            .val.as_int = curr_gus.capacity_consumed
        };
        CHK_TRUE_RET(Attr_Write(stream, &cap_consumed, "capacity_consumed"));

        struct attr target = (struct attr){
            .type = TYPE_INT,
            .val.as_int = curr_gus.target
        };
        CHK_TRUE_RET(Attr_Write(stream, &target, "target"));

        struct attr target_issued = (struct attr){
            .type = TYPE_BOOL,
            .val.as_bool = curr_gus.target_rendevouz_issued
        };
        CHK_TRUE_RET(Attr_Write(stream, &target_issued, "target_rendevouz_issued"));

        struct attr state = (struct attr){
            .type = TYPE_INT,
            .val.as_int = curr_gus.state
        };
        CHK_TRUE_RET(Attr_Write(stream, &state, "state"));

        struct attr wait_ticks = (struct attr){
            .type = TYPE_INT,
            .val.as_int = curr_gus.wait_ticks
        };
        CHK_TRUE_RET(Attr_Write(stream, &wait_ticks, "wait_ticks"));
        Sched_TryYield();
    });

    struct attr num_garrisonable_ents = (struct attr){
        .type = TYPE_INT,
        .val.as_int = kh_size(s_garrisonable_state_table)
    };
    CHK_TRUE_RET(Attr_Write(stream, &num_garrisonable_ents, "num_ents"));
    Sched_TryYield();

    kh_foreach(s_garrisonable_state_table, key, curr_gbs, {

        struct attr uid = (struct attr){
            .type = TYPE_INT,
            .val.as_int = key
        };
        CHK_TRUE_RET(Attr_Write(stream, &uid, "uid"));

        struct attr state = (struct attr){
            .type = TYPE_INT,
            .val.as_int = curr_gbs.state
        };
        CHK_TRUE_RET(Attr_Write(stream, &state, "state"));

        struct attr evict_target = (struct attr){
            .type = TYPE_VEC2,
            .val.as_vec2 = curr_gbs.evict_target
        };
        CHK_TRUE_RET(Attr_Write(stream, &evict_target, "evict_target"));

        struct attr rendevouz_point_unit = (struct attr){
            .type = TYPE_VEC2,
            .val.as_vec2 = curr_gbs.rendevouz_point_unit
        };
        CHK_TRUE_RET(Attr_Write(stream, &rendevouz_point_unit, "rendevouz_point_unit"));

        struct attr rendevouz_point_transport = (struct attr){
            .type = TYPE_VEC2,
            .val.as_vec2 = curr_gbs.rendevouz_point_transport
        };
        CHK_TRUE_RET(Attr_Write(stream, &rendevouz_point_transport, "rendevouz_point_transport"));

        struct attr wait_ticks = (struct attr){
            .type = TYPE_INT,
            .val.as_int = curr_gbs.wait_ticks
        };
        CHK_TRUE_RET(Attr_Write(stream, &wait_ticks, "wait_ticks"));

        struct attr capacity = (struct attr){
            .type = TYPE_INT,
            .val.as_int = curr_gbs.capacity
        };
        CHK_TRUE_RET(Attr_Write(stream, &capacity, "capacity"));

        struct attr current = (struct attr){
            .type = TYPE_INT,
            .val.as_int = curr_gbs.current
        };
        CHK_TRUE_RET(Attr_Write(stream, &current, "current"));

        struct attr garrisoned_size = (struct attr){
            .type = TYPE_INT,
            .val.as_int = vec_size(&curr_gbs.garrisoned)
        };
        CHK_TRUE_RET(Attr_Write(stream, &garrisoned_size, "garrisoned_size"));
        Sched_TryYield();

        for(int i = 0; i < vec_size(&curr_gbs.garrisoned); i++) {
            uint32_t curr = vec_AT(&curr_gbs.garrisoned, i);
            struct attr uid = (struct attr){
                .type = TYPE_INT,
                .val.as_int = curr
            };
            CHK_TRUE_RET(Attr_Write(stream, &uid, "garrisoned_uid"));
        }
        Sched_TryYield();
    });

    struct attr garrison_icon_path = (struct attr){
        .type = TYPE_STRING
    };
    pf_strlcpy(garrison_icon_path.val.as_string, s_garrison_icon_path,
        sizeof(garrison_icon_path.val.as_string));
    CHK_TRUE_RET(Attr_Write(stream, &garrison_icon_path, "garrison_icon_path"));

    struct attr bg_style_type = (struct attr){
        .type = TYPE_INT,
        .val.as_int = s_bg_style.type
    };
    CHK_TRUE_RET(Attr_Write(stream, &bg_style_type, "bg_style_type"));
    Sched_TryYield();

    switch(s_bg_style.type) {
    case NK_STYLE_ITEM_COLOR: {

        CHK_TRUE_RET(save_color(s_bg_style.data.color, stream));
        break;
    }
    case NK_STYLE_ITEM_TEXPATH: {

        struct attr bg_texpath = (struct attr){ .type = TYPE_STRING };
        pf_strlcpy(bg_texpath.val.as_string, s_bg_style.data.texpath, 
            sizeof(bg_texpath.val.as_string));
        CHK_TRUE_RET(Attr_Write(stream, &bg_texpath, "bg_texpath"));
        break;
    }
    default: assert(0);
    }

    CHK_TRUE_RET(save_color(s_font_clr, stream));
    Sched_TryYield();

    struct attr ui_shown = (struct attr){
        .type = TYPE_BOOL,
        .val.as_bool = s_show_ui
    };
    CHK_TRUE_RET(Attr_Write(stream, &ui_shown, "ui_shown"));
    Sched_TryYield();

    struct attr num_evicting = (struct attr){
        .type = TYPE_INT,
        .val.as_int = vec_size(&s_evicting)
    };
    CHK_TRUE_RET(Attr_Write(stream, &num_evicting, "num_evicting"));

    for(int i = 0; i < vec_size(&s_evicting); i++) {

        struct evict_work curr = vec_AT(&s_evicting, i);

        struct attr uid = (struct attr){
            .type = TYPE_INT,
            .val.as_int = curr.uid
        };
        CHK_TRUE_RET(Attr_Write(stream, &uid, "evicting_uid"));

        struct attr target = (struct attr){
            .type = TYPE_VEC2,
            .val.as_vec2 = curr.target
        };
        CHK_TRUE_RET(Attr_Write(stream, &target, "evicting_target"));
    }
    Sched_TryYield();

    return true;
}

bool G_Garrison_LoadState(struct SDL_RWops *stream)
{
    struct attr attr;
    CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
    CHK_TRUE_RET(attr.type == TYPE_INT);
    const size_t num_ents = attr.val.as_int;
    Sched_TryYield();

    for(int i = 0; i < num_ents; i++) {

        uint32_t uid;

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_INT);
        uid = attr.val.as_int;
        CHK_TRUE_RET(G_EntityExists(attr.val.as_int));

        struct garrison_state *gus = gu_state_get(uid);

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_INT);
        gus->capacity_consumed = attr.val.as_int;

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_INT);
        gus->target = attr.val.as_int;

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_BOOL);
        gus->target_rendevouz_issued = attr.val.as_bool;

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_INT);
        gus->state = attr.val.as_int;

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_INT);
        gus->wait_ticks = attr.val.as_int;
        Sched_TryYield();
    }

    CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
    CHK_TRUE_RET(attr.type == TYPE_INT);
    const size_t num_garrisonable = attr.val.as_int;
    Sched_TryYield();

    for(int i = 0; i < num_garrisonable; i++) {

        uint32_t uid;

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_INT);
        uid = attr.val.as_int;
        CHK_TRUE_RET(G_EntityExists(attr.val.as_int));

        struct garrisonable_state *gbs = gb_state_get(uid);

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_INT);
        gbs->state = attr.val.as_int;

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_VEC2);
        gbs->evict_target = attr.val.as_vec2;

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_VEC2);
        gbs->rendevouz_point_unit = attr.val.as_vec2;

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_VEC2);
        gbs->rendevouz_point_transport = attr.val.as_vec2;

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_INT);
        gbs->wait_ticks = attr.val.as_int;

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_INT);
        gbs->capacity = attr.val.as_int;

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_INT);
        gbs->current = attr.val.as_int;

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_INT);
        const size_t garrisoned_size = attr.val.as_int;
        Sched_TryYield();

        for(int i = 0; i < garrisoned_size; i++) {

            CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
            CHK_TRUE_RET(attr.type == TYPE_INT);
            uint32_t uid = attr.val.as_int;
            vec_entity_push(&gbs->garrisoned, uid);
        }
        Sched_TryYield();
    }

    CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
    CHK_TRUE_RET(attr.type == TYPE_STRING);
    pf_strlcpy(s_garrison_icon_path, attr.val.as_string, sizeof(s_garrison_icon_path));

    CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
    CHK_TRUE_RET(attr.type == TYPE_INT);
    s_bg_style.type = attr.val.as_int;

    switch(s_bg_style.type) {
    case NK_STYLE_ITEM_COLOR: {

        CHK_TRUE_RET(load_color(&s_bg_style.data.color, stream));
        break;
    }
    case NK_STYLE_ITEM_TEXPATH: {

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_STRING);
        pf_strlcpy(s_bg_style.data.texpath, attr.val.as_string, sizeof(s_bg_style.data.texpath));
        break;
    }
    default: 
        return false;
    }

    CHK_TRUE_RET(load_color(&s_font_clr, stream));

    CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
    CHK_TRUE_RET(attr.type == TYPE_BOOL);
    s_show_ui = attr.val.as_bool;
    Sched_TryYield();

    CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
    CHK_TRUE_RET(attr.type == TYPE_INT);
    const size_t num_evicting = attr.val.as_int;

    for(int i = 0; i < num_evicting; i++) {
    
        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_INT);
        uint32_t uid = attr.val.as_int;

        CHK_TRUE_RET(Attr_Parse(stream, &attr, true));
        CHK_TRUE_RET(attr.type == TYPE_VEC2);
        vec2_t target = attr.val.as_vec2;

        G_Garrison_EvictAll(uid, target);
    }
    return true;
}

