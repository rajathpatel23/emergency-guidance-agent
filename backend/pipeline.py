import os
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    AudioRawFrame,
    Frame,
    LLMFullResponseEndFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService, GeminiLiveContext
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from models import ModelInterpretation, SessionState
from prompts import build_system_prompt, step_context_message
from session_manager import update_session
from workflow_engine import apply_decision, current_config, evaluate, step_number, TOTAL_STEPS


# ---------------------------------------------------------------------------
# Workflow frame processor
# Sits after Gemini in the pipeline, intercepts text output, runs FSM
# ---------------------------------------------------------------------------

class WorkflowProcessor(FrameProcessor):
    """
    Intercepts completed Gemini text turns, runs the workflow engine,
    updates session state, and injects step-context turns when the step
    advances so Gemini stays aligned.
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
            # Inject step context so Gemini knows the new objective
            context_msg = step_context_message(session.current_step)
            await self._gemini.push_frame(TextFrame(context_msg))


# ---------------------------------------------------------------------------
# Heuristic interpretation (same as before, kept here to avoid circular import)
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
    """
    Build and return a Pipecat pipeline for one WebSocket session.
    Call runner.run(task) to start it.
    """

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            serializer=ProtobufFrameSerializer(),
            add_wav_header=False,
        ),
    )

    gemini = GeminiLiveLLMService(
        api_key=os.environ["GEMINI_API_KEY"],
        model="gemini-2.0-flash-live-001",
        system_instruction=build_system_prompt(session.current_step),
        voice_id="Charon",
    )

    workflow = WorkflowProcessor(session=session, gemini_service=gemini)

    # Context sets up the conversation — no initial user message needed
    context = GeminiLiveContext()
    context_aggregator = gemini.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),             # audio/video from browser
            context_aggregator.user(),     # accumulates user turns
            gemini,                        # Gemini Live reasoning + speech
            workflow,                      # FSM state transitions
            context_aggregator.assistant(),# accumulates assistant turns
            transport.output(),            # audio back to browser
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=True),
    )

    runner = PipelineRunner()
    return runner, task
