# Chainsaw Audio Audit Report

Generated: Thu Jun 11 10:36:46 PST 2026

## Summary

| Metric | Count |
|--------|-------|
| Total files scanned | 30 |
| Real recordings (user-provided, Google Drive) | 6 |
| Generated/synthetic (repo) | 24 |
| Unknown origin | 0 |
| Usable positive chainsaw | 13 |
| Usable negative/non-chainsaw | 12 |
| Rejected (wrong format: 192kHz 32bit, or 24bit) | 3 |
| Borderline (brush cutter) | 1 |
| Baseline/silence | 1 |

### Key findings

**Google Drive files** (`chainsaw_audio/`):
- 6 real user-provided chainsaw recordings (various formats)
- 3 are directly usable (44100 Hz, 16-bit, WAV): `chainsaw-start-attempts.wav` (6.8s), `chainsaw.wav` (115.6s), `chainsaw3.wav` (15.8s)
- 3 need conversion before use: `chainsaw-noises-002.wav` (192kHz/32bit), `chainsaw-noises-003.wav` (192kHz/32bit), `chainsaw2.wav` (24-bit)
- All are stereo — should be converted to mono for FireNode detector compatibility

**Repo synthetic files** (`test_audio/` and `test_audio_real/`):
- All 24 files are generated/synthetic (FM synthesis + noise shaping)
- 14 in `test_audio/` (older generation, includes 16000 Hz files)
- 10 in `test_audio_real/` (newer FM-based generation, all 44100 Hz)
- Good coverage: 7 positive chainsaw variants, 7 negative (motorcycle, rain, wind, forest, voice, generator), 1 borderline (brush cutter), 1 silence baseline

## test_audio

Path: `/Users/macbookm1max321tb/A_Design/A_Coding/ADM Fire/raspi/firenode-system/test_audio`
Files: 14

| File | Origin | Duration | SR | Ch | Depth | Size | Usable | Recommend |
|------|--------|----------|-----|-----|-------|------|--------|-----------|
| chainsaw_close_loud.wav | generated/synthetic | 7.0s | 44100 Hz | 1 | 16bit | 602 KB | YES | positive_chainsaw |
| chainsaw_cutting_pulse.wav | generated/synthetic | 8.0s | 44100 Hz | 1 | 16bit | 689 KB | YES | positive_chainsaw |
| chainsaw_far_low_volume.wav | generated/synthetic | 8.0s | 44100 Hz | 1 | 16bit | 689 KB | YES | positive_chainsaw |
| chainsaw_idle_loop.wav | generated/synthetic | 7.0s | 44100 Hz | 1 | 16bit | 602 KB | YES | positive_chainsaw |
| chainsaw_like_cutting_synthetic.wav | generated/synthetic | 15.0s | 16000 Hz | 1 | 16bit | 468 KB | YES | positive_chainsaw |
| chainsaw_like_idle_synthetic.wav | generated/synthetic | 15.0s | 16000 Hz | 1 | 16bit | 468 KB | YES | positive_chainsaw |
| forest_background_quiet.wav | generated/synthetic | 6.0s | 44100 Hz | 1 | 16bit | 516 KB | YES | negative_non_chainsaw |
| forest_background_synthetic.wav | generated/synthetic | 15.0s | 16000 Hz | 1 | 16bit | 468 KB | YES | negative_non_chainsaw |
| human_voice_false_positive.wav | generated/synthetic | 6.0s | 44100 Hz | 1 | 16bit | 516 KB | YES | negative_non_chainsaw |
| rain_noise.wav | generated/synthetic | 7.0s | 44100 Hz | 1 | 16bit | 602 KB | YES | negative_non_chainsaw |
| silence_baseline.wav | generated/synthetic | 6.0s | 44100 Hz | 1 | 16bit | 516 KB | YES | negative_non_chainsaw |
| vehicle_engine_false_positive.wav | generated/synthetic | 7.0s | 44100 Hz | 1 | 16bit | 602 KB | YES | negative_non_chainsaw |
| wind_noise.wav | generated/synthetic | 7.0s | 44100 Hz | 1 | 16bit | 602 KB | YES | negative_non_chainsaw |
| wind_rain_synthetic.wav | generated/synthetic | 15.0s | 16000 Hz | 1 | 16bit | 468 KB | YES | negative_non_chainsaw |

## test_audio_real

Path: `/Users/macbookm1max321tb/A_Design/A_Coding/ADM Fire/raspi/firenode-system/test_audio_real`
Files: 10

