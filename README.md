# 🐾 Dr. Paws – AI Veterinary Assistant for Alexa+ (MCP) and Voice

Dr. Paws helps panicking pet owners by voice: it triages emergencies, warns about toxic foods, and books vet appointments.

It now runs two ways:

1. **Alexa+ MCP server (new, built for the Amazon Build, Ship, Shape Hackathon 2026).** A self-hosted MCP server over **Streamable HTTP at `/mcp`**, spec **2025-11-25**, built with the official MCP Python SDK (v2).
2. **Real-time voice agent (original).** LiveKit WebRTC + Groq STT/LLM + ElevenLabs TTS, sub-2s speech-to-response.

> Dr. Paws gives first-aid guidance, not a diagnosis. Always confirm with a vet.

---

## 🗣️ Alexa+ experience

> **"Alexa, my cat ate part of a lily."**
> → `check_food_toxicity` → *"Lily is dangerous for a cat… Go to an emergency vet immediately. Treatment within 18 hours is critical."*

> **"Alexa, my dog's belly is swollen and he keeps retching."**
> → `triage_pet_emergency` → `EMERGENCY` (possible bloat/GDV) → *"Go to the nearest emergency vet right now."*

> **"My cat has vomited twice today."**
> → `triage_pet_emergency` → `VISIT_SOON` → `check_appointment_slots` → `book_vet_appointment` → *"You're booked at 14:00 today."*

## 🧰 MCP tools

| Tool | What it does |
|---|---|
| `triage_pet_emergency(species, symptoms)` | Returns `EMERGENCY` / `VISIT_SOON` / `HOME_CARE`, red flags, first-aid steps and a spoken `voice_response` |
| `check_food_toxicity(species, food)` | Known toxins (chocolate, grapes, xylitol, onion, lily, paracetamol…) with severity, why, and what to do |
| `check_appointment_slots()` | Today's open clinic slots (n8n + Supabase, demo store fallback) |
| `book_vet_appointment(owner_name, species, issue, time)` | Books a slot (n8n + Supabase, demo store fallback) |

Every tool returns a short `voice_response` written to be read aloud by Alexa.

## 🛡️ Safety design

- **Rules first, LLM second.** A deterministic red-flag engine (`mcp_server/knowledge.py`) sets the minimum urgency. The LLM (Groq, Llama 3.3 70B) can **raise** urgency but can **never lower** it, so a bloat or blocked-bladder case can't be downgraded by a model.
- **Works without keys.** No `GROQ_API_KEY`? Triage still works on rules plus templated guidance. No n8n? Booking uses an in-memory demo store. Judges can test immediately.

## 🏗️ Architecture

```
Alexa+ / any MCP client
        │  Streamable HTTP (MCP 2025-11-25)
        ▼
  Dr. Paws MCP server  (mcp_server/server.py, MCP Python SDK v2)
        ├── knowledge.py   red-flag rules + toxicity table (deterministic)
        ├── Groq LLM       calm spoken first-aid guidance (optional)
        └── n8n webhooks → Supabase PostgreSQL   appointment slots/booking
```

## ⚙️ Run the MCP server

```bash
cd mcp_server
pip install -r requirements.txt
python server.py                 # → http://localhost:8000/mcp
python test_client.py            # calls all 4 tools over Streamable HTTP
```

Optional `.env` in `mcp_server/`:

```
GROQ_API_KEY=...
N8N_CHECK_SLOTS=...
N8N_BOOK_APPOINTMENT=...
MCP_ALLOWED_HOSTS=your-app.onrender.com   # enables DNS-rebinding protection
```

Inspect it with MCP Inspector: `npx @modelcontextprotocol/inspector` → transport *Streamable HTTP* → URL `http://localhost:8000/mcp`.

**Deploy:** `render.yaml` is included (Render → New → Blueprint). The MCP endpoint is `https://<your-app>.onrender.com/mcp`.

## 🎙️ Run the original LiveKit voice agent

1. Create a venv and `pip install -r requirements.txt`
2. Import the n8n workflow and set the keys from `.env_exmple` (Groq, ElevenLabs, LiveKit, n8n)
3. `python agent.py dev`

## 🛠️ Tech stack

MCP Python SDK v2 (Streamable HTTP) · Groq (Llama 3.3 70B, Whisper STT) · LiveKit WebRTC · ElevenLabs TTS · n8n · Supabase PostgreSQL · Python

## 📸 Voice agent screenshots

![Initial talking](docs/images/1.%20Initial%20talking.png)
![Handles interruption](docs/images/3.%20Handles%20the%20interuption%20in%20the%20call%20too.png)

## 📄 License

MIT, see [LICENSE](LICENSE).
