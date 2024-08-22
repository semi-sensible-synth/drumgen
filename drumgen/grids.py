#!/usr/bin/env python
from array import array
import random


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
        from .resources_drum_map import drum_map

        return drum_map

    def _initialize_euclidean_patterns(self):
        from .resources_euclidean import euclidean_patterns

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


def main():
    pg = PatternGenerator()

    pg.x = random.randint(0, 255)
    pg.y = random.randint(0, 255)
    pg.density = array(
        "B", [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]
    )
    pg.randomness = random.randint(0, 255)  # Set a random value for randomness

    print("x, y, density, randomness: ", pg.x, pg.y, pg.density, pg.randomness)

    resolutions = [
        (PatternGenerator.CLOCK_RESOLUTION_4_PPQN, "4 PPQN"),
        (PatternGenerator.CLOCK_RESOLUTION_8_PPQN, "8 PPQN"),
        (PatternGenerator.CLOCK_RESOLUTION_24_PPQN, "24 PPQN"),
    ]

    for resolution, name in resolutions:
        pg.set_clock_resolution(resolution)
        print(f"\nDrum pattern ({name}):")
        pattern = [[""] * 3 for _ in range(32)]
        for step in range(32 * pg.pulses_per_step):
            output = pg.evaluate()
            for channel in range(3):
                # TODO: Different character of accented beats
                pattern[step // pg.pulses_per_step][channel] += (
                    "*" if output & (1 << channel) else "-"
                )
            pg.tick_clock()

        for channel in range(3):
            print(f"{channel+1}: {''.join(pattern[i][channel] for i in range(32))}")

        print(f"\nEuclidean pattern ({name}):")
        pg.output_mode = "euclidean"
        pg.step = 0
        pattern = [[""] * 3 for _ in range(32)]
        for step in range(32 * pg.pulses_per_step):
            output = pg.evaluate()
            for channel in range(3):
                pattern[step // pg.pulses_per_step][channel] += (
                    "*" if output & (1 << channel) else "-"
                )
            pg.tick_clock()

        for channel in range(3):
            print(f"{channel+1}: {''.join(pattern[i][channel] for i in range(32))}")


if __name__ == "__main__":
    main()
