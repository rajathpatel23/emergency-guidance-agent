from dataclasses import dataclass
from typing import Literal

from loguru import logger
from models import ModelInterpretation, SessionState, WorkflowStep

# ---------------------------------------------------------------------------
# State configuration — CPR workflow
# ---------------------------------------------------------------------------

@dataclass
class StateConfig:
    label: str
    objective: str
    default_instruction: str
    allowed_next: list


STATES: dict = {
    "intake": StateConfig(
        label="Assess the Scene",
        objective="Confirm the scene is safe and establish what is happening.",
        default_instruction="Tell me what's happening. Is someone unconscious?",
        allowed_next=["check_responsiveness"],
    ),
    "check_responsiveness": StateConfig(
        label="Check Responsiveness",
        objective="Determine if the patient is unresponsive and not breathing normally.",
        default_instruction="Tap their shoulders firmly and shout 'Are you okay?' — do they respond?",
        allowed_next=["call_emergency"],
    ),
    "call_emergency": StateConfig(
        label="Call Emergency Services",
        objective="Ensure 911 (or local emergency number) has been called.",
        default_instruction="Call 911 now — or ask someone nearby to call while you start CPR.",
        allowed_next=["position_hands"],
    ),
    "position_hands": StateConfig(
        label="Position Your Hands",
        objective="Get the rescuer's hands correctly placed on the patient's chest.",
        default_instruction="Kneel beside them. Place the heel of your hand on the center of their chest, then your other hand on top. Interlock your fingers.",
        allowed_next=["start_compressions"],
    ),
    "start_compressions": StateConfig(
        label="Start Compressions",
        objective="Begin chest compressions at the correct depth and rate.",
        default_instruction="Push down hard — at least 2 inches — then let the chest fully rise. Aim for 100 to 120 pushes per minute.",
        allowed_next=["keep_rhythm"],
    ),
    "keep_rhythm": StateConfig(
        label="Keep the Rhythm",
        objective="Maintain continuous compressions and reinforce correct technique.",
        default_instruction="Keep going — hard and fast. Don't stop to check. Count to 30, then give 2 rescue breaths if trained.",
        allowed_next=["continue_loop"],
    ),
    "continue_loop": StateConfig(
        label="Continue CPR",
        objective="Sustain CPR cycles until help arrives or the patient recovers.",
        default_instruction="You're doing great. Keep the rhythm going — 30 compressions, 2 breaths. Help is on the way.",
        allowed_next=["complete"],
    ),
    "complete": StateConfig(
        label="Help Arrived",
        objective="Hand off to emergency responders.",
        default_instruction="Help has arrived. Step back and let them take over. You did the right thing.",
        allowed_next=[],
    ),
}

# ---------------------------------------------------------------------------
# Decision type
# ---------------------------------------------------------------------------

DecisionKind = Literal["advance", "repeat", "clarify", "stay"]


@dataclass
class WorkflowDecision:
    kind: str
    next_step: str
    reason: str = ""


# ---------------------------------------------------------------------------
# Core transition logic
# ---------------------------------------------------------------------------

def evaluate(
    session: SessionState,
    interpretation: ModelInterpretation,
    user_action,  # "done" | "repeat" | None
) -> WorkflowDecision:
    """
    Decide what to do next based on session state + audio-derived interpretation.
    No video frames — all signals inferred from what the user says.
    """
    step = session.current_step

    # --- Explicit user action takes priority ---
    if user_action == "done":
        config = STATES[step]
        if config.allowed_next:
            return WorkflowDecision(
                kind="advance",
                next_step=config.allowed_next[0],
                reason="user confirmed step complete",
            )
        return WorkflowDecision(kind="stay", next_step=step, reason="terminal state")

    if user_action == "repeat":
        return WorkflowDecision(kind="repeat", next_step=step, reason="user requested repeat")

    # --- Per-step audio signal checks ---
    if step == "intake":
        if bool(interpretation.transcript_summary):
            return WorkflowDecision(kind="advance", next_step="check_responsiveness", reason="scene described")
        return WorkflowDecision(kind="stay", next_step="intake", reason="waiting for context")

    if step == "check_responsiveness":
        # Advance if patient confirmed unresponsive or after first attempt
        if not interpretation.person_responsive or session.step_attempts >= 1:
            return WorkflowDecision(kind="advance", next_step="call_emergency", reason="responsiveness checked")
        return WorkflowDecision(kind="repeat", next_step="check_responsiveness", reason="awaiting responsiveness check")

    if step == "call_emergency":
        # Auto-advance after delivering the instruction once
        if session.step_attempts >= 1:
            return WorkflowDecision(kind="advance", next_step="position_hands", reason="emergency call instruction delivered")
        return WorkflowDecision(kind="repeat", next_step="call_emergency", reason="delivering call instruction")

    if step == "position_hands":
        if interpretation.hands_positioned:
            return WorkflowDecision(kind="advance", next_step="start_compressions", reason="hands positioned")
        if session.step_attempts >= 2:
            return WorkflowDecision(kind="advance", next_step="start_compressions", reason="hand position repeated twice — proceeding")
        return WorkflowDecision(kind="repeat", next_step="position_hands", reason="confirming hand placement")

    if step == "start_compressions":
        if interpretation.compressions_happening:
            return WorkflowDecision(kind="advance", next_step="keep_rhythm", reason="compressions started")
        if session.step_attempts >= 2:
            return WorkflowDecision(kind="advance", next_step="keep_rhythm", reason="compression instruction repeated — proceeding")
        return WorkflowDecision(kind="repeat", next_step="start_compressions", reason="awaiting compression start")

    if step == "keep_rhythm":
        if session.step_attempts >= 3:
            return WorkflowDecision(kind="advance", next_step="continue_loop", reason="rhythm reinforced")
        return WorkflowDecision(kind="repeat", next_step="keep_rhythm", reason="reinforcing rhythm")

    if step == "continue_loop":
        if session.step_attempts >= 5:
            return WorkflowDecision(kind="advance", next_step="complete", reason="extended CPR — prompting handoff check")
        return WorkflowDecision(kind="repeat", next_step="continue_loop", reason="sustaining CPR")

    return WorkflowDecision(kind="stay", next_step="complete", reason="terminal state")


def apply_decision(session: SessionState, decision: WorkflowDecision) -> SessionState:
    """Apply a WorkflowDecision to session state and return the updated state."""
    prev = session.current_step
    if decision.kind == "advance":
        session.current_step = decision.next_step
        session.step_attempts = 0
        logger.info(f"[workflow] ADVANCE  {prev} → {session.current_step}  reason='{decision.reason}'")
    elif decision.kind == "clarify":
        session.step_attempts += 1
        logger.debug(f"[workflow] CLARIFY  step={prev}  attempts={session.step_attempts}")
    elif decision.kind == "repeat":
        session.step_attempts += 1
        logger.debug(f"[workflow] REPEAT   step={prev}  attempts={session.step_attempts}")
    else:
        logger.debug(f"[workflow] STAY     step={prev}")
    return session


def current_config(session: SessionState) -> StateConfig:
    return STATES[session.current_step]


def step_number(step: str) -> int:
    """1-based step index for progress display."""
    order = [
        "intake", "check_responsiveness", "call_emergency",
        "position_hands", "start_compressions", "keep_rhythm",
        "continue_loop", "complete",
    ]
    return order.index(step) + 1


TOTAL_STEPS = len(STATES)
