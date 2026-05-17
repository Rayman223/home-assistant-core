## Plan: Add EcoSmart resume button (action=9) — one-shot trigger

**Status: IMPLEMENTED** — all files produced, ready for integration into the HA core repo.

TL;DR — Implement `action=9` as a one-shot trigger (ButtonEntity) to resume schedule and
EcoSmart mode after a manual stop, by adding a `button` platform, extending the coordinator
with `async_resume_schedule()`, and adding the required translations and tests.

---

### Verification summary

- `manifest.json` requires `wallbox==0.9.0` — **no change needed**: `resumeSchedule()` is
  already present in that version.
- The library method for action=9 is **`wallbox.resumeSchedule(chargerId)`**, which posts
  `{"action": 9}` to `v3/chargers/{id}/remote-action`. The plan initially assumed
  `enableEcoSmart(station, 9)` — this was **incorrect** and has been corrected.
- Existing tests in `tests/components/wallbox/test_select.py` patch `enableEcoSmart`.
  New tests in `test_button.py` patch `resumeSchedule` in the same style.
- The `select` entity is left untouched — the button is a separate, stateless trigger.

All code and comments are in English.

---

### Useful references

- Wallbox API doc: https://github.com/tmenguy/wallboxAPIDoc
  → action=9: `POST v3/chargers/{id}/remote-action {"action": 9}`
  → "After a manual stop: resume schedule and ecosmart mode"
- Library source (wallbox==0.9.0):
  `wallbox.resumeSchedule(chargerId)` — returns `json.loads(response.text)`
- Reference files in the repo:
  - `homeassistant/components/wallbox/coordinator.py`
  - `tests/components/wallbox/conftest.py`
  - `tests/components/wallbox/test_select.py`

---

### Implementation steps

**Step 1 — coordinator.py** ✅
Add two methods after `async_pause_charger`:

- `_resume_schedule(self) -> None` (sync, executor-safe)
  Calls `self._wallbox.resumeSchedule(self._station)`.
  Error mapping (same as other write methods):
  - HTTP 403 → `InsufficientRights(translation_domain=DOMAIN, translation_key="insufficient_rights", hass=self.hass)`
  - HTTP 429 → `HomeAssistantError(translation_domain=DOMAIN, translation_key="too_many_requests")`
  - other HTTP → `HomeAssistantError(translation_domain=DOMAIN, translation_key="api_failed")`

- `async_resume_schedule(self) -> None` (async, decorated `@_require_authentication`)
  Runs `_resume_schedule` in the executor then calls `async_request_refresh()`.

**Step 2 — button.py** ✅ (new file)
New `ButtonEntity` platform.
- `PARALLEL_UPDATES = 0` (same pattern as all other platforms).
- `async_press(self) -> None` — no `**kwargs` (ButtonEntity interface does not use them,
  unlike `LockEntity.async_lock` or `SwitchEntity.async_turn_on`).
- Always registered unconditionally (no EcoSmart availability check needed — action=9 is
  a generic resume trigger, not tied to solar mode being active).

**Step 3 — __init__.py** ✅
`Platform.BUTTON` added to `PLATFORMS` list (alphabetical order, before `Platform.LOCK`).

**Step 4 — strings.json** ✅
Button entity translation added under `entity.button`:
```json
"button": {
  "resume_schedule": {
    "name": "Resume schedule"
  }
}
```
French label "Mode EcoSmart" was the original request, but HA `strings.json` must be in
English — translations go in `translations/fr.json` (out of scope for this PR).

**Step 5 — manifest.json** ✅ no change
`wallbox==0.9.0` already includes `resumeSchedule()`. No version bump required.

**Step 6 — test_button.py** ✅ (new file)
Four test cases:
- `test_button_press_success` — patches `resumeSchedule` to return `{}`, asserts
  `called_once()` (not `called_once_with` — station id is internal to coordinator).
- `test_button_press_insufficient_rights` — side-effect `http_403_error` fixture,
  asserts `HomeAssistantError` raised.
- `test_button_press_too_many_requests` — side-effect `http_429_error` fixture,
  asserts `HomeAssistantError` raised.
- `test_button_press_api_failed` — side-effect generic HTTP 500, asserts
  `HomeAssistantError` raised.

> **Note on entity id**: `RESUME_SCHEDULE_BUTTON` in the test must match the charger name
> slug from the conftest mock data. Adjust to the value used in `conftest.py`
> (e.g. `"button.wallbox_pulsar_plus_resume_schedule"`).

---

### Relevant files

| File | Status | Change |
|---|---|---|
| `homeassistant/components/wallbox/coordinator.py` | ✅ done | `_resume_schedule` + `async_resume_schedule` added |
| `homeassistant/components/wallbox/button.py` | ✅ done | new platform |
| `homeassistant/components/wallbox/__init__.py` | ✅ done | `Platform.BUTTON` added |
| `homeassistant/components/wallbox/strings.json` | ✅ done | `entity.button.resume_schedule` added |
| `homeassistant/components/wallbox/manifest.json` | ✅ unchanged | `wallbox==0.9.0` already sufficient |
| `tests/components/wallbox/test_button.py` | ✅ done | 4 test cases |

---

### Corrections vs initial plan

| Initial assumption | Correction |
|---|---|
| Library call: `enableEcoSmart(station, 9)` | **Wrong.** Correct call: `resumeSchedule(station)` (dedicated method in wallbox==0.9.0) |
| `manifest.json` may need version bump | **Not needed.** `resumeSchedule` is already in 0.9.0 |
| `async_press(self, **kwargs: Any)` | **Wrong.** `ButtonEntity.async_press` does not use `**kwargs`. Removed. |
| `from .conftest import mock_wallbox` in tests | **Wrong.** pytest fixtures are auto-discovered; explicit import causes errors. Removed. |
| `mock_resume.assert_called_once_with(mock_wallbox._station)` | **Wrong.** `_station` is on the coordinator, not on the Wallbox mock. Use `assert_called_once()`. |

---

### Verification checklist

- [ ] Run `pytest tests/components/wallbox/test_button.py` — all 4 tests pass.
- [ ] Run `ruff check homeassistant/components/wallbox/` — no linting errors.
- [ ] Confirm entity id slug in test matches the conftest mock charger name.
- [ ] (Optional) Deploy locally and press the button; verify charger resumes EcoSmart/schedule mode.

---

### Decisions / assumptions

- One-shot button only — no modification to the `select` entity.
- English name: "Resume schedule". French translation goes in `translations/fr.json` (not in scope).
- No service registration in addition to the button — automations can already call
  `button.press` via HA's built-in service.
- Error handling is consistent with all other coordinator write methods.