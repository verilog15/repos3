#
#  This file is part of Permafrost Engine. 
#  Copyright (C) 2018-2023 Eduard Permyakov 
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

import anim_moveable as am
import anim_combatable as ac

class Goblin(am.AnimMoveable, ac.AnimCombatable):

    def __init__(self, path, pfobj, name):
        self.attack_anim_idx = 0
        super(Goblin, self).__init__(path, pfobj, name, 
            idle_clip=self.idle_anim(),
            max_hp = 120,
            base_dmg = 40,
            base_armour = 0.30)
        self.speed = 20.0

    def idle_anim(self):
        return "Idle"

    def move_anim(self):
        return "Walk"

    def attack_anim(self): 
        attack_anims = ["Attack.000", "Attack.001", "Attack.002"]
        ret = attack_anims[self.attack_anim_idx]
        self.attack_anim_idx = (self.attack_anim_idx + 1) % len(attack_anims)
        return ret

    def death_anim(self): 
        return "Die"

