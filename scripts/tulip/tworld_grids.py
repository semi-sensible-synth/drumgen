#fmt: off

# Copyright 2012 Emilie Gillet, 2024 Andrew Perry
#
# Author: Emilie Gillet (emilie.o.gillet@gmail.com)
# Author: Andrew Perry (ajperry@pansapiens.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

######################################################################
# Tulip ~ World version
#
# Development at: https://github.com/semi-sensible-synth/drumgen
#
# Run like:
#
# run("tworld_grids")
#
# .. or ..
#
# from tworld_grids import TulipGrids
# grids = TulipGrids()  # or TulipGrids(use_internal_drums=True)
# grids.start()
# 
# grids.set_x(128)
# grids.set_y(64)
# grids.set_density(0, 200)
# grids.set_preset(0, 2)
# grids.set_velocity(1, 0.8)
# grids.set_pitch(2, 0.6)
# grids.set_pan(0, 0.3)
#

from array import array
import random
import tulip
import lvgl as lv
from tulip import UIScreen, UIElement, pal_to_lv, lv_depad
from tulip import seq_add_callback, seq_remove_callback

import midi
from patches import drumkit


class PatternGenerator:
    CLOCK_RESOLUTION_4_PPQN = 0
    CLOCK_RESOLUTION_8_PPQN = 1
    CLOCK_RESOLUTION_24_PPQN = 2

    def __init__(self):
        self.x = 128
        self.y = 128
        self.randomness = 0
        self.density = array("B", [128, 128, 128])  # One for each channel
        self.step = 0
        self.pulse = 0
        self.euclidean_step = array("B", [0, 0, 0])
        self.output_mode = "grids"  # 'grids' or 'euclidean'
        self.clock_resolution = self.CLOCK_RESOLUTION_24_PPQN
        self.pulses_per_step = 3  # Default for 24 PPQN
        self.part_perturbation = array("B", [0, 0, 0])

        # Initialize drum map nodes
        self.drum_map = self._initialize_drum_map()
        self.euclidean_patterns = self._initialize_euclidean_patterns()

    def set_clock_resolution(self, resolution):
        self.clock_resolution = resolution
        if resolution == self.CLOCK_RESOLUTION_4_PPQN:
            self.pulses_per_step = 1
        elif resolution == self.CLOCK_RESOLUTION_8_PPQN:
            self.pulses_per_step = 2
        else:  # 24 PPQN
            self.pulses_per_step = 3

    def _initialize_drum_map(self):
        return drum_map

    def _initialize_euclidean_patterns(self):
        return euclidean_patterns

    def _u8_mix(self, a, b, balance):
        return ((b * balance) + (a * (255 - balance))) >> 8

    def read_drum_map(self, step, instrument):
        x, y = self.x, self.y
        i, j = x >> 6, y >> 6

        offset = (instrument * 32) + step

        a_map = self.drum_map[i][j]
        b_map = self.drum_map[min(i + 1, 4)][j]
        c_map = self.drum_map[i][min(j + 1, 4)]
        d_map = self.drum_map[min(i + 1, 4)][min(j + 1, 4)]

        a = a_map[offset]
        b = b_map[offset]
        c = c_map[offset]
        d = d_map[offset]

        x_balance = (x & 0x3F) << 2
        y_balance = (y & 0x3F) << 2

        return self._u8_mix(
            self._u8_mix(a, b, x_balance), self._u8_mix(c, d, x_balance), y_balance
        )
    
    def evaluate_drums(self):
        state = 0
        accent_bits = 0
        
        if self.step == 0:
            for i in range(3):
                self.part_perturbation[i] = (random.randint(0, 255) * self.randomness) >> 8

        for i in range(3):  # For each channel
            level = self.read_drum_map(self.step, i)
            if level < 255 - self.part_perturbation[i]:
                level += self.part_perturbation[i]
            else:
                level = 255
            
            threshold = 255 - self.density[i]
            if level > threshold:
                state |= 1 << i
                if level > 192:  # Accent threshold
                    accent_bits |= 1 << i

        # Combine state and accent bits
        # Use bits 0-2 for triggers, 3-5 for accents
        combined_state = state | (accent_bits << 3)

        # Add clock and reset bits if needed
        # Assuming OUTPUT_BIT_CLOCK is bit 6 and OUTPUT_BIT_RESET is bit 7
        combined_state |= 1 << 6  # Always set clock bit
        if self.step == 0:
            combined_state |= 1 << 7  # Set reset bit at start of pattern

        return combined_state

    def evaluate_euclidean(self):
        state = 0
        for i in range(3):  # For each channel
            length = (self.density[i] >> 5) + 1  # 1 to 8
            pattern = self.euclidean_patterns[length - 1]
            if pattern & (1 << self.euclidean_step[i]):
                state |= 1 << i
            self.euclidean_step[i] = (self.euclidean_step[i] + 1) % 32
        return state

    def tick_clock(self, num_pulses=1):
        self.pulse += num_pulses
        if self.pulse >= self.pulses_per_step:
            self.pulse -= self.pulses_per_step
            self.step = (self.step + 1) % 32

    def evaluate(self):
        if self.pulse == 0:
            if self.output_mode == "grids":
                return self.evaluate_drums()
            else:
                return self.evaluate_euclidean()
        return 0


