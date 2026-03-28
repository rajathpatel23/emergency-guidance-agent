from dataclasses import dataclass
from typing import Literal

WorkflowStep = Literal[
    "intake",
    "escalation",
    "see_patient",
    "start_compressions",
    "continue_cpr",
    "complete",
]

ViewQuality = Literal["unknown", "clear", "unclear"]
CompressionSignal = Literal["unknown", "yes", "no"]
SessionStatus = Literal["active", "ended"]


@dataclass
class SessionState:
    session_id: str
    scenario: str = "cpr_coaching"
    language: str = "en"
    current_step: WorkflowStep = "intake"
    called_emergency: bool = False
    view_quality: ViewQuality = "unknown"
    patient_visible: bool = False
    compressions_detected: CompressionSignal = "unknown"
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
            "patient_visible": self.patient_visible,
            "compressions_detected": self.compressions_detected,
            "last_instruction": self.last_instruction,
            "step_attempts": self.step_attempts,
            "status": self.status,
        }


@dataclass
class ModelInterpretation:
    person_visible: bool = False       # victim / chest visible in frame
    view_unclear: bool = False         # camera angle insufficient
    hands_positioned: bool = False     # hands on center of the chest
    compressions_happening: bool = False  # user appears to be compressing
    person_responsive: bool = False    # patient shows signs of response
    suggested_instruction: str = ""
    language_detected: str = "en"
    transcript_summary: str = ""
