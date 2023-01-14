workspace {

    model {
        user = person "User" "A user of Mopidy through Argos."
        argosSystem = softwareSystem "Argos" "Light weight Mopidy frontend." {
            argosApp = container "Argos" "Client-side desktop application" "Python executable" {
                aiohttpClientSession = component "Client Session" "" "aiohttp Client Session" "External"
                asyncioQueue = component "Message Queue" "" "asyncio Queue" "External"
                networkMonitor = component "Network Monitor" "" "Gio NetworkMonitor" "External"

                windowComponent = component "Argos Window" {
                    description "Implements the user interface."
                    technology "GtkApplicationWindow"
                }
                wsComponent = component "Mopidy WebSocket Connection" {
                    description "Sends JSON-RPC requests through websocket / Deserialize Mopidy events from websocket."
                    technology "GObject"
                }
                httpComponent = component "Mopidy HTTP Client" {
                    description "Converts commands to JSON-RPC requests matching Mopidy APIs."
                    technology "GObject"
                    }
                informationComponent = component "Information Service" {
                    description "Fetch data from Musicbrainz, Wikidata and Wikipedia."
                    technology "GObject"
                    }
                downloadComponent = component "Image Downloader" {
                    description "Downloads images through Mopidy-Local HTTP API."
                    technology "GObject"
                }
                timePositionTrackerComponent = component "Time Position Tracker" {
                    description "Periodically requests Mopidy server to track time position."
                    technology "GObject"
                }
                notifierComponent = component "Notifier" {
                    description "Sends desktop notifications."
                    technology "GObject"
                }

                appComponent = component "Application" "" "GtkApplication" {
                    -> windowComponent "Owns"
                    -> timePositionTrackerComponent "Starts"
                }

                models = group "Model" {
                    libraryModel = component "Library Model" "" "GObject"
                    playbackModel = component "Playback Model" "" "GObject"
                    mixerModel = component "Mixer Model" "" "GObject"
                    trackListModel = component "Track List Model" "" "GObject"
                    playlistModel = component "Playlist Model" "" "GObject"

                    mopidyBackend = component "Mopidy Backend" "" "GObject"
                    fileBackend = component "Mopidy File Backend" "" "GObject" {
                        -> mopidyBackend "Inherits"
                        tags "MopidyBackend"
                    }
                    localBackend = component "Mopidy Local Backend" "" "GObject" {
                        -> mopidyBackend "Inherits"
                        tags "MopidyBackend"
                    }
                    bandcampBackend = component "Mopidy Bandcamp Backend" "" "GObject" {
                        -> mopidyBackend "Inherits"
                        tags "MopidyBackend"
                    }
                    jellyfinBackend = component "Mopidy Jellyfin Backend" "" "GObject" {
                        -> mopidyBackend "Inherits"
                        tags "MopidyBackend"
                    }
                    podcastBackend = component "Mopidy Podcast Backend" "" "GObject" {
                        -> mopidyBackend "Inherits"
                        tags "MopidyBackend"
                    }
                    somafmBackend = component "Mopidy SomaFM Backend" "" "GObject" {
                        -> mopidyBackend "Inherits"
                        tags "MopidyBackend"
                    }

                    modelComponent = component "Model" "" "GObject" {
                        -> networkMonitor "Listen to"
                        -> playbackModel "Contains a"
                        -> mixerModel "Contains a"
                        -> trackListModel "Contains a"
                        -> libraryModel "Contains a"
                        -> playlistModel "Contains list of"
                        -> mopidyBackend "Contains list of"
                    }

                    trackModel = component "Track Model" "" "GObject"
                    directoryModel = component "Directory Model" "" "GObject"
                    albumModel = component "Album Model" "" "GObject"
                    tracksModel = component "Tracks Model" "" "GObject"
                    libraryModel -> directoryModel "Contains a" "Root directory"
                    directoryModel -> albumModel "Contains list of"
                    directoryModel -> directoryModel "Contains list of"
                    directoryModel -> tracksModel "Contains list of"
                    directoryModel -> playlistModel "Contains list of"
                    trackListModel -> trackModel "Contains list of"
                    albumModel -> trackModel "Contains list of"
                    playlistModel -> trackModel "Contains list of"
                    }

                dtos = group "Data Transfer Objects" {
                    refDTO = component "Ref DTO" "" "dataclass"
                    artistDTO = component "Artist DTO" "" "dataclass"
                    albumDTO = component "Album DTO" "" "dataclass"
                    trackDTO = component "Track DTO" "" "dataclass"
                    imageDTO = component "Image DTO" "" "dataclass"
                    playlistDTO = component "Playlist DTO" "" "dataclass"
                    tlTrackDTO = component "TlTrack DTO" "" "dataclass"
                }

                appComponent -> asyncioQueue "Get message from / Put message in"

                timePositionTrackerComponent -> httpComponent "Uses"
                timePositionTrackerComponent -> modelComponent "Update"

                httpComponent -> wsComponent "Uses"
                httpComponent -> refDTO "Generates"
                httpComponent -> artistDTO "Generates"
                httpComponent -> albumDTO "Generates"
                httpComponent -> trackDTO "Generates"
                httpComponent -> imageDTO "Generates"
                httpComponent -> playlistDTO "Generates"
                httpComponent -> tlTrackDTO "Generates"

                downloadComponent -> aiohttpClientSession "Uses"
                informationComponent -> aiohttpClientSession "Uses"
                wsComponent -> aiohttpClientSession "Uses"
                wsComponent -> asyncioQueue "Put message in"

                windowComponent -> modelComponent "Listen to"

                messageConsumers = group "Message Consumers" {
                    baseController = component "Base Controller" "" "GObject" {
                        -> modelComponent "Update and Listen to"
                        -> httpComponent "Send command"
                        -> asyncioQueue "Put message in"
                        -> notifierComponent "Send notification"
                    }

                    playbackController = component "Playback Controller" {
                        description  "Maintains part of the model dedicated to playback state."
                        technology "GObject"

                        -> baseController "Inherits"
                        -> downloadComponent "Uses"
                    }
                    libraryController = component "Library Controller" {
                        description  "Maintains the library."
                        technology "GObject"

                        -> baseController "Inherits"
                        -> downloadComponent "Uses"
                        -> mopidyBackend "Browse library"
                    }
                    albumsController = component "Albums Controller" {
                        description  "Complete albums."
                        technology "GObject"

                        -> baseController "Inherits"
                        -> downloadComponent "Uses"
                        -> informationComponent "Uses"
                    }
                    playlistsController = component "Playlists Controller" {
                        description  "Maintains part of the model dedicated to playlists."
                        technology "GObject"

                        -> baseController "Inherits"
                    }
                    tracklistController = component "Tracklist Controller" {
                        description  "Maintains part of the model dedicated to the tracklist."
                        technology "GObject"

                        -> baseController "Inherits"
                    }
                    volumeController = component "Volume Controller" {
                        description  "Maintains part of the model dedicated to mixer."
                        technology "GObject"

                        -> baseController "Inherits"
                    }

                    appComponent -> playbackController "Dispatch messages to"
                    appComponent -> libraryController "Dispatch messages to"
                    appComponent -> albumsController "Dispatch messages to"
                    appComponent -> playlistsController "Dispatch messages to"
                    appComponent -> tracklistController "Dispatch messages to"
                    appComponent -> volumeController "Dispatch messages to"
                }
                }
            httpCacheContainer = container "HTTP Cache" "Local file system" "SQLite database" "External"
            fileCacheContainer = container "File Cache" "Local file system" "File system" "External"
            dconfContainer = container "Config" "Service provided by local host" "dconf" "External"
            notificationContainer = container "Notification Service" "Service provided by local host" "" "External"

            argosApp -> httpCacheContainer "Stores responses" "aiohttp-client-session"
            argosApp -> fileCacheContainer "Stores images"
            argosApp -> dconfContainer "Stores configuration" "GSettings"
            argosApp -> notificationContainer "Notify" "D-BUS"
        }
        mopidySystem = softwareSystem "Mopidy" "Extensible music server." "External"

        user -> argosSystem "Uses"
        argosSystem -> mopidySystem "Call API" "HTTP/JSON-RPC"

        externalMusicProviders = group "External music providers" {
            musicProviderA = softwareSystem "Bandcamp" "Music store." "External"
            musicProviderB = softwareSystem "Jellyfin" "Free software media system." "External"
            musicProviderC = softwareSystem "SomaFM" " Listener-supported and independent radio." "External"

            mopidySystem -> musicProviderA "Uses (optional)"
            mopidySystem -> musicProviderB "Uses (optional)"
            mopidySystem -> musicProviderC "Uses (optional)"
        }
    }

    views {
        systemLandscape "system-landscape" {
            include *
            autoLayout
        }

        systemContext argosSystem "system-context" {
            include *
            autoLayout
        }

        container argosSystem "containers" {
            include *
            autoLayout
        }

        component argosApp "components" {
            include *
            exclude element.tag==MopidyBackend
            autoLayout lr 600 300
        }

        styles {
            element "Person" {
                shape person
                background #08427b
                color #ffffff
            }
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "Container" {
                background #1168bd
                color #ffffff
            }
            element "Component" {
                background #1168bd
                color #ffffff
            }
            element "External" {
                background #cccccc
                color #ffffff
            }
        }
    }
}