# Node arrays: 
# 0 -  31: BD
# 32 - 63: SD
# 64 - 96: HH
node_0 = array('B', [
    255, 0, 0, 0, 0, 0, 145, 0, 0, 0, 0, 0, 218, 0, 0, 0, 72, 0, 36, 0, 182, 0, 0, 0, 109, 0, 0, 0, 72, 0, 0, 0,
    36, 0, 109, 0, 0, 0, 8, 0, 255, 0, 0, 0, 0, 0, 72, 0, 0, 0, 182, 0, 0, 0, 36, 0, 218, 0, 0, 0, 145, 0, 0, 0,
    170, 0, 113, 0, 255, 0, 56, 0, 170, 0, 141, 0, 198, 0, 56, 0, 170, 0, 113, 0, 226, 0, 28, 0, 170, 0, 113, 0, 198, 0, 85, 0
])

node_1 = array('B', [
    229, 0, 25, 0, 102, 0, 25, 0, 204, 0, 25, 0, 76, 0, 8, 0, 255, 0, 8, 0, 51, 0, 25, 0, 178, 0, 25, 0, 153, 0, 127, 0,
    28, 0, 198, 0, 56, 0, 56, 0, 226, 0, 28, 0, 141, 0, 28, 0, 28, 0, 170, 0, 28, 0, 28, 0, 255, 0, 113, 0, 85, 0, 85, 0,
    159, 0, 159, 0, 255, 0, 63, 0, 159, 0, 159, 0, 191, 0, 31, 0, 159, 0, 127, 0, 255, 0, 31, 0, 159, 0, 127, 0, 223, 0, 95, 0
])

node_2 = array('B', [
    255, 0, 0, 0, 127, 0, 0, 0, 0, 0, 102, 0, 0, 0, 229, 0, 0, 0, 178, 0, 204, 0, 0, 0, 76, 0, 51, 0, 153, 0, 25, 0,
    0, 0, 127, 0, 0, 0, 0, 0, 255, 0, 191, 0, 31, 0, 63, 0, 0, 0, 95, 0, 0, 0, 0, 0, 223, 0, 0, 0, 31, 0, 159, 0,
    255, 0, 85, 0, 148, 0, 85, 0, 127, 0, 85, 0, 106, 0, 63, 0, 212, 0, 170, 0, 191, 0, 170, 0, 85, 0, 42, 0, 233, 0, 21, 0
])

node_3 = array('B', [
    255, 0, 212, 0, 63, 0, 0, 0, 106, 0, 148, 0, 85, 0, 127, 0, 191, 0, 21, 0, 233, 0, 0, 0, 21, 0, 170, 0, 0, 0, 42, 0,
    0, 0, 0, 0, 141, 0, 113, 0, 255, 0, 198, 0, 0, 0, 56, 0, 0, 0, 85, 0, 56, 0, 28, 0, 226, 0, 28, 0, 170, 0, 56, 0,
    255, 0, 231, 0, 255, 0, 208, 0, 139, 0, 92, 0, 115, 0, 92, 0, 185, 0, 69, 0, 46, 0, 46, 0, 162, 0, 23, 0, 208, 0, 46, 0
])

node_4 = array('B', [
    255, 0, 31, 0, 63, 0, 63, 0, 127, 0, 95, 0, 191, 0, 63, 0, 223, 0, 31, 0, 159, 0, 63, 0, 31, 0, 63, 0, 95, 0, 31, 0,
    8, 0, 0, 0, 95, 0, 63, 0, 255, 0, 0, 0, 127, 0, 0, 0, 8, 0, 0, 0, 159, 0, 63, 0, 255, 0, 223, 0, 191, 0, 31, 0,
    76, 0, 25, 0, 255, 0, 127, 0, 153, 0, 51, 0, 204, 0, 102, 0, 76, 0, 51, 0, 229, 0, 127, 0, 153, 0, 51, 0, 178, 0, 102, 0
])

node_5 = array('B', [
    255, 0, 51, 0, 25, 0, 76, 0, 0, 0, 0, 0, 102, 0, 0, 0, 204, 0, 229, 0, 0, 0, 178, 0, 0, 0, 153, 0, 127, 0, 8, 0,
    178, 0, 127, 0, 153, 0, 204, 0, 255, 0, 0, 0, 25, 0, 76, 0, 102, 0, 51, 0, 0, 0, 0, 0, 229, 0, 25, 0, 25, 0, 204, 0,
    178, 0, 102, 0, 255, 0, 76, 0, 127, 0, 76, 0, 229, 0, 76, 0, 153, 0, 102, 0, 255, 0, 25, 0, 127, 0, 51, 0, 204, 0, 51, 0
])

