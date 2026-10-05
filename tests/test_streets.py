"""Pruebas del cruce entre el registro municipal y los nombres de OSM.

Los dos Catálogos nombran las mismas calles distinto: el registro dice
`LOPEZ DE HARO D. DIEGO` y OSM `On Diego Lopez Haroko kale nagisia`. Aquí se
comprueba que el cruce por palabras funciona y, sobre todo, que **no** da
falsos positivos con seguridad.
"""

from __future__ import annotations

from app.data import name_overlap_score, name_tokens, normalize_name
from app.schemas import Section, StreetRecord


def test_normalize_removes_accents_and_punctuation() -> None:
    """`LOPEZ DE HARO D. DIEGO GV` y `López de Haro` deben compararse."""
    assert normalize_name("Lopez de Haro D. Diego GV") == "LOPEZ DE HARO D DIEGO GV"
    assert normalize_name("Gran Vía de Don Diego López de Haro") == (
        "GRAN VIA DE DON DIEGO LOPEZ DE HARO"
    )
    assert normalize_name(None) == ""


def test_tokens_ignore_short_words() -> None:
    """`DE`, `D.` o `GV` no sirven para emparejar calles."""
    assert name_tokens("LOPEZ DE HARO D. DIEGO GV") == {"LOPEZ", "HARO", "DIEGO"}


def test_overlap_matches_reversed_and_bilingual_names() -> None:
    """El caso real: orden invertido y Languages distintos."""
    assert name_overlap_score("Heros kalea", "HEROS") == 1
    assert (
        name_overlap_score(
            "On Diego Lopez Haroko kale nagisia",
            "LOPEZ DE HARO D. DIEGO",
        )
        >= 2
    )


def test_overlap_is_zero_for_unrelated_streets() -> None:
    """Dos calles sin palabras comunes no deben emparejarse nunca."""
    assert name_overlap_score("Iparraguirre kalea", "SANTUTXU ERRERIA") == 0
    assert name_overlap_score("Heros kalea", None) == 0


def make_section(sid: str, name: str, intensity: float = 500.0) -> Section:
    """Sección sintética con nombre de OSM."""
    return Section(
        id=sid,
        name=name,
        display_name=name,
        intensity=intensity,
        length_m=300.0,
        geometry=[[-2.940, 43.268], [-2.938, 43.268]],
        centroid=(-2.940, 43.268),
    )


def test_registry_links_gran_via_to_its_section() -> None:
    """`LOPEZ DE HARO D. DIEGO` debe llegar a la sección de la Gran Vía."""
    from app.config import Settings
    from app.data import build_street_index

    registry = [
        StreetRecord(code="4040", name="LOPEZ DE HARO D. DIEGO", street_type="GRAN VIA"),
        StreetRecord(code="9999", name="SANTUTXU ERRERIA", street_type="CALLE"),
    ]
    sections = [make_section("328", "On Diego Lopez Haroko kale nagisia", 1592.0)]

    index = build_street_index(registry, sections, Settings())

    gran_via = next(s for s in index["streets"] if s.code == "4040")
    assert gran_via.section_id == "328"
    assert gran_via.match == "exact"

    # La calle sin tráfico queda declarada como no simulable, no inventada.
    otra = next(s for s in index["streets"] if s.code == "9999")
    assert otra.section_id is None
    assert otra.match == "none"


def test_single_word_overlap_is_only_probable() -> None:
    """Una sola palabra compartida no basta para decir que es la misma calle."""
    from app.config import Settings
    from app.data import build_street_index

    registry = [StreetRecord(code="1", name="VIA HEROS")]
    sections = [make_section("339", "Heros kalea")]

    index = build_street_index(registry, sections, Settings())

    rec = index["streets"][0]
    assert rec.section_id == "339"
    assert rec.match == "probable", "con una sola palabra el enlace no es seguro"


def test_empty_registry_produces_empty_index() -> None:
    """Sin CSV, el índice no rompe nada."""
    from app.config import Settings
    from app.data import build_street_index

    index = build_street_index([], [make_section("1", "Heros kalea")], Settings())

    assert index["total"] == 0
    assert index["with_traffic_data"] == 0
    assert index["streets"] == []
