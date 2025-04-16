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

#ifndef AUDIO_H
#define AUDIO_H

#include "../../pf_math.h"

#include <stdbool.h>
#include <stddef.h>


#define AUDIO_NUM_FG_CHANNELS (4)

struct map;
struct SDL_RWops;

enum playback_mode{
    MUSIC_MODE_LOOP,
    MUSIC_MODE_PLAYLIST,
    MUSIC_MODE_SHUFFLE,
};

bool        Audio_Init(void);
void        Audio_Shutdown(void);
bool        Audio_PlayMusic(const char *name);
void        Audio_PlayMusicFirst(void);
bool        Audio_PlayForegroundEffect(const char *name, bool interrupt, int channel);
size_t      Audio_GetAllMusic(size_t maxout, const char *out[]);
const char *Audio_CurrMusic(void);
bool        Audio_Effect_Add(vec3_t pos, const char *track);
void        Audio_Pause(void);
void        Audio_Resume(unsigned int dt);
void        Audio_ClearState(void);
bool        Audio_SaveState(struct SDL_RWops *stream);
bool        Audio_LoadState(struct SDL_RWops *stream);

#endif

