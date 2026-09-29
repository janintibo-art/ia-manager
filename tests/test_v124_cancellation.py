import sys
import time

import pytest

from src.backend import process_control


def test_cancellable_process_is_stopped_quickly():
    started = time.monotonic()

    def should_stop():
        return time.monotonic() - started > 0.25

    with pytest.raises(InterruptedError, match="arrêtée"):
        process_control.run(
            [sys.executable, "-c", "import time; time.sleep(20)"],
            timeout=30,
            should_stop=should_stop,
        )
    assert time.monotonic() - started < 3


def test_process_timeout_kills_the_process():
    started = time.monotonic()
    with pytest.raises(TimeoutError, match="délai"):
        process_control.run(
            [sys.executable, "-c", "import time; time.sleep(20)"],
            timeout=0.25,
        )
    assert time.monotonic() - started < 3
