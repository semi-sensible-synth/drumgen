# drumgen

A drum pattern generator, based on Mutable Instruments Grids, ported to Python.

The `drumgen` code primarily targets MicroPython, but should run under vanilla "CPython" too.

To test it out on the command line without installing, do:

```bash
git clone https://github.com/semi-sensible-synth/drumgen
cd drumgen

python drumgen/grids.py
```

You'll get a drum patten with random X, Y, fill, chaos parameters like like:
```
x, y, density, randomness:  228 123 array('B', [95, 182, 228]) 8

Drum pattern (4 PPQN):
1: *---------------*---------------
2: --------*---*-*-*-----*---*-*---
3: *-*-*-*-*-*-*---*-*-*---*---*---

Euclidean pattern (4 PPQN):
1: ---------------*---------------*
2: ---*---*-------*---*-------*---*
3: -*--*--*--*--*--*--*--*--*--*--*
```

## Install as a package

```bash
git clone https://github.com/semi-sensible-synth/drumgen
cd drumgen
pip install .
```

Then in Python, you might do:

```python
from drumgen.grids import PatternGenerator

grids = PatternGenerator()
grids.randomness = 40
grids.x = 64
grids.y = 10
grids.density[0] = 64
grids.density[1] = 128
grids.density[2] = 192
for i in range(42):
    print(format(grids.evaluate(), '08b'))
    grids.tick_clock()
```

You'll get:
```
00000000
00000000
00000000
00000101
```
..etc..

Since this is still a fairly 'straight' port of the original Grids code, the drum triggers output by `PatternGenerator.evaluate()` are packed as bits into an 8-bit int. The last three bits (6-8) are the drum triggers, bits 3-5 are the accents and bits 1 and 2 are reset and clock bits respectively.

You can use this style of loop under your own clock code to trigger MIDI notes, fire off samples, generate control voltage triggers, whatever.

The API might change in the future as it is further Python-ized (eg, to allow between 1 and X channels from the `PatternGenerator`, rather than hardcoded to 3).


## On TulipCC

The [TulipCC](https://github.com/shorepine/tulipcc) is a neat little music computer platform that runs [MicroPython](https://micropython.org/).

<img src="https://github.com/user-attachments/assets/da397185-c020-4ccb-9533-a9f34a989991" width="50%">

The easiest way to run this as an app is to download `scripts/tulip/tworld_grids.py`.

There's a version on *Tulip ~ World* - on your TulipCC run:

```python
world.download('tworld_grids.py')
```
*(unsure if the Tulip ~ World version  will be kept up to date - the bleeding edge will be on Github)*

Then on your TulipCC run:

```python
>>> run('tworld_grids')
```

You'll see some sliders - move them around.

After finding a beat you like, you can even switch to the Drums app and add extra parts in sync to your groove !


## License

GNU General Public License version 3 (GPL3.0)

- Original code copyright [Emilie Gillet](https://github.com/pichenettes/eurorack/blob/master/grids), licensed under the GPL3.0.
- Ported to Python and modified by Andrew Perry, 2024.
