Emergency Guidance Agent — PRD

1. Product overview

Working title

Emergency Guidance Agent

One-line summary

A real-time multimodal assistant that watches the user’s live camera feed, listens to spoken input, maintains a bounded task workflow, and gives the next short actionable instruction during a high-stress physical task.

MVP framing

This is not a general emergency diagnosis system.
This is a live guidance copilot for a narrow, bounded workflow.

For MVP, the recommended workflow is:
	•	Severe bleeding control

The system should:
	•	accept live video + live speech
	•	interpret what the user is showing and saying
	•	track the current step in the protocol
	•	respond with one short instruction at a time
	•	adapt when the view is unclear or the user seems confused

⸻

2. Problem

In urgent or stressful situations, users do not need generic search results or long-form instructions. They need:
	•	immediate guidance
	•	one next step at a time
	•	instructions grounded in what is actually happening in front of them
	•	support in their own language
	•	help even when they cannot describe the situation clearly

Existing assistants are weak in this setting because they mostly:
	•	answer questions in text
	•	do not maintain a structured workflow state
	•	do not verify whether the user is actually performing the step
	•	are not grounded in live visual context

This creates a gap for a multimodal live guidance product.

⸻

3. Goal

Build an MVP that demonstrates the following loop:
	1.	User opens a session.
	2.	User shows the situation on camera and speaks.
	3.	The system identifies the current workflow state.
	4.	The system provides the next short instruction.
	5.	The user acts.
	6.	The system observes again and either:
	•	confirms progress
	•	asks for a better angle
	•	repeats or simplifies the instruction
	•	advances to the next step

The demo should feel like:
	•	grounded
	•	responsive
	•	multilingual
	•	step-based
	•	safety-bounded

⸻

4. Non-goals

The MVP will not:
	•	diagnose arbitrary emergencies
	•	support many protocols at once
	•	retrieve or play tutorial videos
	•	provide medical certainty
	•	replace emergency responders
	•	perform open-ended internet search
	•	support a full clinical workflow

⸻

5. Target user

Primary user

A stressed bystander or user who needs live guidance for a physical task and cannot rely on reading long instructions.

MVP demo user

A hackathon demo participant acting as a bystander performing severe bleeding control on a staged scenario.

⸻

6. Core user story

As a user in a stressful physical situation,
I want the system to see what I am doing, hear what I am saying, and guide me one step at a time,
so that I can perform the right action without needing to interpret a long article or video.

⸻

7. MVP scope

In scope
	•	One workflow: severe bleeding control
	•	Live camera input
	•	Live mic input
	•	Spoken and text response from system
	•	State-based guidance
	•	Multilingual support via Gemini Live
	•	Prompt-bounded response style
	•	App-side workflow engine
	•	Session-based guidance loop

Out of scope
	•	Multiple emergency categories
	•	Dynamic protocol generation
	•	Video recommendation/playback
	•	Human handoff system
	•	User accounts/auth
	•	Persistent storage
	•	Advanced analytics dashboard

⸻

8. Product principles
	1.	One instruction at a time
The system should not overwhelm the user.
	2.	Visual grounding first
If the system cannot see enough, it should ask for a better view.
	3.	Workflow-bounded
The assistant should stay within a narrow approved flow.
	4.	Model interprets; app decides
Gemini should interpret scene/audio and phrase the response. The app should control state transitions.
	5.	Short, stress-friendly language
Instructions should be concise and action-oriented.
	6.	Multilingual by default
The system should detect or follow user language and respond accordingly.

⸻

9. High-level solution

The product consists of four logical layers:
	1.	Frontend session UI
Captures camera and mic input, shows current instruction, and lets user confirm progress.
	2.	Realtime multimodal layer
Gemini 3.1 Flash Live ingests speech and video context and generates structured understanding plus user-facing response.
	3.	Workflow/state engine
Hardcoded application logic maintains scenario state and next allowed steps.
	4.	Response layer
System presents text instruction and optional voice output to the user.

⸻

10. User flow

