# FireNode Chainsaw Detector — Real Audio Validation Pack

All files are synthetic-generated using FM synthesis, harmonic modeling, and noise shaping. No copyrighted audio is used.

## positive_chainsaw/

| File | Duration | Expected Result |
|------|----------|----------------|
| chainsaw_start_real_01.wav | 8.0s | POSITIVE: score > 60 |
| chainsaw_cutting_real_01.wav | 10.0s | POSITIVE: score > 60 |
| chainsaw_idle_real_01.wav | 8.0s | POSITIVE: score > 40 |
| chainsaw_long_real_01.wav | 18.0s | POSITIVE: confirmed detection |

## negative_non_chainsaw/

| File | Duration | Expected Result |
|------|----------|----------------|
| motorcycle_real_01.wav | 8.0s | NEGATIVE: score < 60 |
| rain_wind_real_01.wav | 10.0s | NEGATIVE: score < 30 |
| forest_ambient_real_01.wav | 10.0s | NEGATIVE: score < 30 |
| human_voice_real_01.wav | 8.0s | NEGATIVE: score < 40 |
| engine_generator_real_01.wav | 8.0s | NEGATIVE: score < 50 |

## borderline/

| File | Duration | Expected Result |
|------|----------|----------------|
| brush_cutter_real_01.wav | 8.0s | BORDERLINE: may score 40-70 |

## Format
All files: WAV, 44100 Hz, mono, 16-bit PCM

## License
Synthetic generation. No copyright restrictions. Free for any use.

## Testing
Play from phone speaker near RPi USB mic. Use NODE GUI "Audio File Chainsaw Test" > "Browse RPi Folder" to navigate.
