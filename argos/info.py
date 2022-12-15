import gettext
import logging
import urllib.parse
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import aiohttp
from gi.repository import GLib, GObject

if TYPE_CHECKING:
    from argos.app import Application

from argos.session import HTTPSessionManager

_ = gettext.gettext

LOGGER = logging.getLogger(__name__)

_WIKIPEDIA_BASE_URLS: Dict[str, str] = {
    "dewiki": "https://de.wikipedia.org",
    "enwiki": "https://en.wikipedia.org",
    "frwiki": "https://fr.wikipedia.org",
}

_MUSICBRAINZ_BASE_URL: str = "https://musicbrainz.org/ws/2/"
_WIKIDATA_BASE_URL: str = "https://www.wikidata.org/"


def _get_wikipedia_base_urls(lang_key: str) -> List[str]:
    urls = []
    if lang_key != "enwiki":
        lang_url = _WIKIPEDIA_BASE_URLS.get(lang_key)
        if lang_url is not None:
            urls.append(lang_url)
    urls.append(_WIKIPEDIA_BASE_URLS["enwiki"])
    return urls


class WikidataProperty(Enum):
    MusicBrainzArtistID = "P434"
    MusicBrainzReleaseGroupID = "P436"


class InformationService(GObject.Object):
    """Collect information from Wikipedia and other websites."""

    wikipedia_mention = _("Data source: Wikipedia CC BY-SA 3.0")

    def __init__(
        self,
        application: "Application",
    ):
        super().__init__()

        self._http_session_manager: HTTPSessionManager = (
            application.http_session_manager
        )

        self._mbids_mapping: Dict[str, Tuple[Optional[str], Optional[str]]] = {}
        self._album_abstracts: Dict[str, Optional[str]] = {}  # by release group MBID
        self._artist_abstracts: Dict[str, Optional[str]] = {}  # by artist MBID

    async def _get_related_mbids(
        self, session: aiohttp.ClientSession, release_mbid: str
    ) -> Tuple[Optional[str], Optional[str]]:
        query_string = "inc=release-groups%20artists"
        url = urllib.parse.urljoin(
            _MUSICBRAINZ_BASE_URL, f"release/{release_mbid}?{query_string}"
        )
        LOGGER.debug(f"Sending GET {url}")
        async with session.get(url, headers={"Accept": "application/json"}) as resp:
            parsed_resp = await resp.json()

        group = parsed_resp.get("release-group")
        release_group_mbid = group.get("id") if group is not None else None
        artist_credit = parsed_resp.get("artist-credit", [])
        artist = artist_credit[0].get("artist") if len(artist_credit) != 0 else None
        artist_mbid = artist.get("id") if artist is not None else None
        return release_group_mbid, artist_mbid

    async def _get_sitelinks_from_wikidata(
        self,
        session: aiohttp.ClientSession,
        mbid: str,
        *,
        criteria: WikidataProperty,
    ) -> Optional[Dict[str, Dict[str, str]]]:
        query_string = "&".join(
            [
                "action=query",
                "format=json",
                "list=search",
                f"srsearch=haswbstatement:{criteria.value}={mbid}",
            ]
        )
        url = urllib.parse.urljoin(_WIKIDATA_BASE_URL, f"w/api.php?{query_string}")
        LOGGER.debug(f"Sending GET {url}")
        async with session.get(url) as resp:
            parsed_resp = await resp.json()

        query = parsed_resp.get("query")
        search = query.get("search") if query else None
        if len(search) == 0:
            return None

        title = search[0].get("title") if search is not None else None
        if not title:
            return None

        url = urllib.parse.urljoin(_WIKIDATA_BASE_URL, f"entity/{title}?flavor=json")
        LOGGER.debug(f"Sending GET {url}")
        async with session.get(url) as resp:
            parsed_resp = await resp.json()

        entities = parsed_resp.get("entities")
        entity = entities.get(title) if entities is not None else None
        sitelinks = entity.get("sitelinks") if entity is not None else None
        return sitelinks

    def _build_preferred_abstract_url(
        self, sitelinks: Dict[str, Dict[str, str]]
    ) -> Optional[str]:
        language_names = [
            lang
            for lang in GLib.get_language_names()
            if len(lang) == 2
            and "_" not in lang
            and "." not in lang
            and "@" not in lang
        ]
        # Filters out standard locales ("C", "POSIX"), territory,
        # codeset or modifier

        if len(language_names) == 0:
            LOGGER.warn("Failed to identify language")
            return None
        elif len(language_names) > 1:
            LOGGER.debug(f"Multiple language name {language_names!r}")

        language = language_names[0]
        preferred_lang_key = f"{language}wiki"
        wikipedia_base_urls = _get_wikipedia_base_urls(preferred_lang_key)

        for base_url in wikipedia_base_urls:
            sitelink = sitelinks.get(preferred_lang_key)
            title = sitelink.get("title") if sitelink is not None else None
            if title is not None:
                query_string = "&".join(
                    [
                        "format=json",
                        "action=query",
                        "prop=extracts",
                        "exintro",
                        "explaintext",
                        "redirects=1",
                        f"titles={title}",
                    ]
                )

                url = urllib.parse.urljoin(base_url, f"/w/api.php?{query_string}")
                return url

        return None

    async def _get_abstract(
        self,
        session: aiohttp.ClientSession,
        url: str,
    ) -> Optional[str]:
        LOGGER.debug(f"Sending GET {url}")
        async with session.get(url) as resp:
            parsed_resp = await resp.json()

        query = parsed_resp.get("query")
        pages = query.get("pages") if query is not None else None
        if pages is None:
            return None
        try:
            key = next(iter(pages.keys()))
        except StopIteration:
            LOGGER.debug("Unexpected response without pages")
            return None
        LOGGER.debug(f"Extracting abstract from Wikipedia page {key!r}")
        raw_abstract = pages[key].get("extract")
        if raw_abstract is None:
            return None

        polished_abstract = GLib.markup_escape_text(raw_abstract.replace("\n", "\n\n"))
        return f"{polished_abstract}\n\n{self.wikipedia_mention}"

    async def _get_album_abstract(
        self,
        session: aiohttp.ClientSession,
        release_group_mbid: str,
    ) -> Optional[str]:
        if release_group_mbid in self._album_abstracts:
            abstract = self._album_abstracts.get(release_group_mbid)
            LOGGER.debug("Release MBID found in cache")
        else:
            sitelinks = await self._get_sitelinks_from_wikidata(
                session,
                release_group_mbid,
                criteria=WikidataProperty.MusicBrainzReleaseGroupID,
            )
            abstract = None
            if sitelinks is not None:
                url = self._build_preferred_abstract_url(sitelinks)
                if url is not None:
                    abstract = await self._get_abstract(session, url)
                else:
                    LOGGER.debug(
                        f"No sitelink related to release group MBID {release_group_mbid!r}"
                    )
            else:
                LOGGER.debug(
                    f"Empty sitelinks for release group MBID {release_group_mbid!r}"
                )

        self._album_abstracts[release_group_mbid] = abstract
        LOGGER.debug(f"Cache updated for MBID {release_group_mbid!r}")

        return abstract

    async def _get_artist_abstract(
        self,
        session: aiohttp.ClientSession,
        artist_mbid: str,
    ) -> Optional[str]:
        abstract = None
        if artist_mbid in self._artist_abstracts:
            abstract = self._artist_abstracts.get(artist_mbid)
            LOGGER.debug("Artist MBID found in cache")
        else:
            sitelinks = await self._get_sitelinks_from_wikidata(
                session,
                artist_mbid,
                criteria=WikidataProperty.MusicBrainzArtistID,
            )
            if sitelinks is not None:
                url = self._build_preferred_abstract_url(sitelinks)
                if url is not None:
                    abstract = await self._get_abstract(session, url)
                else:
                    LOGGER.debug(f"No sitelink related to artist MBID {artist_mbid!r}")
            else:
                LOGGER.debug(f"Empty sitelinks for artist MBID {artist_mbid!r}")

        self._artist_abstracts[artist_mbid] = abstract
        LOGGER.debug(f"Cache updated for MBID {artist_mbid!r}")

        return abstract

    async def get_album_information(
        self, release_mbid: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Return short texts for album with given release MBID.

        The first text is the abstract of the Wikipedia page dedicated
        to the album. The second text is the abstract of the Wikipedia
        page dedicated to the album first credited artist.

        Musicbrainz API is used to deduce a Musicbrainz identifier
        (MBID) for the release group and the first credited artist.

        Wikidata API is used to search for Wikipedia pages associated
        to MBIDs.

        Finally, Wikipedia API is used to retrieve pages abstracts.

        Page selection is expected to match current locale language or
        English.

        """
        if release_mbid is None:
            return None, None

        if release_mbid in self._mbids_mapping:
            LOGGER.debug(f"Cache contains release MBID {release_mbid!r}")
            release_group_mbid, artist_mbid = self._mbids_mapping.get(
                release_mbid, (None, None)
            )
            return (
                self._album_abstracts.get(release_mbid)
                if release_mbid is not None
                else None,
                self._artist_abstracts.get(artist_mbid)
                if artist_mbid is not None
                else None,
            )

        album_abstract, artist_abstract = None, None
        async with self._http_session_manager.get_session() as session:
            try:
                release_group_mbid, artist_mbid = await self._get_related_mbids(
                    session, release_mbid
                )
                if release_group_mbid is not None:
                    album_abstract = await self._get_album_abstract(
                        session, release_group_mbid
                    )
                else:
                    LOGGER.debug(
                        f"No release group identified for release MBID {release_mbid!r}"
                    )

                if artist_mbid is not None:
                    artist_abstract = await self._get_artist_abstract(
                        session, artist_mbid
                    )
                else:
                    LOGGER.debug(
                        f"No artist identified for release MBID {release_mbid!r}"
                    )

            except aiohttp.ClientError as err:
                LOGGER.error(
                    f"Failed to request abstracts for release MBID {release_mbid!r}, {err}"
                )
                return None, None

        # Since GObject properties aren't nullable, album controller
        # can't trivially distinguish between this function not called
        # or this function returned None. Thus a cache is
        # introduced. But it duplicates all abstracts: They are in the
        # model and in this cache...

        self._mbids_mapping[release_mbid] = (release_group_mbid, artist_mbid)
        LOGGER.debug(f"Cache updated for MBID {release_mbid!r}")

        return album_abstract, artist_abstract
