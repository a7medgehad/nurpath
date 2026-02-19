export type EvidenceCard = {
  source_id: string;
  source_title: string;
  passage_id: string;
  arabic_quote: string;
  english_quote: string;
  citation_span: string;
  relevance_score: number;
  source_url: string;
};

export type OpinionComparisonItem = {
  school_or_scholar: string;
  stance_summary: string;
  evidence_passage_ids: string[];
};

export type AskResponse = {
  direct_answer: string;
  evidence_cards: EvidenceCard[];
  opinion_comparison: OpinionComparisonItem[];
  confidence: number;
  safety_notice?: string | null;
  abstained: boolean;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function createSession(preferred_language: "ar" | "en") {
  const r = await fetch(`${API_BASE}/v1/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preferred_language, level: "beginner", goals: ["learn with evidence"] }),
  });

  if (!r.ok) throw new Error("Failed to create session");
  return r.json();
}

export async function askQuestion(
  payload: {
    session_id: string;
    question: string;
    preferred_language: "ar" | "en";
  },
): Promise<AskResponse> {
  const r = await fetch(`${API_BASE}/v1/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!r.ok) throw new Error("Failed to ask question");
  return r.json();
}