node_6 = array('B', [
    255, 0, 0, 0, 223, 0, 0, 0, 31, 0, 8, 0, 127, 0, 0, 0, 95, 0, 0, 0, 159, 0, 0, 0, 95, 0, 63, 0, 191, 0, 0, 0,
    51, 0, 204, 0, 0, 0, 102, 0, 255, 0, 127, 0, 8, 0, 178, 0, 25, 0, 229, 0, 0, 0, 76, 0, 204, 0, 153, 0, 51, 0, 25, 0,
    255, 0, 226, 0, 255, 0, 255, 0, 198, 0, 28, 0, 141, 0, 56, 0, 170, 0, 56, 0, 85, 0, 28, 0, 170, 0, 28, 0, 113, 0, 56, 0
])

node_7 = array('B', [
    223, 0, 0, 0, 63, 0, 0, 0, 95, 0, 0, 0, 223, 0, 31, 0, 255, 0, 0, 0, 159, 0, 0, 0, 127, 0, 31, 0, 191, 0, 31, 0,
    0, 0, 0, 0, 109, 0, 0, 0, 218, 0, 0, 0, 182, 0, 72, 0, 8, 0, 36, 0, 145, 0, 36, 0, 255, 0, 8, 0, 182, 0, 72, 0,
    255, 0, 72, 0, 218, 0, 36, 0, 218, 0, 0, 0, 145, 0, 0, 0, 255, 0, 36, 0, 182, 0, 36, 0, 182, 0, 0, 0, 109, 0, 0, 0
])

node_8 = array('B', [
    255, 0, 0, 0, 218, 0, 0, 0, 36, 0, 0, 0, 218, 0, 0, 0, 182, 0, 109, 0, 255, 0, 0, 0, 0, 0, 0, 0, 145, 0, 72, 0,
    159, 0, 0, 0, 31, 0, 127, 0, 255, 0, 31, 0, 0, 0, 95, 0, 8, 0, 0, 0, 191, 0, 31, 0, 255, 0, 31, 0, 223, 0, 63, 0,
    255, 0, 31, 0, 63, 0, 31, 0, 95, 0, 31, 0, 63, 0, 127, 0, 159, 0, 31, 0, 63, 0, 31, 0, 223, 0, 223, 0, 191, 0, 191, 0
])

node_9 = array('B', [
    226, 0, 28, 0, 28, 0, 141, 0, 8, 0, 8, 0, 255, 0, 8, 0, 113, 0, 28, 0, 198, 0, 85, 0, 56, 0, 198, 0, 170, 0, 28, 0,
    8, 0, 95, 0, 8, 0, 8, 0, 255, 0, 63, 0, 31, 0, 223, 0, 8, 0, 31, 0, 191, 0, 8, 0, 255, 0, 127, 0, 127, 0, 159, 0,
    115, 0, 46, 0, 255, 0, 185, 0, 139, 0, 23, 0, 208, 0, 115, 0, 231, 0, 69, 0, 255, 0, 162, 0, 139, 0, 115, 0, 231, 0, 92, 0
])

node_10 = array('B', [
    145, 0, 0, 0, 0, 0, 109, 0, 0, 0, 0, 0, 255, 0, 109, 0, 72, 0, 218, 0, 0, 0, 0, 0, 36, 0, 0, 0, 182, 0, 0, 0,
    0, 0, 127, 0, 159, 0, 127, 0, 159, 0, 191, 0, 223, 0, 63, 0, 255, 0, 95, 0, 31, 0, 95, 0, 31, 0, 8, 0, 63, 0, 8, 0,
    255, 0, 0, 0, 145, 0, 0, 0, 182, 0, 109, 0, 109, 0, 109, 0, 218, 0, 0, 0, 72, 0, 0, 0, 182, 0, 72, 0, 182, 0, 36, 0
])

node_11 = array('B', [
    255, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 255, 0, 0, 0, 218, 0, 72, 36, 0, 0, 182, 0, 0, 0, 145, 109,
    0, 0, 127, 0, 0, 0, 42, 0, 212, 0, 0, 212, 0, 0, 212, 0, 0, 0, 0, 0, 42, 0, 0, 0, 255, 0, 0, 0, 170, 170, 127, 85,
    145, 0, 109, 109, 218, 109, 72, 0, 145, 0, 72, 0, 218, 0, 109, 0, 182, 0, 109, 0, 255, 0, 72, 0, 182, 109, 36, 109, 255, 109, 109, 0
])

