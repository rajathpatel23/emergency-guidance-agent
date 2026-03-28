from dataclasses import dataclass
from typing import Literal

from models import ModelInterpretation, SessionState, WorkflowStep

# ---------------------------------------------------------------------------
# State configuration
# ---------------------------------------------------------------------------

@dataclass
class StateConfig:
    label: str
    objective: str
    default_instruction: str
    allowed_next: list[WorkflowStep]


STATES: dict[WorkflowStep, StateConfig] = {
    "intake": StateConfig(
        label="Intake",
        objective="Collect initial context. See the injury. Understand urgency.",
        default_instruction="Show me the injury and tell me what happened.",
        allowed_next=["escalation"],
    ),
    "escalation": StateConfig(
        label="Escalation",
        objective="Ensure emergency services are contacted.",
        default_instruction="This looks serious. Call emergency services now if you have not already.",
        allowed_next=["identify_injury"],
    ),
    "identify_injury": StateConfig(
        label="Identify Injury",
        objective="Get a clear view of the bleeding site.",
        default_instruction="Move the camera closer to the bleeding area.",
        allowed_next=["apply_pressure"],
    ),
    "apply_pressure": StateConfig(
        label="Apply Pressure",
        objective="Instruct user to apply direct pressure to the wound.",
        default_instruction="Press firmly on the wound with a clean cloth or towel now.",
        allowed_next=["maintain_pressure"],
    ),
    "maintain_pressure": StateConfig(
        label="Maintain Pressure",
        objective="Reinforce continued steady pressure.",
        default_instruction="Keep steady pressure. If blood soaks through, place more cloth on top and keep pressing.",
        allowed_next=["complete"],
    ),
    "complete": StateConfig(
        label="Complete",
        objective="Close the session cleanly.",
        default_instruction="Good. Keep pressure on the wound until help arrives.",
        allowed_next=[],
    ),
}

# ---------------------------------------------------------------------------
# Decision type
# ---------------------------------------------------------------------------

DecisionKind = Literal["advance", "repeat", "clarify", "stay"]


@dataclass
class WorkflowDecision:
    kind: DecisionKind
    next_step: WorkflowStep
    reason: str = ""


# ---------------------------------------------------------------------------
# Core transition logic
# ---------------------------------------------------------------------------

def evaluate(
    session: SessionState,
    interpretation: ModelInterpretation,
    user_action: str | None,  # "done" | "repeat" | None
) -> WorkflowDecision:
    """
    Decide what to do next based on session state, model interpretation,
    and explicit user action. The app — not Gemini — owns this logic.
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

    # --- Scene is unclear: ask for better angle ---
    if interpretation.view_unclear:
        return WorkflowDecision(kind="clarify", next_step=step, reason="view unclear")

    # --- Per-step model signal checks ---
    if step == "intake":
        has_context = bool(interpretation.transcript_summary) or interpretation.injury_visible
        if has_context:
            return WorkflowDecision(kind="advance", next_step="escalation", reason="initial context captured")
        return WorkflowDecision(kind="stay", next_step="intake", reason="waiting for context")

    if step == "escalation":
        # Auto-advance after one delivery
        if session.step_attempts >= 1:
            return WorkflowDecision(kind="advance", next_step="identify_injury", reason="escalation delivered")
        return WorkflowDecision(kind="repeat", next_step="escalation", reason="delivering escalation")

    if step == "identify_injury":
        if interpretation.injury_visible:
            return WorkflowDecision(kind="advance", next_step="apply_pressure", reason="injury visible")
        return WorkflowDecision(kind="repeat", next_step="identify_injury", reason="injury not yet visible")

    if step == "apply_pressure":
        if interpretation.pressure_applied:
            return WorkflowDecision(kind="advance", next_step="maintain_pressure", reason="pressure applied")
        return WorkflowDecision(kind="repeat", next_step="apply_pressure", reason="pressure not yet applied")

    if step == "maintain_pressure":
        if session.step_attempts >= 2:
            return WorkflowDecision(kind="advance", next_step="complete", reason="reinforcement delivered")
        return WorkflowDecision(kind="repeat", next_step="maintain_pressure", reason="reinforcing pressure")

    return WorkflowDecision(kind="stay", next_step="complete", reason="terminal state")


def apply_decision(session: SessionState, decision: WorkflowDecision) -> SessionState:
    """Apply a WorkflowDecision to session state and return the updated state."""
    if decision.kind == "advance":
        session.current_step = decision.next_step
        session.step_attempts = 0
    elif decision.kind in ("repeat", "clarify"):
        session.step_attempts += 1
    # "stay" leaves state unchanged
    return session


def current_config(session: SessionState) -> StateConfig:
    return STATES[session.current_step]


def step_number(step: WorkflowStep) -> int:
    """1-based step index for progress display."""
    order: list[WorkflowStep] = [
        "intake", "escalation", "identify_injury",
        "apply_pressure", "maintain_pressure", "complete",
    ]
    return order.index(step) + 1


TOTAL_STEPS = len(STATES)
