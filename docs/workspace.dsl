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
                    playbackModel = component "Playback Model" "" "GObject"
                    mixerModel = component "Mixer Model" "" "GObject"
                    trackListModel = component "Track List Model" "" "GObject"
                    albumModel = component "Album Model" "" "GObject"
                    playlistModel = component "Playlist Model" "" "GObject"

                    mopidyBackend = component "Mopidy Backend" "" "GObject"
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

                    modelComponent = component "Model" "" "GObject" {
                        -> networkMonitor "Listen to"
                        -> playbackModel "Contains a"
                        -> mixerModel "Contains a"
                        -> trackListModel "Contains a"
                        -> albumModel "Contains list of"
                        -> playlistModel "Contains list of"
                        -> mopidyBackend "Contains list of"
                    }

                    trackModel = component "Track Model" "" "GObject"
                    trackListModel -> trackModel "Contains list of"
                    albumModel -> trackModel "Contains list of"
                    playlistModel -> trackModel "Contains list of"
                }

                appComponent -> asyncioQueue "Get message from / Put message in"

                timePositionTrackerComponent -> httpComponent "Uses"
                timePositionTrackerComponent -> modelComponent "Update"

                httpComponent -> wsComponent "Uses"

                downloadComponent -> aiohttpClientSession "Uses"
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
                    albumsController = component "Albums Controller" {
                        description  "Maintains the album library."
                        technology "GObject"

                        -> baseController "Inherits"
                        -> downloadComponent "Uses"
                        -> mopidyBackend "Get albums URI"
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
                    appComponent -> albumsController "Dispatch messages to"
                    appComponent -> playlistsController "Dispatch messages to"
                    appComponent -> tracklistController "Dispatch messages to"
                    appComponent -> volumeController "Dispatch messages to"
                }
            }
            cacheContainer = container "Cache" "Local file system" "File system" "External"
            dconfContainer = container "Config" "Service provided by local host" "dconf" "External"
            notificationContainer = container "Notification Service" "Service provided by local host" "" "External"

            argosApp -> cacheContainer "Stores images"
            argosApp -> dconfContainer "Stores configuration" "GSettings"
            argosApp -> notificationContainer "Notify" "D-BUS"
        }
        mopidySystem = softwareSystem "Mopidy" "Extensible music server." "External"

        user -> argosSystem "Uses"
        argosSystem -> mopidySystem "Call API" "HTTP/JSON-RPC"

        externalMusicProviders = group "External music providers" {
            musicProviderA = softwareSystem "Bandcamp" "Music store." "External"
            musicProviderB = softwareSystem "Jellyfin" "Free software media system." "External"

            mopidySystem -> musicProviderA "Uses (optional)"
            mopidySystem -> musicProviderB "Uses (optional)"
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