node_12 = array('B', [
    255, 0, 0, 0, 255, 0, 191, 0, 0, 0, 0, 0, 95, 0, 63, 0, 31, 0, 0, 0, 223, 0, 223, 0, 0, 0, 8, 0, 159, 0, 127, 0,
    0, 0, 85, 0, 56, 0, 28, 0, 255, 0, 28, 0, 0, 0, 226, 0, 0, 0, 170, 0, 56, 0, 113, 0, 198, 0, 0, 0, 113, 0, 141, 0,
    255, 0, 42, 0, 233, 0, 63, 0, 212, 0, 85, 0, 191, 0, 106, 0, 191, 0, 21, 0, 170, 0, 8, 0, 170, 0, 127, 0, 148, 0, 148, 0
])

node_13 = array('B', [
    255, 0, 0, 0, 0, 0, 63, 0, 191, 0, 95, 0, 31, 0, 223, 0, 255, 0, 63, 0, 95, 0, 63, 0, 159, 0, 0, 0, 0, 0, 127, 0,
    72, 0, 0, 0, 0, 0, 0, 0, 255, 0, 0, 0, 0, 0, 0, 0, 72, 0, 72, 0, 36, 0, 8, 0, 218, 0, 182, 0, 145, 0, 109, 0,
    255, 0, 162, 0, 231, 0, 162, 0, 231, 0, 115, 0, 208, 0, 139, 0, 185, 0, 92, 0, 185, 0, 46, 0, 162, 0, 69, 0, 162, 0, 23, 0
])

node_14 = array('B', [
    255, 0, 0, 0, 51, 0, 0, 0, 0, 0, 0, 0, 102, 0, 0, 0, 204, 0, 0, 0, 153, 0, 0, 0, 0, 0, 0, 0, 51, 0, 0, 0,
    0, 0, 0, 0, 8, 0, 36, 0, 255, 0, 0, 0, 182, 0, 8, 0, 0, 0, 0, 0, 72, 0, 109, 0, 145, 0, 0, 0, 255, 0, 218, 0,
    212, 0, 8, 0, 170, 0, 0, 0, 127, 0, 0, 0, 85, 0, 8, 0, 255, 0, 8, 0, 170, 0, 0, 0, 127, 0, 0, 0, 42, 0, 8, 0
])

node_15 = array('B', [
    255, 0, 0, 0, 0, 0, 0, 0, 36, 0, 0, 0, 182, 0, 0, 0, 218, 0, 0, 0, 0, 0, 0, 0, 72, 0, 0, 0, 145, 0, 109, 0,
    36, 0, 36, 0, 0, 0, 0, 0, 255, 0, 0, 0, 182, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 109, 218, 0, 0, 0, 145, 0, 72, 72,
    255, 0, 28, 0, 226, 0, 56, 0, 198, 0, 0, 0, 0, 0, 28, 28, 170, 0, 0, 0, 141, 0, 0, 0, 113, 0, 0, 0, 85, 85, 85, 85
])

node_16 = array('B', [
    255, 0, 0, 0, 0, 0, 95, 0, 0, 0, 127, 0, 0, 0, 0, 0, 223, 0, 95, 0, 63, 0, 31, 0, 191, 0, 0, 0, 159, 0, 0, 0,
    0, 0, 31, 0, 255, 0, 0, 0, 0, 0, 95, 0, 223, 0, 0, 0, 0, 0, 63, 0, 191, 0, 0, 0, 0, 0, 0, 0, 159, 0, 127, 0,
    141, 0, 28, 0, 28, 0, 28, 0, 113, 0, 8, 0, 8, 0, 8, 0, 255, 0, 0, 0, 226, 0, 0, 0, 198, 0, 56, 0, 170, 0, 85, 0
])

node_17 = array('B', [
    255, 0, 0, 0, 8, 0, 0, 0, 182, 0, 0, 0, 72, 0, 0, 0, 218, 0, 0, 0, 36, 0, 0, 0, 145, 0, 0, 0, 109, 0, 0, 0,
    0, 0, 51, 25, 76, 25, 25, 0, 153, 0, 0, 0, 127, 102, 178, 0, 204, 0, 0, 0, 0, 0, 255, 0, 0, 0, 102, 0, 229, 0, 76, 0,
    113, 0, 0, 0, 141, 0, 85, 0, 0, 0, 0, 0, 170, 0, 0, 0, 56, 28, 255, 0, 0, 0, 0, 0, 198, 0, 0, 0, 226, 0, 0, 0
])

node_18 = array('B', [
    255, 0, 8, 0, 28, 0, 28, 0, 198, 0, 56, 0, 56, 0, 85, 0, 255, 0, 85, 0, 113, 0, 113, 0, 226, 0, 141, 0, 170, 0, 141, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 255, 0, 0, 0, 127, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 63, 0, 0, 0, 191, 0, 0, 0,
    255, 0, 0, 0, 255, 0, 127, 0, 0, 0, 85, 0, 0, 0, 212, 0, 0, 0, 212, 0, 42, 0, 170, 0, 0, 0, 127, 0, 0, 0, 0, 0
])