Start session
	•	User lands on the session screen
	•	User taps “Start Session”
	•	Camera and mic permissions are requested
	•	System opens a Gemini Live session
	•	System says: “Show me what happened.”

Intake
	•	User points camera toward the injury
	•	User says what happened
	•	System interprets visible context + spoken context
	•	App initializes workflow state

Guidance loop
	•	System asks for clearer view if needed
	•	System instructs user to call emergency services if needed
	•	System gives next action instruction
	•	User performs action
	•	System observes updated visual/audio context
	•	App advances or repeats

End session
	•	Session ends when demo flow is complete or user exits

⸻

11. MVP workflow: severe bleeding control

Workflow states
	1.	intake
	2.	escalation
	3.	identify_injury
	4.	apply_pressure
	5.	maintain_pressure
	6.	complete

State descriptions

1. intake
Objective:
	•	collect initial context
	•	see the injury area
	•	understand user language and urgency

Example instruction:
	•	“Show me the injury and tell me what happened.”

2. escalation
Objective:
	•	ensure emergency escalation message is delivered

Example instruction:
	•	“This looks serious. Call emergency services now if you have not already.”

3. identify_injury
Objective:
	•	get a sufficiently clear view of the bleeding site

Example instruction:
	•	“Move the camera closer to the bleeding area.”

4. apply_pressure
Objective:
	•	instruct user to apply direct pressure

Example instruction:
	•	“Press firmly on the wound with a clean cloth or towel now.”

5. maintain_pressure
Objective:
	•	reinforce continued action

Example instruction:
	•	“Keep steady pressure. If blood soaks through, place more cloth on top and keep pressing.”

6. complete
Objective:
	•	end demo loop cleanly

Example instruction:
	•	“Good. Keep pressure on the wound until help arrives.”

⸻

12. Functional requirements

FR1. Live session start

The system must allow the user to start a live camera/mic session.

FR2. Live multimodal intake

The system must consume video and speech context in the same session.

FR3. State tracking

The system must maintain the current workflow state on the application side.

FR4. Scene-aware instruction

The system must generate or present instructions based on current visual/audio context plus workflow state.

FR5. One-step instruction format

The system must present one short instruction at a time.

FR6. Clarify when uncertain

If the scene is unclear, the system must ask for a better angle rather than pretending certainty.

FR7. Multilingual support

The system should respond in the user’s language or follow system-configured language instructions.

FR8. User confirmation

The UI must allow the user to indicate “done” or request a repeat.

FR9. Spoken output

The system should optionally speak the current instruction aloud.

FR10. Safe bounded workflow

The system must only operate inside the predefined workflow for MVP.

⸻

13. Non-functional requirements

NFR1. Low latency

Response latency should feel near-real-time for demo purposes.
Target: under ~2 seconds perceived response after user utterance or state event.

NFR2. Robustness to noisy speech

System should remain usable if user speech is partial or stressed.

NFR3. Graceful uncertainty

System should degrade to “show me more clearly” rather than hallucinating.

NFR4. Simple deployability

System should be runnable locally or on a simple hackathon stack.

NFR5. Clear failure handling

If model input is insufficient or transport fails, UI should show a simple retry/repeat path.

⸻

14. Safety guardrails

This product is safety-adjacent, so even the MVP should be bounded.

Guardrails
	•	Only one supported workflow in MVP
	•	No broad diagnosis language
	•	No unsupported advanced interventions
	•	Always allow escalation language
	•	Prompt should instruct model to stay within demo workflow
	•	App should reject off-workflow state transitions
	•	UI should avoid language implying medical authority beyond the bounded flow

Safe response style

Good:
	•	“Show me the injury more clearly.”
	•	“Press firmly on the wound now.”
	•	“Call emergency services now if you have not already.”

Avoid:
	•	speculative diagnosis
	•	claims of certainty without visual support
	•	open-ended medical advice outside the defined workflow

⸻

15. Frontend requirements

Frontend responsibilities

The frontend should own:
	•	camera capture
	•	mic capture
	•	session initiation
	•	rendering current instruction
	•	rendering transcript/status
	•	user controls
	•	optional voice playback
	•	sending media/state events to backend or Gemini session layer

