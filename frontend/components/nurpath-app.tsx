"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AskResponse,
  LearningObjective,
  QuizGenerateResponse,
  QuizGradeResponse,
  SourceDocument,
  askQuestion,
  createSession,
  generateQuiz,
  getSources,
  gradeQuiz,
} from "@/lib/api";

export function NurPathApp() {
  const [language, setLanguage] = useState<"ar" | "en">("ar");
  const [question, setQuestion] = useState("ما الفرق في الوضوء عند لمس الزوجة؟");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [roadmap, setRoadmap] = useState<LearningObjective[]>([]);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [sourceTopic, setSourceTopic] = useState("فقه");
  const [sourceQuery, setSourceQuery] = useState("");
  const [sources, setSources] = useState<SourceDocument[]>([]);
  const [sourceLoading, setSourceLoading] = useState(false);

  const [quizLoading, setQuizLoading] = useState(false);
  const [quiz, setQuiz] = useState<QuizGenerateResponse | null>(null);
  const [quizAnswers, setQuizAnswers] = useState<Record<string, string>>({});
  const [quizGrade, setQuizGrade] = useState<QuizGradeResponse | null>(null);

  const dir = useMemo(() => (language === "ar" ? "rtl" : "ltr"), [language]);

  async function ensureSession(): Promise<string> {
    if (sessionId) return sessionId;
    const s = await createSession(language);
    setSessionId(s.session_id);
    setRoadmap(s.roadmap);
    return s.session_id;
  }

  async function handleCreateSession() {
    setError(null);
    try {
      const s = await createSession(language);
      setSessionId(s.session_id);
      setRoadmap(s.roadmap);
      setQuiz(null);
      setQuizGrade(null);
    } catch (err) {
      setError(
        language === "ar" ? "تعذر إنشاء الجلسة." : err instanceof Error ? err.message : "Unexpected error",
      );
    }
  }

  async function handleAsk(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const sid = await ensureSession();
      const response = await askQuestion({
        session_id: sid,
        question,
        preferred_language: language,
      });
      setResult(response);
    } catch (err) {
      setError(language === "ar" ? "تعذر إتمام الطلب." : err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadSources(e?: FormEvent) {
    e?.preventDefault();
    setSourceLoading(true);
    try {
      const payload = await getSources({
        topic: sourceTopic || undefined,
        q: sourceQuery || undefined,
        language: language === "ar" ? "ar" : undefined,
        ui_language: language,
      });
      setSources(payload.items);
    } catch (err) {
      setError(language === "ar" ? "تعذر تحميل المصادر." : err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setSourceLoading(false);
    }
  }

  async function handleGenerateQuiz() {
    setQuizLoading(true);
    setError(null);
    try {
      let sid = sessionId;
      let currentRoadmap = roadmap;
      if (!sid || currentRoadmap.length === 0) {
        const created = await createSession(language);
        sid = created.session_id;
        currentRoadmap = created.roadmap;
        setSessionId(created.session_id);
        setRoadmap(created.roadmap);
      }
      const objectiveId = currentRoadmap[0]?.id;
      if (!objectiveId) {
        throw new Error(
          language === "ar"
            ? "لا يوجد هدف تعليمي متاح حاليًا. ابدأ جلسة أولًا."
            : "No learning objective available yet. Create a session first.",
        );
      }
      const q = await generateQuiz({
        session_id: sid,
        objective_id: objectiveId,
        num_questions: 3,
        preferred_language: language,
      });
      setQuiz(q);
      setQuizAnswers({});
      setQuizGrade(null);
    } catch (err) {
      setError(language === "ar" ? "تعذر إنشاء الاختبار." : err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setQuizLoading(false);
    }
  }

  async function handleGradeQuiz() {
    if (!quiz) return;
    setQuizLoading(true);
    setError(null);
    try {
      const sid = await ensureSession();
      const grade = await gradeQuiz({
        session_id: sid,
        objective_id: quiz.objective_id,
        answers: quizAnswers,
      });
      setQuizGrade(grade);
    } catch (err) {
      setError(language === "ar" ? "تعذر تصحيح الاختبار." : err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setQuizLoading(false);
    }
  }

  useEffect(() => {
    void handleLoadSources();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

  useEffect(() => {
    setSourceTopic(language === "ar" ? "فقه" : "fiqh");
  }, [language]);

  function ikhtilafStatusLabel(status: "ikhtilaf" | "consensus" | "insufficient"): string {
    if (language === "ar") {
      if (status === "ikhtilaf") return "اختلاف معتبر";
      if (status === "consensus") return "اتفاق";
      return "بيانات غير كافية";
    }
    if (status === "ikhtilaf") return "Ikhtilaf";
    if (status === "consensus") return "Consensus";
    return "Insufficient Data";
  }

  function ikhtilafStatusStyle(status: "ikhtilaf" | "consensus" | "insufficient"): string {
    if (status === "ikhtilaf") return "bg-amber-100 text-amber-900";
    if (status === "consensus") return "bg-emerald-100 text-emerald-900";
    return "bg-slate-100 text-slate-800";
  }

  function stanceLabel(stance: "invalidates" | "does_not_invalidate" | "unclear"): string {
    if (language === "ar") {
      if (stance === "invalidates") return "ناقض للوضوء";
      if (stance === "does_not_invalidate") return "غير ناقض بمفرده";
      return "غير صريح";
    }
    if (stance === "invalidates") return "Nullifies";
    if (stance === "does_not_invalidate") return "Does Not Nullify";
    return "Unclear";
  }

  function sourceTypeLabel(sourceType: "quran" | "hadith" | "fiqh"): string {
    if (language === "ar") {
      if (sourceType === "quran") return "القرآن";
      if (sourceType === "hadith") return "السنة";
      return "الفقه";
    }
    if (sourceType === "quran") return "Quran";
    if (sourceType === "hadith") return "Sunnah";
    return "Fiqh";
  }

  function authenticityLabel(level: string): string {
    if (language === "ar") {
      if (level === "qat_i") return "قطعي الثبوت";
      if (level === "sahih") return "صحيح";
      if (level === "hasan") return "حسن";
      if (level === "mu_tabar") return "معتبر";
      return "موثّق";
    }
    return level;
  }

  function validationReasonLabel(reason: string): string {
    if (language === "ar") {
      if (reason === "passed") return "تم اجتياز التحقق";
      if (reason === "citation_integrity_failed") return "فشل في سلامة الاستشهاد";
      if (reason === "grounding_below_threshold") return "الاستناد أقل من العتبة";
      if (reason === "faithfulness_below_threshold") return "التوافق مع الدليل أقل من العتبة";
      if (reason === "abstained_by_safety_policy") return "تم التحفظ بسبب سياسة السلامة";
      return "نتيجة تحقق غير معروفة";
    }
    return reason.replaceAll("_", " ");
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 md:px-8" dir={dir}>
      <section className="card-enter rounded-3xl border border-white/70 bg-white/80 p-6 shadow-soft backdrop-blur md:p-10">
        <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-oasis">
              {language === "ar" ? "نور المسار" : "NurPath"}
            </p>
            <h1 className="mt-2 text-3xl font-bold text-ink md:text-5xl">
              {language === "ar"
                ? "مُعلّم ذكي للمعرفة الإسلامية المبنية على الدليل"
                : "An evidence-first tutor for Islamic learning"}
            </h1>
            <p className="mt-4 max-w-2xl text-sm text-ink/80 md:text-base">
              {language === "ar"
                ? "يعرض الأقوال الفقهية المختلفة، ويربط كل ادعاء بمصدر واضح، ويقترح مسار تعلم لاحق."
                : "Compare scholarly positions, inspect citations, and get a personalized next lesson path."}
            </p>
          </div>

          <div className="flex gap-2">
            <button
              className={`rounded-full px-4 py-2 text-sm font-semibold ${
                language === "ar" ? "bg-oasis text-white" : "bg-sand text-ink"
              }`}
              onClick={() => setLanguage("ar")}
              type="button"
            >
              {language === "ar" ? "العربية" : "Arabic"}
            </button>
            <button
              className={`rounded-full px-4 py-2 text-sm font-semibold ${
                language === "en" ? "bg-oasis text-white" : "bg-sand text-ink"
              }`}
              onClick={() => setLanguage("en")}
              type="button"
            >
              {language === "ar" ? "الإنجليزية" : "English"}
            </button>
          </div>
        </div>

        <form onSubmit={handleAsk} className="mt-8 grid gap-3">
          <label className="text-sm font-semibold text-ink/90">
            {language === "ar" ? "سؤالك" : "Your question"}
          </label>
          <textarea
            className="min-h-28 rounded-2xl border border-ink/15 bg-white px-4 py-3 text-base outline-none transition focus:border-oasis"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleCreateSession}
              className="rounded-xl bg-sand px-4 py-2 text-sm font-semibold text-ink"
            >
              {language === "ar" ? "بدء جلسة" : "Create Session"}
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-xl bg-oasis px-5 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {loading ? (language === "ar" ? "جاري المعالجة..." : "Working...") : language === "ar" ? "اسأل" : "Ask"}
            </button>
          </div>

          {sessionId && language === "en" && (
            <p className="text-xs text-ink/70">
              Session ID: <span className="font-mono">{sessionId}</span>
            </p>
          )}

          {error && <p className="text-sm text-red-700">{error}</p>}
        </form>
      </section>

      <section className="mt-8 grid gap-4 md:grid-cols-2">
        <article className="card-enter rounded-3xl border border-white/70 bg-white/85 p-5 shadow-soft">
          <h3 className="text-lg font-bold text-ink">{language === "ar" ? "مستكشف المصادر" : "Source Explorer"}</h3>
          <form className="mt-3 grid gap-3" onSubmit={handleLoadSources}>
            <input
              className="rounded-xl border border-ink/15 bg-white px-3 py-2 text-sm"
              value={sourceTopic}
              onChange={(e) => setSourceTopic(e.target.value)}
              placeholder={language === "ar" ? "موضوع (مثل: فقه)" : "Topic (e.g. fiqh)"}
            />
            <input
              className="rounded-xl border border-ink/15 bg-white px-3 py-2 text-sm"
              value={sourceQuery}
              onChange={(e) => setSourceQuery(e.target.value)}
              placeholder={language === "ar" ? "بحث بالنص" : "Text search"}
            />
            <button className="rounded-xl bg-oasis px-4 py-2 text-sm font-semibold text-white" type="submit">
              {sourceLoading ? (language === "ar" ? "جاري التحميل..." : "Loading...") : language === "ar" ? "تحديث" : "Refresh"}
            </button>
          </form>

          <div className="mt-4 max-h-80 space-y-2 overflow-auto">
            {sources.map((s) => (
              <a key={s.id} href={s.url} target="_blank" rel="noreferrer" className="block rounded-xl border border-ink/10 p-3 hover:bg-sand/40">
                <p className="text-sm font-semibold text-ink">{language === "ar" ? s.title_ar : s.title}</p>
                {language === "ar" ? (
                  <p className="text-xs text-ink/70">
                    {s.author_ar} • {sourceTypeLabel(s.source_type)} • {authenticityLabel(s.authenticity_level)}
                  </p>
                ) : (
                  <p className="text-xs text-ink/70">{s.author} • {s.language} • {s.license}</p>
                )}
              </a>
            ))}
            {sources.length === 0 && <p className="text-sm text-ink/70">{language === "ar" ? "لا توجد نتائج." : "No sources found."}</p>}
          </div>
        </article>

        <article className="card-enter rounded-3xl border border-white/70 bg-white/85 p-5 shadow-soft">
          <h3 className="text-lg font-bold text-ink">{language === "ar" ? "تقييم التعلم" : "Learning Quiz"}</h3>
          <button
            className="mt-3 rounded-xl bg-warm px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            type="button"
            onClick={handleGenerateQuiz}
            disabled={quizLoading}
          >
            {quizLoading ? (language === "ar" ? "جاري التحضير..." : "Preparing...") : language === "ar" ? "إنشاء اختبار" : "Generate Quiz"}
          </button>

          {quiz && (
            <div className="mt-4 space-y-3">
              {quiz.questions.map((q, idx) => (
                <div key={q.id} className="rounded-xl border border-ink/10 p-3">
                  <p className="text-sm font-semibold text-ink">{idx + 1}. {q.prompt}</p>
                  <textarea
                    className="mt-2 min-h-20 w-full rounded-lg border border-ink/15 p-2 text-sm"
                    value={quizAnswers[q.id] ?? ""}
                    onChange={(e) => setQuizAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
                  />
                </div>
              ))}
              <button
                className="rounded-xl bg-oasis px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                type="button"
                onClick={handleGradeQuiz}
                disabled={quizLoading}
              >
                {language === "ar" ? "تصحيح" : "Grade"}
              </button>
            </div>
          )}

          {quizGrade && (
            <p className="mt-3 rounded-lg bg-sand px-3 py-2 text-sm text-ink">
              {language === "ar" ? "النتيجة" : "Score"}: {(quizGrade.score * 100).toFixed(0)}%
            </p>
          )}
        </article>
      </section>

      {result && (
        <section className="card-enter mt-8 grid gap-4 md:grid-cols-5">
          <article className="rounded-3xl border border-white/70 bg-white/85 p-5 shadow-soft md:col-span-3">
            <h2 className="text-xl font-bold text-ink">{language === "ar" ? "الإجابة" : "Answer"}</h2>
            <p className="mt-3 leading-8 text-ink/90">{result.direct_answer}</p>
            <p className="mt-4 text-xs uppercase tracking-wide text-warm">
              {language === "ar" ? "درجة الثقة" : "Confidence"}: {(result.confidence * 100).toFixed(0)}%
            </p>
            <div className="mt-3 rounded-xl border border-ink/10 bg-sand/40 px-3 py-2 text-xs text-ink/90">
              <p>
                {language === "ar" ? "حالة التحقق" : "Validation"}:{" "}
                {result.validation.passed
                  ? language === "ar"
                    ? "مقبول"
                    : "Passed"
                  : language === "ar"
                    ? "مرفوض"
                    : "Failed"}
              </p>
              <p>
                {language === "ar" ? "السبب" : "Reason"}:{" "}
                {validationReasonLabel(result.validation.decision_reason)}
              </p>
              <p>
                {language === "ar" ? "تغطية الاستشهاد" : "Citation Coverage"}:{" "}
                {(result.validation.citation_integrity.coverage * 100).toFixed(0)}%
              </p>
            </div>
            {result.safety_notice && (
              <p className="mt-3 rounded-xl bg-amber-100 px-3 py-2 text-sm text-amber-900">{result.safety_notice}</p>
            )}
          </article>

          <article className="rounded-3xl border border-white/70 bg-white/85 p-5 shadow-soft md:col-span-2">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-lg font-bold text-ink">
                {language === "ar" ? "الاختلاف الفقهي" : "Opinion Comparison"}
              </h3>
              {result.ikhtilaf_analysis && (
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${ikhtilafStatusStyle(
                    result.ikhtilaf_analysis.status,
                  )}`}
                >
                  {ikhtilafStatusLabel(result.ikhtilaf_analysis.status)}
                </span>
              )}
            </div>
            {result.ikhtilaf_analysis && (
              <p className="mt-2 text-sm text-ink/80">{result.ikhtilaf_analysis.summary}</p>
            )}
            <div className="mt-3 space-y-3">
              {result.opinion_comparison.length === 0 && (
                <p className="text-sm text-ink/70">{language === "ar" ? "لا يوجد مقارنة متاحة." : "No comparison available."}</p>
              )}
              {result.opinion_comparison.map((item) => (
                <div key={item.school_or_scholar} className="rounded-xl border border-ink/10 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-semibold text-ink">{item.school_or_scholar}</p>
                    <span className="rounded-full bg-sand px-2 py-1 text-[10px] font-semibold uppercase text-ink/90">
                      {stanceLabel(item.stance_type)}
                    </span>
                  </div>
                  <p className="text-sm text-ink/80">{item.stance_summary}</p>
                </div>
              ))}
              {result.ikhtilaf_analysis && result.ikhtilaf_analysis.conflict_pairs.length > 0 && (
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                  <p className="font-semibold">
                    {language === "ar" ? "أزواج التعارض المكتشفة" : "Detected conflict pairs"}
                  </p>
                  {result.ikhtilaf_analysis.conflict_pairs.map((pair) => (
                    <p key={`${pair.school_a}-${pair.school_b}-${pair.issue_topic}`} className="mt-1">
                      {pair.school_a} ↔ {pair.school_b} (
                      {language === "ar" && /[A-Za-z]/.test(pair.issue_topic) ? "المسألة" : pair.issue_topic})
                    </p>
                  ))}
                </div>
              )}
            </div>
          </article>

          <article className="rounded-3xl border border-white/70 bg-white/85 p-5 shadow-soft md:col-span-5">
            <h3 className="text-lg font-bold text-ink">{language === "ar" ? "بطاقات الدليل" : "Evidence Cards"}</h3>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {result.evidence_cards.map((card) => (
                <div key={card.passage_id} className="rounded-2xl border border-ink/10 bg-white p-4">
                  <p className="text-sm font-semibold text-ink">
                    {language === "ar" ? card.source_title_ar : card.source_title}
                  </p>
                  {language === "ar" ? (
                    <p className="mt-1 text-xs text-ink/70">
                      {sourceTypeLabel(card.source_type)} • {authenticityLabel(card.authenticity_level)}
                    </p>
                  ) : null}
                  <p className="mt-2 text-sm text-ink/80">{card.arabic_quote}</p>
                  {language === "en" ? <p className="mt-2 text-sm text-ink/80">{card.english_quote}</p> : null}
                  {card.reference?.display_ar && language === "ar" ? (
                    <p className="mt-2 text-xs text-ink/70">{card.reference.display_ar}</p>
                  ) : null}
                  <a
                    href={card.passage_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-block text-xs font-semibold text-oasis underline"
                  >
                    {language === "ar" ? "المرجع التفصيلي" : "Open passage"}
                  </a>
                </div>
              ))}
            </div>
          </article>
        </section>
      )}
    </main>
  );
}