node_19 = array('B', [
    255, 0, 0, 0, 0, 0, 218, 0, 182, 0, 0, 0, 0, 0, 145, 0, 145, 0, 36, 0, 0, 0, 109, 0, 109, 0, 0, 0, 72, 0, 36, 0,
    0, 0, 0, 0, 109, 0, 8, 0, 72, 0, 0, 0, 255, 0, 182, 0, 0, 0, 0, 0, 145, 0, 8, 0, 36, 0, 8, 0, 218, 0, 182, 0,
    255, 0, 0, 0, 0, 0, 226, 0, 85, 0, 0, 0, 141, 0, 0, 0, 0, 0, 0, 0, 170, 0, 56, 0, 198, 0, 0, 0, 113, 0, 28, 0
])

node_20 = array('B', [
    255, 0, 0, 0, 113, 0, 0, 0, 198, 0, 56, 0, 85, 0, 28, 0, 255, 0, 0, 0, 226, 0, 0, 0, 170, 0, 0, 0, 141, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 255, 0, 145, 0, 109, 0, 218, 0, 36, 0, 182, 0, 72, 0, 72, 0, 255, 0, 0, 0, 0, 0, 109, 0,
    36, 0, 36, 0, 145, 0, 0, 0, 72, 0, 72, 0, 182, 0, 0, 0, 72, 0, 72, 0, 218, 0, 0, 0, 109, 0, 109, 0, 255, 0, 0, 0
])

node_21 = array('B', [
    255, 0, 0, 0, 218, 0, 0, 0, 145, 0, 0, 0, 36, 0, 0, 0, 218, 0, 0, 0, 36, 0, 0, 0, 182, 0, 72, 0, 0, 0, 109, 0,
    0, 0, 0, 0, 8, 0, 0, 0, 255, 0, 85, 0, 212, 0, 42, 0, 0, 0, 0, 0, 8, 0, 0, 0, 85, 0, 170, 0, 127, 0, 42, 0,
    109, 0, 109, 0, 255, 0, 0, 0, 72, 0, 72, 0, 218, 0, 0, 0, 145, 0, 182, 0, 255, 0, 0, 0, 36, 0, 36, 0, 218, 0, 8, 0
])

node_22 = array('B', [
    255, 0, 0, 0, 42, 0, 0, 0, 212, 0, 0, 0, 8, 0, 212, 0, 170, 0, 0, 0, 85, 0, 0, 0, 212, 0, 8, 0, 127, 0, 8, 0,
    255, 0, 85, 0, 0, 0, 0, 0, 226, 0, 85, 0, 0, 0, 198, 0, 0, 0, 141, 0, 56, 0, 0, 0, 170, 0, 28, 0, 0, 0, 113, 0,
    113, 0, 56, 0, 255, 0, 0, 0, 85, 0, 56, 0, 226, 0, 0, 0, 0, 0, 170, 0, 0, 0, 141, 0, 28, 0, 28, 0, 198, 0, 28, 0
])

node_23 = array('B', [
    255, 0, 0, 0, 229, 0, 0, 0, 204, 0, 204, 0, 0, 0, 76, 0, 178, 0, 153, 0, 51, 0, 178, 0, 178, 0, 127, 0, 102, 51, 51, 25,
    0, 0, 0, 0, 0, 0, 0, 31, 0, 0, 0, 0, 255, 0, 0, 31, 0, 0, 8, 0, 0, 0, 191, 159, 127, 95, 95, 0, 223, 0, 63, 0,
    255, 0, 255, 0, 204, 204, 204, 204, 0, 0, 51, 51, 51, 51, 0, 0, 204, 0, 204, 0, 153, 153, 153, 153, 153, 0, 0, 0, 102, 102, 102, 102
])

node_24 = array('B', [
    170, 0, 0, 0, 0, 255, 0, 0, 198, 0, 0, 0, 0, 28, 0, 0, 141, 0, 0, 0, 0, 226, 0, 0, 56, 0, 0, 113, 0, 85, 0, 0,
    255, 0, 0, 0, 0, 113, 0, 0, 85, 0, 0, 0, 0, 226, 0, 0, 141, 0, 0, 8, 0, 170, 56, 56, 198, 0, 0, 56, 0, 141, 28, 0,
    255, 0, 0, 0, 0, 191, 0, 0, 159, 0, 0, 0, 0, 223, 0, 0, 95, 0, 0, 0, 0, 63, 0, 0, 127, 0, 0, 0, 0, 31, 0, 0
])

