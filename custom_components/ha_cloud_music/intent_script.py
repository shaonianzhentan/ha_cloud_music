import asyncio
from homeassistant.helpers import intent
import homeassistant.helpers.config_validation as cv
import re

def async_register(hass, conversation):
  if conversation:
    intent.async_register(hass, CloudMusicIntent())
    hass.components.conversation.async_register(
          "CloudMusicIntent",
          [
            "播放专辑{album}",
            "播放电台{radio}",
            "播放歌单{playlist}",
            "播放歌曲{song}",
            "播放{singer}的歌"
          ]
      )

class CloudMusicIntent(intent.IntentHandler):

  intent_type = "CloudMusicIntent"

  slot_schema = {
    'playlist': cv.string,
    'album': cv.string,
    'radio': cv.string,
    'singer': cv.string,
    'song': cv.string
  }

  @asyncio.coroutine
  async def async_handle(self, intent_obj):
      hass = intent_obj.hass
      slots = intent_obj.slots

      cloud_music = hass.data['cloud_music']
      playlist = slots.get('playlist')
      album = slots.get('album')
      radio = slots.get('radio')
      singer = slots.get('singer')
      song = slots.get('song')

      media_content_id = None
      # 专辑搜索
      if album is not None:
        _list = await cloud_music.async_search_xmly(album["value"])
        if len(_list) > 0:
          media_content_id = f'cloudmusic://xmly/playlist?id={_list[0]["id"]}'

      # 电台搜索
      if radio is not None:
        _list = await cloud_music.async_search_djradio(radio["value"])
        if len(_list) > 0:
          media_content_id = f'cloudmusic://163/radio/playlist?id={_list[0]["id"]}'

      # 歌单搜索
      if playlist is not None:
        _list = await cloud_music.async_search_playlist(playlist["value"])
        if len(_list) > 0:
          media_content_id = f'cloudmusic://163/playlist?id={_list[0]["id"]}'

      # 歌曲
      if song is not None:
        media_content_id = f'cloudmusic://search/name?kv={song["value"]}'

      # 歌手搜索
      if singer is not None:
        _list = await cloud_music.async_search_singer(singer["value"])
        if len(_list) > 0:
          media_content_id = f'cloudmusic://163/artist/playlist?id={_list[0]["id"]}'

      if media_content_id is None:
        message = '没有找到对应的资源'

      states = hass.states.async_all()
      for state in states:
        domain = state.domain
        platform = state.attributes.get('platform')
        friendly_name = state.attributes.get('friendly_name')
        if state.domain == 'media_player' and platform == 'cloud_music':
          
          hass.async_create_task(hass.services.async_call(domain, 'play_media', {
            'entity_id': state.entity_id,
            'media_content_id': media_content_id,
            'media_content_type': 'music'
          }))
          message = f"正在{friendly_name}上{intent_obj.text_input}"
          break

      response = intent_obj.create_response()
      response.async_set_speech(message)
      return response