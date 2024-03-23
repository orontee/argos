from typing import Protocol

from gi.repository import GLib

from argos.model import Model


class ProgressNotifierProtocol(Protocol):
    def __call__(self, step: int) -> None: ...


class DirectoryCompletionProgressNotifier:
    def __init__(self, model: Model, *, directory_uri: str, step_count: int):
        self._model = model
        self._signal_name = "directory-completion-progress"
        self._directory_uri = directory_uri
        self._step_count = step_count

    def __call__(self, step: int) -> None:
        GLib.idle_add(
            self._model.emit,
            self._signal_name,
            self._directory_uri,
            step,
            self._step_count,
        )
