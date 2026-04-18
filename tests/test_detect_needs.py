import pytest

from data import detect_needs


@pytest.mark.parametrize(
    "text,expected",
    [
        ("피로가 너무 심해요", ["피로 개선"]),
        ("눈이 뻑뻑해요", ["눈 건강"]),
        ("관절이 안 좋아요", ["관절 건강"]),
        ("변비가 있어요", ["장 건강"]),
        ("면역력이 약해진 것 같아요", ["면역력 증진"]),
        ("피로하고 면역력 걱정돼요", ["피로 개선", "면역력 증진"]),
    ],
)
def test_detect_needs_positive(text, expected):
    assert detect_needs(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("피로는 괜찮은데 눈이 침침해요", ["눈 건강"]),
        ("관절은 멀쩡하고 면역력이 걱정돼요", ["면역력 증진"]),
        ("눈은 괜찮고 피로만 심해요", ["피로 개선"]),
        ("아무 증상도 없어요", []),
    ],
)
def test_detect_needs_negation(text, expected):
    assert detect_needs(text) == expected


def test_detect_needs_empty():
    assert detect_needs("") == []
    assert detect_needs("안녕하세요") == []
