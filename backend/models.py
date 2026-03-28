from dataclasses import dataclass
from typing import Literal

WorkflowStep = Literal[
    "intake",
    "check_responsiveness",
    "call_emergency",
    "position_hands",
    "start_compressions",
    "keep_rhythm",
    "continue_loop",
    "complete",
]

ViewQuality = Literal["unknown", "clear", "unclear"]
PressureSignal = Literal["unknown", "yes", "no"]
SessionStatus = Literal["active", "ended"]


@dataclass
class SessionState:
    session_id: str
    scenario: str = "cpr"
    language: str = "en"
    current_step: WorkflowStep = "intake"
    called_emergency: bool = False
    view_quality: ViewQuality = "unknown"
    injury_visible: bool = False
    pressure_applied: PressureSignal = "unknown"
    last_instruction: str = ""
    step_attempts: int = 0
    status: SessionStatus = "active"

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "scenario": self.scenario,
            "language": self.language,
            "current_step": self.current_step,
            "called_emergency": self.called_emergency,
            "view_quality": self.view_quality,
            "injury_visible": self.injury_visible,
            "pressure_applied": self.pressure_applied,
            "last_instruction": self.last_instruction,
            "step_attempts": self.step_attempts,
            "status": self.status,
        }


@dataclass
class ModelInterpretation:
    """
    Derived from audio/transcript alone — no video frames required.
    The LLM infers CPR state from what the user says.
    """
    person_visible: bool = False          # user confirmed someone is present
    view_unclear: bool = False            # user seems confused or uncertain
    hands_positioned: bool = False        # user said hands are on center of chest
    compressions_happening: bool = False  # user said they are compressing
    person_responsive: bool = False       # user mentioned patient is responsive/breathing
    suggested_instruction: str = ""
    language_detected: str = "en"
    transcript_summary: str = ""
