import asyncio, json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
async def main():
    async with streamable_http_client(__import__("sys").argv[1] if len(__import__("sys").argv)>1 else "http://127.0.0.1:8000/mcp") as (r, w, *_):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            print("protocol:", init.protocol_version, "| server:", init.server_info.name)
            print("tools:", [t.name for t in (await s.list_tools()).tools])
            for name, args in [
                ("triage_pet_emergency", {"species":"dog","symptoms":"his belly is bloated and he keeps retching but nothing comes out"}),
                ("triage_pet_emergency", {"species":"cat","symptoms":"vomiting twice since morning"}),
                ("check_food_toxicity", {"species":"dog","food":"dark chocolate"}),
                ("check_food_toxicity", {"species":"cat","food":"lily"}),
                ("check_appointment_slots", {}),
                ("book_vet_appointment", {"owner_name":"Asad","species":"cat","issue":"vomiting","time":"14:00"}),
                ("check_appointment_slots", {}),
            ]:
                res = await s.call_tool(name, args)
                d = res.structured_content or json.loads(res.content[0].text)
                print(f"\n{name}: {d.get('urgency', d.get('status',''))} -> {d.get('voice_response')}")
asyncio.run(main())
