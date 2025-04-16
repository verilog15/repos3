/*
 *  This file is part of Permafrost Engine. 
 *  Copyright (C) 2019-2023 Eduard Permyakov 
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

#ifndef PY_TRAVERSE_H
#define PY_TRAVERSE_H

#include <Python.h> /* Must be included first */
#include <stdbool.h>
#include "../lib/public/khash.h"

__KHASH_TYPE      (str, khint64_t, const char*)
__KHASH_PROTOTYPES(str, khint64_t, const char*)

__KHASH_TYPE      (pobj, kh_cstr_t, PyObject*)
__KHASH_PROTOTYPES(pobj, kh_cstr_t, PyObject*)

bool S_Traverse_DF(PyObject *root, visitproc visit, void *user);
bool S_Traverse_PrintDF(PyObject *root);

bool S_Traverse_BF(PyObject *root, visitproc visit, void *user);
bool S_Traverse_PrintBF(PyObject *root);

bool S_Traverse_IndexQualnames(khash_t(str) *inout);
bool S_Traverse_ReferencesObj(PyObject *root, PyObject *obj, bool *out);

#endif

