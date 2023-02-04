import gettext
import logging
from pathlib import Path
from typing import List, Optional

from gi.repository import Gio, GLib, GObject, Gtk

from argos.model import (
    RANDOM_TRACKS_CHOICE_STRATEGY,
    AlbumModel,
    Model,
    RandomTracksChoiceState,
)
from argos.utils import ms_to_text
from argos.widgets.utils import default_image_pixbuf, scale_album_image

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

CHOICE_IMAGE_SIZE = 50


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/tracklist_random_dialog.ui")
class TracklistRandomDialog(Gtk.Dialog):
    """Dialog used to prepare a random tracklist.

    Currently only random album choice is supported."""

    __gtype_name__ = "TracklistRandomDialog"

    default_choice_image = default_image_pixbuf(
        "media-optical",
        target_width=CHOICE_IMAGE_SIZE,
    )

    choice_image: Gtk.Image = Gtk.Template.Child()
    album_name_label: Gtk.Label = Gtk.Template.Child()
    album_artist_name_label: Gtk.Label = Gtk.Template.Child()
    choice_length_label: Gtk.Label = Gtk.Template.Child()
    choice_num_tracks_label: Gtk.Label = Gtk.Template.Child()
    choice_disc_no_title_label: Gtk.Label = Gtk.Template.Child()
    choice_disc_no_label: Gtk.Label = Gtk.Template.Child()

    play_button: Gtk.CheckButton = Gtk.Template.Child()

    info_bar: Gtk.InfoBar = Gtk.Template.Child()

    album_uri = GObject.Property(type=str, default="")
    play = GObject.Property(type=bool, default=False)

    def __init__(self, application: Gtk.Application, *, play: bool = False):
        super().__init__(application=application, transient_for=application.window)

        self._model: Model = application.props.model
        self._settings: Gio.Settings = application.props.settings
        self._disable_tooltips = application.props.disable_tooltips

        self.track_uris: List[str] = []

        for widget in (self.play_button,):
            if self._disable_tooltips:
                widget.props.has_tooltip = False

        self.add_buttons(
            Gtk.STOCK_OK,
            Gtk.ResponseType.OK,
        )

        validate_button = self.get_widget_for_response(Gtk.ResponseType.OK)
        validate_button.set_can_default(True)
        validate_button.grab_default()

        self.play_button.set_active(play)

        title_bar = Gtk.HeaderBar(title=_("Random tracklist"), show_close_button=True)
        self.set_titlebar(title_bar)

        self.show_all()

        self._choose_random_album()

    def _choose_random_album(self) -> None:
        strategy = self._settings.get_string("random-tracks-choice-strategy")
        result = self._model.choose_random_album(strategy=strategy)

        album: Optional[AlbumModel] = None
        if result.state == RandomTracksChoiceState.FOUND:
            self.props.album_uri = result.source_album_uri
            album = self._model.get_album(self.props.album_uri)
            self.track_uris = result.track_uris
        else:
            self.props.album_uri = ""
            self.track_uris = []

        album_name: Optional[str] = None
        artist_name: Optional[str] = None
        choice_length: Optional[int] = None
        num_tracks: Optional[int] = None
        disc_no: Optional[int] = None
        image_path: Optional[str] = None
        if album is not None:
            album_name = album.name
            artist_name = album.artist_name
            choice_length = sum(
                [t.length for t in album.tracks if t.uri in self.track_uris]
            )
            num_tracks = len(self.track_uris)
            disc_no = result.source_album_disc_no
            image_path = album.image_path

        self._update_album_name_label(album_name)
        self._update_album_artist_name_label(artist_name)
        self._update_choice_length_label(choice_length)
        self._update_choice_num_tracks_label(num_tracks)
        self._update_choice_disc_no_labels(
            disc_no, show=strategy == "random_disc_tracks"
        )
        self._update_choice_image(image_path)
        self._update_info_bar(result.state)

    def _update_album_name_label(self, album_name: Optional[str]) -> None:
        if album_name:
            safe_album_name = GLib.markup_escape_text(album_name)
            album_name_text = (
                f"""<span size="xx-large"><b>{safe_album_name}</b></span>"""
            )
            self.album_name_label.set_markup(album_name_text)

            if not self._disable_tooltips:
                self.album_name_label.set_has_tooltip(True)
                self.album_name_label.set_tooltip_text(album_name)
        else:
            self.album_name_label.set_markup("")
            self.album_name_label.set_has_tooltip(False)

        self.album_name_label.show_now()

    def _update_album_artist_name_label(self, artist_name: Optional[str]) -> None:
        if artist_name:
            safe_artist_name = GLib.markup_escape_text(artist_name)
            artist_name_text = f"""<span size="x-large">{safe_artist_name}</span>"""
            self.album_artist_name_label.set_markup(artist_name_text)
            if not self._disable_tooltips:
                self.album_artist_name_label.set_has_tooltip(True)
                self.album_artist_name_label.set_tooltip_text(artist_name)
        else:
            self.album_artist_name_label.set_markup("")
            self.album_artist_name_label.set_has_tooltip(False)

        self.album_artist_name_label.show_now()

    def _update_choice_length_label(self, choice_length: Optional[int]) -> None:
        if choice_length is not None:
            pretty_length = ms_to_text(choice_length)
        else:
            pretty_length = ""

        self.choice_length_label.set_text(pretty_length)
        self.choice_length_label.show_now()

    def _update_choice_num_tracks_label(self, choice_num_tracks: Optional[int]) -> None:
        if choice_num_tracks is not None and choice_num_tracks != -1:
            self.choice_num_tracks_label.set_text(str(choice_num_tracks))
        else:
            self.choice_num_tracks_label.set_text("")
        self.choice_num_tracks_label.show_now()

    def _update_choice_disc_no_labels(
        self,
        choice_disc_no: Optional[int],
        *,
        show: bool,
    ) -> None:
        if show:
            self.choice_disc_no_title_label.show_now()
            self.choice_disc_no_label.set_text(
                str(choice_disc_no) if choice_disc_no is not None else ""
            )
            self.choice_disc_no_label.show_now()
        else:
            self.choice_disc_no_title_label.hide()
            self.choice_num_tracks_label.set_text("")
            self.choice_disc_no_label.hide()

    def _update_choice_image(self, choice_image_path: Optional[str]) -> None:
        image_path = Path(choice_image_path) if choice_image_path else None
        scaled_pixbuf = None
        if image_path:
            rectangle = self.choice_image.get_allocation()
            target_width = min(rectangle.width, rectangle.height)
            scaled_pixbuf = scale_album_image(image_path, target_width=target_width)

        if scaled_pixbuf:
            self.choice_image.set_from_pixbuf(scaled_pixbuf)
        else:
            self.choice_image.set_from_pixbuf(self.default_choice_image)

        self.choice_image.show_now()

    def _update_info_bar(self, state: RandomTracksChoiceState) -> None:
        info_bar_content_area = self.info_bar.get_content_area()
        for child in info_bar_content_area.get_children():
            child.destroy()

        if state == RandomTracksChoiceState.FOUND:
            self.info_bar.set_revealed(False)
        elif state == RandomTracksChoiceState.EMPTY_LIBRARY:
            self.info_bar.props.message_type = Gtk.MessageType.INFO
            label = Gtk.Label(_("Browse the library first, it's currently empty!"))
            info_bar_content_area.add(label)
            self.info_bar.set_revealed(True)
        else:
            self.info_bar.props.message_type = Gtk.MessageType.ERROR
            label = Gtk.Label(_("Oups, failed to select random tracks…"))
            info_bar_content_area.add(label)
            self.info_bar.set_revealed(True)

        self.info_bar.show_all()

    @Gtk.Template.Callback()
    def on_skip_button_clicked(
        self,
        _1: Gtk.Button,
    ) -> None:
        self._choose_random_album()

    @Gtk.Template.Callback()
    def on_TracklistRandomDialog_response(
        self,
        _1: Gtk.Dialog,
        response_id: int,
    ) -> None:
        self.props.play = self.play_button.props.active
