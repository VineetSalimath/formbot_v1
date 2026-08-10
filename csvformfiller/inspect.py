from __future__ import annotations

import json
from pathlib import Path

from selenium import webdriver

from .adapters import MicrosoftFormsAdapter


def inspect_form(url: str, output: str | None = None) -> None:
    driver = webdriver.Chrome()
    adapter = MicrosoftFormsAdapter(driver)
    captured: list[dict] = []

    try:
        driver.get(url)
        page_number = 1

        while True:
            print(f"\n--- Capture page {page_number} ---")
            page = adapter.inspect_visible_page()
            captured.append({"page": page_number, "questions": page})

            for question in page:
                preview = question["text"][:140].replace("\n", " | ")
                print(
                    f"[{question['index']}] {question['type']}: {preview}"
                )

            print(
                "\nNavigate the browser manually if another page exists, then "
                "press ENTER to capture it. Type q and ENTER when finished."
            )
            command = input("> ").strip().lower()
            if command == "q":
                break
            page_number += 1

    finally:
        driver.quit()

    payload = {"provider": "microsoft_forms", "pages": captured}
    text = json.dumps(payload, indent=2, ensure_ascii=False)

    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
        print(f"Saved inspection to {output}")
    else:
        print(text)
