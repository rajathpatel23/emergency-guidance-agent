"""
Manual integration test — simulates a CPR coaching session
without a browser. Run while uvicorn is up on port 8000.

Usage:
    python test_session.py
"""
import asyncio
import json
import httpx
import websockets

BASE_HTTP = "http://localhost:8000"
BASE_WS = "ws://localhost:8000"


async def run():
    # 1. Health check
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_HTTP}/health")
        print(f"[health] {r.json()}")

        # 2. Create session
        r = await client.post(f"{BASE_HTTP}/session")
        session = r.json()
        session_id = session["session_id"]
        print(f"[session created] id={session_id} step={session['current_step']}")

    # 3. Open WebSocket and run through the scenario
    uri = f"{BASE_WS}/ws/stream/{session_id}"
    print(f"\n[ws] connecting to {uri}\n")

    async with websockets.connect(uri) as ws:

        async def send(msg: dict):
            await ws.send(json.dumps(msg))
            print(f"  --> sent: {msg}")

        async def recv_until_instruction():
            """Read messages until we get a full instruction response."""
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=15)
                msg = json.loads(raw)
                if msg["type"] == "text_chunk":
                    print(f"  ... chunk: {msg['content']}", end="", flush=True)
                elif msg["type"] == "instruction":
                    print(f"\n  <-- instruction: [{msg['step_label']}] {msg['instruction']}")
                    print(f"      step {msg['step_number']}/{msg['total_steps']} | uncertain={msg['uncertain']}")
                    return msg
                elif msg["type"] == "state_update":
                    print(f"  <-- state_update: step={msg['current_step']}")
                elif msg["type"] == "status":
                    print(f"  <-- status: {msg['status']}")
                elif msg["type"] == "error":
                    print(f"  <-- ERROR: {msg['message']}")
                    return None

        # Wait for connected status
        raw = await asyncio.wait_for(ws.recv(), timeout=10)
        msg = json.loads(raw)
        print(f"  <-- {msg['type']}: step={msg.get('current_step')}\n")

        # --- Step 1: intake — describe the situation
        print("[test] describing unresponsive patient...")
        await send({"type": "transcript", "text": "He's not responding I don't think he's breathing."})
        await recv_until_instruction()

        # --- Step 2: user confirms escalation step
        print("\n[test] user confirms done with escalation...")
        await send({"type": "user.done"})
        await recv_until_instruction()

        # --- Step 3: patient visible / on back
        print("\n[test] sending transcript — patient in view...")
        await send({"type": "transcript", "text": "I can see him on the floor on his back, chest is in the frame."})
        await recv_until_instruction()

        # --- Step 4: compressions
        print("\n[test] user starting compressions...")
        await send({"type": "transcript", "text": "I'm pushing on the center of his chest doing compressions now."})
        await recv_until_instruction()

        # --- Step 5: user confirms continuing
        print("\n[test] user confirms continuing CPR...")
        await send({"type": "user.done"})
        await recv_until_instruction()

        # --- End session
        print("\n[test] ending session...")
        await send({"type": "end"})

    # 4. Verify final state via HTTP
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_HTTP}/session/{session_id}")
        final = r.json()
        print(f"\n[final state] step={final['current_step']} status={final['status']}")
        print(json.dumps(final, indent=2))


if __name__ == "__main__":
    asyncio.run(run())
