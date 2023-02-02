import logging, time, datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import track_time_interval
from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerDeviceClass
from homeassistant.components.media_player.const import (
    SUPPORT_BROWSE_MEDIA,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_STEP,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_SELECT_SOUND_MODE,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PLAY,
    SUPPORT_PAUSE,
    SUPPORT_SEEK,
    SUPPORT_CLEAR_PLAYLIST,
    SUPPORT_SHUFFLE_SET,
    SUPPORT_REPEAT_SET,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PREVIOUS_TRACK,
    MEDIA_TYPE_ALBUM,
    MEDIA_TYPE_ARTIST,
    MEDIA_TYPE_CHANNEL,
    MEDIA_TYPE_EPISODE,
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_PLAYLIST,
    MEDIA_TYPE_SEASON,
    MEDIA_TYPE_TRACK,
    MEDIA_TYPE_TVSHOW,
)
from homeassistant.const import (
    CONF_TOKEN, 
    CONF_URL,
    CONF_NAME,
    STATE_OFF, 
    STATE_ON, 
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_IDLE,
    STATE_UNAVAILABLE
)

from .manifest import manifest
DOMAIN = manifest.domain

_LOGGER = logging.getLogger(__name__)

SUPPORT_FEATURES = SUPPORT_VOLUME_STEP | SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET | \
    SUPPORT_SELECT_SOURCE | SUPPORT_SELECT_SOUND_MODE | \
    SUPPORT_PLAY_MEDIA | SUPPORT_PLAY | SUPPORT_PAUSE | SUPPORT_PREVIOUS_TRACK | SUPPORT_NEXT_TRACK | \
    SUPPORT_BROWSE_MEDIA | SUPPORT_SEEK | SUPPORT_CLEAR_PLAYLIST | SUPPORT_SHUFFLE_SET | SUPPORT_REPEAT_SET

# 定时器时间
TIME_BETWEEN_UPDATES = datetime.timedelta(seconds=2)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:    
    media_player = CloudMusicMediaPlayer(hass)

    await hass.async_add_executor_job(track_time_interval, hass, media_player.interval, TIME_BETWEEN_UPDATES)
    async_add_entities([ media_player ], True)

