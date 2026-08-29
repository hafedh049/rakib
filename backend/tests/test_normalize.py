"""Normalisation is pure and load-bearing, so it is tested hard.

Everything downstream — the classifier, the department router, search —
reads the output of this module.
"""

import pytest

from app.intelligence.text.normalize import (
    collapse_repeats,
    extract_features,
    is_arabizi_token,
    mask_entities,
    normalize,
    normalize_arabic,
    strip_signatures,
    transliterate_arabizi,
)


# ------------------------------------------------------------------------ masking
def test_urls_are_masked():
    assert "<URL>" in mask_entities("voir https://uib.com.tn/releve pour le detail")


def test_emails_are_masked():
    assert "<EMAIL>" in mask_entities("ecrivez a service@operateur.tn svp")


@pytest.mark.parametrize(
    "raw",
    [
        "appelez moi au 20 145 879",
        "mon numero est +216 20 145 879",
        "contact 71845200",
    ],
)
def test_tunisian_phone_numbers_are_masked(raw):
    assert "<PHONE>" in mask_entities(raw)


def test_masking_removes_the_identifier_itself():
    """The point is that a model cannot memorise individual claimants."""
    masked = mask_entities("ma ligne 20145879 et mon mail fatma@example.tn")
    assert "20145879" not in masked
    assert "fatma@example.tn" not in masked


# --------------------------------------------------------------------- signatures
def test_dash_signature_is_stripped():
    text = "Ma agios est fausse.\n--\nKarim Jelassi\nDirecteur"
    assert "Directeur" not in strip_signatures(text)


@pytest.mark.parametrize(
    "signature",
    ["Envoye de mon iPhone", "Envoyé de mon Samsung", "Sent from my iPhone"],
)
def test_mobile_signatures_are_stripped(signature):
    assert signature.lower() not in strip_signatures(
        f"Aucun remboursement depuis hier.\n{signature}"
    ).lower()


def test_quoted_history_is_stripped():
    text = "Toujours rien.\n> Le 12 janvier, le support a ecrit :\n> Bonjour, ..."
    cleaned = strip_signatures(text)
    assert "Toujours rien." in cleaned
    assert "le support a ecrit" not in cleaned


def test_closing_formula_is_stripped():
    text = "Merci de regulariser ma agios.\nCordialement\nSami Ouertani"
    assert "Sami Ouertani" not in strip_signatures(text)


# ------------------------------------------------------------------------- arabic
def test_diacritics_are_removed():
    assert normalize_arabic("مُشْكِلَة") == "مشكله"


@pytest.mark.parametrize("variant", ["أحمد", "إحمد", "آحمد"])
def test_alef_variants_collapse(variant):
    assert normalize_arabic(variant).startswith("ا")


def test_teh_marbuta_and_alef_maqsura_are_folded():
    assert normalize_arabic("شكاية") == "شكايه"
    assert normalize_arabic("علي") == "علي"
    assert normalize_arabic("مستوى") == "مستوي"


def test_tatweel_is_removed():
    assert normalize_arabic("مشـــكل") == "مشكل"


def test_two_spellings_of_one_word_converge():
    """The whole point: spelling variants must land on the same token."""
    assert normalize_arabic("شكاية") == normalize_arabic("شكايه")


# ------------------------------------------------------------------------ arabizi
@pytest.mark.parametrize(
    "token,expected",
    [
        ("3andi", True), ("7aja", True), ("9olt", True), ("mochkla", False),
        ("2026", False), ("rec", False), ("m3a", True),
    ],
)
def test_arabizi_token_detection(token, expected):
    assert is_arabizi_token(token) is expected


def test_reference_numbers_are_not_mistaken_for_arabizi():
    """`REC-2026-00412` must not be transliterated into Arabic."""
    assert transliterate_arabizi("rec 2026 00412 agios") == ""


