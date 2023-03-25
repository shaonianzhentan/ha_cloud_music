"""Support for media browsing."""
from enum import Enum
import logging, os, random, time
from urllib.parse import urlparse, parse_qs, parse_qsl, quote
from homeassistant.util.json import save_json
from custom_components.ha_cloud_music.http_api import http_get
from .utils import parse_query

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    BrowseError, BrowseMedia,
    async_process_play_media_url
)
from homeassistant.components.media_player.const import (
    MEDIA_CLASS_ALBUM,
    MEDIA_CLASS_ARTIST,
    MEDIA_CLASS_CHANNEL,
    MEDIA_CLASS_DIRECTORY,
    MEDIA_CLASS_EPISODE,
    MEDIA_CLASS_MOVIE,
    MEDIA_CLASS_MUSIC,
    MEDIA_CLASS_PLAYLIST,
    MEDIA_CLASS_SEASON,
    MEDIA_CLASS_TRACK,
    MEDIA_CLASS_TV_SHOW,
    MEDIA_TYPE_ALBUM,
    MEDIA_TYPE_ARTIST,
    MEDIA_TYPE_CHANNEL,
    MEDIA_TYPE_EPISODE,
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_PLAYLIST,
    MEDIA_TYPE_SEASON,
    MEDIA_TYPE_TRACK,
    MEDIA_TYPE_TVSHOW,
)

PLAYABLE_MEDIA_TYPES = [
    MEDIA_TYPE_ALBUM,
    MEDIA_TYPE_ARTIST,
    MEDIA_TYPE_TRACK,
]

CONTAINER_TYPES_SPECIFIC_MEDIA_CLASS = {
    MEDIA_TYPE_ALBUM: MEDIA_CLASS_ALBUM,
    MEDIA_TYPE_ARTIST: MEDIA_CLASS_ARTIST,
    MEDIA_TYPE_PLAYLIST: MEDIA_CLASS_PLAYLIST,
    MEDIA_TYPE_SEASON: MEDIA_CLASS_SEASON,
    MEDIA_TYPE_TVSHOW: MEDIA_CLASS_TV_SHOW,
}

CHILD_TYPE_MEDIA_CLASS = {
    MEDIA_TYPE_SEASON: MEDIA_CLASS_SEASON,
    MEDIA_TYPE_ALBUM: MEDIA_CLASS_ALBUM,
    MEDIA_TYPE_MUSIC: MEDIA_CLASS_MUSIC,
    MEDIA_TYPE_ARTIST: MEDIA_CLASS_ARTIST,
    MEDIA_TYPE_MOVIE: MEDIA_CLASS_MOVIE,
    MEDIA_TYPE_PLAYLIST: MEDIA_CLASS_PLAYLIST,
    MEDIA_TYPE_TRACK: MEDIA_CLASS_TRACK,
    MEDIA_TYPE_TVSHOW: MEDIA_CLASS_TV_SHOW,
    MEDIA_TYPE_CHANNEL: MEDIA_CLASS_CHANNEL,
    MEDIA_TYPE_EPISODE: MEDIA_CLASS_EPISODE,
}

_LOGGER = logging.getLogger(__name__)

protocol = 'cloudmusic://'
cloudmusic_protocol = 'cloudmusic://163/'
xmly_protocol = 'cloudmusic://xmly/'
fm_protocol = 'cloudmusic://fm/'
qq_protocol = 'cloudmusic://qq/'
ting_protocol = 'cloudmusic://ting/'
search_protocol = 'cloudmusic://search/'
play_protocol = 'cloudmusic://play/'

