import array
import random
import tulip
from tulip import seq_add_callback, seq_remove_callback
import midi
from patches import drumkit

import lvgl as lv
from tulip import UIElement, pal_to_lv, lv_depad


from .grids import PatternGenerator

"""
grids = TulipGrids()  # or TulipGrids(use_internal_drums=True)
grids.start()

grids.set_x(128)
grids.set_y(64)
grids.set_density(0, 200)
grids.set_preset(0, 2)
grids.set_velocity(1, 0.8)
grids.set_pitch(2, 0.6)
grids.set_pan(0, 0.3)
"""


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
        self.velocities = array.array("f", [0.5, 0.5, 0.5])
        self.pitches = array.array("f", [0.5, 0.5, 0.5])
        self.pans = array.array("f", [0.5, 0.5, 0.5])

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
