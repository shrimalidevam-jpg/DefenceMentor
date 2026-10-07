"""Curated daily English vocabulary and SSB preparation guidance."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class VocabularyQuestion:
    id: str
    word: str
    options: tuple[str, str, str, str]
    correct_option: str
    meaning: str
    example: str


VOCABULARY_BANK = (
    VocabularyQuestion("abundant", "abundant", ("plentiful", "fragile", "brief", "ordinary"), "A", "existing in large quantities; plentiful", "The region has abundant water during the monsoon."),
    VocabularyQuestion("candid", "candid", ("careless", "frank and honest", "uncertain", "silent"), "B", "truthful and direct; frank", "The candidate gave a candid answer about the challenge."),
    VocabularyQuestion("diligent", "diligent", ("careless", "hesitant", "hard-working and careful", "fortunate"), "C", "showing steady, careful effort", "A diligent student reviews mistakes after every test."),
    VocabularyQuestion("fortitude", "fortitude", ("patience", "curiosity", "speed", "courage in difficulty"), "D", "courage and strength of mind during adversity", "The team showed fortitude after losing its first match."),
    VocabularyQuestion("obsolete", "obsolete", ("outdated and no longer useful", "widely accepted", "easy to repair", "carefully planned"), "A", "no longer used because something newer exists", "The obsolete equipment was replaced with a safer model."),
    VocabularyQuestion("prudent", "prudent", ("generous", "wise and careful", "very quick", "easily upset"), "B", "acting with good judgment and care", "It is prudent to check the route before a long journey."),
    VocabularyQuestion("resilient", "resilient", ("easily distracted", "very strict", "able to recover after difficulty", "unwilling to change"), "C", "able to recover, adapt, or continue after difficulty", "A resilient learner uses setbacks to improve."),
    VocabularyQuestion("scarce", "scarce", ("very common", "highly valuable", "easy to find", "limited in amount"), "D", "not available in large amounts; limited", "Clean water can be scarce in a drought."),
    VocabularyQuestion("vigilant", "vigilant", ("watchful and alert", "calm and sleepy", "kind and helpful", "slow to decide"), "A", "carefully watching for possible danger or problems", "The sentry remained vigilant throughout the night."),
    VocabularyQuestion("benevolent", "benevolent", ("ambitious", "kind and charitable", "strictly neutral", "easily frightened"), "B", "well-meaning and kindly", "The benevolent officer arranged help for the villagers."),
    VocabularyQuestion("coherent", "coherent", ("short-lived", "incorrect", "clear and logically connected", "unusually brave"), "C", "clear, logical, and easy to understand", "She presented a coherent plan for the group task."),
    VocabularyQuestion("concise", "concise", ("overly detailed", "unclear", "informal", "brief but complete"), "D", "giving information clearly in few words", "Keep the situation reaction response concise and relevant."),
    VocabularyQuestion("credible", "credible", ("believable and trustworthy", "difficult to read", "very expensive", "partly complete"), "A", "able to be believed or trusted", "Use credible facts when discussing a current issue."),
    VocabularyQuestion("deteriorate", "deteriorate", ("improve gradually", "become worse", "move quickly", "become familiar"), "B", "to become progressively worse", "Without maintenance, the road may deteriorate."),
    VocabularyQuestion("endeavour", "endeavour", ("a lucky event", "a final decision", "a serious effort", "a public speech"), "C", "a determined effort to achieve something", "Completing the expedition was a demanding endeavour."),
    VocabularyQuestion("impartial", "impartial", ("unprepared", "very experienced", "overconfident", "fair and not taking sides"), "D", "treating all sides fairly without favour", "An impartial leader listens to each team member."),
    VocabularyQuestion("meticulous", "meticulous", ("very careful about details", "quick to forgive", "ready to compete", "often confused"), "A", "showing great attention to detail", "The team made a meticulous check of its equipment."),
    VocabularyQuestion("persevere", "persevere", ("change direction suddenly", "continue despite difficulty", "avoid responsibility", "give advice freely"), "B", "to keep doing something despite obstacles", "She continued to persevere with daily practice."),
    VocabularyQuestion("proficient", "proficient", ("new to a subject", "unwilling to act", "skilled and competent", "careful with money"), "C", "competent or skilled in doing something", "He is proficient in map-reading and navigation."),
    VocabularyQuestion("scrutinize", "scrutinize", ("ignore deliberately", "explain simply", "change completely", "examine very carefully"), "D", "to inspect or examine closely", "Scrutinize each option before choosing an answer."),
    VocabularyQuestion("tenacious", "tenacious", ("persistent and determined", "easily persuaded", "quiet and reserved", "careless with details"), "A", "holding firmly to a goal; persistent", "The tenacious team kept working until the task was complete."),
    VocabularyQuestion("versatile", "versatile", ("difficult to approach", "able to adapt to many tasks", "always cautious", "unusually formal"), "B", "able to do many different things effectively", "A versatile cadet can contribute in varied team roles."),
    VocabularyQuestion("adversity", "adversity", ("a strong advantage", "a formal meeting", "a difficult or challenging situation", "a clear instruction"), "C", "a state of difficulty or misfortune", "The group stayed united in adversity."),
    VocabularyQuestion("commend", "commend", ("question repeatedly", "delay a decision", "give a warning", "praise formally"), "D", "to praise or express approval", "The instructor commended the team for its cooperation."),
    VocabularyQuestion("initiative", "initiative", ("the ability to act without being told", "fear of failure", "a short break", "a written complaint"), "A", "the ability to assess and act independently", "Taking initiative, she organized the group materials."),
    VocabularyQuestion("rational", "rational", ("based mainly on emotion", "based on reason and logic", "hard to measure", "easy to replace"), "B", "based on clear reasoning rather than emotion", "A rational decision considers evidence and consequences."),
    VocabularyQuestion("substantial", "substantial", ("temporary", "unimportant", "large or considerable", "not clearly stated"), "C", "large in amount, value, or importance", "The project made substantial progress this month."),
    VocabularyQuestion("tactful", "tactful", ("extremely impatient", "unusually cautious", "difficult to convince", "careful not to offend others"), "D", "sensitive to other people's feelings; diplomatic", "A tactful response can resolve disagreement respectfully."),
    VocabularyQuestion("unanimous", "unanimous", ("agreed by everyone", "decided in secret", "based on a guess", "opposed by most people"), "A", "fully in agreement", "The group reached a unanimous decision after discussion."),
    VocabularyQuestion("zeal", "zeal", ("doubt about a plan", "great energy and enthusiasm", "a strict rule", "a quiet warning"), "B", "strong enthusiasm or eagerness", "She approached her preparation with zeal and discipline."),
)


SSB_TIPS = (
    ("Be genuine", "Use your own experiences and speak honestly. Memorized scripts often sound inconsistent across interview, psychology tests, and group tasks.", "Personal interview"),
    ("Practice clear narration", "For picture perception, notice the setting, people, and likely situation; build a plausible story and present it clearly within the time limit.", "PPDT"),
    ("Listen before contributing", "In group discussion, understand the topic first, make relevant points, and build on others' ideas instead of trying to dominate.", "Group discussion"),
    ("Show practical teamwork", "During group tasks, communicate calmly, include teammates, and focus on a workable shared solution rather than personal credit.", "GTO tasks"),
    ("Keep a current-affairs notebook", "Summarize one national, one international, and one defence-related item each day; note the issue, key facts, and your balanced view.", "Interview preparation"),
    ("Reflect on real examples", "Prepare truthful examples from study, sports, responsibilities, and setbacks that show how you acted and what you learned.", "Personal interview"),
    ("Build a steady routine", "Use regular sleep, exercise, reading, and speaking practice. Sustainable preparation is more useful than a last-minute burst.", "Daily preparation"),
    ("Explain your reasoning", "When asked for an opinion, state your view, support it with a reason or example, and acknowledge a reasonable alternative.", "Communication"),
    ("Take responsibility", "If asked about a mistake, describe your part honestly, the correction you made, and what you would do differently next time.", "Personal interview"),
    ("Stay composed under time limits", "Practice short timed tasks so you can organize thoughts quickly without rushing into unsupported answers.", "Psychology tests"),
    ("Know your application", "Review the information you submitted and be ready to discuss your education, interests, responsibilities, and stated achievements accurately.", "Personal interview"),
    ("Use simple, direct language", "Organize answers in a clear order. Strong communication is about relevant ideas and listening, not complicated vocabulary.", "Communication"),
    ("Participate constructively", "In a group task, offer a safe, practical suggestion, explain it briefly, and remain open to improving it with the group.", "GTO tasks"),
    ("Treat feedback as practice data", "After a mock interview or group exercise, write down one strength and one specific behavior to improve in the next attempt.", "Self-review"),
)


def today_vocabulary(today: date) -> tuple[VocabularyQuestion, ...]:
    start = (today.toordinal() * 5) % len(VOCABULARY_BANK)
    return tuple(VOCABULARY_BANK[(start + offset) % len(VOCABULARY_BANK)] for offset in range(5))


def today_ssb_tip(today: date) -> tuple[str, str, str]:
    return SSB_TIPS[today.toordinal() % len(SSB_TIPS)]
