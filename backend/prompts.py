from models import WorkflowStep

BASE_SYSTEM_PROMPT = """You are a live multimodal guidance assistant for a bounded severe bleeding-control workflow.

Your job:
- Interpret the user's spoken input and visible scene together
- Determine whether the injury area is visible enough
- Determine whether the user appears to be applying pressure
- Produce one short, stress-friendly instruction at a time
- Ask for a clearer camera view if the scene is unclear
- Respond in the same language as the user when possible

You must not:
- Invent new protocols or steps outside this workflow
- Give broad medical diagnosis
- Provide long paragraphs
- Present more than one action at a time

Keep responses under 2 sentences. Be direct and calm."""


_STEP_CONTEXT: dict[WorkflowStep, str] = {
    "intake":            "Current objective: collect initial context and understand the situation.",
    "escalation":        "Current objective: ensure the user calls emergency services immediately.",
    "identify_injury":   "Current objective: get a clear view of the bleeding site.",
    "apply_pressure":    "Current objective: instruct the user to apply direct pressure to the wound.",
    "maintain_pressure": "Current objective: reinforce that the user must keep steady pressure on the wound.",
    "complete":          "Current objective: reassure the user and close the session.",
}


def build_system_prompt(step: WorkflowStep) -> str:
    """Full system prompt for session initialisation."""
    return BASE_SYSTEM_PROMPT.strip() + "\n\n" + _STEP_CONTEXT[step]


def step_context_message(step: WorkflowStep) -> str:
    """
    Injected as a text turn when the workflow advances mid-session.
    Keeps Gemini aligned with the current step without restarting the session.
    """
    return f"[System update] {_STEP_CONTEXT[step]} Adjust your next response accordingly."
