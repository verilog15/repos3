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

#ifndef MEM_H
#define MEM_H

#include <stdlib.h>
#include <stdint.h>

#ifdef _MSC_VER
#include <malloc.h>
#endif

#define PF_FREE(...)                                    \
    do{                                                 \
        free((void*)__VA_ARGS__);                       \
        __VA_ARGS__ = (void*)((uintptr_t)0xDEADBEEF);   \
    }while(0)

#endif

#ifdef _MSC_VER
#define STALLOC(_type, _name, _size)                    \
    _type *_name = _malloca(sizeof(_type) * (_size))
#else
#define STALLOC(_type, _name, _size)                    \
    _type _name[_size]
#endif

#ifdef _MSC_VER
#define STFREE(_ptr) _freea(_ptr)
#else
#define STFREE(_ptr) /* no-op */
#endif

