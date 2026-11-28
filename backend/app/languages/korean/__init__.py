"""Korean, as the app teaches it."""

from ..base import Language, supertonic
from .openers import OPENERS
from .patterns import PATTERNS

# Native Korean numbers said on their own ("고양이가 셋 있어요"), with their figures. The forms
# before a counter ("세 마리") and the Sino-Korean ones ("일", "이", "사") are left out: each is
# also a common word of its own ("이" is "this", "일" is "work", "네" is "yes").
NUMBERS = dict(
    zip(
        "하나 둘 셋 넷 다섯 여섯 일곱 여덟 아홉 열 스물 서른 마흔 쉰 예순 일흔 여든 아흔".split(),
        [*map(str, range(1, 11)), "20", "30", "40", "50", "60", "70", "80", "90"],
        strict=True,
    )
)


def spell_out(word: str) -> str:
    """Korean is not written with short forms that stand for two words, so a word is heard as written."""
    return word


KOREAN = Language(
    code="ko",
    name="Korean",
    native="한국어",
    locale="ko-KR",
    whisper_model="small",
    subtitles=("ko", "ko-KR"),
    # Korean does not abbreviate words with a full stop; these come up in loanwords and names.
    abbreviations=frozenset({"dr.", "mr.", "ms.", "vs.", "etc."}),
    spell_out=spell_out,
    numbers=NUMBERS,
    # Kokoro and Piper have no Korean voice. These are Supertonic 3's ten voices; one download
    # of its model serves all of them, and each adds a small style file.
    voices=(
        supertonic("F1", "F1 · female", 292_046),
        supertonic("F2", "F2 · female", 292_423),
        supertonic("F3", "F3 · female", 290_794),
        supertonic("F4", "F4 · female", 291_808),
        supertonic("F5", "F5 · female", 291_479),
        supertonic("M1", "M1 · male", 291_748),
        supertonic("M2", "M2 · male", 292_055),
        supertonic("M3", "M3 · male", 290_198),
        supertonic("M4", "M4 · male", 291_522),
        supertonic("M5", "M5 · male", 291_469),
    ),
    sample="안녕하세요! 만나서 반가워요. 이번 주는 어떻게 지냈어요?",
    openers=OPENERS,
    patterns=PATTERNS,
    pattern_slots='"V-", "A-", "N", "-아/어요", "-(으)ㄹ", or "…"',
    pattern_example='from "더 일찍 출발할 걸 그랬어요" with "출발할 걸 그랬어요" marked: "V-(으)ㄹ 걸 그랬어요"',
    instruction_example="더 일찍 출발하지 않은 것을 후회한다고 말해 보세요.",
    address=(
        "Use the polite 해요체 by default. Use 반말 only where the situation is between close friends, "
        "family, or classmates of the same age, and the formal 합쇼체 only where staff or officials would; keep to it."
    ),
    opener_address="Use 해요체, or 반말 between close friends, as the situation calls for.",
    text_address="Speak to the learner in 해요체.",
)
