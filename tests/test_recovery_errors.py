import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from recovery import describe_error


def raises_bad_descriptor():
    raise OSError(9, "Bad file descriptor")


def test_the_message_names_where_the_error_was_raised():
    try:
        raises_bad_descriptor()
    except OSError as error:
        text = describe_error(error)
    assert "Bad file descriptor" in text
    assert "OSError" in text
    assert "test_recovery_errors.py" in text
    assert "raises_bad_descriptor" in text


def test_an_error_that_never_ran_has_only_its_message():
    assert describe_error(RuntimeError("no frames")) == "no frames"
