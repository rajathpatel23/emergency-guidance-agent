import type { ModelInterpretation, SessionState } from "@emergency-guidance/shared";
import { BLEEDING_CONTROL_SYSTEM_PROMPT } from "./prompts/system-prompt.js";

export interface GeminiOrchestrator {
  interpret(input: {
    state: SessionState;
    transcript?: string;
    frameBase64?: string;
  }): Promise<ModelInterpretation>;
}

/**
 * Stub: swap for Gemini 3.1 Flash Live integration (PRD §16.D, §17).
 * Returns safe defaults so the workflow engine can be exercised without API keys.
 */
export function createStubGeminiOrchestrator(): GeminiOrchestrator {
  return {
    async interpret(input) {
      void BLEEDING_CONTROL_SYSTEM_PROMPT;
      const t = input.transcript?.toLowerCase() ?? "";
      const interpretation: ModelInterpretation = {
        transcript_summary: input.transcript,
        injury_visible: /blood|bleed|cut|arm|injury|wound/.test(t),
        view_unclear: false,
        pressure_applied: /press|push|holding|firm/.test(t),
        suggested_instruction: undefined,
      };
      return interpretation;
    },
  };
}
