"""Deterministic tutoring guidance layered under the conversational AI provider."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PrerequisiteTopic:
    name: str
    reason: str


@dataclass(frozen=True)
class TutorTurn:
    guidance: str
    next_state: str | None
    fixed_response: str | None = None


PREREQUISITE_PATHS: dict[str, tuple[PrerequisiteTopic, ...]] = {
    "probability": (
        PrerequisiteTopic("Basic arithmetic", "operations and numerical reasoning are used in every probability calculation"),
        PrerequisiteTopic("Fractions, decimals and percentages", "probability is commonly represented as a fraction, decimal and percentage"),
        PrerequisiteTopic("Sets and Venn diagrams", "events are represented as sets and combined with union, intersection and complement"),
        PrerequisiteTopic("Counting principles", "sample spaces and favourable outcomes often require systematic counting"),
        PrerequisiteTopic("Permutation and combination", "ordered and unordered outcomes are counted with nPr and nCr"),
        PrerequisiteTopic("Basic probability", "experiments, outcomes, sample spaces and events form the foundation"),
        PrerequisiteTopic("Addition and multiplication theorems", "combined and sequential events require these rules"),
        PrerequisiteTopic("Conditional probability and independence", "dependent events require conditional reasoning"),
        PrerequisiteTopic("Bayes theorem", "reverse conditional probability uses prior and posterior reasoning"),
        PrerequisiteTopic("Random variables and distributions", "NDA and higher study questions use probability distributions"),
    ),
}


def _normalise(value: str) -> str:
    return " ".join(value.casefold().split())


def _is_negative(value: str) -> bool:
    return bool(re.search(r"\b(no|not|don't|dont|didn't|didnt|haven't|havent|cannot|can't|नहीं|नही|समझ नहीं|नहीं किया|नहीं समझा|नहीं आता|નથી|ખબર નથી|ન આવડતું)\b", _normalise(value)))


def _is_affirmative(value: str) -> bool:
    return bool(re.search(r"\b(yes|yeah|yep|sure|tried|read|solved|attempted|know|understand|understood|हाँ|हां|कोशिश|समझा|समझी|हां|હા|આવડે|સમજાય છે)\b", _normalise(value)))


def _is_binary_answer(value: str) -> bool:
    return _normalise(value).strip(".!?") in {"yes", "no", "yeah", "yep", "હા", "ના"}


def _topic_for(value: str) -> str | None:
    normalised = _normalise(value)
    for topic in PREREQUISITE_PATHS:
        if topic in normalised:
            return topic
    return None


def _study_topic(user_message: str) -> str:
    known_topic = _topic_for(user_message)
    if known_topic:
        return known_topic.replace("_", " ").title()
    cleaned = re.sub(
        r"^(?:please\s+)?(?:i\s+(?:don't|dont|do not|can't|cannot)\s+(?:understand|get|solve)\s+|i\s+need\s+help\s+with\s+|help\s+me\s+(?:with|understand|solve)\s+|explain\s+|teach\s+me\s+|solve\s+|what\s+is\s+|how\s+does\s+|how\s+to\s+)",
        "",
        user_message.strip(),
        flags=re.IGNORECASE,
    )
    return cleaned.strip(" .?!")[:100] or "this topic"


def _is_study_request(value: str) -> bool:
    normalised = _normalise(value)
    if normalised in {"hi", "hello", "hey", "thanks", "thank you", "હાય", "નમસ્તે"}:
        return False
    return bool(re.search(
        r"\b(explain|teach|solve|understand|help|topic|chapter|formula|question|what|why|how|"
        r"math|maths|mathematics|algebra|geometry|trigonometry|calculus|arithmetic|probability|"
        r"physics|chemistry|biology|science|english|grammar|vocabulary|history|geography|"
        r"समझ|समझाओ|पढ़ाओ|हल|सवाल|प्रश्न|क्या|क्यों|कैसे|गणित|अंकगणित|बीजगणित|"
        r"ज्यामिति|त्रिकोणमिति|भौतिकी|रसायन|जीवविज्ञान|समज|શીખ|ઉકેલ|પ્રશ્ન|કેમ|શું)\b",
        normalised,
    )) or len(normalised.split()) >= 2


def _is_greeting(value: str) -> bool:
    return _normalise(value).strip(" .!?") in {
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
        "how are you", "thanks", "thank you", "ok", "okay", "bye",
        "नमस्ते", "नमस्कार", "धन्यवाद", "हाँ", "हां",
    }


def _is_nda_related(value: str) -> bool:
    normalised = _normalise(value)
    if _is_greeting(normalised):
        return True
    return bool(re.search(
        r"\b(nda|exam|maths?|mathematics|algebra|geometry|trigonometry|calculus|arithmetic|"
        r"probability|probabilities|equations?|fractions?|percentages?|ratios?|sets?|"
        r"statistics|permutations?|combinations?|vectors?|geometry|logarithms?|"
        r"derivatives?|integrals?|limits?|functions?|variables?|expressions?|theorem|formula|"
        r"physics|chemistry|biology|science|english|grammar|vocabulary|gravity|motion|force|energy|"
        r"photosynthesis|cell|ecosystem|electricity|magnetism|"
        r"history|geography|polity|constitution|economics|current affairs|general knowledge|"
        r"reasoning|defence|military|ssb|syllabus|yes|no|yeah|yep|tried|read|solved|attempted|"
        r"understand|understood|derivative|integral|गणित|अंकगणित|बीजगणित|ज्यामिति|"
        r"अवकलन|समाकलन|चर|सूत्र|"
        r"त्रिकोणमिति|भौतिकी|रसायन|जीवविज्ञान|विज्ञान|अंग्रेज़ी|अंग्रेजी|व्याकरण|"
        r"इतिहास|भूगोल|संविधान|अर्थशास्त्र|सामान्य ज्ञान|समसामयिकी|परीक्षा|पढ़ाई|"
        r"हाँ|हां|नहीं|नही|कोशिश|हल किया|समझा|समझी|उत्तर|जवाब|क्योंकि)\b",
        normalised,
    )) or (
        bool(re.search(r"\d", normalised))
        and bool(re.search(r"[=+\-*/×÷]|answer|उत्तर|जवाब|solve|हल", normalised))
    )


def _is_hindi(value: str) -> bool:
    return bool(re.search(r"[\u0900-\u097f]", value))


def _requested_response_language(history: list[dict[str, str]]) -> str | None:
    for item in reversed(history[-12:]):
        if item.get("role") != "user":
            continue
        content = item.get("content", "")
        match = re.search(
            r"\b(?:in|into)\s+(?:simple\s+)?(hindi|english)\b"
            r"|\b(hindi|english)\s+(?:mein|me|please)\b"
            r"|\b(?:reply|respond|answer|explain|teach|speak|write|give|provide|use)"
            r"\b.{0,40}\b(?:in\s+)?(hindi|english)\b",
            content,
            re.IGNORECASE,
        )
        if match:
            language = next(group for group in match.groups() if group)
            return "Hindi" if language.casefold() == "hindi" else "English"
    return None


def _attempt_status(value: str) -> str | None:
    normalised = _normalise(value).strip(" .!?")
    if _is_negative(normalised):
        return "no"
    if _is_affirmative(normalised):
        return "yes"
    return None


def orchestrate_tutor_turn(user_message: str, history: list[dict[str, str]], current_state: str | None) -> TutorTurn:
    """Guide a topic discussion through an attempt check and student teach-back."""
    requested_language = _requested_response_language(
        [*history, {"role": "user", "content": user_message}]
    )
    explicit_language_explanation = requested_language is not None and bool(
        re.search(
            r"\b(explain(?:ation)?|teach me|walk me through|solve)\b",
            user_message,
            re.IGNORECASE,
        )
        or re.search(r"(?:समझाओ|समझाइए|समझा दो|हल करो)", user_message)
    )
    is_hindi = requested_language == "Hindi" or (
        requested_language is None and _is_hindi(user_message)
    )
    common_guidance = (
        "Follow the student's most recent explicit language request, even when it differs from the language they used to write. "
        "If they have not explicitly requested a language, reply in the same language and writing system as their latest message. "
        "Be supportive and specific; never shame the student. "
        "Use the current topic and recent conversation context, and do not change topics. "
        "If a fact is uncertain, say so instead of guessing."
    )
    if requested_language == "Hindi":
        language_guidance = (
            "The student requested Hindi. Reply in natural, clear Hindi using Devanagari, "
            "even if the request or conversation is written in English. Because this is NDA "
            "preparation, add one brief, encouraging reminder to keep practising English."
        )
    elif requested_language == "English":
        language_guidance = (
            "The student requested English. Reply in clear English, even if the request or "
            "conversation is written in another language."
        )
    elif is_hindi:
        language_guidance = (
            "The student wrote in Hindi. Reply in natural, clear Hindi using Devanagari. "
            "Because this is NDA preparation, add one brief, encouraging reminder to keep practising English."
        )
    else:
        language_guidance = ""

    if not _is_nda_related(user_message) and not (
        explicit_language_explanation and current_state is not None
    ):
        response = (
            "**अपना ध्यान मत भटकने दें।** आइए NDA की पढ़ाई पर वापस आएँ—किस विषय पर काम करना चाहेंगे? साथ में English का अभ्यास भी जारी रखें।"
            if is_hindi else
            "**Do not lose your focus.** Let’s get back to NDA preparation—which subject would you like to work on?"
        )
        return TutorTurn(
            guidance=common_guidance + " The request is outside NDA preparation. Redirect politely to NDA study.",
            next_state=current_state or "ai_response",
            fixed_response=response,
        )

    if explicit_language_explanation:
        return TutorTurn(
            guidance=common_guidance
            + language_guidance
            + " The student explicitly asked for an explanation in the requested language. "
            "Give the explanation now using the current topic and verified context; do not first ask whether they have tried it.",
            next_state="ai_response",
        )

    if current_state == "awaiting_attempt_status":
        status = _attempt_status(user_message)
        if status == "yes":
            return TutorTurn(
                guidance=common_guidance
                + language_guidance
                + " The student says they have tried, read, or understood some of the topic. Do not explain the topic yet. Ask them to explain in their own words what they understood and what is still unclear.",
                next_state="awaiting_student_explanation",
            )
        if status == "no":
            return TutorTurn(
                guidance=common_guidance
                + language_guidance
                + " The student says they have not understood or tried the topic yet. Do not explain the whole topic yet. Ask which exact part, word, step, or idea they did not understand.",
                next_state="awaiting_confusion_detail",
            )
        return TutorTurn(
            guidance=common_guidance
            + language_guidance
            + " The student has not answered whether they have tried reading, solving, or understanding the topic. Ask them to answer that question briefly before proceeding.",
            next_state="awaiting_attempt_status",
        )

    if current_state == "awaiting_student_explanation":
        if _is_negative(user_message):
            return TutorTurn(
                guidance=common_guidance
                + language_guidance
                + " The student cannot explain the topic yet. Ask which exact part, word, step, or idea remains unclear; do not criticize them.",
                next_state="awaiting_confusion_detail",
            )
        return TutorTurn(
            guidance=common_guidance
            + language_guidance
            + " Evaluate the student's explanation against the topic and verified context. Identify what is correct, gently correct each incorrect or incomplete idea, and explain why. Do not simply agree. Then ask one focused question about what remains unclear.",
            next_state="awaiting_confusion_detail",
        )

    if current_state == "awaiting_confusion_detail":
        return TutorTurn(
            guidance=common_guidance
            + language_guidance
            + " First address the exact part the student says they did not understand. Explain it in small, simple steps with a relevant example when useful. Then invite them to explain in their own words what they now understand and what is still unclear.",
            next_state="awaiting_student_explanation",
        )

    if _is_greeting(user_message):
        return TutorTurn(
            guidance=common_guidance
            + language_guidance
            + " Answer the student's latest non-study message naturally and briefly.",
            next_state="ai_response",
        )

    math_request = bool(re.search(
        r"\b(math|maths|mathematics|algebra|geometry|trigonometry|calculus|arithmetic|"
        r"probability|equations?|fractions?|percentages?|ratios?|derivative|integral|limit|"
        r"function|variable|expression|theorem|formula|गणित|अंकगणित|बीजगणित|ज्यामिति|"
        r"त्रिकोणमिति|समीकरण|भिन्न|प्रतिशत|अनुपात|अवकलन|समाकलन|सूत्र)\b",
        user_message.casefold(),
    ))
    return TutorTurn(
        guidance=common_guidance
        + language_guidance
        + (
            " The student asked a mathematics question or topic. Do not solve it or reveal the answer yet. First ask whether they have tried to solve the question or understand the topic. For a topic, encourage them to study it and explain it in their own words; if they are stuck, offer to explain the unclear part."
            if math_request else
            " The student has asked about an NDA study topic. Before teaching or solving it, ask whether they have tried to read, understand, or solve it by themselves. Do not reveal the explanation or answer yet. Keep the question friendly and concise."
        ),
        next_state="awaiting_attempt_status",
    )


def build_tutor_guidance(user_message: str, history: list[dict[str, str]]) -> str:
    """Compatibility wrapper for callers that only need the guidance text."""
    return orchestrate_tutor_turn(user_message, history, None).guidance
