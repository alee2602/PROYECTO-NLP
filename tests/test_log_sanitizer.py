from src.security.log_sanitizer import hash_for_log, sanitize_for_log


def test_redacts_email():
    text = "Contacto: monica.salvatierra@uvg.edu.gt para dudas."
    sanitized = sanitize_for_log(text)
    assert "monica.salvatierra@uvg.edu.gt" not in sanitized
    assert "[EMAIL_REDACTADO]" in sanitized


def test_redacts_phone_number():
    text = "Llamar al +502 5555-1234 si hay dudas."
    sanitized = sanitize_for_log(text)
    assert "5555-1234" not in sanitized
    assert "[TELEFONO_REDACTADO]" in sanitized


def test_leaves_ordinary_text_untouched():
    text = "FAISS indexa vectores densos de alta dimensión."
    assert sanitize_for_log(text) == text


def test_hash_for_log_is_deterministic_and_does_not_contain_source_text():
    text = "Afirmación con datos sensibles del usuario."
    digest1 = hash_for_log(text)
    digest2 = hash_for_log(text)
    assert digest1 == digest2
    assert text not in digest1
    assert len(digest1) == 12


def test_hash_for_log_differs_for_different_text():
    assert hash_for_log("afirmación A") != hash_for_log("afirmación B")
