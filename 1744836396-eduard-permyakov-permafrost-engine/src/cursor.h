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

#ifndef CURSOR_H
#define CURSOR_H

#include <stdbool.h>

struct SDL_RWops;

enum cursortype{
    CURSOR_POINTER = 0,
    CURSOR_SCROLL_TOP,
    CURSOR_SCROLL_TOP_RIGHT,
    CURSOR_SCROLL_RIGHT,
    CURSOR_SCROLL_BOT_RIGHT,
    CURSOR_SCROLL_BOT,
    CURSOR_SCROLL_BOT_LEFT,
    CURSOR_SCROLL_LEFT,
    CURSOR_SCROLL_TOP_LEFT,
    CURSOR_TARGET,
    CURSOR_ATTACK,
    CURSOR_NO_ATTACK,
    CURSOR_BUILD,
    CURSOR_DROP_OFF,
    CURSOR_TRANSPORT,
    CURSOR_GARRISON,
    _CURSOR_MAX
};

bool Cursor_InitDefault(const char *basedir);
void Cursor_FreeAll(void);

void Cursor_SetActive(enum cursortype type);
bool Cursor_LoadBMP(enum cursortype type, const char *path, int hotx, int hoty);

/* When RTS mode is set, an event handler will continuosly update the cursor icon to be
 * the correct scrolling icon for the cursor's current position on the screen 
 * Must be called after Event subsystem is initialized. */
void Cursor_SetRTSMode(bool on);
bool Cursor_GetRTSMode(void);
void Cursor_SetRTSPointer(enum cursortype type);

bool Cursor_NamedLoadBMP(const char *name, const char *path, int hotx, int hoty);
bool Cursor_NamedSetActive(const char *name);
bool Cursor_NamedSetRTSPointer(const char *name);

void Cursor_ClearState(void);
bool Cursor_SaveState(struct SDL_RWops *stream);
bool Cursor_LoadState(struct SDL_RWops *stream);

#endif