Frontend components

A. Session screen
Contains the full live experience.

B. Camera panel
Shows live preview from user camera.

C. Instruction panel
Shows the current system instruction prominently.

D. Transcript/status panel
Shows recent system and user utterances plus current workflow state.

E. Action buttons
At minimum:
	•	Start Session
	•	I Did This
	•	Repeat Step
	•	End Session

F. Optional language chip
Shows detected/selected language.

Frontend UX requirements
	•	Very large instruction text
	•	Minimal clutter
	•	Single-screen flow
	•	Clear system status: listening / thinking / responding
	•	Strong mobile-friendly layout if time permits

Frontend tech suggestions
	•	React / Next.js or simple Vite React app
	•	Browser camera APIs
	•	Browser microphone APIs
	•	WebSocket/WebRTC depending on Gemini Live integration path
	•	Browser speech output if needed as fallback

⸻

16. Backend requirements

Backend responsibilities

The backend should own:
	•	session orchestration
	•	Gemini Live connection management (if not directly from client)
	•	workflow state management
	•	prompt scaffolding / session instructions
	•	validation of model outputs
	•	event handling for step transitions

Backend modules

A. Session Manager
Creates and manages active sessions.

Responsibilities:
	•	session start
	•	session end
	•	keep current state object
	•	route events between UI and model

B. Workflow Engine
Hardcoded finite-state machine for bleeding control workflow.

Responsibilities:
	•	determine next allowed steps
	•	advance or repeat current step
	•	enforce bounded behavior

C. Gemini Orchestrator
Wrapper around Gemini Live session.

Responsibilities:
	•	initialize model session
	•	pass system instructions
	•	stream or attach video/audio context
	•	receive model responses
	•	extract structured interpretation if needed

D. Response Formatter
Converts model/app output into UI-friendly structure.

Responsibilities:
	•	current instruction text
	•	optional voice text
	•	state label
	•	confidence or uncertainty flags

Backend tech suggestions
	•	Node.js / TypeScript or Python FastAPI
	•	lightweight in-memory store for session state
	•	no database required for MVP

⸻

17. Suggested architecture

Architecture overview

The MVP architecture is intentionally simple and bounded.

The system is composed of five layers:
	1.	Client application
	2.	Realtime session transport
	3.	Backend orchestration layer
	4.	Workflow/state engine
	5.	Gemini Live multimodal reasoning layer

The guiding principle is:

Gemini interprets. The application decides.

That means:
	•	Gemini handles multimodal understanding and response phrasing
	•	the backend/application owns the current workflow step and all allowed state transitions

This prevents the model from improvising the workflow and keeps the product deterministic.

Architectural goals

The architecture should optimize for:
	•	low perceived latency
	•	simple end-to-end demo reliability
	•	bounded workflow logic
	•	easy debugging
	•	support for multilingual spoken interaction
	•	clean separation between UI, model reasoning, and protocol state

High-level component diagram

User
  ↓
Frontend Web App
  ├─ Camera Stream
  ├─ Microphone Stream
  ├─ Session Controls
  └─ Instruction UI
  ↓
Session Transport Layer
  ↓
Backend Orchestrator
  ├─ Session Manager
  ├─ Workflow Engine
  ├─ Gemini Live Orchestrator
  └─ Response Formatter
  ↓
Gemini 3.1 Flash Live Preview
  ↓
Backend Orchestrator
  ↓
Frontend Web App
  ↓
User

End-to-end interaction flow

1. User starts a session
2. Frontend opens camera + mic
3. Frontend creates or joins a live backend session
4. Backend initializes workflow state
5. Media and user utterances are streamed/sent into Gemini Live
6. Gemini interprets the current visual + spoken context
7. Backend receives model output and maps it into bounded workflow logic
8. Backend chooses the next allowed step
9. Frontend renders the next instruction and optionally speaks it aloud
10. User performs the action
11. New media context arrives
12. Loop repeats until workflow completes or session ends

Primary architecture decision

The most important architecture decision is that the workflow engine must live outside the model.

