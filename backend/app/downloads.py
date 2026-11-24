"""Background downloads of the models the app needs, with a state the UI can show."""

import threading
from collections.abc import Callable


class Download:
    """One model: whether it is on disk, and a background download that fetches it.

    `is_ready` says whether the model is complete on disk, `fetch` downloads it (blocking), and
    `measure` returns the bytes on disk so far, partial files included. `total` is the expected
    size in bytes when it is known; `fetch` may set it once it finds out. `size`, when given,
    is asked for the expected size instead, for a model that can change (a chosen voice).
    """

    def __init__(
        self,
        id: str,
        label: str,
        is_ready: Callable[[], bool],
        fetch: Callable[[], None],
        measure: Callable[[], int],
        total: int | None = None,
        size: Callable[[], int | None] | None = None,
    ):
        self.id = id
        self.label = label
        self._total = total
        self._size = size
        self.error: str | None = None
        self._is_ready = is_ready
        self._fetch = fetch
        self._measure = measure
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def total(self) -> int | None:
        return self._size() if self._size else self._total

    @total.setter
    def total(self, value: int | None) -> None:
        self._total = value

    def _downloading(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _run(self) -> None:
        try:
            self._fetch()
        except Exception as e:  # reported through status(); the UI offers to try again
            self.error = str(e) or type(e).__name__

    def start(self) -> None:
        """Begin downloading unless the model is there or a download is already running."""
        with self._lock:
            # While a download runs the files are not checked: a check may wait for it to end.
            if self._downloading() or self._is_ready():
                return
            self.error = None
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def wait(self) -> None:
        """Block until the model is on disk, downloading it if needed. Raises if that fails."""
        self.start()
        thread = self._thread
        if thread:
            thread.join()
        if not self._is_ready():
            raise RuntimeError(self.error or f"The {self.label.lower()} model could not be downloaded.")

    def status(self) -> dict:
        downloading = self._downloading()
        ready = not downloading and self._is_ready()
        if downloading:
            state = "downloading"
        elif ready:
            state = "ready"
        elif self.error:
            state = "error"
        else:
            state = "missing"
        downloaded = self._measure()
        return {
            "id": self.id,
            "label": self.label,
            "state": state,
            # A finished model counts as fully downloaded even if its size was an estimate.
            "downloaded": self.total if ready and self.total else downloaded,
            "total": self.total,
            "error": None if ready else self.error,
        }
