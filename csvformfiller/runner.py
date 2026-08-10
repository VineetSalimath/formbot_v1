from __future__ import annotations

import random
import time
from pathlib import Path

from selenium import webdriver

from .adapters import MicrosoftFormsAdapter
from .logging_utils import append_log, successful_ids
from .models import MappingConfig, PacingConfig


def pause(minimum: float, maximum: float, label: str) -> None:
    delay = random.uniform(minimum, maximum)
    print(f"  {label}: {delay:.1f}s")
    time.sleep(delay)


def expected_mapping_keys(mapping: MappingConfig) -> set[str]:
    keys = {f"field:{field.column}" for field in mapping.fields}
    keys.update(f"matrix:{matrix.name}" for matrix in mapping.matrices)
    return keys


def run_rows(
    *,
    url: str,
    rows: list[dict[str, str]],
    mapping: MappingConfig,
    submit: bool,
    id_column: str | None,
    limit: int | None,
    pacing: PacingConfig,
    log_file: str,
    screenshot_dir: str,
    start_index: int = 1,
) -> None:
    pacing.validate()
    Path(screenshot_dir).mkdir(parents=True, exist_ok=True)

    if limit is not None:
        rows = rows[:limit]

    done = successful_ids(log_file) if submit else set()

    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    adapter = MicrosoftFormsAdapter(driver)

    expected_keys = expected_mapping_keys(mapping)

    try:
        for ordinal, row in enumerate(rows, start=start_index):
            row_id = (
                str(row.get(id_column, "")).strip()
                if id_column
                else f"ROW-{ordinal:04d}"
            )
            if not row_id:
                row_id = f"ROW-{ordinal:04d}"

            if submit and row_id in done:
                print(f"Skipping {row_id}: already logged SUCCESS")
                continue

            print("\n" + "=" * 72)
            print(f"Filling {row_id}")
            print("=" * 72)

            driver.get(url)
            completed: set[str] = set()
            visited_pages = 0

            try:
                while True:
                    visited_pages += 1
                    if visited_pages > 50:
                        raise RuntimeError("Aborted after 50 pages to prevent a loop")

                    completed = adapter.fill_visible_page(
                        row,
                        mapping,
                        completed,
                    )

                    if adapter.has_next():
                        pause(
                            pacing.page_delay_min,
                            pacing.page_delay_max,
                            "Page pacing",
                        )
                        adapter.click_next()
                        continue

                    if adapter.has_submit():
                        break

                    raise RuntimeError(
                        "No visible Next or Submit button. The form may contain "
                        "an unsupported control or a validation error."
                    )

                missing = sorted(expected_keys - completed)
                if missing:
                    raise RuntimeError(
                        "Mapped fields were not encountered in the form: "
                        + ", ".join(missing)
                    )

                if not submit:
                    print("\nDRY RUN: final page filled; nothing was submitted.")
                    input("Press ENTER after inspecting the browser...")
                    break

                adapter.click_submit()
                adapter.wait_for_submission_confirmation(timeout=45)
                print(f"  SUCCESS: {row_id}")
                append_log(log_file, row_id, "SUCCESS")
                done.add(row_id)

                if row is not rows[-1]:
                    pause(
                        pacing.row_delay_min,
                        pacing.row_delay_max,
                        "Pause before next CSV row",
                    )

            except Exception as error:
                screenshot = Path(screenshot_dir) / f"failed_{row_id}.png"
                try:
                    driver.save_screenshot(str(screenshot))
                except Exception:
                    pass

                try:
                    Path("last_page.txt").write_text(
                        driver.find_element("tag name", "body").text,
                        encoding="utf-8",
                    )
                    Path("last_page.html").write_text(
                        driver.page_source,
                        encoding="utf-8",
                    )
                except Exception:
                    pass

                if submit:
                    append_log(log_file, row_id, "FAILED", str(error))

                print(f"\nFAILED: {row_id}")
                print(f"Reason: {error}")
                print(f"Screenshot: {screenshot}")
                raise
    finally:
        driver.quit()
