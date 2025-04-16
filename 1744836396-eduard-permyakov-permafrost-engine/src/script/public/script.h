/*
 *  This file is part of Permafrost Engine. 
 *  Copyright (C) 2017-2023 Eduard Permyakov 
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

#ifndef SCRIPT_H
#define SCRIPT_H

#include "../../scene.h"
#include "../../pf_math.h"

#include <stdio.h>
#include <stdbool.h>
#include <SDL.h> /* for SDL_RWops */

/* 'Handle' type to let the rest of the engine hold on to scripting objects 
 * without needing to include Python.h */
typedef void *script_opaque_t;

enum eventtype;
struct nk_context;
struct future;

/*###########################################################################*/
/* SCRIPT GENERAL                                                            */
/*###########################################################################*/

bool            S_Init(const char *progname, const char *base_path, struct nk_context *ctx);
void            S_Shutdown(void);
bool            S_RunFile(const char *path, int argc, char **argv);
void            S_RunFileAsync(const char *path, int argc, char **argv, struct future *result);
bool            S_GetFilePath(char *out, size_t maxout);
void            S_ShowLastError(void);

void            S_RunEventHandler(script_opaque_t callable, script_opaque_t user_arg, 
                                  void *event_arg);

void            S_Retain(script_opaque_t obj);
/* Decrement reference count for Python objects. 
 * No-op in the case of a NULL-pointer passed in */
void            S_Release(script_opaque_t obj);
script_opaque_t S_WrapEngineEventArg(int eventnum, void *arg);
/* Returns 'arg' if this is not a weakref object. Otherwise, return a borrowed
 * reference extracted from the weakref. */
script_opaque_t S_UnwrapIfWeakref(script_opaque_t arg);
bool            S_WeakrefDied(script_opaque_t arg);
bool            S_ObjectsEqual(script_opaque_t a, script_opaque_t b);
/* This value is not persistent accross sessions - careful */
uint64_t        S_ScriptTypeID(uint32_t uid);
int             S_FormationPriority(uint32_t uid);

void            S_ClearState(void);
bool            S_SaveState(SDL_RWops *stream);
bool            S_LoadState(SDL_RWops *stream);

void            S_Task_MaybeExit(void);
void            S_Task_MaybeEnter(void);

/*###########################################################################*/
/* SCRIPT UI                                                                 */
/*###########################################################################*/

bool            S_UI_MouseOverWindow(int mouse_x, int mouse_y);
bool            S_UI_TextEditHasFocus(void);

/*###########################################################################*/
/* SCRIPT ENTITY                                                             */
/*###########################################################################*/

script_opaque_t S_Entity_ObjFromAtts(const char *path, const char *name,
                                     const khash_t(attr) *attr_table, 
                                     const vec_attr_t *construct_args);
bool            S_Entity_UIDForObj(script_opaque_t, uint32_t *out);
script_opaque_t S_Entity_ObjForUID(uint32_t uid);
uint64_t        S_Entity_TypeID(script_opaque_t obj);

/*###########################################################################*/
/* SCRIPT REGION                                                             */
/*###########################################################################*/

void            S_Region_NotifyContentsChanged(const char *name);
script_opaque_t S_Region_ObjFromAtts(const char *name, int type, vec2_t pos, 
                                     float radius, float xlen, float zlen);

/*###########################################################################*/
/* SCRIPT CAMERA                                                             */
/*###########################################################################*/

script_opaque_t S_Camera_ObjFromAtts(const char *name, vec3_t pos, 
                                     float pitch, float yaw);

#endif

