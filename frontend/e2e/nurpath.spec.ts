import { expect, test } from "@playwright/test";

test.describe("NurPath end-to-end", () => {
  test("Arabic ask flow keeps visible content Arabic-only", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("button", { name: "اسأل" }).click();

    await expect(page.getByRole("heading", { name: "الإجابة" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "بطاقات الدليل" })).toBeVisible();
    await expect(page.getByText("حالة التحقق")).toBeVisible();
    await expect(
      page.locator("span", { hasText: /اختلاف معتبر|اتفاق|بيانات غير كافية/ }),
    ).toBeVisible();

    const hasLatin = await page.evaluate(() => /[A-Za-z]/.test(document.querySelector("main")?.innerText ?? ""));
    expect(hasLatin).toBeFalsy();
  });

  test("English mode supports source explorer and quiz grading", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "الإنجليزية" }).click();

    await expect(page.getByRole("heading", { name: "Source Explorer" })).toBeVisible();

    await page.getByRole("button", { name: "Refresh" }).click();
    await expect(page.getByRole("link").first()).toBeVisible();

    await page.getByRole("button", { name: "Generate Quiz" }).click();
    const firstQuestion = page.locator("textarea").nth(1);
    await expect(firstQuestion).toBeVisible();
    await firstQuestion.fill("evidence scholar difference citation");

    const secondQuestion = page.locator("textarea").nth(2);
    await secondQuestion.fill("evidence scholar difference citation");

    const thirdQuestion = page.locator("textarea").nth(3);
    await thirdQuestion.fill("evidence scholar difference citation");

    await page.getByRole("button", { name: "Grade" }).click();
    await expect(page.getByText(/Score:/)).toBeVisible();
  });

  test("Sensitive fatwa query triggers abstain safety notice", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "الإنجليزية" }).click();

    const mainQuestion = page.locator("textarea").first();
    await mainQuestion.fill("I need a personal fatwa for my private divorce case");
    await page.getByRole("button", { name: "Ask" }).click();

    await expect(page.getByText("Educational guidance only. Escalate to a qualified scholar.")).toBeVisible();
  });

  test("English non-comparative query shows insufficient-data status", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "الإنجليزية" }).click();

    const mainQuestion = page.locator("textarea").first();
    await mainQuestion.fill("What is ihsan in hadith jibril?");
    await page.getByRole("button", { name: "Ask" }).click();

    await expect(page.getByText("Insufficient Data")).toBeVisible();
  });

  test("Evidence links target passage-level references", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "الإنجليزية" }).click();

    const mainQuestion = page.locator("textarea").first();
    await mainQuestion.fill("What are wudu evidences from Quran and Sunnah?");
    await page.getByRole("button", { name: "Ask" }).click();

    const firstEvidenceLink = page.getByRole("link", { name: "Open passage" }).first();
    await expect(firstEvidenceLink).toBeVisible();
    const href = await firstEvidenceLink.getAttribute("href");
    expect(href).toBeTruthy();
    expect(href).not.toBe("https://shamela.ws/book/1655");
  });
});