Why:
	•	the model may be good at perception and language, but it should not be trusted to invent protocol state transitions
	•	keeping workflow state in application code makes the system easier to test and safer to demo
	•	debugging becomes much simpler because state is explicit and inspectable

So the responsibilities split as follows:

Gemini responsibilities
	•	understand the spoken language
	•	interpret visible scene context
	•	detect if view is unclear
	•	infer whether the user appears to have completed a requested action
	•	phrase the next instruction in concise user-facing language
	•	respond in the detected or configured language

Application responsibilities
	•	create and manage session lifecycle
	•	store current state
	•	define allowed workflow transitions
	•	decide whether to advance, repeat, or request clarification
	•	enforce prompt bounds and safety constraints
	•	render and speak final instructions to the user

Layer-by-layer architecture

A. Frontend layer
The frontend should be a single-page session interface.

Its responsibilities are:
	•	request camera and microphone permissions
	•	display live camera preview
	•	display current instruction prominently
	•	capture user actions like Start, Done, Repeat, End
	•	render system status such as listening, thinking, responding
	•	stream or forward audio/video input to the backend or Gemini session layer
	•	optionally play spoken output

The frontend should not own workflow logic.
It should remain mostly stateless apart from local UI state.

B. Session transport layer
This layer is responsible for carrying media and events between frontend and backend/model.

Depending on implementation, this may be:
	•	WebSocket-based event transport
	•	direct Gemini Live session integration from client
	•	backend-mediated streaming session

For MVP, the transport only needs to reliably support:
	•	live audio input
	•	live or periodic visual input
	•	text/status responses back to the UI

If full continuous streaming becomes unstable, the fallback architecture is:
	•	stream audio continuously
	•	send periodic visual frames or snapshots at intervals

That fallback keeps the product loop intact without changing the rest of the architecture.

C. Backend orchestrator
This is the system control plane.

It should contain four submodules:

1. Session Manager
Responsible for:
	•	creating a new session
	•	assigning session id
	•	holding session state in memory
	•	closing sessions cleanly
	•	routing events to the correct session

2. Gemini Live Orchestrator
Responsible for:
	•	initializing Gemini Live connection
	•	passing system instructions and session context
	•	forwarding relevant media/events to Gemini
	•	receiving model responses or structured interpretation
	•	normalizing model output into a consistent format

3. Workflow Engine
Responsible for:
	•	storing the finite-state machine for the severe bleeding workflow
	•	deciding allowed next states
	•	converting model observations into workflow actions
	•	handling repeat/clarify/escalate logic

4. Response Formatter
Responsible for:
	•	converting workflow decisions into a frontend-ready payload
	•	formatting instruction text
	•	attaching status flags like listening, unclear_view, step_complete
	•	providing text that can also be used for TTS playback

Workflow/state engine design

The workflow engine should be implemented as a finite-state machine.

Recommended states:
	•	intake
	•	escalation
	•	identify_injury
	•	apply_pressure
	•	maintain_pressure
	•	complete

Each state should define:
	•	entry condition
	•	expected user action
	•	validation signal
	•	allowed next states
	•	repeat behavior

Example:

State: identify_injury
Entry: escalation message has already been delivered
Expected user action: point camera at injury
Validation signal: Gemini indicates injury area visible
If success: advance to apply_pressure
If failure: stay in identify_injury and ask for clearer view

This engine should be hand-coded and deterministic.

Gemini integration design

Gemini 3.1 Flash Live Preview is used as the multimodal reasoning and spoken response layer.

Gemini should receive:
	•	current workflow state
	•	system instructions describing the bounded workflow
	•	current or recent video context
	•	current or recent speech context
	•	optional language preference

Gemini should return either:
	•	short user-facing instructions directly
	•	or structured interpretation that the app maps into final instructions

Preferred pattern for reliability:
	•	backend asks Gemini for scene interpretation + concise suggested instruction
	•	workflow engine validates whether that suggestion is compatible with current step
	•	frontend receives the approved instruction

This gives the product a strong separation between reasoning and control.

Multilingual design

Multilingual support should be handled primarily by Gemini Live.