# Create the 5x5 grid of nodes
drum_map = [
    [node_10, node_8, node_0, node_9, node_11],
    [node_15, node_7, node_13, node_12, node_6],
    [node_18, node_14, node_4, node_5, node_3],
    [node_23, node_16, node_21, node_1, node_2],
    [node_24, node_19, node_17, node_20, node_22]
]

# Euclidean patterns
euclidean_patterns = array('I', [
    0x00000000, 0x80000000, 0x80008000, 0x80808080, 0x88080808, 0x88088088, 0x88888888, 0x92492492,
    0x00000000, 0x80000000, 0x80008000, 0x80808080, 0x88080808, 0x88088088, 0x88888888, 0x92492492,
    0x00000000, 0x80000000, 0x80008000, 0x80808080, 0x88080808, 0x88088088, 0x88888888, 0x92492492,
    0x00000000, 0x80000000, 0x80008000, 0x80808080, 0x88080808, 0x88088088, 0x88888888, 0x92492492,
    0x00000000, 0x80000000, 0x84004000, 0x84208410, 0x88220811, 0x89124889, 0x91248891, 0x92492492,
    0x00000000, 0x80000000, 0x82002000, 0x88082080, 0x88822080, 0x90909088, 0x92249249, 0x94924924,
    0x00000000, 0x80000000, 0x80008000, 0x84008400, 0x88084808, 0x90089008, 0x92289228, 0x94489448,
    0x00000000, 0x80000000, 0x80040000, 0x82082080, 0x88084808, 0x88888808, 0x92288888, 0x92488888,
    0x00000000, 0x80000000, 0x80008000, 0x80808080, 0x84084084, 0x88088808, 0x90090909, 0x92492492,
    0x00000000, 0x80000000, 0x80008000, 0x80808080, 0x84084084, 0x88088808, 0x90090909, 0x92492492,
    0x00000000, 0x80000000, 0x80020000, 0x82008200, 0x88022088, 0x88888222, 0x90909090, 0x92492492,
    0x00000000, 0x80000000, 0x80100010, 0x84104104, 0x88888410, 0x90909090, 0x92492492, 0x94924924,
    0x00000000, 0x80000000, 0x80808080, 0x84848484, 0x88888888, 0x90909090, 0x92492492, 0x94924924,
    0x00000000, 0x80000000, 0x82000000, 0x88000800, 0x88888000, 0x90909088, 0x92492490, 0x94924924,
    0x00000000, 0x80000000, 0x82000000, 0x88000800, 0x88888000, 0x90909088, 0x92492490, 0x94924924,
    0x00000000, 0x80000000, 0x84000000, 0x88200820, 0x88888220, 0x90909090, 0x92492492, 0x94924924,
    0x00000000, 0x80000000, 0x88000000, 0x88880880, 0x88888888, 0x90909090, 0x92492492, 0x94924924,
    0x00000000, 0x80000000, 0x88000000, 0x88880880, 0x88888888, 0x90909090, 0x92492492, 0x94924924,
    0x00000000, 0x80000000, 0x88000000, 0x88880880, 0x88888888, 0x90909090, 0x92492492, 0x94924924,
    0x00000000, 0x80000000, 0x88000000, 0x88880880, 0x88888888, 0x90909090, 0x92492492, 0x94924924,
    0x00000000, 0x80000000, 0x90000000, 0x90909090, 0x90909090, 0x92492492, 0x92492492, 0x94924924,
    0x00000000, 0x80000000, 0x90000000, 0x90909090, 0x90909090, 0x92492492, 0x92492492, 0x94924924,
    0x00000000, 0x80000000, 0x90000000, 0x90909090, 0x90909090, 0x92492492, 0x92492492, 0x94924924,
    0x00000000, 0x80000000, 0x90000000, 0x90909090, 0x90909090, 0x92492492, 0x92492492, 0x94924924,
    0x00000000, 0x80000000, 0xa0000000, 0xa0a0a0a0, 0xa0a0a0a0, 0xa4a4a4a4, 0xa4a4a4a4, 0xa4a4a4a4,
    0x00000000, 0x80000000, 0xa0000000, 0xa0a0a0a0, 0xa0a0a0a0, 0xa4a4a4a4, 0xa4a4a4a4, 0xa4a4a4a4,
    0x00000000, 0x80000000, 0xa0000000, 0xa0a0a0a0, 0xa0a0a0a0, 0xa4a4a4a4, 0xa4a4a4a4, 0xa4a4a4a4,
    0x00000000, 0x80000000, 0xa0000000, 0xa0a0a0a0, 0xa0a0a0a0, 0xa4a4a4a4, 0xa4a4a4a4, 0xa4a4a4a4,
    0x00000000, 0x80000000, 0xc0000000, 0xc0c0c0c0, 0xc0c0c0c0, 0xc0c0c0c0, 0xc0c0c0c0, 0xc4c4c4c4,
    0x00000000, 0x80000000, 0xc0000000, 0xc0c0c0c0, 0xc0c0c0c0, 0xc0c0c0c0, 0xc0c0c0c0, 0xc4c4c4c4,
    0x00000000, 0x80000000, 0xc0000000, 0xc0c0c0c0, 0xc0c0c0c0, 0xc0c0c0c0, 0xc0c0c0c0, 0xc4c4c4c4,
    0x00000000, 0x80000000, 0xc0000000, 0xc0c0c0c0, 0xc0c0c0c0, 0xc0c0c0c0, 0xc0c0c0c0, 0xc4c4c4c4
])