| File | Origin | Duration | SR | Ch | Depth | Size | Usable | Recommend |
|------|--------|----------|-----|-----|-------|------|--------|-----------|
| brush_cutter_real_01.wav | generated/synthetic | 8.0s | 44100 Hz | 1 | 16bit | 689 KB | YES | borderline |
| chainsaw_cutting_real_01.wav | generated/synthetic | 10.0s | 44100 Hz | 1 | 16bit | 861 KB | YES | positive_chainsaw |
| chainsaw_idle_real_01.wav | generated/synthetic | 8.0s | 44100 Hz | 1 | 16bit | 689 KB | YES | positive_chainsaw |
| chainsaw_long_real_01.wav | generated/synthetic | 18.0s | 44100 Hz | 1 | 16bit | 1550 KB | YES | positive_chainsaw |
| chainsaw_start_real_01.wav | generated/synthetic | 8.0s | 44100 Hz | 1 | 16bit | 689 KB | YES | positive_chainsaw |
| engine_generator_real_01.wav | generated/synthetic | 8.0s | 44100 Hz | 1 | 16bit | 689 KB | YES | negative_non_chainsaw |
| forest_ambient_real_01.wav | generated/synthetic | 10.0s | 44100 Hz | 1 | 16bit | 861 KB | YES | negative_non_chainsaw |
| human_voice_real_01.wav | generated/synthetic | 8.0s | 44100 Hz | 1 | 16bit | 689 KB | YES | negative_non_chainsaw |
| motorcycle_real_01.wav | generated/synthetic | 8.0s | 44100 Hz | 1 | 16bit | 689 KB | YES | negative_non_chainsaw |
| rain_wind_real_01.wav | generated/synthetic | 10.0s | 44100 Hz | 1 | 16bit | 861 KB | YES | negative_non_chainsaw |

## chainsaw_audio

Path: `/Users/macbookm1max321tb/Library/CloudStorage/GoogleDrive-pagi.betech@gmail.com/My Drive/1A_BETech Files/chainsaw_audio`
Files: 6

| File | Origin | Duration | SR | Ch | Depth | Size | Usable | Recommend |
|------|--------|----------|-----|-----|-------|------|--------|-----------|
| chainsaw-noises-002.wav | user-provided/local recording | 226.8s | 192000 Hz | 2 | 32bit | 340161 KB | no | positive_chainsaw |
| chainsaw-noises-003.wav | user-provided/local recording | 103.9s | 192000 Hz | 2 | 32bit | 155841 KB | no | positive_chainsaw |
| chainsaw-start-attempts.wav | user-provided/local recording | 6.8s | 44100 Hz | 2 | 16bit | 1171 KB | YES | positive_chainsaw |
| chainsaw.wav | user-provided/local recording | 115.6s | 44100 Hz | 2 | 16bit | 19918 KB | YES | positive_chainsaw |
| chainsaw2.wav | user-provided/local recording | 59.6s | 44100 Hz | 2 | 24bit | 15402 KB | no | positive_chainsaw |
| chainsaw3.wav | user-provided/local recording | 15.8s | 44100 Hz | 2 | 16bit | 2726 KB | YES | positive_chainsaw |

### Notes on Google Drive real recordings

**3 files ready to use** (need mono conversion):
- `chainsaw-start-attempts.wav` — short startup burst, good for quick test
- `chainsaw.wav` — 115s full session, excellent for long-running validation
- `chainsaw3.wav` — 15.8s segment, good single-file test

**3 files need format conversion before use**:
- `chainsaw-noises-002.wav` — 192kHz/32bit/stereo (~340 MB). Convert: `ffmpeg -i in.wav -ac 1 -ar 44100 -sample_fmt s16 out.wav`
- `chainsaw-noises-003.wav` — 192kHz/32bit/stereo (~155 MB). Same conversion needed.
- `chainsaw2.wav` — 24-bit/stereo (~15 MB). Convert: `ffmpeg -i in.wav -ac 1 -sample_fmt s16 out.wav`

### Recommended validation set

**Primary** (test_audio_real/):
- Positive: `chainsaw_cutting_real_01.wav`, `chainsaw_long_real_01.wav`
- Negative: `motorcycle_real_01.wav`, `forest_ambient_real_01.wav`
- Borderline: `brush_cutter_real_01.wav`

**Real recording supplement** (after mono+44100Hz conversion):
- `chainsaw.wav` (Google Drive) — real chainsaw, 115s
- `chainsaw3.wav` (Google Drive) — real chainsaw, 15.8s
