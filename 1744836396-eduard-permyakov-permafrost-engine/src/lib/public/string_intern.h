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

#ifndef STRING_INTERN_H
#define STRING_INTERN_H

#include "mpool.h"
#include "khash.h"

#include <stdbool.h>
#include <stddef.h>

#ifndef STRBUFF_SZ
#define STRBUFF_SZ (256)
#endif

typedef char strbuff_t[STRBUFF_SZ];

MPOOL_TYPE(strbuff, strbuff_t)
__KHASH_TYPE(stridx, khint32_t, mp_ref_t)

bool        si_init(mp_strbuff_t *pool, khash_t(stridx) **index, size_t size);
const char *si_intern(const char *str, mp_strbuff_t *pool, khash_t(stridx) *index);
void        si_shutdown(mp_strbuff_t *pool, khash_t(stridx) *index);
void        si_clear(mp_strbuff_t *pool, khash_t(stridx) *index);

#endif

