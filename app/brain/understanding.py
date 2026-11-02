

import re

from pathlib import Path



from sentence_transformers import SentenceTransformer



from app.database.vector_store import VectorStore





MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"





# --------------------------------------------------

# PRE-SAVED UNDERSTANDING EXAMPLES

# --------------------------------------------------



INTENT_EXAMPLES = {
    "show_syllabus": [
        "Show me all experiments", "Show me the experiment list",
        "Show all practicals", "Display my experiment list",
        "What experiments are in my course?", "Open the syllabus",
        "Show me the syllabus", "What can I learn?",
        "List all experiments", "Show the experiment window",
        "I want to see all practicals",
    ],
    "start_experiment": [
        "Let's start an experiment", "I want to start an experiment",
        "Start teaching me", "Let's begin today's practical",
        "I want to learn a new topic", "Teach me Python loops",
        "I want to study strings", "Let's learn functions",
    ],
    "continue_lesson": [
        "Continue the lesson", "Go ahead", "Continue teaching me",
        "What is the next step?", "Explain the next part",
        "Continue from where we stopped",
    ],
    "change_experiment": [
        "Switch to another experiment", "I want to change the practical",
        "Let's study something else", "Choose a different experiment",
    ],
    "question": [
        "I have a doubt", "I want to ask a question",
        "What is a Python function?", "Explain this programming concept",
        "Why does this code work?", "How does Python work?",
        "Why am I getting this error?", "Can you explain this?",
    ],
    "greeting": ["Hello LabBuddy", "Hi there", "Good morning", "Hey assistant"],
    "stop_or_idle": ["Stop listening", "Go to idle mode", "Take a break", "Stop for now"],
}

PRESET_EXAMPLES = [
    (phrase, intent, None)
    for intent, phrases in INTENT_EXAMPLES.items()
    for phrase in phrases
] + [
    ("I want to learn how Python repeats instructions", "start_experiment", 4),
    ("Teach me how to use for and while loops", "start_experiment", 4),
    ("I want to understand functions and recursion", "start_experiment", 7),
    ("Teach me Python functions", "start_experiment", 7),
    ("Can you explain loops in Python?", "question", None),
    ("How do loops work in Python?", "question", None),
    ("What are for loops and while loops?", "question", None),
]


