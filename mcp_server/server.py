"""Dr. Paws MCP server for Alexa+.

A self-hosted MCP server (Streamable HTTP at /mcp) that lets Alexa+ (or any
MCP client) triage pet emergencies, check food toxicity, and book vet
appointments by voice.

Run:  python mcp_server/server.py      -> http://localhost:8000/mcp
"""

import json
import os
from datetime import date

import httpx
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from knowledge import SAFE_TREATS, URGENCY_ORDER, lookup_food, rule_triage

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
N8N_CHECK_SLOTS = os.getenv("N8N_CHECK_SLOTS")
N8N_BOOK_APPOINTMENT = os.getenv("N8N_BOOK_APPOINTMENT")

ALL_SLOTS = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00"]
_demo_bookings: dict[str, dict] = {}  # used when n8n is not configured

DISCLAIMER = "Dr. Paws gives first-aid guidance, not a diagnosis. Always confirm with a vet."

mcp = MCPServer(
    name="dr-paws",
    title="Dr. Paws - AI Veterinary Assistant",
    version="2.0.0",
    instructions=(
        "Dr. Paws helps pet owners by voice. For any symptom, call triage_pet_emergency first. "
        "If the pet ate something, call check_food_toxicity. If urgency is VISIT_SOON or the user "
        "wants an appointment, call check_appointment_slots then book_vet_appointment. "
        "Read the voice_response field aloud. If urgency is EMERGENCY, tell the user to go to an "
        "emergency vet now before anything else."
    ),
)


# ---------------------------------------------------------------- helpers
async def _groq_guidance(species: str, symptoms: str, urgency: str) -> dict | None:
    """Ask Groq for calm, spoken first-aid steps. Returns None if unavailable."""
    if not GROQ_API_KEY:
        return None
    prompt = (
        f"You are Dr. Paws, a calm veterinary first-aid assistant speaking through a smart speaker.\n"
        f"Species: {species}\nSymptoms reported: {symptoms}\n"
        f"Minimum urgency from safety rules: {urgency} (you may raise it, never lower it).\n"
        'Reply ONLY with JSON: {"urgency": "EMERGENCY|VISIT_SOON|HOME_CARE", '
        '"first_aid_steps": [max 4 short steps], "follow_up_question": "one question", '
        '"voice_response": "2-3 calm spoken sentences, no lists"}'
    )
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                },
            )
            r.raise_for_status()
            return json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception:
        return None


def _template_guidance(urgency: str) -> dict:
    if urgency == "EMERGENCY":
        steps = [
            "Keep your pet calm, still and warm.",
            "Do not give food, water or human medicine.",
            "Call the nearest emergency vet and go now.",
        ]
        voice = "This sounds like an emergency. Keep your pet calm and still, and go to the nearest emergency vet right now."
    elif urgency == "VISIT_SOON":
        steps = [
            "Keep fresh water available.",
            "Note when symptoms started and how often they happen.",
            "Book a vet visit within 24 hours, sooner if it gets worse.",
        ]
        voice = "This isn't an emergency yet, but your pet should see a vet within a day. I can book you a slot if you like."
    else:
        steps = [
            "Monitor your pet for the next 24 hours.",
            "Make sure they are eating, drinking and toileting normally.",
            "Call a vet if anything changes or gets worse.",
        ]
        voice = "This sounds mild. Keep an eye on your pet for the next day, and call a vet if anything gets worse."
    return {"first_aid_steps": steps, "voice_response": voice, "follow_up_question": None}


# ---------------------------------------------------------------- tools
@mcp.tool(title="Triage a pet emergency")
async def triage_pet_emergency(species: str, symptoms: str) -> dict:
    """Assess a pet's symptoms and return urgency (EMERGENCY, VISIT_SOON, HOME_CARE)
    with calm first-aid steps and a short spoken reply.

    Args:
        species: Type of animal, e.g. dog, cat, bird, rabbit
        symptoms: What the owner sees, in their own words
    """
    rule_urgency, reasons = rule_triage(symptoms)
    llm = await _groq_guidance(species, symptoms, rule_urgency)

    urgency = rule_urgency
    if llm and URGENCY_ORDER.get(llm.get("urgency"), -1) > URGENCY_ORDER[rule_urgency]:
        urgency = llm["urgency"]  # model may escalate, never downgrade

    guidance = llm if llm else _template_guidance(urgency)
    if llm and urgency != llm.get("urgency"):
        guidance = {**llm, "voice_response": _template_guidance(urgency)["voice_response"]}

    return {
        "species": species,
        "urgency": urgency,
        "red_flags": reasons,
        "first_aid_steps": guidance.get("first_aid_steps", []),
        "follow_up_question": guidance.get("follow_up_question"),
        "voice_response": guidance.get("voice_response"),
        "recommend_booking": urgency == "VISIT_SOON",
        "guidance_source": "groq+rules" if llm else "rules",
        "disclaimer": DISCLAIMER,
    }


