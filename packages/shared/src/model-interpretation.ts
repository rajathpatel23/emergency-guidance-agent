/**
 * Optional structured interpretation from Gemini (PRD §20).
 * The app still owns state transitions — no step hint field intentionally.
 */
export interface ModelInterpretation {
  patient_visible?: boolean;
  view_unclear?: boolean;
  compressions_detected?: boolean;
  suggested_instruction?: string;
  language_detected?: string;
  transcript_summary?: string;
}
