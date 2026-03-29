import os
from loguru import logger

from pipecat.frames.frames import (
    AudioRawFrame,
    Frame,
    LLMFullResponseEndFrame,
    StartFrame,
    TextFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response_universal import LLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from google.genai.types import HttpOptions
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from models import ModelInterpretation, SessionState
from prompts import build_system_prompt, step_context_message
from session_manager import update_session
from workflow_engine import apply_decision, evaluate, TOTAL_STEPS


# ---------------------------------------------------------------------------
# Workflow frame processor
# ---------------------------------------------------------------------------

class WorkflowProcessor(FrameProcessor):
    """
    Intercepts completed Gemini turns, runs the workflow FSM, and injects
    step-context messages when the step advances.
    """

    def __init__(self, session: SessionState, gemini_service: GeminiLiveLLMService):
        super().__init__()
        self._session = session
        self._gemini = gemini_service
        self._buffer: list[str] = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, StartFrame):
            logger.info("[pipeline] StartFrame received — pipeline is live")

        elif isinstance(frame, TTSAudioRawFrame):
            logger.debug(f"[pipeline] audio frame flowing to browser  bytes={len(frame.audio)}")

        elif isinstance(frame, TextFrame):
            self._buffer.append(frame.text)

        elif isinstance(frame, TranscriptionFrame):
            logger.debug(f"[gemini] user: '{frame.text}'")
            interp = _extract_interpretation("", frame.text)
            interp.transcript_summary = frame.text
            await self._run_engine(interp)

        elif isinstance(frame, LLMFullResponseEndFrame):
            full_text = "".join(self._buffer).strip()
            self._buffer.clear()
            if full_text:
                logger.debug(f"[gemini] bot: '{full_text[:120]}'")
                interp = _extract_interpretation(full_text)
                await self._run_engine(interp)

        await self.push_frame(frame, direction)

    async def _run_engine(self, interp: ModelInterpretation):
        session = self._session
        prev_step = session.current_step

        decision = evaluate(session, interp, user_action=None)
        apply_decision(session, decision)

        update_session(
            session.session_id,
            current_step=session.current_step,
            step_attempts=session.step_attempts,
            patient_visible=interp.person_visible or interp.user_asserts_view_adequate,
            view_quality=(
                "unclear"
                if interp.view_unclear and not interp.user_asserts_view_adequate
                else "clear"
            ),
        )

        if session.current_step != prev_step:
            logger.info(
                f"[workflow] {prev_step} → {session.current_step} "
                f"(reason: {decision.reason})"
            )
            context_msg = step_context_message(session.current_step)
            await self._gemini.push_frame(TextFrame(context_msg))


# ---------------------------------------------------------------------------
# Heuristic interpretation
# ---------------------------------------------------------------------------

# Phrases suggesting the victim/chest is actually visible (vision or confident description).
_VISIBILITY_POSITIVE = (
    "i can see",
    "i see the",
    "i see them",
    "see the patient",
    "see them on",
    "chest is visible",
    "chest in view",
    "in the frame",
    "in frame",
    "lying on",
    "on the floor",
    "on their back",
    "unresponsive",
    "not breathing",
)

# Phrases that deny visibility — checked before loose "patient" matches (avoids "can't see the patient" → visible).
_VISIBILITY_NEGATIVE = (
    "cannot see the patient",
    "can't see the patient",
    "cannot see them",
    "can't see them",
    "don't see the patient",
    "don't see anyone",
    "i don't see",
    "no one visible",
    "no one in the frame",
    "not in the frame",
    "not visible",
    "too dark to see",
    "too blurry",
)

# Rescuer affirms camera/view is adequate — transcript only; workflow may advance without confirming vision.
_USER_VIEW_OK = (
    "good angle",
    "right angle",
    "got a better angle",
    "have a good angle",
    "better angle now",
    "clear view",
    "clearer now",
    "you should see",
    "in view now",
    "moved the camera",
    "positioned the camera",
    "i moved the",
    "phone is steady",
    "trust me",
    "have to trust",
    "best i can",
    "that's as good",
    "how's that",
    "is that ok",
)


def _person_visible_heuristic(model_text: str, transcript: str) -> bool:
    combined = (model_text + " " + transcript).lower()
    if any(p in combined for p in _VISIBILITY_NEGATIVE):
        return False
    return any(p in combined for p in _VISIBILITY_POSITIVE)


def _user_asserts_view_adequate(transcript: str) -> bool:
    t = transcript.lower()
    if not t.strip():
        return False
    return any(p in t for p in _USER_VIEW_OK)


def _extract_interpretation(model_text: str, transcript: str = "") -> ModelInterpretation:
    combined = (model_text + " " + transcript).lower()
    return ModelInterpretation(
        person_visible=_person_visible_heuristic(model_text, transcript),
        user_asserts_view_adequate=_user_asserts_view_adequate(transcript),
        view_unclear=any(
            w in combined
            for w in [
                "cannot see",
                "can't see",
                "unclear",
                "move the camera",
                "closer",
                "better angle",
                "show me",
            ]
        ),
        hands_positioned=any(
            w in combined
            for w in [
                "hands",
                "heel",
                "stacked",
                "center of the chest",
                "sternum",
                "placed",
                "interlocked",
            ]
        ),
        compressions_happening=any(
            w in combined
            for w in [
                "compressions",
                "compressing",
                "pushing",
                "pumping",
                "pressing",
                "cpr",
                "push hard",
            ]
        ),
        person_responsive=any(w in combined for w in ["responsive", "breathing", "moving", "conscious", "coughing"]),
        transcript_summary=transcript,
    )


# ---------------------------------------------------------------------------
# Pipeline factory
# ---------------------------------------------------------------------------

async def create_pipeline(
    websocket,
    session: SessionState,
) -> tuple[PipelineRunner, PipelineTask]:

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            serializer=ProtobufFrameSerializer(),
            add_wav_header=False,
            # TransportParams defaults audio_in/out to False — mic and TTS are dropped.
            audio_in_enabled=True,
            audio_in_sample_rate=16000,
            audio_out_enabled=True,
            audio_out_sample_rate=24000,
        ),
    )

    # Use a Live-native-audio model + v1alpha — see Pipecat GeminiLiveLLMService defaults.
    # Aliases like "gemini-2.0-flash-live-001" or "*-latest" often 404 or fail on BidiGenerateContent.
    live_model = os.getenv(
        "GEMINI_LIVE_MODEL",
        "models/gemini-2.5-flash-native-audio-preview-12-2025",
    )
    gemini = GeminiLiveLLMService(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options=HttpOptions(api_version="v1alpha"),
        settings=GeminiLiveLLMService.Settings(
            model=live_model,
            system_instruction=build_system_prompt(session.current_step),
            voice="Charon",
        ),
    )

    # Seed the context so Gemini speaks the mandatory Emergency Guidance Agent opening
    # immediately on connect (see prompts.BASE_SYSTEM_PROMPT).
    seed_context = LLMContext(
        messages=[
            {
                "role": "user",
                "content": (
                    "Session just started. Speak now: introduce yourself as the Emergency Guidance Agent, "
                    "ask what you can help them with, keep it to one or two short sentences."
                ),
            }
        ]
    )
    await gemini.set_context(seed_context)  # type: ignore[arg-type]

    workflow = WorkflowProcessor(session=session, gemini_service=gemini)

    pipeline = Pipeline(
        [
            transport.input(),   # audio from browser
            gemini,              # Gemini Live reasoning + speech output
            workflow,            # FSM state transitions
            transport.output(),  # audio back to browser
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=True),
    )

    runner = PipelineRunner()
    return runner, task
