from __future__ import annotations

import re
import time
from typing import Any

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from .base import FormAdapter
from ..models import FieldMapping, MappingConfig, MatrixMapping


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def norm(value: Any) -> str:
    return clean(value).casefold()


def xpath_literal(text: str) -> str:
    if '"' not in text:
        return f'"{text}"'
    if "'" not in text:
        return f"'{text}'"

    parts = text.split('"')
    expressions: list[str] = []
    for index, part in enumerate(parts):
        if part:
            expressions.append(f'"{part}"')
        if index < len(parts) - 1:
            expressions.append("'\"'")
    return "concat(" + ", ".join(expressions) + ")"


class MicrosoftFormsAdapter(FormAdapter):
    QUESTION_SELECTOR = "div[data-automation-id='questionItem']"

    def __init__(self, driver, render_wait: float = 1.0):
        self.driver = driver
        self.render_wait = render_wait

    def _click(self, element) -> None:
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});",
            element,
        )
        self.driver.execute_script("arguments[0].click();", element)

    def _question_container(self, question_text: str):
        literal = xpath_literal(question_text)
        xpath = (
            "//div[@data-automation-id='questionItem']"
            f"[.//*[contains(normalize-space(.), {literal})]]"
        )
        matches = [
            item
            for item in self.driver.find_elements(By.XPATH, xpath)
            if item.is_displayed()
        ]

        if not matches:
            return None
        if len(matches) > 1:
            raise RuntimeError(
                f"Question text {question_text!r} matched multiple visible questions. "
                "Use a more specific mapping phrase."
            )
        return matches[0]

    def _question_text(self, container) -> str:
        return clean(container.text)

    def inspect_visible_page(self) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for index, container in enumerate(
            self.driver.find_elements(By.CSS_SELECTOR, self.QUESTION_SELECTOR),
            start=1,
        ):
            if not container.is_displayed():
                continue

            radios = container.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
            checks = container.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
            texts = container.find_elements(
                By.CSS_SELECTOR,
                'input[data-automation-id="textInput"], textarea',
            )

            radio_groups = {}
            for radio in radios:
                name = radio.get_attribute("name") or ""
                radio_groups.setdefault(name, []).append(radio)

            if len(radio_groups) > 1:
                detected_type = "matrix"
            elif radios:
                detected_type = "radio"
            elif checks:
                detected_type = "checkbox"
            elif texts:
                detected_type = "text"
            else:
                detected_type = "unknown"

            options = []
            source = radios if radios else checks
            for element in source:
                value = clean(element.get_attribute("value"))
                if value and value not in options:
                    options.append(value)

            output.append(
                {
                    "index": index,
                    "type": detected_type,
                    "text": self._question_text(container),
                    "options": options,
                    "radio_group_count": len(radio_groups),
                }
            )
        return output

    def _fill_radio(self, container, value: str) -> None:
        target = norm(value)
        radios = container.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
        matches = [
            radio
            for radio in radios
            if norm(radio.get_attribute("value")) == target
        ]
        if len(matches) != 1:
            available = sorted(
                {
                    clean(radio.get_attribute("value"))
                    for radio in radios
                    if clean(radio.get_attribute("value"))
                }
            )
            raise RuntimeError(
                f"Expected one radio option {value!r}; found {len(matches)}. "
                f"Available: {available}"
            )
        self._click(matches[0])

    def _fill_checkbox(self, container, raw_value: str, separator: str) -> None:
        requested = {
            norm(item)
            for item in raw_value.split(separator)
            if clean(item)
        }
        if not requested:
            return

        checks = container.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
        found: set[str] = set()
        for checkbox in checks:
            value = clean(checkbox.get_attribute("value"))
            if not value:
                continue
            if norm(value) in requested:
                self._click(checkbox)
                found.add(norm(value))

        missing = requested - found
        if missing:
            raise RuntimeError(
                "Checkbox value(s) not found: " + ", ".join(sorted(missing))
            )

    def _fill_text(self, container, value: str) -> None:
        inputs = [
            element
            for element in container.find_elements(
                By.CSS_SELECTOR,
                'input[data-automation-id="textInput"], textarea',
            )
            if element.is_displayed()
        ]
        if len(inputs) != 1:
            raise RuntimeError(
                f"Expected exactly one visible text input, found {len(inputs)}"
            )
        inputs[0].clear()
        inputs[0].send_keys(clean(value))

    def _fill_field(self, field: FieldMapping, row: dict[str, str]) -> bool:
        container = self._question_container(field.question)
        if container is None:
            return False

        value = row.get(field.column, "")
        if field.type == "radio":
            self._fill_radio(container, value)
        elif field.type == "checkbox":
            self._fill_checkbox(container, value, field.separator)
        elif field.type == "text":
            self._fill_text(container, value)
        else:
            raise RuntimeError(f"Unsupported field type: {field.type}")
        return True

    def _radio_groups_in_order(self, container):
        radios = container.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
        groups: dict[str, list[Any]] = {}
        order: list[str] = []

        for radio in radios:
            name = radio.get_attribute("name") or ""
            if name not in groups:
                groups[name] = []
                order.append(name)
            groups[name].append(radio)

        result = []
        for name in order:
            options = groups[name]
            positions = [item.get_attribute("aria-posinset") for item in options]
            if positions and all(positions):
                try:
                    options.sort(
                        key=lambda item: int(item.get_attribute("aria-posinset"))
                    )
                except (TypeError, ValueError):
                    pass
            result.append(options)
        return result

    def _fill_matrix(self, matrix: MatrixMapping, row: dict[str, str]) -> bool:
        container = self._question_container(matrix.question)
        if container is None:
            return False

        groups = self._radio_groups_in_order(container)
        if len(groups) != len(matrix.columns):
            raise RuntimeError(
                f"Matrix {matrix.name!r} mapped {len(matrix.columns)} CSV columns "
                f"but the visible form has {len(groups)} radio rows"
            )

        option_lookup = {norm(value): index for index, value in enumerate(matrix.options)}

        for row_index, (group, column) in enumerate(
            zip(groups, matrix.columns),
            start=1,
        ):
            answer = row.get(column, "")
            key = norm(answer)
            if key not in option_lookup:
                raise RuntimeError(
                    f"Matrix {matrix.name!r}, row {row_index}: answer {answer!r} "
                    f"is not in configured options {list(matrix.options)}"
                )

            option_index = option_lookup[key]
            if option_index >= len(group):
                raise RuntimeError(
                    f"Matrix {matrix.name!r}, row {row_index}: configured option "
                    f"index {option_index} exceeds visible options ({len(group)})"
                )
            self._click(group[option_index])

        return True

    def fill_visible_page(
        self,
        row: dict[str, str],
        mapping: MappingConfig,
        completed_keys: set[str],
    ) -> set[str]:
        completed = set(completed_keys)

        for field in mapping.fields:
            key = f"field:{field.column}"
            if key in completed:
                continue
            if self._fill_field(field, row):
                completed.add(key)

        for matrix in mapping.matrices:
            key = f"matrix:{matrix.name}"
            if key in completed:
                continue
            if self._fill_matrix(matrix, row):
                completed.add(key)

        return completed

    def _visible_button(self, text: str):
        xpath = f"//button[normalize-space()={xpath_literal(text)}]"
        matches = [
            item
            for item in self.driver.find_elements(By.XPATH, xpath)
            if item.is_displayed()
        ]
        return matches[0] if matches else None

    def has_next(self) -> bool:
        return self._visible_button("Next") is not None

    def click_next(self) -> None:
        button = self._visible_button("Next")
        if button is None:
            raise RuntimeError("No visible Next button")
        self._click(button)
        time.sleep(self.render_wait)

    def has_submit(self) -> bool:
        return self._visible_button("Submit") is not None

    def click_submit(self) -> None:
        button = self._visible_button("Submit")
        if button is None:
            raise RuntimeError("No visible Submit button")
        self._click(button)

    def wait_for_submission_confirmation(self, timeout: int = 45) -> None:
        success_phrases = (
            "your response was submitted",
            "your response has been submitted",
            "response submitted",
            "thanks for submitting",
            "thank you for submitting",
            "submit another response",
            "thanks!",
        )

        def confirmed(driver) -> bool:
            text = clean(driver.find_element(By.TAG_NAME, "body").text).casefold()
            return any(phrase in text for phrase in success_phrases)

        try:
            WebDriverWait(self.driver, timeout).until(confirmed)
        except TimeoutException as error:
            body = clean(self.driver.find_element(By.TAG_NAME, "body").text)
            raise RuntimeError(
                "Submission confirmation could not be verified. "
                f"Visible page text begins: {body[:300]!r}"
            ) from error
