# CSVFormFiller

CSVFormFiller is a small Selenium-based CLI for filling **Microsoft Forms** from a CSV file using an explicit YAML mapping between CSV columns and form questions.

It grew out of a one-off automation script and was refactored so the form URL, question text, data columns, pacing, and submission behavior are configuration rather than hard-coded Python.

> **Current scope:** Microsoft Forms. The adapter structure is intentionally separated so other providers can be added later.

## Why use a mapping file?

Matching answers globally by text is fragile. Two questions can contain the same option, such as `A few times a month`. CSVFormFiller scopes each answer to its specific question container, which prevents that class of error.

## Supported controls in v0.1

- single-choice radio questions
- checkbox / multi-select questions
- single-line text questions and textareas
- matrix / Likert questions (mapped by visible row order)
- multi-page Microsoft Forms
- dry-run mode by default
- screenshots and saved page HTML/text on failure
- resumable submission log
- configurable page and row pacing

## Installation

```bash
python -m venv .venv
```

Windows Command Prompt:

```cmd
.venv\Scripts\activate.bat
pip install -e .
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -e .
```

Chrome and a compatible Selenium-managed ChromeDriver are required. Modern Selenium versions normally manage the driver automatically.

## 1. Inspect a form

```bash
csvformfiller inspect --url "https://forms.cloud.microsoft/..." --output form_schema.json
```

The browser opens and the CLI prints the visible questions. For multi-page forms, navigate manually in the browser and press Enter in the terminal to capture each page. Type `q` when finished.

This is an inspection helper, not an automatic mapping generator yet.

## 2. Create a CSV

Example:

```csv
id,age,purchase_frequency,country
DEMO-001,22-25,A few times a month,United Kingdom
DEMO-002,26-34,About once a month,India
```

## 3. Create a mapping

```yaml
fields:
  - column: age
    question: "What is your age group?"
    type: radio

  - column: purchase_frequency
    question: "How often do you make purchases online?"
    type: radio

  - column: country
    question: "Which country do you currently reside in?"
    type: text
```

Use a question phrase that uniquely identifies that question on its page.

### Checkbox example

```yaml
fields:
  - column: products
    question: "Which types of products do you usually buy or browse online?"
    type: checkbox
    separator: ";"
```

CSV cell:

```text
Clothing;Electronics;Books or stationery
```

### Matrix / Likert example

```yaml
matrices:
  - name: digital_habits
    question: "Digital Habits"
    columns:
      - habit_1
      - habit_2
      - habit_3
      - habit_4
    options:
      - Strongly Disagree
      - Disagree
      - Neutral
      - Agree
      - Strongly Agree
```

Matrix rows are associated with the listed CSV columns by visible row order. The configured `options` list defines the visible left-to-right answer order.

## 4. Validate before opening a browser

```bash
csvformfiller validate --data responses.csv --mapping mapping.yaml
```

## 5. Dry run

Dry-run is the default. It fills one row and stops on the final page without submitting:

```bash
csvformfiller run \
  --url "https://forms.cloud.microsoft/..." \
  --data responses.csv \
  --mapping mapping.yaml \
  --id-column id \
  --limit 1
```

On Windows Command Prompt, use `^` instead of `\` for line continuation, or put the command on one line.

## 6. Submit

Actual submission requires both flags:

```bash
csvformfiller run \
  --url "https://forms.cloud.microsoft/..." \
  --data responses.csv \
  --mapping mapping.yaml \
  --id-column id \
  --submit \
  --confirm-authorized
```

`--confirm-authorized` is an explicit acknowledgement that you own the form or have permission to automate submissions to it.

## Pacing

Defaults are intentionally short system pacing rather than human-behavior simulation:

```text
--page-delay-min 0.5
--page-delay-max 1.5
--row-delay-min 1
--row-delay-max 3
```

Override them from the CLI without editing source code:

```bash
csvformfiller run ... --page-delay-min 2 --page-delay-max 5
```

## Resume behavior

Successful submissions are recorded in `submission_log.csv`. If `--id-column` is supplied, successfully submitted IDs are skipped on later runs.

If no ID column is supplied, IDs are generated as `ROW-0001`, `ROW-0002`, and so on.

## Failure diagnostics

When a row fails, CSVFormFiller stops rather than continuing blindly. It writes:

- `screenshots/failed_<ID>.png`
- `last_page.txt`
- `last_page.html`
- a `FAILED` entry in `submission_log.csv` when submission mode is enabled

Fix the mapping or form issue, then rerun. Previously successful IDs are skipped.

## Project layout

```text
csvformfiller/
  adapters/
    base.py
    microsoft_forms.py
  cli.py
  data.py
  inspect.py
  logging_utils.py
  mapping.py
  models.py
  runner.py
examples/
tests/
```

## Roadmap

- automatic mapping suggestions from CSV headers and question text
- richer question inspection metadata
- support for dropdowns and date inputs
- Google Forms adapter
- generic HTML adapter where practical
- headless mode for validated workflows

## Responsible use

Use this only with forms you own or where you have permission to automate submissions. Do not use it to spam public forms, evade response controls, or misrepresent automated responses as human submissions.

## Development

```bash
pip install -e ".[dev]"
pytest
```