def get_euclidean_pattern(steps, pulses):
    """
    Get the Euclidean pattern for a given number of steps and pulses.
    
    :param steps: Number of steps (1-32)
    :param pulses: Number of pulses (0-32)
    :return: 32-bit integer representing the Euclidean pattern
    """
    if steps < 1 or steps > 32 or pulses < 0 or pulses > 32:
        raise ValueError("Invalid steps or pulses value")
    
    index = (steps - 1) * 8 + (pulses * 8 // 32)
    return euclidean_patterns[index]


class TulipGrids:
    def __init__(self, use_internal_drums=True):
        self.pattern_generator = PatternGenerator()
        self.mode = "grids"
        self.seq_slot = None
        self.use_internal_drums = use_internal_drums

        if use_internal_drums:
            self.synth = midi.config.synth_per_channel[10]
        else:
            self.synth = midi.Synth(3)  # 3-voice polyphony for drums
            self.synth.program_change(128)  # Set to GM drums

        self.drum_presets = [1, 2, 0]  # Default presets for BD, SD, HH
        self.velocities = array("f", [0.5, 0.5, 0.5])
        self.pitches = array("f", [0.5, 0.5, 0.5])
        self.pans = array("f", [0.5, 0.5, 0.5])

    def __del__(self):
        self.stop()

    def start(self):
        if self.seq_slot is None:
            self.seq_slot = seq_add_callback(
                self._sequencer_callback, 2
            )  # Call every 2 ticks (24 PPQN equivalent)

    def stop(self):
        if self.seq_slot is not None:
            seq_remove_callback(self.seq_slot)
            self.seq_slot = None

    def set_mode_grids(self):
        self.mode = "grids"
        self.pattern_generator.output_mode = "grids"

    def set_mode_euclidean(self):
        self.mode = "euclidean"
        self.pattern_generator.output_mode = "euclidean"

    def _sequencer_callback(self, time):
        if self.mode == "grids":
            state = self.pattern_generator.evaluate()
        else:  # Euclidean mode
            state = self.pattern_generator.evaluate_euclidean()

        for i in range(3):
            if state & (1 << i):
                if self.use_internal_drums:
                    base_note = drumkit[self.drum_presets[i]][0]
                    note_for_pitch = int(base_note + (self.pitches[i] - 0.5) * 24.0)
                    self.synth.note_on(
                        note_for_pitch,
                        self.velocities[i] * 2,
                        pcm_patch=self.drum_presets[i],
                        pan=self.pans[i],
                        time=time,
                    )
                else:
                    note = [36, 38, 42][i]  # Bass drum, Snare drum, Closed hi-hat
                    self.synth.note_on(note, int(self.velocities[i] * 127), time=time)

        self.pattern_generator.tick_clock()

    def set_x(self, value):
        self.pattern_generator.x = value

    def set_y(self, value):
        self.pattern_generator.y = value

    def set_density(self, channel, value):
        self.pattern_generator.density[channel] = value

    def set_chaos(self, value):
        self.pattern_generator.randomness = value

    def set_preset(self, channel, preset):
        if 0 <= channel < 3 and 0 <= preset < len(drumkit):
            self.drum_presets[channel] = preset

    def set_velocity(self, channel, velocity):
        if 0 <= channel < 3 and 0 <= velocity <= 1:
            self.velocities[channel] = velocity

    def set_pitch(self, channel, pitch):
        if 0 <= channel < 3 and 0 <= pitch <= 1:
            self.pitches[channel] = pitch

    def set_pan(self, channel, pan):
        if 0 <= channel < 3 and 0 <= pan <= 1:
            self.pans[channel] = pan


class GridsGUI(UIElement):
    def __init__(self, grids_instance):
        super().__init__()
        self.grids = grids_instance
        self.group.set_size(700, 500)
        self.group.set_style_bg_color(pal_to_lv(9), 0)
        lv_depad(self.group)

        self._create_sliders()
        self._create_mode_switch()

    def _create_sliders(self):
        slider_configs = [
            ("Tempo", 30, 240, self._tempo_cb),
            ("X", 0, 255, self._x_cb),
            ("Y", 0, 255, self._y_cb),
            ("Fill BD", 0, 255, lambda e: self._fill_cb(e, 0)),
            ("Fill SD", 0, 255, lambda e: self._fill_cb(e, 1)),
            ("Fill HH", 0, 255, lambda e: self._fill_cb(e, 2)),
            ("Chaos", 0, 255, self._chaos_cb),
        ]

        for i, (name, min_val, max_val, callback) in enumerate(slider_configs):
            slider = lv.slider(self.group)
            slider.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
            slider.set_width(300)
            slider.set_style_bg_color(pal_to_lv(255), lv.PART.INDICATOR)
            slider.set_style_bg_color(pal_to_lv(255), lv.PART.MAIN)
            slider.set_style_bg_color(pal_to_lv(129), lv.PART.KNOB)
            slider.set_range(min_val, max_val)
            slider.align(lv.ALIGN.TOP_LEFT, 20, 20 + i * 60)
            slider.add_event_cb(callback, lv.EVENT.VALUE_CHANGED, None)

            label = lv.label(self.group)
            label.set_text(f"{name}: {min_val}")
            label.align_to(slider, lv.ALIGN.OUT_TOP_LEFT, 0, -5)

            value_label = lv.label(self.group)
            value_label.align_to(slider, lv.ALIGN.OUT_RIGHT_MID, 10, 0)

            setattr(self, f"{name.lower().replace(' ', '_')}_slider", slider)
            setattr(self, f"{name.lower().replace(' ', '_')}_label", label)
            setattr(self, f"{name.lower().replace(' ', '_')}_value", value_label)

        # Set initial values without animation
        self.tempo_slider.set_value(120, lv.ANIM.OFF)
        self.x_slider.set_value(128, lv.ANIM.OFF)
        self.y_slider.set_value(128, lv.ANIM.OFF)
        self.fill_bd_slider.set_value(128, lv.ANIM.OFF)
        self.fill_sd_slider.set_value(128, lv.ANIM.OFF)
        self.fill_hh_slider.set_value(128, lv.ANIM.OFF)
        self.chaos_slider.set_value(0, lv.ANIM.OFF)

        # Update value labels
        self._tempo_cb(None)
        self._x_cb(None)
        self._y_cb(None)
        self._fill_cb(None, 0)
        self._fill_cb(None, 1)
        self._fill_cb(None, 2)
        self._chaos_cb(None)

    def _create_mode_switch(self):
        self.mode_switch = lv.switch(self.group)
        self.mode_switch.align(lv.ALIGN.TOP_RIGHT, -20, 20)
        self.mode_switch.add_event_cb(self._mode_cb, lv.EVENT.VALUE_CHANGED, None)

        self.mode_label = lv.label(self.group)
        self.mode_label.set_text("Grids")
        self.mode_label.align_to(self.mode_switch, lv.ALIGN.OUT_LEFT_MID, -10, 0)

        # Set initial state
        if self.grids.pattern_generator.output_mode == "euclidean":
            self.mode_switch.add_state(lv.STATE.CHECKED)
            self.mode_label.set_text("Euclidean")

    def _tempo_cb(self, e):
        new_bpm = self.tempo_slider.get_value()
        tulip.seq_bpm(new_bpm)
        self.tempo_value.set_text(f"{new_bpm} BPM")

    def _x_cb(self, e):
        value = self.x_slider.get_value()
        self.grids.set_x(value)
        self.x_value.set_text(str(value))

    def _y_cb(self, e):
        value = self.y_slider.get_value()
        self.grids.set_y(value)
        self.y_value.set_text(str(value))

    def _fill_cb(self, e, channel):
        slider = getattr(
            self,
            f"fill_{'bd' if channel == 0 else 'sd' if channel == 1 else 'hh'}_slider",
        )
        value = slider.get_value()
        self.grids.set_density(channel, value)
        value_label = getattr(
            self,
            f"fill_{'bd' if channel == 0 else 'sd' if channel == 1 else 'hh'}_value",
        )
        value_label.set_text(str(value))

    def _chaos_cb(self, e):
        value = self.chaos_slider.get_value()
        self.grids.set_chaos(value)
        self.chaos_value.set_text(str(value))

    def _mode_cb(self, e):
        if self.mode_switch.get_state() == lv.STATE.CHECKED:
            self.mode_label.set_text("Euclidean")
            self.grids.pattern_generator.output_mode = "euclidean"
        else:
            self.mode_label.set_text("Grids")
            self.grids.pattern_generator.output_mode = "grids"


def run(screen):
    screen.set_bg_color(0)
    screen.offset_y = 25
    screen.offset_x = 50

    grids = TulipGrids()
    gui = GridsGUI(grids)
    screen.add(gui, x=screen.offset_x, y=screen.offset_y)

    screen.present()
    grids.start()

    def quit(screen):
        grids.stop()

    screen.quit_callback = quit