def test_arabizi_is_transliterated_to_arabic_script():
    result = transliterate_arabizi("3andi mochkla f7al")
    assert "ع" in result  # 3 -> ع
    assert "ح" in result  # 7 -> ح


def test_normalize_keeps_both_scripts():
    normalized = normalize(body="3andi mochkla fel internet, 7atta hne walou")
    assert normalized.transliterated
    assert normalized.text in normalized.indexable
    assert normalized.transliterated in normalized.indexable


# ------------------------------------------------------------------------ repeats
@pytest.mark.parametrize(
    "raw,expected",
    [("inacceptable!!!!!", "inacceptable!!"), ("aaaah", "aah"), ("normal", "normal")],
)
def test_collapse_repeats(raw, expected):
    assert collapse_repeats(raw)[0] == expected


def test_repetition_is_counted_even_though_it_is_removed():
    """It is an anger signal, so it survives as a feature."""
    _, runs = collapse_repeats("quoi!!!! encore????")
    assert runs == 2


# ----------------------------------------------------------------------- features
def test_uppercase_ratio_is_measured_before_lowercasing():
    features = extract_features("AUCUN REMBOURSEMENT DEPUIS TROIS JOURS")
    assert features.uppercase_ratio == 1.0


def test_features_count_punctuation():
    features = extract_features("C'est inacceptable !!! Vous faites quoi ??")
    assert features.exclamation_count == 3
    assert features.question_count == 2


def test_arabic_ratio_detects_script():
    assert extract_features("ما فماش شبكة").arabic_ratio > 0.9
    assert extract_features("aucun remboursement").latin_ratio == 1.0


def test_arabizi_ratio():
    features = extract_features("3andi 7aja mochkla")
    assert features.arabizi_token_ratio == pytest.approx(2 / 3)


def test_empty_text_does_not_divide_by_zero():
    features = extract_features("")
    assert features.uppercase_ratio == 0.0
    assert features.digit_ratio == 0.0
    assert features.arabizi_token_ratio == 0.0


# ----------------------------------------------------------------------- pipeline
def test_subject_is_repeated_to_double_its_weight():
    normalized = normalize("agios", "probleme")
    assert normalized.text.count("agios") == 2


def test_full_pipeline_is_lowercased_and_whitespace_collapsed():
    normalized = normalize("AGIOS   ANORMALE", "Trop\n\n  cher")
    assert "  " not in normalized.text
    assert normalized.text == normalized.text.lower()


def test_pipeline_is_idempotent_on_already_clean_text():
    once = normalize(body="mes agios sont trop eleves ce mois ci").text
    twice = normalize(body=once).text
    assert once == twice


# ------------------------------------------------------------- accent folding
def test_indexable_folds_french_accents():
    """Every lexicon term is written unaccented, so the match text must be too.

    Without this, "chèque" never matched "cheque": a complaint typed in correct
    French failed to categorise while the same sentence typed carelessly worked.
    """
    normalized = normalize("Chèque rejeté à tort", "Échéance prélevée deux fois")
    assert "cheque" in normalized.indexable
    assert "rejete" in normalized.indexable
    assert "echeance" in normalized.indexable
    assert "prelevee" in normalized.indexable


def test_display_text_keeps_its_accents():
    """Only the match text is folded — people still read `text`."""
    normalized = normalize("Chèque rejeté", "Mainlevée non délivrée")
    assert "è" in normalized.text or "é" in normalized.text


def test_accent_folding_leaves_arabic_alone():
    """Arabic marks were already handled deliberately; do not re-process them."""
    normalized = normalize("الموزع", "الموزع خذا الفلوس و ما خرجش")
    assert "الموزع" in normalized.indexable


def test_an_accented_complaint_classifies_like_its_bare_twin():
    from app.intelligence.lexicon.classifier import classify

    accented = classify(normalize("Chèque rejeté à tort", "défaut de provision").indexable)
    bare = classify(normalize("Cheque rejete a tort", "defaut de provision").indexable)
    assert accented.category == bare.category is not None
