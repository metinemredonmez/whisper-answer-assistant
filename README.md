# Whisper Answer Assistant – Tek README

Mikrofondan **gerçek zamanlı İngilizce transkript** alır; cümle **İngilizce soru** ise **kısa ve söylenebilir** bir İngilizce yanıtı ChatGPT’den anlık olarak üretir.

---

## ✨ Özellikler
- WebRTC VAD ile **segment bazlı dinleme**
- `faster-whisper` ASR (dil otomatik; **EN** ise yönlendirme)
- **İngilizce soru tespiti**
- **Kısa, konuşulabilir** İngilizce yanıt (stream)
- İsteğe bağlı: **yanıtı panoya kopyalama**
- İsteğe bağlı **sıkı filtreler**: minimum İngilizce dil güveni, minimum karakter
- İsteğe bağlı **sadece teknik sorulara** yanıt (anahtar kelime listesi)

---

## ✅ Gereksinimler
- Python **3.9+**
- Mikrofon erişimi olan macOS / Windows / Linux
- `.env` içinde **OpenAI API key**

---

## 🛠 Kurulum
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -e .

cp .env.example .env           # içine OPENAI_API_KEY=... yaz
# (opsiyonel) configs/keywords.en.txt dosyasına teknik terimleri ekle (her satıra bir tane)
```

---

## ▶️ Çalıştırma
```bash
waa --list-devices
waa --whisper-model base --device <INDEX>

# PATH karışırsa (ör. micromamba), modül ya da tam yol kullan:
python -m waa.cli --whisper-model base --device <INDEX>
# veya
./.venv/bin/waa --whisper-model base --device <INDEX>
```
- `--device` vermezsen sistemin **varsayılan giriş** cihazı kullanılır.
- Model önerisi: `tiny` (en hızlı), `base` (dengeli), `small/medium` (daha doğru).

---

## ⚙️ Ayarlar (tek yer)
Tüm ayarlar **`configs/settings.yaml`** dosyasında tutulur:

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

  # Sadece teknik anahtar kelime varsa yanıtla:
  # (Bunu TRUE yaparsan yalnız teknik sorulara cevap üretilir)
  require_dev_keyword: false

  # İsteğe bağlı daha sıkı filtre:
  # - Whisper EN dil güven eşiği
  # - Çok kısa soruları yok say
  min_lang_prob: 0.75
  min_chars: 12
```

### 🔧 “Sadece teknik sorular” modu
`require_dev_keyword: true` yaparsan, uygulama **yalnızca** aşağıdaki dosyadaki terimlerden **en az biri** geçen İngilizce soruları ChatGPT’ye yollar:

**`configs/keywords.en.txt` (örnek):**
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

---

## 🧪 Beklenen çıktı
Her biten cümle için transkript satırı görünür.  
Cümle **İngilizce soru** ise aşağıdaki akış gelir:
```
🧩 English question detected:
> <soru>
🤖 Suggested answer (speak this):
<stream edilen yanıt...>
```

---

## 🧯 Sorun Giderme (tek bakış)
- **Invalid number of channels** → Çıkış-only aygıt seçilmiş. `--list-devices` çıktısında `(1 in, 0 out)` olan mikrofonu seç.  
- **PATH/micromamba çakışması** → `python -m waa.cli ...` veya `./.venv/bin/waa ...` kullan.  
- **`webrtcvad` pkg_resources uyarısı** → Zararsız, göz ardı edebilirsin.  
- **macOS mikrofon izni** → Sistem Ayarları → Gizlilik & Güvenlik → Mikrofon → Terminal/IDE’ye izin ver.  
- **Linux** → PortAudio için: `sudo apt-get install portaudio19-dev`.  
- **Windows** → Gerekirse VC++ Build Tools kurulu olsun.

---

## 🔌 (Opsiyonel) Hotkey ile aç/kapat
Toplantıda **ben konuşurken yanıt üretmesin**, karşı taraf konuşurken **açayım** dersen:

1. Kur:
   ```bash
   pip install pynput
   ```
2. `src/waa/app.py` içinde (üst kısma) ekle:
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
3. `run()` başında listener’ı aç:
   ```python
   listener = keyboard.Listener(on_press=on_press)
   listener.start()
   ```
4. Soru tetikleme bloğunun başında kontrol et:
   ```python
   if not ARMED:
       continue
   ```

---

## 🎧 (Opsiyonel) Sadece karşı tarafı dinle (Pro)
Kendi sesin tetikleme yapmasın istiyorsan, macOS’ta **BlackHole** / **Loopback** gibi sanal ses aygıtı ile toplantı uygulamasının **çıktısını** bu programa giriş olarak ver:
- Sistem ses çıkışı = BlackHole
- Meet/Zoom/Teams çıkışı = BlackHole
- Uygulamada `--device` olarak BlackHole girişini seç
- (İsteğe göre Multi-Output ile aynı sesi kulaklığa da ver)

---

## ✅ Hızlı Kontrol Listesi
- [ ] `.env` → `OPENAI_API_KEY=...`  
- [ ] `waa --list-devices` ile mikrofon index’i bulundu  
- [ ] Gerekirse `require_dev_keyword: true` + `keywords.en.txt` düzenlendi  
- [ ] (Opsiyonel) `min_lang_prob`, `min_chars` eşikleri ayarlandı  
- [ ] Çalıştır:  
  ```bash
  python -m waa.cli --whisper-model base --device <INDEX>
  # veya
  ./.venv/bin/waa --whisper-model base --device <INDEX>
  ```
