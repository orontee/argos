from enum import IntEnum
import gettext
import logging
from pathlib import Path
from typing import Optional, List

from gi.repository import GLib, Gtk, GObject, Pango

from ..message import MessageType
from ..model import Model, Track
from ..utils import elide_maybe, ms_to_text
from .utils import default_album_image_pixbuf, scale_album_image

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

ALBUM_IMAGE_SIZE = 80


class TrackStoreColumns(IntEnum):
    TRACK_NO = 0
    DISC_NO = 1
    NAME = 2
    LENGTH = 3
    TOOLTIP = 4
    URI = 5


def _compare_track_rows(
    model: Gtk.ListStore,
    a: Gtk.TreeIter,
    b: Gtk.TreeIter,
    user_data: None,
) -> int:
    a_disc_no = model.get_value(a, TrackStoreColumns.DISC_NO)
    a_track_no = model.get_value(a, TrackStoreColumns.TRACK_NO)
    b_disc_no = model.get_value(b, TrackStoreColumns.DISC_NO)
    b_track_no = model.get_value(b, TrackStoreColumns.TRACK_NO)

    if a_disc_no < b_disc_no:
        return -1
    elif a_disc_no == b_disc_no:
        if a_track_no < b_track_no:
            return -1
        elif a_track_no == b_track_no:
            return 0

    return 1


