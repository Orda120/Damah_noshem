import assert from "node:assert/strict";
import test from "node:test";

import { defaultLocalePath } from "@/middleware";

test("default locale path redirects root to Hebrew login", () => {
  assert.equal(defaultLocalePath("/"), "/he/login");
});

test("default locale path preserves nested routes under Hebrew prefix", () => {
  assert.equal(defaultLocalePath("/workspaces/123"), "/he/workspaces/123");
});
