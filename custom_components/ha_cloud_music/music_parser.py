from bs4 import BeautifulSoup
import requests
import re
from .models.music_info import MusicInfo, MusicSource


def get_last_part(path):
    last_slash_index = path.rfind('/')
    if last_slash_index != -1:
        return path[last_slash_index + 1:]
    return path


def get_music(keyword):
    # https://www.gequbao.com
    api = 'https://www.fangpi.net'
    session = requests.Session()
    try:
        response = session.get(f'{api}/s/{keyword}')
        soup = BeautifulSoup(response.text.encode(response.encoding), 'lxml')
        items = soup.select('.card-text .row')
        if len(items) > 1:
            row = items[1]
            song = row.select('.col-5 a')[0].get_text().strip()
            singer = row.select('.col-4')[0].get_text().strip()

            a = row.select('.col-3 a')
            href = a[0].attrs['href']

            response = session.get(f'{api}{href}')
            html = response.text

            soup = BeautifulSoup(html, 'lxml')
            cover = soup.select('head meta[property="og:image"]')
            pic = 'https://p2.music.126.net/tGHU62DTszbFQ37W9qPHcg==/2002210674180197.jpg'
            # 封面
            if len(cover) > 0:
                pic = cover[0].attrs['content']

            songId = get_last_part(href)
            album = ''
            audio_url = f'https://www.fangpi.net/api/play_url?id={songId}'
            return MusicInfo(songId, song, singer, album, 0, audio_url, pic, MusicSource.URL.value)
    except Exception as ex:
        pass