The intended behavior is:
	•	detect the language from user speech when possible
	•	continue responding in that language
	•	keep instruction length short regardless of language
	•	preserve workflow semantics even when language changes

The backend should store the active language in session state so that:
	•	the UI can display language status if desired
	•	fallback text generation remains consistent

Data flow

Input flow

Camera/Mic Input
  → Frontend Capture
  → Session Transport
  → Backend Orchestrator
  → Gemini Live

Decision flow

Gemini Live Output
  → Gemini Orchestrator
  → Workflow Engine
  → Response Formatter
  → Frontend UI

State flow

User action / model interpretation
  → Session Manager updates session state
  → Workflow Engine evaluates state
  → next allowed instruction is selected

Observability/debugging design

For hackathon and rapid development, the architecture should expose internal state clearly.

At minimum, log:
	•	current session id
	•	current workflow step
	•	latest user transcript
	•	latest Gemini response
	•	whether view is marked unclear
	•	whether step was advanced or repeated

Optional frontend debug panel:
	•	current state object
	•	last model interpretation
	•	current language
	•	last instruction

This will make live debugging dramatically easier.

Failure handling design

The system should fail gracefully rather than silently.

Examples:

If media input is weak
Respond with:
	•	“Show me the injury more clearly.”
	•	“Move the camera closer.”

If transcript is empty or noisy
Respond with:
	•	“I could not hear clearly. Say that again.”

If Gemini response is malformed
Backend should:
	•	ignore malformed payload
	•	retain current step
	•	send a safe repeat instruction

If latency spikes
Fallback behavior:
	•	pause advancement
	•	keep current instruction visible
	•	show a simple thinking state

Recommended deployment shape for MVP

For the MVP, use the lightest deployable architecture:
	•	frontend app served locally or on a simple web host
	•	backend service with in-memory session state
	•	Gemini Live connection managed centrally
	•	no database
	•	no auth
	•	no background jobs

This keeps the build surface minimal and aligned with the demo goal.

Why this architecture is the right cut

This architecture works for MVP because it:
	•	keeps the model in the loop without making it the controller
	•	allows live multimodal interaction
	•	supports multilingual guidance
	•	isolates protocol behavior in code
	•	can degrade gracefully if live video transport is imperfect
	•	is simple enough to implement quickly in Cursor

18. State model

State model

Session state object

{
  "session_id": "uuid",
  "scenario": "bleeding_control",
  "language": "en",
  "current_step": "intake",
  "called_emergency": false,
  "view_quality": "unknown",
  "injury_visible": false,
  "pressure_applied": "unknown",
  "last_instruction": "",
  "step_attempts": 0,
  "status": "active"
}

Notes
	•	current_step is authoritative and app-owned
	•	pressure_applied can be inferred by model but only used as input to app logic
	•	language may be selected explicitly or inferred from user speech

⸻

19. Event model

Client events
	•	session.start
	•	media.frame
	•	audio.chunk or speech.transcript
	•	user.done
	•	user.repeat
	•	session.end

Internal backend/model events
	•	model.interpretation
	•	workflow.advance
	•	workflow.repeat
	•	workflow.escalate

Response events
	•	assistant.instruction
	•	assistant.status
	•	assistant.error

⸻

20. Prompting strategy

System prompt goals

The system prompt should tell Gemini to:
	•	operate only inside the severe bleeding-control demo workflow
	•	use visual and spoken context together
	•	respond in the user’s language where possible
	•	ask for a better view when uncertain
	•	provide one short instruction at a time
	•	avoid diagnosis outside scope

Example system prompt

You are a live multimodal guidance assistant for a bounded severe bleeding-control workflow demo.

Your job is to:
- interpret the user’s spoken input and visible scene
- determine whether the injury area is visible enough
- determine whether the user appears to be applying pressure
- produce one short, stress-friendly instruction at a time
- ask for a clearer camera view if uncertain
- respond in the same language as the user when possible

You must not:
- invent new protocols
- give broad medical diagnosis
- provide long paragraphs
- present more than one action at a time

Keep responses concise and actionable.