# 云音乐路由表
class CloudMusicRouter():

    media_source = 'media-source://'
    local_playlist = f'{protocol}local/playlist'

    toplist = f'{cloudmusic_protocol}toplist'
    playlist = f'{cloudmusic_protocol}playlist'
    radio_playlist = f'{cloudmusic_protocol}radio/playlist'
    artist_playlist = f'{cloudmusic_protocol}artist/playlist'

    my_login = f'{cloudmusic_protocol}my/login'
    my_daily = f'{cloudmusic_protocol}my/daily'
    my_recommend_resource = f'{cloudmusic_protocol}my/recommend_resource'
    my_cloud = f'{cloudmusic_protocol}my/cloud'
    my_created = f'{cloudmusic_protocol}my/created'
    my_radio = f'{cloudmusic_protocol}my/radio'
    my_artist = f'{cloudmusic_protocol}my/artist'

    # 乐听头条
    ting_homepage = f'{ting_protocol}homepage'
    ting_playlist = f'{ting_protocol}playlist'

    # 喜马拉雅
    xmly_playlist = f'{xmly_protocol}playlist'

    # FM
    fm_channel = f'{fm_protocol}channel'
    fm_playlist = f'{fm_protocol}playlist'

    # 搜索名称
    search_name = f'{search_protocol}name'
    search_play = f'{search_protocol}play'

    # 播放
    play_song = f'{play_protocol}song'
    play_singer = f'{play_protocol}singer'
    play_list = f'{play_protocol}list'
    play_radio = f'{play_protocol}radio'
    play_xmly = f'{play_protocol}xmly'
    play_fm = f'{play_protocol}fm'
    


