#
#  This file is part of Permafrost Engine. 
#  Copyright (C) 2019-2023 Eduard Permyakov 
#
#  Permafrost Engine is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Permafrost Engine is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
#  Linking this software statically or dynamically with other modules is making 
#  a combined work based on this software. Thus, the terms and conditions of 
#  the GNU General Public License cover the whole combination. 
#  
#  As a special exception, the copyright holders of Permafrost Engine give 
#  you permission to link Permafrost Engine with independent modules to produce 
#  an executable, regardless of the license terms of these independent 
#  modules, and to copy and distribute the resulting executable under 
#  terms of your choice, provided that you also meet, for each linked 
#  independent module, the terms and conditions of the license of that 
#  module. An independent module is a module which is not derived from 
#  or based on Permafrost Engine. If you modify Permafrost Engine, you may 
#  extend this exception to your version of Permafrost Engine, but you are not 
#  obliged to do so. If you do not wish to do so, delete this exception 
#  statement from your version.
#

import pf
from common.constants import *
import view_controller as vc
import sys


def _gcd(a, b):
    while b != 0:
        t = b
        b = a % b
        a = t
    return a

class VideoSettingsVC(vc.ViewController):

    def __init__(self, view):
        self.view = view
        self.view.dirty = False
        self.__og_ar_idx = self.view.ar_idx
        self.__og_res_idx = self.view.res_idx
        self.__og_mode_idx = self.view.mode_idx
        self.__og_win_on_top_idx = self.view.win_on_top_idx
        self.__og_vsync_ids = self.view.vsync_idx
        self.__og_shadows_ids = self.view.vsync_idx
        self.__update_res_opts()
        self.__load_selection()

    def __load_selection(self):
        err = None
        try:
            ar_saved = pf.settings_get("pf.video.aspect_ratio")
            ar_saved = tuple( (int(num)) for num in ar_saved )
            gcd = _gcd(*ar_saved)
            ar_saved = tuple( (num//gcd) for num in ar_saved )
            for i, cand in enumerate(self.view.ar_opts):
                gcd = _gcd(*cand)
                cand = tuple( (num//gcd) for num in cand )
                if cand == ar_saved:
                    self.view.ar_idx = i
                    self.__og_ar_idx = i
                    break

            res_saved = pf.settings_get("pf.video.resolution")
            for i, cand in enumerate(self.view.res_opts):
                if cand == res_saved:
                    self.view.res_idx = i
                    self.__og_res_idx = i
                    break

            dm_saved = pf.settings_get("pf.video.display_mode")
            for i, cand in enumerate(self.view.mode_opts):
                if cand == dm_saved:
                    self.view.mode_idx = i
                    self.__og_mode_idx = i
                    break

            wat_saved = pf.settings_get("pf.video.window_always_on_top")
            self.view.win_on_top_idx = int(wat_saved == 0)
            self.__og_win_on_top_idx = int(wat_saved == 0)

            vsync_saved = pf.settings_get("pf.video.vsync")
            self.view.vsync_idx = int(vsync_saved == 0)
            self.__og_vsync_idx = int(vsync_saved == 0)

            shadows_saved = pf.settings_get("pf.video.shadows_enabled")
            self.view.shadows_idx = int(shadows_saved == 0)
            self.__og_shadows_idx = int(shadows_saved == 0)

            water_reflect_saved = pf.settings_get("pf.video.water_reflection")
            self.view.water_reflect_idx = int(water_reflect_saved == 0)
            self.__og_water_reflect_idx = int(water_reflect_saved == 0)
        except:
            err = sys.exc_info()
            raise err[0], err[1], err[2]

    def __update_dirty_flag(self):
        if self.view.res_idx != self.__og_res_idx \
        or self.view.mode_idx != self.__og_mode_idx \
        or self.view.win_on_top_idx != self.__og_win_on_top_idx \
        or self.view.ar_idx != self.__og_ar_idx \
        or self.view.vsync_idx != self.__og_vsync_idx \
        or self.view.shadows_idx != self.__og_shadows_idx \
        or self.view.water_reflect_idx != self.__og_water_reflect_idx:
            self.view.dirty = True
        else:
            self.view.dirty = False

    def __on_settings_apply(self, event):
        if self.view.ar_idx != self.__og_ar_idx:
            try:
                pf.settings_set("pf.video.aspect_ratio", self.view.ar_opts[self.view.ar_idx])
                self.__og_ar_idx = self.view.ar_idx
            except Exception as e:
                print("Could not set pf.video.aspect_ratio:" + str(e))

        if self.view.res_idx != self.__og_res_idx:
            try:
                pf.settings_set("pf.video.resolution", self.view.res_opts[self.view.res_idx])
                self.__og_res_idx = self.view.res_idx
            except Exception as e:
                print("Could not set pf.video.resolution:" + str(e))

        if self.view.mode_idx != self.__og_mode_idx:
            try:
                pf.settings_set("pf.video.display_mode", self.view.mode_opts[self.view.mode_idx])
                self.__og_mode_idx = self.view.mode_idx
            except Exception as e:
                print("Could not set pf.video.display_mode:" + str(e))

        if self.view.win_on_top_idx != self.__og_win_on_top_idx:
            try:
                pf.settings_set("pf.video.window_always_on_top", self.view.win_on_top_opts[self.view.win_on_top_idx])
                self.__og_win_on_top_idx = self.view.win_on_top_idx
            except Exception as e:
                print("Could not set pf.video.window_always_on_top:" + str(e))

        if self.view.vsync_idx != self.__og_vsync_idx:
            try:
                pf.settings_set("pf.video.vsync", self.view.vsync_opts[self.view.vsync_idx])
                self.__og_vsync_idx = self.view.vsync_idx
            except Exception as e:
                print("Could not set pf.video.vsync:" + str(e))

        if self.view.shadows_idx != self.__og_shadows_idx:
            try:
                pf.settings_set("pf.video.shadows_enabled", self.view.shadows_opts[self.view.shadows_idx])
                self.__og_shadows_idx = self.view.shadows_idx
            except Exception as e:
                print("Could not set pf.video.shadows_enabled:" + str(e))

        if self.view.water_reflect_idx != self.__og_water_reflect_idx:
            try:
                pf.settings_set("pf.video.water_reflection", self.view.water_reflect_opts[self.view.water_reflect_idx])
                self.__og_water_reflect_idx = self.view.water_reflect_idx
            except Exception as e:
                print("Could not set pf.video.water_reflect_enabled:" + str(e))

        self.__update_res_opts()
        self.__load_selection()
        self.__update_dirty_flag()

    def __update_res_opts(self):
        nx, ny = pf.get_native_resolution()
        arx, ary = pf.settings_get("pf.video.aspect_ratio")
        ar = arx / ary
        native_ar = float(nx) / ny

        if ar < native_ar:
            base = (ny * ar, ny)
        else:
            base = (nx, nx / ar)
        assert base[0] <= nx
        assert base[1] <= ny
        new_opts = [
            base,
            (base[0]/1.5,  base[1]/1.5),
            (base[0]/2,  base[1]/2),
        ]

        res = pf.settings_get("pf.video.resolution")
        int_new_opts = [(int(o[0]), int(o[1])) for o in new_opts]
        if (int(res[0]), int(res[1])) not in int_new_opts:
            new_opts += [res]
        new_opts.sort(reverse=True)

        self.view.res_opts = new_opts
        self.view.res_opt_strings = ["{}:{}".format(int(opt[0]), int(opt[1])) for opt in new_opts]


    def __update_dirty(self, event):
        self.__update_dirty_flag()

    def activate(self):
        pf.register_ui_event_handler(EVENT_SETTINGS_APPLY, VideoSettingsVC.__on_settings_apply, self)
        pf.register_ui_event_handler(EVENT_RES_SETTING_CHANGED, VideoSettingsVC.__update_dirty, self)
        pf.register_ui_event_handler(EVENT_WINMODE_SETTING_CHANGED, VideoSettingsVC.__update_dirty, self)
        pf.register_ui_event_handler(EVENT_AR_SETTING_CHANGED, VideoSettingsVC.__update_dirty, self)
        pf.register_ui_event_handler(EVENT_WIN_TOP_SETTING_CHANGED, VideoSettingsVC.__update_dirty, self)
        pf.register_ui_event_handler(EVENT_VSYNC_SETTING_CHANGED, VideoSettingsVC.__update_dirty, self)
        pf.register_ui_event_handler(EVENT_SHADOWS_SETTING_CHANGED, VideoSettingsVC.__update_dirty, self)
        pf.register_ui_event_handler(EVENT_WATER_REF_SETTING_CHANGED, VideoSettingsVC.__update_dirty, self)

    def deactivate(self):
        pf.unregister_event_handler(EVENT_WATER_REF_SETTING_CHANGED, VideoSettingsVC.__update_dirty)
        pf.unregister_event_handler(EVENT_SHADOWS_SETTING_CHANGED, VideoSettingsVC.__update_dirty)
        pf.unregister_event_handler(EVENT_VSYNC_SETTING_CHANGED, VideoSettingsVC.__update_dirty)
        pf.unregister_event_handler(EVENT_WIN_TOP_SETTING_CHANGED, VideoSettingsVC.__update_dirty)
        pf.unregister_event_handler(EVENT_AR_SETTING_CHANGED, VideoSettingsVC.__update_dirty)
        pf.unregister_event_handler(EVENT_WINMODE_SETTING_CHANGED, VideoSettingsVC.__update_dirty)
        pf.unregister_event_handler(EVENT_RES_SETTING_CHANGED, VideoSettingsVC.__update_dirty)
        pf.unregister_event_handler(EVENT_SETTINGS_APPLY, VideoSettingsVC.__on_settings_apply)

