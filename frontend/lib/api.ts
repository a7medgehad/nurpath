export type ReferenceData = {
  surah?: string | null;
  ayah?: string | null;
  collection?: string | null;
  book?: string | null;
  hadith_number?: string | null;
  grading_authority?: string | null;
  volume?: string | null;
  page?: string | null;
  madhhab?: string | null;
  display_ar?: string | null;
};

export type EvidenceCard = {
  source_id: string;
  source_title: string;
  source_title_ar: string;
  passage_id: string;
  arabic_quote: string;
  english_quote: string;
  citation_span: string;
  relevance_score: number;
  source_url: string;
  passage_url: string;
  source_type: "quran" | "hadith" | "fiqh";
  authenticity_level: string;
  reference?: ReferenceData | null;
};

export type CitationIntegrityResult = {
  passed: boolean;
  coverage: number;
};

export type ScoreGateResult = {
  score: number;
  threshold: number;
  passed: boolean;
};

export type ValidationResult = {
  passed: boolean;
  citation_integrity: CitationIntegrityResult;
  grounding: ScoreGateResult;
  faithfulness: ScoreGateResult;
  decision_reason: string;
};

export type OpinionComparisonItem = {
  school_or_scholar: string;
  stance_summary: string;
  stance_type: "invalidates" | "does_not_invalidate" | "unclear";
  evidence_passage_ids: string[];
};

export type ConflictPair = {
  school_a: string;
  school_b: string;
  issue_topic: string;
  evidence_passage_ids: string[];
};

export type IkhtilafAnalysis = {
  status: "ikhtilaf" | "consensus" | "insufficient";
  summary: string;
  compared_schools: string[];
  shared_topic_tags: string[];
  conflict_pairs: ConflictPair[];
};

export type AskResponse = {
  direct_answer: string;
  evidence_cards: EvidenceCard[];
  opinion_comparison: OpinionComparisonItem[];
  ikhtilaf_analysis?: IkhtilafAnalysis | null;
  confidence: number;
  safety_notice?: string | null;
  abstained: boolean;
  validation: ValidationResult;
};

export type LearningObjective = {
  id: string;
  title: string;
  difficulty: string;
  prerequisites: string[];
  expected_outcomes: string[];
};

export type SessionCreateResponse = {
  session_id: string;
  roadmap: LearningObjective[];
  lesson_path: {
    session_id: string;
    objective_ids: string[];
    mastery_state: Record<string, number>;
  };
};

export type SourceDocument = {
  id: string;
  title: string;
  title_ar: string;
  author: string;
  author_ar: string;
  era: string;
  language: string;
  license: string;
  url: string;
  citation_policy: string;
  citation_policy_ar: string;
  source_type: "quran" | "hadith" | "fiqh";
  authenticity_level: string;
};

export type SourceListResponse = {
  items: SourceDocument[];
  total: number;
};

export type QuizQuestion = {
  id: string;
  prompt: string;
  expected_keywords: string[];
};

export type QuizGenerateResponse = {
  objective_id: string;
  questions: QuizQuestion[];
};

export type QuizGradeResponse = {
  objective_id: string;
  score: number;
  feedback: Record<string, string>;
  updated_mastery: Record<string, number>;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function createSession(preferred_language: "ar" | "en"): Promise<SessionCreateResponse> {
  const r = await fetch(`${API_BASE}/v1/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      preferred_language,
      level: "beginner",
      goals: preferred_language === "ar" ? ["التعلم بالدليل"] : ["learn with evidence"],
    }),
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

export async function getSources(filters?: {
  language?: string;
  topic?: string;
  q?: string;
  ui_language?: "ar" | "en";
  source_type?: "quran" | "hadith" | "fiqh";
  authenticity_level?: string;
}): Promise<SourceListResponse> {
  const params = new URLSearchParams();
  if (filters?.language) params.set("language", filters.language);
  if (filters?.topic) params.set("topic", filters.topic);
  if (filters?.q) params.set("q", filters.q);
  if (filters?.ui_language) params.set("ui_language", filters.ui_language);
  if (filters?.source_type) params.set("source_type", filters.source_type);
  if (filters?.authenticity_level) params.set("authenticity_level", filters.authenticity_level);

  const query = params.toString();
  const r = await fetch(`${API_BASE}/v1/sources${query ? `?${query}` : ""}`);
  if (!r.ok) throw new Error("Failed to load sources");
  return r.json();
}

export async function generateQuiz(payload: {
  session_id: string;
  objective_id: string;
  num_questions: number;
  preferred_language: "ar" | "en";
}): Promise<QuizGenerateResponse> {
  const r = await fetch(`${API_BASE}/v1/quiz/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error("Failed to generate quiz");
  return r.json();
}

export async function gradeQuiz(payload: {
  session_id: string;
  objective_id: string;
  answers: Record<string, string>;
}): Promise<QuizGradeResponse> {
  const r = await fetch(`${API_BASE}/v1/quiz/grade`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error("Failed to grade quiz");
  return r.json();
}