class UnderstandingEngine:



    def __init__(self, model_name=MODEL_NAME):



        print("Initializing LabBuddy Understanding Engine...")



        self.encoder = SentenceTransformer(model_name)



        self.vector_store = VectorStore(self.encoder)



        self.experiments = []

        self.selected_experiment = None



        self._load_presets()

        self.loaded_experiment_ids = set()



        print("Understanding Engine ready.")



    # --------------------------------------------------

    # PRESET DATA

    # --------------------------------------------------



    def _load_presets(self):



        print("Loading preset understanding examples...")



        for text, intent, experiment_id in PRESET_EXAMPLES:



            self.vector_store.add_example(

                text=text,

                intent=intent,

                experiment_id=experiment_id,

                source="preset"

            )



        print(

            f"Understanding database contains "

            f"{self.vector_store.count()} examples."

        )



    # --------------------------------------------------

    # EXPERIMENT DATA

    # --------------------------------------------------



    def prepare_experiments(self, experiments):



        self.experiments = experiments or []



        for experiment in self.experiments:



            number = experiment.get("number")



            if number in self.loaded_experiment_ids:

                continue



            title = experiment.get("title", "")

            description = experiment.get("description", "")

            concepts = experiment.get("concepts", [])



            if isinstance(concepts, list):

                concepts_text = ", ".join(

                    str(item) for item in concepts

                )

            else:

                concepts_text = str(concepts)



            experiment_texts = [

                title,

                f"Teach me {title}",

                f"I want to learn {title}",

                f"Let's study {title}",

            ]



            if isinstance(concepts, list):

                for concept in concepts:

                    concept = str(concept).strip()



                    if concept:

                        experiment_texts.extend([

                            concept,

                            f"Teach me {concept}",

                            f"I want to learn {concept}",

                        ])



            elif concepts_text:

                experiment_texts.extend([

                    concepts_text,

                    f"Teach me {concepts_text}",

                ])



            if description:

                experiment_texts.append(description)



            for text in experiment_texts:



                text = text.strip()



                if not text:

                    continue



                self.vector_store.add_example(

                    text=text,

                    intent="start_experiment",

                    experiment_id=number,

                    source="experiment"

                )



            self.loaded_experiment_ids.add(number)



        print(

            f"Prepared {len(self.loaded_experiment_ids)} experiments."

        )



    # --------------------------------------------------

    # EXPLICIT EXPERIMENT NUMBER DETECTION

    # --------------------------------------------------



    def _extract_experiment_number(self, text):



        text = text.lower()



        number_words = {

            "one": 1,

            "first": 1,

            "two": 2,

            "second": 2,

            "three": 3,

            "third": 3,

            "four": 4,

            "fourth": 4,

            "five": 5,

            "fifth": 5,

            "six": 6,

            "sixth": 6,

            "seven": 7,

            "seventh": 7,

            "eight": 8,

            "eighth": 8,

            "nine": 9,

            "ninth": 9,

            "ten": 10,

            "tenth": 10,

            "eleven": 11,

            "eleventh": 11,

            "twelve": 12,

            "twelfth": 12

        }



        if "last experiment" in text:

            if self.experiments:

                return self.experiments[-1].get("number")



        patterns = [

            r"(?:experiment|exp|practical)\s*(?:number\s*)?(\d+)",

            r"(?:experiment|exp|practical)\s*(?:number\s*)?([a-z]+)"

        ]



        for pattern in patterns:



            match = re.search(pattern, text)



            if match:



                value = match.group(1)



                if value.isdigit():

                    return int(value)



                return number_words.get(value)



        return None



    # --------------------------------------------------

    # EXPERIMENT SEARCH

    # --------------------------------------------------



    def _search_experiments(self, text, top_k=3):



        results = self.vector_store.search(

            text,

            top_k=10

        )



        experiment_results = {}



        for result in results:



            experiment_id = result.get("experiment_id")



            if experiment_id is None:

                continue



            similarity = result["similarity"]



            if (

                experiment_id not in experiment_results

                or similarity > experiment_results[experiment_id]["similarity"]

            ):



                experiment_results[experiment_id] = {

                    "experiment_id": experiment_id,

                    "similarity": similarity,

                    "matched_text": result["text"]

                }



        ranked = sorted(

            experiment_results.values(),

            key=lambda item: item["similarity"],

            reverse=True

        )



        final_results = []



        for result in ranked[:top_k]:



            experiment = next(

                (

                    item for item in self.experiments

                    if item.get("number") == result["experiment_id"]

                ),

                None

            )



            if experiment:



                final_results.append({

                    "experiment": experiment,

                    "similarity": result["similarity"],

                    "matched_text": result["matched_text"]

                })



        return final_results



    # --------------------------------------------------

    # INTENT MATCHING

    # --------------------------------------------------



    def _classify_intent(self, text, top_k=5):



        # Search a larger set, then exclude experiment records.

        results = self.vector_store.search(

            text,

            top_k=50

        )



        intent_results = [

            result for result in results

            if result["source"] != "experiment"

        ]



        intent_results = intent_results[:top_k]



        if not intent_results:

            return {

                "intent": "unclear",

                "confidence": 0.0,

                "matches": []

            }



        intent_scores = {}



        for result in intent_results:



            intent = result["intent"]

            similarity = result["similarity"]



            intent_scores.setdefault(intent, []).append(similarity)



        ranked_intents = []



        weights = [1.0, 0.7, 0.5]



        for intent, scores in intent_scores.items():



            scores.sort(reverse=True)

            selected_scores = scores[:3]



            weighted_score = sum(

                score * weights[index]

                for index, score in enumerate(selected_scores)

            )



            total_weight = sum(weights[:len(selected_scores)])



            average_score = weighted_score / total_weight



            ranked_intents.append((intent, average_score))



        ranked_intents.sort(

            key=lambda item: item[1],

            reverse=True

        )



        best_intent, best_score = ranked_intents[0]



        second_score = (

            ranked_intents[1][1]

            if len(ranked_intents) > 1

            else 0.0

        )



        if best_score < 0.35:

            best_intent = "unclear"



        elif (

            best_score < 0.48

            and best_score - second_score < 0.04

        ):

            best_intent = "unclear"



        return {

            "intent": best_intent,

            "confidence": best_score,

            "matches": intent_results

        }



    # --------------------------------------------------

    # MAIN UNDERSTANDING FUNCTION

    # --------------------------------------------------



    def process(

        self,

        text,

        experiments=None,

        selected_experiment=None

    ):



        text = text.strip()



        if not text:



            return {

                "intent": "unclear",

                "confidence": 0.0,

                "experiment": None,

                "candidates": [],

                "matches": []

            }



        if experiments is not None:

            self.prepare_experiments(experiments)



        if selected_experiment is not None:

            self.selected_experiment = selected_experiment



        # First check explicit experiment numbers

        experiment_number = self._extract_experiment_number(text)



        if experiment_number is not None:



            experiment = next(

                (

                    item for item in self.experiments

                    if item.get("number") == experiment_number

                ),

                None

            )



            if experiment:



                return {

                    "intent": "start_experiment",

                    "confidence": 1.0,

                    "experiment": experiment,

                    "candidates": [],

                    "matches": [],

                    "source": "explicit_number"

                }



        # Semantic intent detection

        intent_result = self._classify_intent(text)



        intent = intent_result["intent"]



        candidates = self._search_experiments(

            text,

            top_k=3

        )



        selected = (

            candidates[0]["experiment"]

            if candidates

            else None

        )



        # Don't start an experiment based only on a weak match

        if intent == "start_experiment":



            if (

                not candidates

                or candidates[0]["similarity"] < 0.35

            ):



                intent = "unclear"

                selected = None



        # Continue requires an existing selected experiment

        if (

            intent == "continue_lesson"

            and self.selected_experiment is None

        ):



            intent = "unclear"



        return {

            "intent": intent,

            "confidence": intent_result["confidence"],

            "experiment": selected if intent == "start_experiment" else None,

            "candidates": candidates,

            "matches": intent_result["matches"],

            "source": "semantic_search"

        }



    # --------------------------------------------------

    # LEARN A CONFIRMED EXAMPLE

    # --------------------------------------------------



    def learn_example(

        self,

        text,

        intent,

        experiment_id=None

    ):



        return self.vector_store.add_example(

            text=text,

            intent=intent,

            experiment_id=experiment_id,

            source="confirmed"

        )





# Compatibility with the old controller import.

ConversationManager = UnderstandingEngine
