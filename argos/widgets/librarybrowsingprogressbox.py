import logging

from gi.repository import GObject, Gtk

from argos.model import Model

LOGGER = logging.getLogger(__name__)


@Gtk.Template(
    resource_path="/io/github/orontee/Argos/ui/library_browsing_progress_box.ui"
)
class LibraryBrowsingProgressBox(Gtk.Box):
    __gtype_name__ = "LibraryBrowsingProgressBox"

    progress_spinner: Gtk.Spinner = Gtk.Template.Child()
    progress_bar: Gtk.ProgressBar = Gtk.Template.Child()

    uri = GObject.Property(type=str)

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._model = application.model
        self.props.uri = self._model.library.props.default_uri

        self._model.connect(
            "directory-completion_progress", self.on_directory_completion_progress
        )
        self._model.connect("directory-completed", self.on_directory_completed)

        self.show_all()

    def track_directory_completion(self, uri: str) -> None:
        self.props.uri = uri
        self.progress_bar.set_fraction(0)
        self.progress_bar.set_show_text(False)

    def on_directory_completion_progress(
        self, _1: Model, uri: str, step: int, step_count: int
    ) -> None:
        if uri != self.props.uri:
            return

        if step_count < step or step_count <= 0 or step <= 0:
            LOGGER.warning(f"Incoherent steps values {step} / {step_count}")
            return

        self.progress_bar.set_fraction(step / step_count)
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text(f"{step} / {step_count}")

    def on_directory_completed(self, _1: Model, uri: str) -> None:
        if uri != self.props.uri:
            return

        self.progress_bar.set_fraction(1)
        self.progress_bar.set_show_text(False)
