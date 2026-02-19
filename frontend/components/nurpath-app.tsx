"use client";

import { FormEvent, useMemo, useState } from "react";
import { AskResponse, askQuestion, createSession } from "@/lib/api";

export function NurPathApp() {
  const [language, setLanguage] = useState<"ar" | "en">("ar");
  const [question, setQuestion] = useState("ما الفرق في الوضوء عند لمس الزوجة؟");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dir = useMemo(() => (language === "ar" ? "rtl" : "ltr"), [language]);

  async function handleCreateSession() {
    setError(null);
    const s = await createSession(language);
    setSessionId(s.session_id);
  }

  async function handleAsk(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let sid = sessionId;
      if (!sid) {
        const s = await createSession(language);
        sid = s.session_id;
        setSessionId(sid);
      }

      if (!sid) {
        throw new Error("Session initialization failed");
      }

      const response = await askQuestion({
        session_id: sid,
        question,
        preferred_language: language,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 md:px-8" dir={dir}>
      <section className="card-enter rounded-3xl border border-white/70 bg-white/80 p-6 shadow-soft backdrop-blur md:p-10">
        <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-oasis">NurPath</p>
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
              عربي
            </button>
            <button
              className={`rounded-full px-4 py-2 text-sm font-semibold ${
                language === "en" ? "bg-oasis text-white" : "bg-sand text-ink"
              }`}
              onClick={() => setLanguage("en")}
              type="button"
            >
              English
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

          {sessionId && (
            <p className="text-xs text-ink/70">
              {language === "ar" ? "معرّف الجلسة:" : "Session ID:"} <span className="font-mono">{sessionId}</span>
            </p>
          )}

          {error && <p className="text-sm text-red-700">{error}</p>}
        </form>
      </section>

      {result && (
        <section className="card-enter mt-8 grid gap-4 md:grid-cols-5">
          <article className="rounded-3xl border border-white/70 bg-white/85 p-5 shadow-soft md:col-span-3">
            <h2 className="text-xl font-bold text-ink">{language === "ar" ? "الإجابة" : "Answer"}</h2>
            <p className="mt-3 leading-8 text-ink/90">{result.direct_answer}</p>
            <p className="mt-4 text-xs uppercase tracking-wide text-warm">
              {language === "ar" ? "درجة الثقة" : "Confidence"}: {(result.confidence * 100).toFixed(0)}%
            </p>
            {result.safety_notice && (
              <p className="mt-3 rounded-xl bg-amber-100 px-3 py-2 text-sm text-amber-900">{result.safety_notice}</p>
            )}
          </article>

          <article className="rounded-3xl border border-white/70 bg-white/85 p-5 shadow-soft md:col-span-2">
            <h3 className="text-lg font-bold text-ink">{language === "ar" ? "الاختلاف الفقهي" : "Opinion Comparison"}</h3>
            <div className="mt-3 space-y-3">
              {result.opinion_comparison.length === 0 && (
                <p className="text-sm text-ink/70">{language === "ar" ? "لا يوجد مقارنة متاحة." : "No comparison available."}</p>
              )}
              {result.opinion_comparison.map((item) => (
                <div key={item.school_or_scholar} className="rounded-xl border border-ink/10 p-3">
                  <p className="font-semibold text-ink">{item.school_or_scholar}</p>
                  <p className="text-sm text-ink/80">{item.stance_summary}</p>
                </div>
              ))}
            </div>
          </article>

          <article className="rounded-3xl border border-white/70 bg-white/85 p-5 shadow-soft md:col-span-5">
            <h3 className="text-lg font-bold text-ink">{language === "ar" ? "بطاقات الدليل" : "Evidence Cards"}</h3>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {result.evidence_cards.map((card) => (
                <div key={card.passage_id} className="rounded-2xl border border-ink/10 bg-white p-4">
                  <p className="text-sm font-semibold text-ink">{card.source_title}</p>
                  <p className="mt-2 text-sm text-ink/80">{card.arabic_quote}</p>
                  <p className="mt-2 text-sm text-ink/80">{card.english_quote}</p>
                  <a
                    href={card.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-block text-xs font-semibold text-oasis underline"
                  >
                    {language === "ar" ? "المصدر" : "Source"}
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
