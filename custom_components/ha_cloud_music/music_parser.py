from bs4 import BeautifulSoup
import requests, re
from .models.music_info import MusicInfo, MusicSource

def get_music(keywords):
  api = 'https://www.fangpi.net'
  session = requests.Session()
  try:
    response = session.get(f'{api}/s/{keywords}')
    soup = BeautifulSoup(response.text.encode(response.encoding), 'lxml')
    items = soup.select('.table tbody tr')
    if len(items) > 0:
      a = items[0].select('a')
      href = a[0].attrs['href']
      song = a[0].string
      singer = a[1].string

      # print(href)
      response = session.get(f'{api}{href}')

      pattren = re.compile(r'https://[^\s]+.mp3')
      url_lst = pattren.findall(response.text)
      # print(url_lst)
      if len(url_lst) > 0:
        soup = BeautifulSoup(response.text.encode(response.encoding), 'lxml')
        cover = soup.select('#cover')
        # 封面
        pic = cover[0].attrs['src']

        songId = href.replace('/', '')
        album = ''
        audio_url = url_lst[0]
        return MusicInfo(songId, song, singer, album, 0, audio_url, pic, MusicSource.URL.value)
  except Exception as ex:
    print(ex)

def get_music2(keywords):
  api = 'https://thewind.xyz/music/api/'
  url = f'{api}search'
  files = {
      "src": (None, "KW"),
      "keyword": (None, keyword),
      "num": (None, 10)
  }
  response = requests.post(url, files=files)
  result = response.json()
  # print(result)
  if len(result) > 0:
      result = list(filter(lambda x: x.get('songId') is not None, result))
      if len(result) > 0:
          item = result[0]
          albumName = item.get('albumName')
          songSrc = item['songSrc']
          songId = item['songId']
          play_url = f'{api}player?shareId={songSrc}_{songId}'
          # print(play_url)
          response = requests.get(play_url)
          result = response.json()
          # print(result)
          if isinstance(result, list) and len(result) > 0:
              info = result[0]
              audio_url = info.get('url', '')
              if audio_url != '':
                  return MusicInfo(songId, info.get('title'), info.get('author'), albumName, 0, audio_url, info.get('pic'), MusicSource.URL.value)