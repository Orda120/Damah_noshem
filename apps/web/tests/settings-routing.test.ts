import assert from "node:assert/strict";
import test from "node:test";

import { buildLocaleHref } from "@/lib/api";
import { getMessages, normalizeLocale } from "@/lib/i18n";

test("settings route builds under the selected locale", () => {
  assert.equal(buildLocaleHref("he", "/settings"), "/he/settings");
  assert.equal(buildLocaleHref("en", "/settings"), "/en/settings");
  assert.equal(buildLocaleHref("he", "/settings#language"), "/he/settings#language");
  assert.equal(buildLocaleHref("en", "/settings#logout"), "/en/settings#logout");
});

test("settings labels are available in both locales", () => {
  assert.equal(getMessages("he").settings, "הגדרות");
  assert.equal(getMessages("en").settings, "Settings");
  assert.equal(getMessages("he").language, "שפה");
  assert.equal(getMessages("en").language, "Language");
});

test("unknown locales still normalize to Hebrew", () => {
  assert.equal(normalizeLocale("fr"), "he");
});
