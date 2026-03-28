import os
from loguru import logger

from pipecat.frames.frames import (
    Frame,
    LLMFullResponseEndFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
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

        if isinstance(frame, TextFrame):
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
            injury_visible=interp.person_visible,
            view_quality="unclear" if interp.view_unclear else "clear",
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

def _extract_interpretation(model_text: str, transcript: str = "") -> ModelInterpretation:
    combined = (model_text + " " + transcript).lower()
    return ModelInterpretation(
        person_visible=any(w in combined for w in ["person", "patient", "body", "chest", "lying"]),
        view_unclear=any(w in combined for w in ["cannot see", "can't see", "unclear", "move the camera", "closer", "better angle", "show me"]),
        hands_positioned=any(w in combined for w in ["hands", "positioned", "center of the chest", "placed"]),
        compressions_happening=any(w in combined for w in ["pressing", "compressions", "pushing", "pumping"]),
        person_responsive=any(w in combined for w in ["responsive", "breathing", "moving", "conscious"]),
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
        ),
    )

    gemini = GeminiLiveLLMService(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options=HttpOptions(api_version="v1alpha"),
        settings=GeminiLiveLLMService.Settings(
            model="gemini-2.5-flash-native-audio-latest",
            system_instruction=build_system_prompt(session.current_step),
            voice="Charon",
        ),
    )

    # Seed the context with a minimal user message so _create_initial_response()
    # sends a real turn_complete to Gemini when the session connects, causing it
    # to speak the opening line immediately without waiting for user input.
    seed_context = OpenAILLMContext(
        messages=[{"role": "user", "content": "begin"}]
    )
    await gemini.set_context(seed_context)

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