@Gtk.Template(resource_path="/app/argos/Argos/ui/album_box.ui")
class AlbumBox(Gtk.Box):
    __gtype_name__ = "AlbumBox"

    back_button: Gtk.Button = Gtk.Template.Child()
    add_button: Gtk.Button = Gtk.Template.Child()
    play_button: Gtk.Button = Gtk.Template.Child()

    album_image: Gtk.Image = Gtk.Template.Child()

    album_name_label: Gtk.Label = Gtk.Template.Child()
    artist_name_label: Gtk.Label = Gtk.Template.Child()
    publication_label: Gtk.Label = Gtk.Template.Child()
    length_label: Gtk.Label = Gtk.Template.Child()

    track_view: Gtk.TreeView = Gtk.Template.Child()

    uri = GObject.Property(type=str, default="")

    def __init__(self, application: Gtk.Application):
        super().__init__()

        self._app = application
        self._model = application.model
        self._disable_tooltips = application._disable_tooltips

        track_store = Gtk.ListStore(int, int, str, str, str, str)
        track_store.set_default_sort_func(_compare_track_rows, None)
        track_store.set_sort_column_id(
            Gtk.TREE_SORTABLE_DEFAULT_SORT_COLUMN_ID,
            Gtk.SortType.ASCENDING,
        )
        self.track_view.set_model(track_store)
        if not self._disable_tooltips:
            self.track_view.set_tooltip_column(TrackStoreColumns.TOOLTIP)

        column = Gtk.TreeViewColumn(_("Track"))
        track_no_renderer = Gtk.CellRendererText(xpad=5, ypad=5)
        attrs = Pango.AttrList()
        attrs.insert(Pango.attr_weight_new(Pango.Weight.LIGHT))
        track_no_renderer.props.attributes = attrs

        track_name_renderer = Gtk.CellRendererText(
            xpad=5,
            ypad=5,
            ellipsize=Pango.EllipsizeMode.END,
        )
        track_length_renderer = Gtk.CellRendererText(xalign=1.0, xpad=5, ypad=5)
        column.pack_start(track_no_renderer, True)
        column.pack_start(track_name_renderer, True)
        column.pack_start(track_length_renderer, True)
        column.add_attribute(track_no_renderer, "text", TrackStoreColumns.TRACK_NO)
        column.add_attribute(track_name_renderer, "text", TrackStoreColumns.NAME)
        column.add_attribute(track_length_renderer, "text", TrackStoreColumns.LENGTH)
        self.track_view.append_column(column)

        if self._disable_tooltips:
            for widget in (
                self.back_button,
                self.add_button,
                self.play_button,
                self.track_view,
            ):
                widget.props.has_tooltip = False

        self._default_album_image = default_album_image_pixbuf(
            target_width=ALBUM_IMAGE_SIZE,
        )

        self._model.connect("album-completed", self.update_children)

    def update_children(self, model: Model, uri: str) -> None:
        if self.uri != uri:
            return

        found = [album for album in model.albums if album.uri == uri]
        if len(found) == 0:
            LOGGER.warning(f"No album found with URI {uri}")
            return

        album = found[0]
        self._update_album_name_label(album.name)
        self._update_artist_name_label(album.artist_name)
        self._update_publication_label(album.date)
        self._update_length_label(album.length)
        self._update_album_image(Path(album.image_path) if album.image_path else None)
        self._update_track_view(album.tracks)

    def _update_album_name_label(self, album_name: Optional[str]) -> None:
        if album_name:
            short_album_name = GLib.markup_escape_text(elide_maybe(album_name))
            album_name_text = (
                f"""<span size="xx-large"><b>{short_album_name}</b></span>"""
            )
            self.album_name_label.set_markup(album_name_text)
            if not self._disable_tooltips:
                self.album_name_label.set_has_tooltip(True)
                self.album_name_label.set_tooltip_text(album_name)
        else:
            self.album_name_label.set_markup("")
            self.album_name_label.set_has_tooltip(False)

        self.album_name_label.show_now()

    def _update_artist_name_label(self, artist_name: Optional[str]) -> None:
        if artist_name:
            short_artist_name = GLib.markup_escape_text(elide_maybe(artist_name))
            artist_name_text = f"""<span size="x-large">{short_artist_name}</span>"""
            self.artist_name_label.set_markup(artist_name_text)
            if not self._disable_tooltips:
                self.artist_name_label.set_has_tooltip(True)
                self.artist_name_label.set_tooltip_text(artist_name)
        else:
            self.artist_name_label.set_markup("")
            self.artist_name_label.set_has_tooltip(False)

        self.artist_name_label.show_now()

    def _update_publication_label(self, date: Optional[str]) -> None:
        if date:
            self.publication_label.set_text(date)
        else:
            self.publication_label.set_text("")

        self.publication_label.show_now()

    def _update_length_label(self, length: Optional[int]) -> None:
        if length:
            pretty_length = ms_to_text(length)
            self.length_label.set_text(pretty_length)
        else:
            self.length_label.set_text("")

        self.length_label.show_now()

    def _update_album_image(self, image_path: Optional[Path]) -> None:
        scaled_pixbuf = None
        if image_path:
            rectangle = self.album_image.get_allocation()
            target_width = min(rectangle.width, rectangle.height)
            scaled_pixbuf = scale_album_image(image_path, target_width=target_width)

        if scaled_pixbuf:
            self.album_image.set_from_pixbuf(scaled_pixbuf)
        else:
            self.album_image.set_from_pixbuf(self._default_album_image)

        self.album_image.show_now()

    def _update_track_view(self, tracks: List[Track]) -> None:
        store = self.track_view.get_model()
        store.clear()

        for track in tracks:
            store.append(
                [
                    track.track_no,
                    track.disc_no,
                    track.name,
                    ms_to_text(track.length) if track.length else "",
                    GLib.markup_escape_text(track.name),
                    track.uri,
                ]
            )

    @Gtk.Template.Callback()
    def on_back_button_clicked(self, _1: Gtk.Button) -> None:
        stack = self.get_parent()
        if stack:
            stack.set_visible_child_name("main_page")

    @Gtk.Template.Callback()
    def on_play_button_clicked(self, _1: Gtk.Button) -> None:
        self._app.send_message(MessageType.PLAY_TRACKS, {"uris": [self.uri]})

    @Gtk.Template.Callback()
    def on_add_button_clicked(self, _1: Gtk.Button) -> None:
        self._app.send_message(MessageType.ADD_TO_TRACKLIST, {"uris": [self.uri]})

    @Gtk.Template.Callback()
    def on_track_view_row_activated(
        self,
        track_view: Gtk.TreeView,
        path: Gtk.TreePath,
        _1: Gtk.TreeViewColumn,
    ) -> None:
        store = track_view.get_model()
        store_iter = store.get_iter(path)
        uri = store.get_value(store_iter, TrackStoreColumns.URI)
        self._app.send_message(MessageType.PLAY_TRACKS, {"uris": [uri]})
