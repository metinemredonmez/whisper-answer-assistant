# Whisper Answer Assistant – Single README
Captures **real-time English transcripts** from the microphone; if the sentence is an **English question**, it instantly generates a **short, speakable** English answer from ChatGPT.

## ✨ Features
- WebRTC VAD for **segment-based listening**
- `faster-whisper` ASR (automatic language detection; forwards if EN)
- English question detection
- Short, speakable English answer (streamed)
- Optional: Copy answer to clipboard
- Optional strict filters: minimum English language confidence, minimum characters
- Optional answer only technical questions (keyword list)

## ✅ Requirements
- Python **3.9+**
- macOS / Windows / Linux with microphone access
- `.env` containing **OpenAI API key**

## 🛠 Installation
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -e .

cp .env.example .env           # add OPENAI_API_KEY=... inside
# (optional) Add technical terms to configs/keywords.en.txt (one per line)
```

## ▶️ Running
```bash
waa --list-devices
waa --whisper-model base --device <INDEX>

# If PATH conflicts occur (e.g., micromamba), use module or full path:
python -m waa.cli --whisper-model base --device <INDEX>
# or
./.venv/bin/waa --whisper-model base --device <INDEX>
```
- If you don’t provide `--device`, the system default input device will be used.
- Recommended models: `tiny` (fastest), `base` (balanced), `small/medium` (more accurate).

## ⚙️ Settings (single location)
All settings are in **`configs/settings.yaml`**:
```yaml
audio:
  sample_rate: 16000
  frame_ms: 20
  vad_aggressiveness: 2
  max_segment_sec: 15
  silence_follow_sec: 0.6

assistant:
  auto_copy: false
  openai_model: gpt-4o-mini

  # Answer only if technical keyword is present:
  # (If TRUE, only technical questions will get answers)
  require_dev_keyword: false

  # Optional stricter filters:
  # - Whisper EN language probability threshold
  # - Ignore very short questions
  min_lang_prob: 0.75
  min_chars: 12
```

### 🔧 “Only technical questions” mode
If you set `require_dev_keyword: true`, the app will send **only** English questions containing **at least one** term from the following file to ChatGPT:
```
api
sdk
python
docker
kubernetes
sql
postgres
mongodb
redis
kafka
llm
rag
embedding
security
oauth
jwt
latency
scalability
throughput
```

## 🧪 Expected output
```
🧩 English question detected:
> <question>
🤖 Suggested answer (speak this):
<streamed answer...>
```

## 🧯 Troubleshooting (at a glance)
- **Invalid number of channels** → You selected an output-only device. From `--list-devices` output, choose a microphone with `(1 in, 0 out)`.
- **PATH/micromamba conflicts** → Use `python -m waa.cli ...` or `./.venv/bin/waa ...`.
- **`webrtcvad` pkg_resources warning** → Harmless, can be ignored.
- **macOS mic permission** → System Settings → Privacy & Security → Microphone → Allow Terminal/IDE.
- **Linux** → For PortAudio: `sudo apt-get install portaudio19-dev`.
- **Windows** → Make sure VC++ Build Tools are installed if needed.

## 🔌 (Optional) Toggle on/off with hotkey
```bash
pip install pynput
```
In `src/waa/app.py` (top of file) add:
```python
from pynput import keyboard
ARMED = True
def on_press(key):
    global ARMED
    try:
        if key == keyboard.Key.f8:
            ARMED = not ARMED
            print(f"\n[Toggle] Answer routing: {'ON' if ARMED else 'OFF'}")
    except Exception:
        pass
```
At the start of `run()` open the listener:
```python
listener = keyboard.Listener(on_press=on_press)
listener.start()
```
At the start of the question-trigger block, check:
```python
if not ARMED:
    continue
```

## 🎧 (Optional) Listen only to the other party (Pro)
- System audio output = BlackHole
- Meet/Zoom/Teams output = BlackHole
- In the app, select BlackHole input with `--device`
- (Optionally use Multi-Output to also send the same sound to your headphones)

## ✅ Quick Checklist
- `.env` → `OPENAI_API_KEY=...`
- Found microphone index with `waa --list-devices`
- If needed, set `require_dev_keyword: true` + edit `keywords.en.txt`
- (Optional) Adjust `min_lang_prob`, `min_chars` thresholds
```bash
python -m waa.cli --whisper-model base --device <INDEX>
# or
./.venv/bin/waa --whisper-model base --device <INDEX>
```
