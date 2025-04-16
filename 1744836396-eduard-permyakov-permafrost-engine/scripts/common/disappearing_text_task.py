#
#  This file is part of Permafrost Engine. 
#  Copyright (C) 2020-2023 Eduard Permyakov 
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

class DisappearingTextTask(pf.Task):

    def __init__(self, text, bounds, color, duration, travel=50):
        self.text = text
        self.bounds = bounds
        self.color = color
        self.duration = duration
        self.travel = travel

    def __run__(self):
        elapsed = 0
        while elapsed < self.duration:

            frac_done = elapsed / float(self.duration)
            bounds = (self.bounds[0], int(self.bounds[1] - self.travel * frac_done), self.bounds[2], self.bounds[3])
            color = tuple(list(self.color[:-1]) + [int(self.color[3] * (1.0 - frac_done))])

            pf.draw_text(self.text, bounds, color)
            self.await_event(pf.EVENT_UPDATE_START)
            elapsed += pf.prev_frame_ms()

