
import json
from pathlib import Path

from app.brain.understanding import UnderstandingEngine


BASE_DIR = Path(__file__).resolve().parent

COURSE_FILE = (
    BASE_DIR
    / "course_workspaces"
    / "Python"
    / "course.json"
)


print("\nLoading Python course...")

with open(COURSE_FILE, "r", encoding="utf-8") as file:
    course_data = json.load(file)

experiments = course_data.get("experiments", [])

print("Experiments loaded:", len(experiments))


print("\nInitializing Understanding Engine...")

engine = UnderstandingEngine()

engine.prepare_experiments(experiments)


# --------------------------------------------------
# TEST QUESTIONS
# --------------------------------------------------

test_questions = [

    "Show me all the practicals",

    "I want to learn how Python repeats instructions",

    "Teach me for loops and while loops",

    "Can you explain loops in Python?",

    "I want to study strings",

    "Teach me recursion",

    "Let's start experiment five",

    "I want to learn Python functions",

    "Continue from where we stopped",

    "Switch to another experiment",

    "Hello LabBuddy",

    "Stop listening for now",

    "What is a dictionary in Python?"

]


# --------------------------------------------------
# RUN TESTS
# --------------------------------------------------

print("\n" + "=" * 65)
print("LABBUDDY UNDERSTANDING TEST")
print("=" * 65)


for question in test_questions:

    result = engine.process(question)

    print("\nQuestion:", question)

    print("Intent:", result["intent"])

    print(
        "Similarity:",
        round(result["confidence"], 4)
    )

    experiment = result.get("experiment")

    if experiment:

        print(
            "Selected experiment:",
            experiment.get("number"),
            "-",
            experiment.get("title")
        )

    if result.get("candidates"):

        print("Other experiment matches:")

        for candidate in result["candidates"]:

            item = candidate["experiment"]

            print(
                " ",
                item.get("number"),
                item.get("title"),
                "| Score:",
                round(candidate["similarity"], 4)
            )

    else:

        print("No experiment candidates found.")

    print("-" * 65)


print("\nTotal database examples:", engine.vector_store.count())

print("Test completed.")
print("\nTesting confirmed learning...")

result = engine.learn_example(
    text="I want to practice repeating statements in Python",
    intent="start_experiment",
    experiment_id=4
)

print(result)

print(
    "Updated database count:",
    engine.vector_store.count()
)
