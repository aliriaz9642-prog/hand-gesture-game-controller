# Hand Gesture Controller — Asphalt (or any WASD game)

This script tracks both of your hands using your webcam and uses them like a
steering wheel to control the game — without touching any controller or keyboard.

## Gestures

| Gesture | Action | Key |
|---|---|---|
| Both hands roll/tilt left | Steer left | `A` |
| Both hands roll/tilt right | Steer right | `D` |
| One hand's palm fully open | Brake | `S` |
| Both hands normal (fist/grip) | Auto accelerate | `W` (hold) |
| Both thumbs out (other fingers closed) | Nitro/Boost | `Space` + `W` |
| No hands visible | All keys released (pause/safety) | — |

## Setup (on Windows laptop)

1. Install Python (if not already installed): https://www.python.org/downloads/  
   Make sure to tick **"Add Python to PATH"** during installation.

2. Open Terminal/CMD and navigate to the folder where `hand_gesture_control.py` is located.

3. Install the requirements:
   ```
   pip install -r requirements.txt
   ```

4. Open an emulator (BlueStacks / LDPlayer / NoxPlayer), launch Asphalt, and start
   a race. Confirm that the emulator controls Asphalt with **W/A/S/D + Space**
   (this is the default in most emulators — if not, assign these keys in the
   emulator's "Key Mapping" settings).

5. Run the script:
   ```
   python hand_gesture_control.py
   ```

6. A webcam window will open. **Immediately click on the emulator window to bring
   it into focus** — steering won't work until you do this, because keypress
   events are only sent to the active window.

7. Hold your hands in front of the camera in a "steering wheel grip" position and
   test it out. To quit, select the webcam window and press `q`.

## If Detection Is Not Working Correctly (Tuning)

At the top of the script there are values you can adjust based on your
lighting and camera:

- `STEER_ANGLE_THRESHOLD` — how much tilt is required to register a turn
  (default: 12 degrees). If it turns too easily, increase this value (e.g., 18–20).
  If you have to tilt a lot to turn, decrease it.

- If left/right is inverted (tilting left moves the car right), find the blocks
  inside the script where `angle > STEER_ANGLE_THRESHOLD` and
  `angle < -STEER_ANGLE_THRESHOLD` are checked, and swap `KEY_LEFT` / `KEY_RIGHT`
  between them.

- If brake or nitro is not being detected, improve your lighting (your hands
  should be clearly visible to the camera) and try moving slightly closer or
  farther from the camera.

## Important Notes

- The emulator window **must be active (in the foreground)**, otherwise
  keypresses will be sent elsewhere.
- If a hand goes out of the camera's view, the script automatically releases
  all keys (for safety) so the car doesn't drive uncontrolled.
- This is purely keyboard simulation (`pydirectinput`) — no hacking or game
  file modification is happening. It works exactly as if you were pressing
  A/D/W/S yourself.