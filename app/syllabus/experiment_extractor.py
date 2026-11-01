import re


EXPERIMENT_PATTERN = re.compile(
    r"^\s*(?:experiment|exp\.?)\s*"
    r"(\d+)\s*[:.\-–—)]*\s*(.*?)\s*$",
    re.IGNORECASE
)


def extract_experiments(syllabus_text: str) -> list:
    """
    Identify experiments from extracted syllabus text.
    Returns a list of experiment dictionaries.
    """

    lines = syllabus_text.splitlines()

    experiments = []
    current_experiment = None

    for line in lines:
        line = line.strip()

        if not line:
            continue

        match = EXPERIMENT_PATTERN.match(line)

        if match:
            if current_experiment:
                experiments.append(current_experiment)

            number = match.group(1)
            title = match.group(2).strip()

            current_experiment = {
                "number": int(number),
                "title": title or f"Experiment {number}",
                "description": "",
                "concepts": ""
            }

        elif current_experiment:

            if line.lower().startswith("task:"):
                current_experiment["description"] = (
                    line.split(":", 1)[1].strip()
                )

            elif line.lower().startswith("key concepts:"):
                current_experiment["concepts"] = (
                    line.split(":", 1)[1].strip()
                )

            else:
                # Preserve any additional experiment details.
                current_experiment["description"] += (
                    " " + line
                )

    if current_experiment:
        experiments.append(current_experiment)

    # Remove duplicate experiment numbers.
    unique = {}
    for experiment in experiments:
        unique[experiment["number"]] = experiment

    return list(unique.values())