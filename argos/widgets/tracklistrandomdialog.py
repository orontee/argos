import gettext
import logging
from pathlib import Path
from typing import Optional

from gi.repository import GLib, GObject, Gtk

from argos.model import Model
from argos.utils import ms_to_text
from argos.widgets.utils import default_image_pixbuf, scale_album_image

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

ALBUM_IMAGE_SIZE = 50


@Gtk.Template(resource_path="/io/github/orontee/Argos/ui/tracklist_random_dialog.ui")
class TracklistRandomDialog(Gtk.Dialog):
    """Dialog used to prepare a random tracklist.

    Currently only random album choice is supported."""

    __gtype_name__ = "TracklistRandomDialog"

    default_album_image = default_image_pixbuf(
        "media-optical",
        target_width=ALBUM_IMAGE_SIZE,
    )

    album_image: Gtk.Image = Gtk.Template.Child()
    album_name_label: Gtk.Label = Gtk.Template.Child()
    album_artist_name_label: Gtk.Label = Gtk.Template.Child()
    album_length_label: Gtk.Label = Gtk.Template.Child()
    album_num_tracks_label: Gtk.Label = Gtk.Template.Child()
    play_button: Gtk.CheckButton = Gtk.Template.Child()

    album_uri = GObject.Property(type=str, default="")
    play = GObject.Property(type=bool, default=False)

    def __init__(self, application: Gtk.Application, *, play: bool = False):
        super().__init__(application=application, transient_for=application.window)

        self._model: Model = application.props.model
        self._disable_tooltips = application.props.disable_tooltips

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
        album_uri = self._model.choose_random_album()
        LOGGER.debug(f"Album with URI {album_uri!r} chosen")

        self.props.album_uri = album_uri if album_uri is not None else ""
        album = self._model.get_album(self.props.album_uri)

        album_name: Optional[str] = None
        artist_name: Optional[str] = None
        album_length: Optional[int] = None
        num_tracks: Optional[int] = None
        image_path: Optional[str] = None
        if album is not None:
            album_name = album.name
            artist_name = album.artist_name
            album_length = album.length
            num_tracks = album.num_tracks
            image_path = album.image_path

        self._update_album_name_label(album_name)
        self._update_album_artist_name_label(artist_name)
        self._update_album_length_label(album_length)
        self._update_album_num_tracks_label(num_tracks)
        self._update_album_image(image_path)

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

    def _update_album_length_label(self, album_length: Optional[int]) -> None:
        if album_length is not None:
            pretty_length = ms_to_text(album_length)
        else:
            pretty_length = ""

        self.album_length_label.set_text(pretty_length)
        self.album_length_label.show_now()

    def _update_album_num_tracks_label(self, album_num_tracks: Optional[int]) -> None:
        if album_num_tracks is not None and album_num_tracks != -1:
            self.album_num_tracks_label.set_text(str(album_num_tracks))
        else:
            self.album_num_tracks_label.set_text("")
        self.album_num_tracks_label.show_now()

    def _update_album_image(self, album_image_path: Optional[str]) -> None:
        image_path = Path(album_image_path) if album_image_path else None
        scaled_pixbuf = None
        if image_path:
            rectangle = self.album_image.get_allocation()
            target_width = min(rectangle.width, rectangle.height)
            scaled_pixbuf = scale_album_image(image_path, target_width=target_width)

        if scaled_pixbuf:
            self.album_image.set_from_pixbuf(scaled_pixbuf)
        else:
            self.album_image.set_from_pixbuf(self.default_album_image)

        self.album_image.show_now()

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