async def async_browse_media(media_player, media_content_type, media_content_id):
    print(media_content_type, media_content_id)
    hass = media_player.hass
    cloud_music = hass.data['cloud_music']

    # 媒体库
    if media_content_id is not None and media_content_id.startswith(CloudMusicRouter.media_source):
        if media_content_id.startswith(CloudMusicRouter.media_source + '?title='):
            media_content_id = None
        return await media_source.async_browse_media(
            hass,
            media_content_id,
            content_filter=lambda item: item.media_content_type.startswith("audio/"),
        )

    # 主界面
    if media_content_id in [None, protocol]:
        children = [
            {
                'title': '播放列表',
                'path': CloudMusicRouter.local_playlist,
                'type': MEDIA_TYPE_PLAYLIST
            },
            {
                'title': '媒体库',
                'path': CloudMusicRouter.media_source,
                'type': MEDIA_TYPE_PLAYLIST,
                'thumbnail': 'https://brands.home-assistant.io/_/media_source/icon.png'
            },
            {
                'title': '榜单',
                'path': CloudMusicRouter.toplist,
                'type': MEDIA_TYPE_ALBUM,
                'thumbnail': 'http://p2.music.126.net/pcYHpMkdC69VVvWiynNklA==/109951166952713766.jpg'
            }
        ]
        # 当前登录用户
        if cloud_music.userinfo.get('uid') is not None:
            children.extend([
                {
                    'title': '每日推荐歌曲',
                    'path': CloudMusicRouter.my_daily,
                    'type': MEDIA_TYPE_MUSIC
                },{
                    'title': '每日推荐歌单',
                    'path': CloudMusicRouter.my_recommend_resource,
                    'type': MEDIA_TYPE_ALBUM
                },{
                    'title': '我的云盘',
                    'path': CloudMusicRouter.my_cloud,
                    'type': MEDIA_TYPE_ALBUM,
                    'thumbnail': 'http://p3.music.126.net/ik8RFcDiRNSV2wvmTnrcbA==/3435973851857038.jpg'
                },{
                    'title': '我的歌单',
                    'path': CloudMusicRouter.my_created,
                    'type': MEDIA_TYPE_ALBUM,
                    'thumbnail': 'https://p2.music.126.net/tGHU62DTszbFQ37W9qPHcg==/2002210674180197.jpg'
                },{
                    'title': '我的电台',
                    'path': CloudMusicRouter.my_radio,
                    'type': MEDIA_TYPE_SEASON
                },{
                    'title': '我的歌手',
                    'path': CloudMusicRouter.my_artist,
                    'type': MEDIA_TYPE_ARTIST,
                    #'thumbnail': 'http://p1.music.126.net/9M-U5gX1gccbuBXZ6JnTUg==/109951165264087991.jpg'
                }
            ])
        else:
            qr = cloud_music.login_qrcode
            now = int(time.time())
            # 超过5分钟重新获取验证码
            if qr['time'] is None or now - qr['time'] > 300:
                res = await cloud_music.netease_cloud_music('/login/qr/key')
                if res['code'] == 200:
                    codekey = res['data']['unikey']
                    res = await cloud_music.netease_cloud_music(f'/login/qr/create?key={codekey}')
                    qr['key'] = codekey
                    qr['url'] = res['data']['qrurl']
                    qr['time'] = now

            children.extend([
                {
                    'title': 'APP扫码授权后，点击这里登录',
                    'path': CloudMusicRouter.my_login + '?id=' + qr['key'],
                    'type': MEDIA_TYPE_MUSIC,
                    'thumbnail': f'https://cdn.dotmaui.com/qrc/?t={qr["url"]}'
                }
            ])

        # 扩展资源
        children.extend([
            {
                'title': '新闻快讯',
                'path': CloudMusicRouter.ting_homepage,
                'type': MEDIA_TYPE_ALBUM,
                'thumbnail': 'https://p1.music.126.net/ilcqG4jS0GJgAlLs9BCz0g==/109951166709733089.jpg'
            },{
                'title': 'FM电台',
                'path': CloudMusicRouter.fm_channel,
                'type': MEDIA_TYPE_CHANNEL
            }
        ])

        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=protocol,
            media_content_type=MEDIA_TYPE_CHANNEL,
            title="云音乐",
            can_play=False,
            can_expand=True,
            children=[],
        )
        for item in children:
            title = item['title']
            media_content_type = item['type']
            media_content_id = item['path']
            if '?' not in media_content_id:
                media_content_id = media_content_id + f'?title={quote(title)}'
            thumbnail = item.get('thumbnail')
            if thumbnail is not None and 'music.126.net' in thumbnail:
                thumbnail = cloud_music.netease_image_url(thumbnail)
            library_info.children.append(
                BrowseMedia(
                    title=title,
                    media_class=CHILD_TYPE_MEDIA_CLASS[media_content_type],
                    media_content_type=media_content_type,
                    media_content_id=media_content_id,
                    can_play=False,
                    can_expand=True,
                    thumbnail=thumbnail
                )
            )
        return library_info

    # 判断是否云音乐协议
    if media_content_id.startswith(protocol) == False:
        return None

    # 协议转换
    url = urlparse(media_content_id)
    query = parse_query(url.query)

    title = query.get('title')
    id = query.get('id')

    if media_content_id.startswith(CloudMusicRouter.local_playlist):
        # 本地播放列表
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            title=title,
            can_play=False,
            can_expand=False,
            children=[],
        )

        playlist = [] if hasattr(media_player, 'playlist') == False else media_player.playlist
        for index, item in enumerate(playlist):
            title = item.song
            if not item.singer:
                title = f'{title} - {item.singer}'
            library_info.children.append(
                BrowseMedia(
                    title=title,
                    media_class=MEDIA_CLASS_MUSIC,
                    media_content_type=MEDIA_TYPE_PLAYLIST,
                    media_content_id=f"{media_content_id}&index={index}",
                    can_play=True,
                    can_expand=False,
                    thumbnail=item.thumbnail
                )
            )
        return library_info
    if media_content_id.startswith(CloudMusicRouter.my_login):
        # 用户登录        
        res = await cloud_music.netease_cloud_music(f'/login/qr/check?key={id}&t={int(time.time())}')
        _LOGGER.debug(res)
        message = res['message']
        if res['code'] == 803:
            title = f'{message}，刷新页面开始使用吧'
            # ck格式化
            arr = res['cookie'].split(';')
            cookie = {}
            for item in arr:
                x = item.strip()
                if x == '' or x.startswith('Max-Age=') or x.startswith('Expires=') \
                    or x.startswith('Path=') or x.startswith('HTTPOnly'):
                    continue
                kv = x.split('=')
                if kv[1] != '':
                    cookie[kv[0]] = kv[1]
            # 设置cookie
            cloud_music.userinfo['cookie'] = cookie
            res = await cloud_music.netease_cloud_music('/user/account')
            _LOGGER.debug(res)
            cloud_music.userinfo['uid'] = res['account']['id']
            save_json(cloud_music.userinfo_filepath, cloud_music.userinfo)
        else:
            title = f'{message}，点击返回重试'

        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            title=title,
            can_play=False,
            can_expand=False,
            children=[],
        )
        return library_info
    if media_content_id.startswith(CloudMusicRouter.my_daily):
        # 每日推荐
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            title=title,
            can_play=True,
            can_expand=False,
            children=[],
        )
        playlist = await cloud_music.async_get_dailySongs()
        for index, music_info in enumerate(playlist):
            library_info.children.append(
                BrowseMedia(
                    title=music_info.song,
                    media_class=MEDIA_CLASS_MUSIC,
                    media_content_type=MEDIA_TYPE_PLAYLIST,
                    media_content_id=f"{media_content_id}&index={index}",
                    can_play=True,
                    can_expand=False,
                    thumbnail=music_info.thumbnail
                )
            )
        return library_info
    if media_content_id.startswith(CloudMusicRouter.my_cloud):
        # 我的云盘
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            title=title,
            can_play=True,
            can_expand=False,
            children=[],
        )
        playlist = await cloud_music.async_get_cloud()
        for index, music_info in enumerate(playlist):
            library_info.children.append(
                BrowseMedia(
                    title=music_info.song,
                    media_class=MEDIA_CLASS_MUSIC,
                    media_content_type=MEDIA_TYPE_PLAYLIST,
                    media_content_id=f"{media_content_id}&index={index}",
                    can_play=True,
                    can_expand=False,
                    thumbnail=music_info.thumbnail
                )
            )
        return library_info
    if media_content_id.startswith(CloudMusicRouter.my_created):
        # 我创建的歌单
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            title=title,
            can_play=False,
            can_expand=False,
            children=[],
        )
        uid = cloud_music.userinfo.get('uid')
        res = await cloud_music.netease_cloud_music(f'/user/playlist?uid={uid}')
        for item in res['playlist']:
            library_info.children.append(
                BrowseMedia(
                    title=item.get('name'),
                    media_class=MEDIA_CLASS_DIRECTORY,
                    media_content_type=MEDIA_TYPE_MUSIC,
                    media_content_id=f"{CloudMusicRouter.playlist}?title={quote(item['name'])}&id={item['id']}",
                    can_play=False,
                    can_expand=True,
                    thumbnail=cloud_music.netease_image_url(item['coverImgUrl'])
                )
            )
        return library_info
    if media_content_id.startswith(CloudMusicRouter.my_radio):
        # 收藏的电台
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            title=title,
            can_play=False,
            can_expand=False,
            children=[],
        )
        res = await cloud_music.netease_cloud_music('/dj/sublist')
        for item in res['djRadios']:
            library_info.children.append(
                BrowseMedia(
                    title=item.get('name'),
                    media_class=MEDIA_CLASS_DIRECTORY,
                    media_content_type=MEDIA_TYPE_PLAYLIST,
                    media_content_id=f"{CloudMusicRouter.radio_playlist}?title={quote(item['name'])}&id={item['id']}",
                    can_play=False,
                    can_expand=True,
                    thumbnail=cloud_music.netease_image_url(item['picUrl'])
                )
            )
        return library_info
    if media_content_id.startswith(CloudMusicRouter.radio_playlist):
        # 电台音乐列表
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            title=title,
            can_play=True,
            can_expand=False,
            children=[],
        )
        playlist = await cloud_music.async_get_djradio(id)
        for index, music_info in enumerate(playlist):
            library_info.children.append(
                BrowseMedia(
                    title=music_info.song,
                    media_class=MEDIA_CLASS_MUSIC,
                    media_content_type=MEDIA_TYPE_PLAYLIST,
                    media_content_id=f"{media_content_id}&index={index}",
                    can_play=True,
                    can_expand=False,
                    thumbnail=music_info.thumbnail
                )
            )
        return library_info
    if media_content_id.startswith(CloudMusicRouter.my_artist):
        # 收藏的歌手
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            title=title,
            can_play=False,
            can_expand=False,
            children=[],
        )
        res = await cloud_music.netease_cloud_music('/artist/sublist')
        for item in res['data']:
            library_info.children.append(
                BrowseMedia(
                    title=item['name'],
                    media_class=MEDIA_CLASS_ARTIST,
                    media_content_type=MEDIA_TYPE_PLAYLIST,
                    media_content_id=f"{cloudmusic_protocol}my/artist/playlist?title={quote(item['name'])}&id={item['id']}",
                    can_play=False,
                    can_expand=True,
                    thumbnail=cloud_music.netease_image_url(item['picUrl'])
                )
            )
        return library_info
    if media_content_id.startswith(CloudMusicRouter.artist_playlist):
        # 歌手音乐列表
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            title=title,
            can_play=True,
            can_expand=False,
            children=[],
        )
        playlist = await cloud_music.async_get_artists(id)
        for index, music_info in enumerate(playlist):
            library_info.children.append(
                BrowseMedia(
                    title=music_info.song,
                    media_class=MEDIA_CLASS_MUSIC,
                    media_content_type=MEDIA_TYPE_PLAYLIST,
                    media_content_id=f"{media_content_id}&index={index}",
                    can_play=True,
                    can_expand=False,
                    thumbnail=music_info.thumbnail
                )
            )
        return library_info
    if media_content_id.startswith(CloudMusicRouter.my_recommend_resource):
        # 每日推荐歌单
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_CLASS_TRACK,
            title=title,
            can_play=False,
            can_expand=True,
            children=[],
        )
        res = await cloud_music.netease_cloud_music('/recommend/resource')
        for item in res['recommend']:
            library_info.children.append(
                BrowseMedia(
                    title=item['name'],
                    media_class=MEDIA_CLASS_PLAYLIST,
                    media_content_type=MEDIA_TYPE_PLAYLIST,
                    media_content_id=f"{CloudMusicRouter.playlist}?title={quote(item['name'])}&id={item['id']}",
                    can_play=False,
                    can_expand=True,
                    thumbnail=cloud_music.netease_image_url(item['picUrl'])
                )
            )
        return library_info
    if media_content_id.startswith(CloudMusicRouter.toplist):
        # 排行榜
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_CLASS_TRACK,
            title=title,
            can_play=False,
            can_expand=True,
            children=[],
        )
        res = await cloud_music.netease_cloud_music('/toplist')
        for item in res['list']:
            library_info.children.append(
                BrowseMedia(
                    title=item['name'],
                    media_class=MEDIA_CLASS_PLAYLIST,
                    media_content_type=MEDIA_TYPE_PLAYLIST,
                    media_content_id=f"{CloudMusicRouter.playlist}?title={quote(item['name'])}&id={item['id']}",
                    can_play=False,
                    can_expand=True,
                    thumbnail=cloud_music.netease_image_url(item['coverImgUrl'])
                )
            )
        return library_info
    if media_content_id.startswith(CloudMusicRouter.playlist):
        # 歌单列表
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_PLAYLIST,
            media_content_id=media_content_id,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            title=title,
            can_play=True,
            can_expand=False,
            children=[],
        )
        playlist = await cloud_music.async_get_playlist(id)
        for index, music_info in enumerate(playlist):
            library_info.children.append(
                BrowseMedia(
                    title=f'{music_info.song} - {music_info.singer}',
                    media_class=MEDIA_CLASS_MUSIC,
                    media_content_type=MEDIA_TYPE_PLAYLIST,
                    media_content_id=f"{media_content_id}&index={index}",
                    can_play=True,
                    can_expand=False,
                    thumbnail=music_info.thumbnail
                )
            )
        return library_info

    #================= 乐听头条
    if media_content_id.startswith(CloudMusicRouter.ting_homepage):
        children = [
            {
                'id': 'f3f5a6d2-5557-4555-be8e-1da281f97c22',
                'title': '热点'
            },
            {
                'id': 'd8e89746-1e66-47ad-8998-1a41ada3beee',
                'title': '社会'
            },
            {
                'id': '4905d954-5a85-494a-bd8c-7bc3e1563299',
                'title': '国际'
            },
            {
                'id': 'fc583bff-e803-44b6-873a-50743ce7a1e9',
                'title': '国内'
            },
            {
                'id': 'c7467c00-463d-4c93-b999-7bbfc86ec2d4',
                'title': '体育'
            },
            {
                'id': '75564ed6-7b68-4922-b65b-859ea552422c',
                'title': '娱乐'
            },
            {
                'id': 'c6bc8af2-e1cc-4877-ac26-bac1e15e0aa9',
                'title': '财经'
            },
            {
                'id': 'f5cff467-2d78-4656-9b72-8e064c373874',
                'title': '科技'
            },
            {
                'id': 'ba89c581-7b16-4d25-a7ce-847a04bc9d91',
                'title': '军事'
            },
            {
                'id': '40f31d9d-8af8-4b28-a773-2e8837924e2e',
                'title': '生活'
            },
            {
                'id': '0dee077c-4956-41d3-878f-f2ab264dc379',
                'title': '教育'
            },
            {
                'id': '5c930af2-5c8a-4a12-9561-82c5e1c41e48',
                'title': '汽车'
            },
            {
                'id': 'f463180f-7a49-415e-b884-c6832ba876f0',
                'title': '人文'
            },
            {
                'id': '8cae0497-4878-4de9-b3fe-30518e2b6a9f',
                'title': '旅游'
            }
        ]
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_TYPE_CHANNEL,
            title=title,
            can_play=False,
            can_expand=False,
            children=[],
        )
        for item in children:
            title = item['title']
            library_info.children.append(
                BrowseMedia(
                    title=title,
                    media_class=CHILD_TYPE_MEDIA_CLASS[MEDIA_TYPE_EPISODE],
                    media_content_type=MEDIA_TYPE_EPISODE,
                    media_content_id=f'{CloudMusicRouter.ting_playlist}?title={quote(title)}&id=' + item['id'],
                    can_play=True,
                    can_expand=False
                )
            )
        return library_info

    #================= FM
    if media_content_id.startswith(CloudMusicRouter.fm_channel):

        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_TYPE_CHANNEL,
            title=title,
            can_play=False,
            can_expand=False,
            children=[],
        )

        result = await http_get('https://rapi.qingting.fm/categories?type=channel')
        data = result['Data']
        for item in data:
            title = item['title']
            library_info.children.append(
                BrowseMedia(
                    title=title,
                    media_class=CHILD_TYPE_MEDIA_CLASS[MEDIA_TYPE_CHANNEL],
                    media_content_type=MEDIA_TYPE_CHANNEL,
                    media_content_id=f'{CloudMusicRouter.fm_playlist}?title={quote(title)}&id={item["id"]}',
                    can_play=False,
                    can_expand=True
                )
            )
        return library_info

    if media_content_id.startswith(CloudMusicRouter.fm_playlist):
        
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            title=title,
            can_play=True,
            can_expand=False,
            children=[],
        )
        playlist = await cloud_music.async_fm_playlist(id)
        for index, music_info in enumerate(playlist):
            library_info.children.append(
                BrowseMedia(
                    title=f'{music_info.song} - {music_info.singer}',
                    media_class=MEDIA_CLASS_MUSIC,
                    media_content_type=MEDIA_TYPE_PLAYLIST,
                    media_content_id=f"{media_content_id}&index={index}",
                    can_play=True,
                    can_expand=False,
                    thumbnail=music_info.thumbnail
                )
            )
        return library_info

    #================= 喜马拉雅

    


