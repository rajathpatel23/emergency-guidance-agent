# Product Requirements Document (PRD)

## CPR Copilot — Multimodal Emergency Guidance Agent (Hackathon MVP)

---

## 1. Overview

CPR Copilot is a **multimodal emergency guidance assistant** designed to help a bystander perform **CPR (Cardiopulmonary Resuscitation)** in a critical situation.

The system uses:

* **Audio input (voice)**
* **Optional video input (camera)**
* **LLM reasoning (multimodal)**

It provides:

* **Step-by-step voice instructions**
* **Real-time guidance and feedback**
* **Interactive confirmation loop**

⚠️ This is a **demo / assistive tool**, not a replacement for medical professionals.

---

## 2. Goals

### Primary Goal

Deliver a **clear, autonomous CPR guidance experience** in under 3 minutes for demo purposes.

### Success Criteria

* User can follow CPR steps with minimal manual input
* System gives **one instruction at a time**
* System adapts based on user responses
* Strong demo impact (visual + audio loop)

---

## 3. Non-Goals (Important)

* ❌ General medical diagnosis
* ❌ Multiple emergency types
* ❌ Clinical accuracy validation
* ❌ Video tutorial playback (YouTube etc.)
* ❌ Advanced pose detection / accuracy scoring

---

## 4. Target Use Case (ONLY ONE)

### Scenario: CPR Assistance

A user encounters an unresponsive person and needs immediate guidance.

---

## 5. User Flow (Demo Flow)

1. User opens app
2. Selects: **"CPR Emergency"**
3. Grants mic (and optional camera)
4. System begins guidance
5. User follows instructions step-by-step
6. System continues until completion

---

## 6. Core Experience

### Interaction Model

* System is **proactive (autonomous)**
* User gives minimal input (voice or button)
* Instructions are **short and imperative**

Example:

> "Check if the person is responsive. Tap when done."

---

## 7. Workflow (State Machine)

### States

1. **intake**

   * "You are in CPR mode. I will guide you."

2. **check_responsiveness**

   * "Tap their shoulders and ask if they are okay."
   * Wait for confirmation

3. **call_emergency**

   * "Call emergency services now or ask someone nearby."

4. **position_hands**

   * "Place your hands in the center of the chest."

5. **start_compressions**

   * "Start chest compressions. Push hard and fast."

6. **keep_rhythm**

   * System counts: "1, 2, 3..."
   * Reminds: "Keep a steady pace"

7. **continue_loop**

   * "Continue until help arrives"

8. **complete (demo end)**

---

## 8. Multimodal Inputs

### Audio Input

* User responses ("done", "yes")
* Questions

### Video Input (Optional)

* Basic context awareness
* Camera positioning feedback

---

## 9. Outputs

### Primary

* **Voice instructions (TTS)**

### Secondary

* Text instructions on screen
* Visual step indicator

---

## 10. System Architecture (Simplified)

### Frontend

* Lovable (UI)
* Assistant UI (chat / interaction)

### Backend

* Session Manager
* Workflow Engine (state machine)
* Gemini (DeepMind) for reasoning

### Infra

* Unkey (API management)
* Optional: DigitalOcean (deployment)

---

## 11. Autonomy Design

System should:

* Move between states automatically
* Ask for minimal confirmations
* Provide continuous guidance

NOT:

* Wait for full user prompts
* Dump large explanations

---

## 12. Demo Script (Critical)

1. Person lying down
2. Open app → CPR mode
3. System:

   * "Check responsiveness"
4. User taps "done"
5. System:

   * "Start compressions. I’ll count with you"
6. System counts aloud

Duration: ~60–90 seconds

---

## 13. Risks & Mitigations

### Risk: Over-complexity

→ Mitigation: Single use case only

### Risk: Medical liability concerns

→ Mitigation: Add disclaimer

### Risk: Weak demo

→ Mitigation: Strong scripted flow

---

## 14. Future Extensions (Post Hackathon)

* Multiple emergency types
* Sensor integration (Senso)
* Visual pose validation
* Real-time emergency detection

---

## 15. Key Differentiator

A **real-time, multimodal, autonomous agent** that:

* Sees
* Listens
* Guides
* Adapts

All within a **single focused emergency scenario (CPR)**

---

## 16. Summary

CPR Copilot is a **high-impact, tightly scoped hackathon MVP** designed to maximize:

* Autonomy
* Multimodal interaction
* Demo clarity

by focusing on **one life-saving workflow executed well**.