@mcp.tool(title="Check if a food is toxic for a pet")
def check_food_toxicity(species: str, food: str) -> dict:
    """Check whether a food, plant or medicine is dangerous for a pet and what to do.

    Args:
        species: Type of animal, e.g. dog, cat, bird
        food: What the pet ate, e.g. chocolate, grapes, lily, paracetamol
    """
    result = lookup_food(food, species)
    if result is None:
        return {
            "food": food,
            "species": species,
            "known_toxic": False,
            "severity": "UNKNOWN",
            "voice_response": (
                f"I don't have {food} in my poison list for a {species}. If your pet seems unwell "
                "or ate a lot, call your vet to be safe."
            ),
            "disclaimer": DISCLAIMER,
        }
    severity, why, action = result
    voice = f"{food.capitalize()} is {'dangerous' if severity == 'HIGH' else 'risky'} for a {species}. {why} {action}"
    return {
        "food": food,
        "species": species,
        "known_toxic": True,
        "severity": severity,
        "why": why,
        "action": action,
        "urgency": "EMERGENCY" if severity == "HIGH" else "VISIT_SOON",
        "safe_alternatives": SAFE_TREATS.get(species.lower()),
        "voice_response": voice,
        "disclaimer": DISCLAIMER,
    }


@mcp.tool(title="Check today's vet appointment slots")
async def check_appointment_slots() -> dict:
    """List today's open appointment slots at the Dr. Paws clinic."""
    booked: list[str] = []
    source = "demo"
    if N8N_CHECK_SLOTS:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                data = (await client.post(N8N_CHECK_SLOTS)).json()
            booked = [s.strip()[:5] for s in data.get("booked_slots", "").split(",") if s.strip()]
            source = "n8n+supabase"
        except Exception:
            source = "demo (n8n unreachable)"
    if source.startswith("demo"):
        booked = list(_demo_bookings)
    available = [s for s in ALL_SLOTS if s not in booked]
    voice = (
        f"I have {', '.join(available[:3])}{' and more' if len(available) > 3 else ''} open today. Which works for you?"
        if available
        else "Sorry, there are no slots left today."
    )
    return {"date": date.today().isoformat(), "available_slots": available, "source": source, "voice_response": voice}


@mcp.tool(title="Book a vet appointment")
async def book_vet_appointment(owner_name: str, species: str, issue: str, time: str) -> dict:
    """Book a vet appointment for today.

    Args:
        owner_name: Full name of the pet owner
        species: Type of animal, e.g. dog, cat
        issue: Short description of the problem
        time: Slot in HH:MM 24-hour format, e.g. 14:00
    """
    time = time.strip()[:5]
    if time not in ALL_SLOTS:
        return {"status": "invalid_time", "voice_response": f"{time} isn't a clinic slot. Please pick one of {', '.join(ALL_SLOTS)}."}

    payload = {
        "patient_name": owner_name,
        "animal_type": species,
        "issue": issue,
        "appointment_date": date.today().isoformat(),
        "appointment_time": time,
    }
    if N8N_BOOK_APPOINTMENT:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                data = (await client.post(N8N_BOOK_APPOINTMENT, json=payload)).json()
            if data.get("status") == "confirmed":
                return {"status": "confirmed", "source": "n8n+supabase", **payload,
                        "voice_response": f"You're booked, {owner_name}. See you and your {species} at {time} today."}
            return {"status": "failed", "voice_response": "Sorry, I couldn't book that slot. Want to try another time?"}
        except Exception:
            pass  # fall through to demo store

    if time in _demo_bookings:
        return {"status": "taken", "voice_response": f"{time} was just taken. Want me to check other slots?"}
    _demo_bookings[time] = payload
    return {"status": "confirmed", "source": "demo", **payload,
            "voice_response": f"You're booked, {owner_name}. See you and your {species} at {time} today."}


# ---------------------------------------------------------------- run
if __name__ == "__main__":
    hosts = [h.strip() for h in os.getenv("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    security = (
        TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts)
        if hosts
        else TransportSecuritySettings(enable_dns_rebinding_protection=False)
    )
    mcp.run(
        transport="streamable-http",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=security,
    )