''' ==================  播放音乐 ================== '''
async def async_play_media(media_player, cloud_music, media_content_id):
    print(media_content_id)
    hass = media_player.hass
    # 媒体库
    if media_source.is_media_source_id(media_content_id):
        play_item = await media_source.async_resolve_media(
            hass, media_content_id, media_player.entity_id
        )
        return async_process_play_media_url(hass, play_item.url)

    # 判断是否云音乐协议
    if media_content_id.startswith(protocol) == False:
        return

    # 协议转换
    url = urlparse(media_content_id)
    query = parse_query(url.query)

    playlist = None
    # 通用索引
    playindex = int(query.get('index', 0))
    # 通用ID
    id = query.get('id')
    # 通用搜索关键词
    keywords = query.get('kv')

    if media_content_id.startswith(CloudMusicRouter.local_playlist):
        media_player.playindex = playindex
        return 'index'

    if media_content_id.startswith(CloudMusicRouter.playlist):
        playlist = await cloud_music.async_get_playlist(id)
    elif media_content_id.startswith(CloudMusicRouter.my_daily):
        playlist = await cloud_music.async_get_dailySongs()
    elif media_content_id.startswith(CloudMusicRouter.my_cloud):
        playlist = await cloud_music.async_get_cloud()
    elif media_content_id.startswith(CloudMusicRouter.artist_playlist):
        playlist = await cloud_music.async_get_artists(id)
    elif media_content_id.startswith(CloudMusicRouter.radio_playlist):
        playlist = await cloud_music.async_get_djradio(id)
    elif media_content_id.startswith(CloudMusicRouter.ting_playlist):
        playlist = await cloud_music.async_ting_playlist(id)
    elif media_content_id.startswith(CloudMusicRouter.xmly_playlist):
        page = query.get('page', 1)
        size = query.get('size', 50)
        asc = query.get('asc', 1)
        playlist = await cloud_music.async_xmly_playlist(id, page, size, asc)
    elif media_content_id.startswith(CloudMusicRouter.fm_playlist):
        page = query.get('page', 1)
        size = query.get('size', 200)
        playlist = await cloud_music.async_fm_playlist(id, page, size)
    elif media_content_id.startswith(CloudMusicRouter.search_name):
        playlist = await cloud_music.async_search_song(keywords)
    elif media_content_id.startswith(CloudMusicRouter.search_play):
        ''' 外部接口搜索 '''
        result = await cloud_music.async_music_source(keywords)
        if result is not None:
            playlist = [ result ]
    elif media_content_id.startswith(CloudMusicRouter.play_song):
        playlist = await cloud_music.async_play_song(keywords)
    elif media_content_id.startswith(CloudMusicRouter.play_list):
        playlist = await cloud_music.async_play_playlist(keywords)
    elif media_content_id.startswith(CloudMusicRouter.play_radio):
        playlist = await cloud_music.async_play_radio(keywords)
    elif media_content_id.startswith(CloudMusicRouter.play_singer):
        playlist = await cloud_music.async_play_singer(keywords)
        

    if playlist is not None:
        media_player.playindex = playindex
        media_player.playlist = playlist
        return 'playlist'


# 上一曲
async def async_media_previous_track(media_player, shuffle=False):
    if hasattr(media_player, 'playlist') == False:
        return

    playlist = media_player.playlist
    count = len(playlist)
    # 随机
    if shuffle:
        playindex = random.randint(0, count - 1)
    else:
        if count <= 1:
            return
        playindex = media_player.playindex - 1
        if playindex < 0:
            playindex = count - 1
    media_player.playindex = playindex
    await media_player.async_play_media(MEDIA_TYPE_MUSIC, playlist[playindex].url)

# 下一曲
async def async_media_next_track(media_player, shuffle=False):
    if hasattr(media_player, 'playlist') == False:
        return

    playindex = media_player.playindex + 1
    playlist = media_player.playlist
    count = len(playlist)
    # 随机
    if shuffle:
        playindex = random.randint(0, count - 1)
    else:
        if playindex >= len(playlist):
            playindex = 0
    media_player.playindex = playindex
    await media_player.async_play_media(MEDIA_TYPE_MUSIC, playlist[playindex].url)