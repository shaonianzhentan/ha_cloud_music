from urllib.parse import parse_qsl, quote

def parse_query(url_query):
    query = parse_qsl(url_query)
    data = {}
    for item in query:
        data[item[0]] = item[1]
    return data