class CloudMusicMediaPlayer(MediaPlayerEntity):

    def __init__(self, hass):
        self.hass = hass
        self._attributes = {
            'platform': 'cloud_music'
        }
        # fixed attribute
        self._attr_media_image_remotely_accessible = True
        self._attr_device_class = MediaPlayerDeviceClass.TV.value
        self._attr_supported_features = SUPPORT_FEATURES

        # default attribute
        self._attr_source_list = []
        self._attr_sound_mode = None
        self._attr_sound_mode_list = []
        self._attr_name = manifest.name
        self._attr_unique_id = manifest.documentation
        self._attr_state =  STATE_ON
        self._attr_volume_level = 1
        self._attr_repeat = 'all'
        self._attr_shuffle = False

        self.cloud_music = hass.data['cloud_music']
        self.before_state = None
        self.current_state = None

    def interval(self, now):
        # 暂停时不更新
        if self._attr_state == STATE_PAUSED:
            return

        media_player = self.media_player
        if media_player is not None:
            attrs = media_player.attributes
            self._attr_media_position = attrs.get('media_position', 0)
            self._attr_media_duration = attrs.get('media_duration', 0)
            self._attr_media_position_updated_at = datetime.datetime.now()
            # 判断是否下一曲
            if self.before_state is not None:
                # 判断音乐总时长
                if self.before_state['media_duration'] > 0 and self.before_state['media_duration'] - self.before_state['media_duration'] <= 5:
                    # 判断源音乐播放器状态
                    if self.before_state['state'] == STATE_PLAYING and self.current_state == STATE_IDLE:
                        self.hass.async_create_task(self.async_media_next_track())
                        self.before_state = None
                        return

            self.before_state = {
                'media_position': self._attr_media_position,
                'media_duration': self._attr_media_duration,
                'state': self.current_state
            }
            self.current_state = media_player.state

        if hasattr(self, 'playlist'):
            music_info = self.playlist[self.playindex]
            self._attr_app_name = music_info.singer
            self._attr_media_image_url = music_info.thumbnail
            self._attr_media_album_name = music_info.album
            self._attr_media_title = music_info.song
            self._attr_media_artist = music_info.singer

    @property
    def media_player(self):
        if self.entity_id is not None and self._attr_sound_mode is not None:
            return self.hass.states.get(self._attr_sound_mode)

    @property
    def device_info(self):
        return {
            'identifiers': {
                (DOMAIN, manifest.documentation)
            },
            'name': self.name,
            'manufacturer': 'shaonianzhentan',
            'model': 'CloudMusic',
            'sw_version': manifest.version
        }

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_browse_media(self, media_content_type=None, media_content_id=None):
        return await self.cloud_music.async_browse_media(self, media_content_type, media_content_id)

    async def async_select_source(self, source):
        if self._attr_source_list.count(source) > 0:
            self._attr_source = source

    async def async_select_sound_mode(self, sound_mode):
        if self._attr_sound_mode_list.count(sound_mode) > 0:
            await self.async_media_pause()
            self._attr_sound_mode = sound_mode

    async def async_volume_up(self):
        await self.async_call('volume_up')

    async def async_volume_down(self):
        await self.async_call('volume_down')

    async def async_mute_volume(self, mute):
        await self.async_call('mute_volume', { 'mute': mute })

    async def async_set_volume_level(self, volume: float):
        self._attr_volume_level = volume
        await self.async_call('volume_set', { 'volume_level': volume })

    async def async_play_media(self, media_type, media_id, **kwargs):

        self._attr_state = STATE_PAUSED
        
        media_content_id = media_id
        result = await self.cloud_music.async_play_media(self, self.cloud_music, media_id)
        if result is not None:
            if result == 'index':
                # 播放当前列表指定项
                media_content_id = self.playlist[self.playindex].url
            elif result.startswith('http'):
                # HTTP播放链接
                media_content_id = result
            else:
                # 添加播放列表到播放器
                media_content_id = self.playlist[self.playindex].url

        self._attr_media_content_id = media_content_id
        await self.async_call('play_media', {
            'media_content_id': media_content_id,
            'media_content_type': 'music'
        })
        self._attr_state = STATE_PLAYING

        self.before_state = None

    async def async_media_play(self):
        self._attr_state = STATE_PLAYING
        await self.async_call('media_play')

    async def async_media_pause(self):
        self._attr_state = STATE_PAUSED
        await self.async_call('media_pause')

    async def async_set_repeat(self, repeat):
        self._attr_repeat = repeat

    async def async_set_shuffle(self, shuffle):
        self._attr_shuffle = shuffle

    async def async_media_next_track(self):
        self._attr_state = STATE_PAUSED
        await self.cloud_music.async_media_next_track(self, self._attr_shuffle)

    async def async_media_previous_track(self):
        self._attr_state = STATE_PAUSED
        await self.cloud_music.async_media_previous_track(self, self._attr_shuffle)

    async def async_media_seek(self, position):
        await self.async_call('media_seek', { 'seek_position': position })

    async def async_media_stop(self):
        await self.async_call('media_stop')

    # 更新属性
    async def async_update(self):
        if self.entity_id is not None:
            state = self.hass.states.get(self.entity_id)
            entities = state.attributes.get('media_player')
            if entities is not None:
                # 兼容初版
                if isinstance(entities, str):
                    entities = [ entities ]

                if len(entities) > 0:
                    self._attr_sound_mode_list = entities
                    if self._attr_sound_mode is None:
                        self._attr_sound_mode = entities[0]

    # 调用服务
    async def async_call(self, service, service_data={}):
        media_player = self.media_player
        if media_player is not None:
            service_data.update({ 'entity_id': media_player.entity_id })
            await self.hass.services.async_call('media_player', service, service_data)