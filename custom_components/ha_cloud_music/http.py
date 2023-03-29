import os, json, requests
from urllib.parse import parse_qsl, quote
from homeassistant.components.http import HomeAssistantView
from aiohttp import web
from .models.music_info import MusicSource
from .manifest import manifest

DOMAIN = manifest.domain

class HttpView(HomeAssistantView):

    url = "/cloud_music/url"
    name = f"cloud_music:url"
    requires_auth = False

    play_key = None
    play_url = None

    async def get(self, request):
        hass = request.app["hass"]        
        cloud_music = hass.data['cloud_music']

        query = request.query
        print(query)
        id = query.get('id')
        source = query.get('source')
        song = query.get('song')
        singer = query.get('singer')

        not_found_tips = quote(f'当前没有找到编号是{id}，歌名为{song}，作者是{singer}的播放链接')
        play_url = f'https://fanyi.baidu.com/gettts?lan=zh&text={not_found_tips}&spd=5&source=web'

        if id is None or source is None:
            return web.HTTPFound(play_url)

        # 缓存KEY
        play_key = f'{id}{song}{singer}{source}'
        if self.play_key == play_key:
            return web.HTTPFound(self.play_url)
            
        source = int(source)
        if source == MusicSource.PLAYLIST.value \
            or source == MusicSource.ARTISTS.value \
            or source == MusicSource.DJRADIO.value \
            or source == MusicSource.CLOUD.value:
                # 获取播放链接
                url, fee = await cloud_music.song_url(id)
                if url is not None:
                    # 收费音乐
                    if fee == 1:
                        result = await cloud_music.async_music_source(song, singer)
                        if result is not None:
                            url = result.url

                    play_url = url
                else:
                    # 从云盘里获取
                    url = await cloud_music.cloud_song_url(id)
                    if url is not None:
                        play_url = url
                    else:
                        result = await cloud_music.async_music_source(song, singer)
                        if result is not None:
                            play_url = result.url

        print(play_url)        
        self.play_key = play_key
        self.play_url = play_url
        # 重定向到可播放链接
        return web.HTTPFound(play_url)