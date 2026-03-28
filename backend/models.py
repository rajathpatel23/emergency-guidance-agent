from dataclasses import dataclass, field
from typing import Literal

WorkflowStep = Literal[
    "intake",
    "escalation",
    "identify_injury",
    "apply_pressure",
    "maintain_pressure",
    "complete",
]

ViewQuality = Literal["unknown", "clear", "unclear"]
PressureSignal = Literal["unknown", "yes", "no"]
SessionStatus = Literal["active", "ended"]


@dataclass
class SessionState:
    session_id: str
    scenario: str = "bleeding_control"
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
    injury_visible: bool = False
    view_unclear: bool = False
    pressure_applied: bool = False
    suggested_instruction: str = ""
    language_detected: str = "en"
    transcript_summary: str = ""
