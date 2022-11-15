import enum

class MusicSource(enum.Enum):

    URL = 1
    XIMALAYA = 2
    PLAYLIST = 3
    DJRADIO = 4
    ARTISTS = 5
    CLOUD = 6

class MusicInfo:

    def __init__(self, id, song, singer, album, duration, url, picUrl, source) -> None:
        self._id = id
        self._song = song
        self._singer = singer
        self._duration = duration
        self._album = album
        self._url = url
        self._picUrl = picUrl
        self._source = source

    @property
    def id(self):
        return self._id

    @property
    def song(self):
        return self._song

    @property
    def singer(self):
        return self._singer

    @property
    def duration(self):
        return self._duration

    @property
    def album(self):
        return self._album

    @property
    def url(self):
        return self._url

    @property
    def picUrl(self):
        return self._picUrl

    @property
    def thumbnail(self):
        return self._picUrl + '?param=200y200'

    @property
    def source(self) -> MusicSource:
        return self._source

    def to_dict(self):
        return {
            'id': self.id, 
            'song': self.song, 
            'singer': self.singer, 
            'album': self.album, 
            'duration': self.duration, 
            'url': self.url, 
            'picUrl': self.picUrl,
            'source': self.source
        }