Optional structured interpretation output

If the implementation uses structured outputs, Gemini can be asked to provide fields like:
	•	injury_visible
	•	view_unclear
	•	pressure_applied
	•	suggested_instruction
	•	language_detected

The app should still own state transitions.

⸻

21. Step logic

Transition rules

intake → escalation
If user describes injury and session is active.

escalation → identify_injury
After escalation instruction has been delivered.

identify_injury → apply_pressure
If injury area is visible enough.

identify_injury → identify_injury
If view is unclear.

apply_pressure → maintain_pressure
If user confirms action or model indicates pressure likely applied.

apply_pressure → apply_pressure
If action not completed or view remains unclear.

maintain_pressure → complete
After stable reinforcement instruction delivered.

⸻

22. MVP API contracts

Example request from frontend to backend

{
  "session_id": "abc123",
  "event_type": "speech.transcript",
  "transcript": "He cut his arm and there is blood.",
  "frame": "<image-bytes-or-reference>",
  "current_step": "intake"
}

Example backend response to frontend

{
  "session_id": "abc123",
  "current_step": "identify_injury",
  "instruction": "Move the camera closer to the bleeding area.",
  "speak": true,
  "status": "responding"
}


⸻

23. Demo plan

Demo scenario
	•	Person has a simulated bleeding arm injury
	•	User opens app
	•	User says: “He cut his arm badly.”
	•	System asks to show injury
	•	System tells user to call emergency services
	•	System asks for clearer view
	•	System instructs direct pressure
	•	User applies pressure
	•	System says to keep pressure steady

Demo success criteria
	•	The system consumes live camera and speech
	•	The system gives the right next step
	•	The system feels grounded in the visible scene
	•	The system stays concise

⸻

24. Success metrics for MVP

Primary
	•	End-to-end demo works without major breaks
	•	Response is grounded in current step and context
	•	User can complete the full bleeding-control flow

Secondary
	•	Multilingual response works in at least one non-English test
	•	System asks for better view when input is weak
	•	System avoids long or off-scope instructions

⸻

25. Engineering plan

Frontend checklist
	•	Build single session page
	•	Add camera permission and live preview
	•	Add mic capture or transcript input path
	•	Add current instruction banner
	•	Add transcript/status area
	•	Add Start / Done / Repeat / End buttons
	•	Hook into backend session events
	•	Add optional speech playback

Backend checklist
	•	Build session manager
	•	Define session state object
	•	Implement hardcoded workflow state machine
	•	Integrate Gemini Live session or wrapper
	•	Add prompt scaffolding
	•	Validate model outputs
	•	Return frontend-ready instruction payloads
	•	Add basic error handling

Prompt/model checklist
	•	Write bounded system instruction
	•	Test concise instruction style
	•	Test multilingual response
	•	Test unclear-scene handling

⸻

26. Risks and mitigations

Risk 1: realtime integration complexity

Mitigation:
	•	fall back to event-based media updates if full streaming becomes unstable

Risk 2: model goes off workflow

Mitigation:
	•	app-owned state machine
	•	bounded prompt
	•	explicit transition rules

Risk 3: unclear visual signal

Mitigation:
	•	prioritize “show me more clearly” behavior
	•	do not force false confidence

Risk 4: latency too high

Mitigation:
	•	reduce event frequency
	•	keep responses short
	•	avoid extra subsystems

Risk 5: UX too cluttered

Mitigation:
	•	one-screen minimal interface
	•	very large current instruction

⸻

27. Future extensions

Not in MVP, but natural future directions:
	•	more workflows beyond bleeding control
	•	richer action verification
	•	tutorial clip alignment
	•	responder handoff summaries
	•	audit/replay of session timeline
	•	stronger structured outputs from model
	•	optional second camera/source context

⸻

28. Final build recommendation

For the first build, prioritize this exact loop:

Observe → infer state → give one instruction → verify/repeat → continue

Do not expand scope until this loop is reliable.

The product will feel strong if it does these three things well:
	•	sees enough of the scene
	•	speaks clearly and concisely
	•	stays consistent with the workflow