from collections import defaultdict
from typing import Callable, Dict, List, Mapping, Optional, Sequence

from argos.dto import ArtistDTO, TlTrackDTO, TrackDTO
from argos.model import TracklistTrackModel, TrackModel


class ModelHelper:
    """Help convert DTOs to model instances.

    Some conversions can be tracked through visitors.

    """

    def convert_track(self, track_dto: TrackDTO) -> TrackModel:
        track = TrackModel(
            uri=track_dto.uri,
            name=track_dto.name,
            track_no=track_dto.track_no if track_dto.track_no is not None else -1,
            disc_no=track_dto.disc_no if track_dto.disc_no is not None else 1,
            length=track_dto.length if track_dto.length is not None else -1,
            artist_name=track_dto.artists[0].name if len(track_dto.artists) > 0 else "",
            album_name=track_dto.album.name if track_dto.album is not None else "",
            last_modified=track_dto.last_modified
            if track_dto.last_modified is not None
            else -1,
        )
        return track

    def convert_tl_track(self, tl_track_dto: TlTrackDTO) -> TracklistTrackModel:
        track = self.convert_track(tl_track_dto.track)
        tl_track = TracklistTrackModel(tlid=tl_track_dto.tlid, track=track)
        return tl_track

    def parse_tracks(
        self,
        tracks_dto: Mapping[str, Sequence[TrackDTO]],
        *,
        visitors: Optional[Sequence[Callable[[str, TrackDTO], None]]] = None,
    ) -> Dict[str, List[TrackModel]]:
        """Parse a track list.

        Keys in ``track_dto`` can be album URIs or track URIs (when fetching
        details of playlist tracks).

        Args:
            tracks_dto: Track data transfer objects to parse.

            visitors: An optional list of callable to be called on each
                visited track.

        Returns:
            Dict of list of ``TrackModel``.

        """
        parsed_tracks: Dict[str, List[TrackModel]] = defaultdict(list)
        for uri in tracks_dto:
            for track_dto in tracks_dto[uri]:
                if visitors is not None:
                    for visitor in visitors:
                        visitor(uri, track_dto)

                parsed_tracks[uri].append(self.convert_track(track_dto))

        return parsed_tracks
