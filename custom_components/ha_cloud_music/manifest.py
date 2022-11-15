import os
from homeassistant.util.json import load_json

def custom_components_path(file_path):
    return os.path.abspath('./custom_components/' + file_path)

class Manifest():

    def __init__(self, domain):
        self.domain = domain
        self.manifest_path = custom_components_path(f'{domain}/manifest.json')
        self.update()

    @property
    def remote_url(self):
        return 'https://gitee.com/shaonianzhentan/ha_cloud_music/raw/dev/custom_components/ha_cloud_music/manifest.json'

    def update(self):
        data = load_json(self.manifest_path, {})
        self.domain = data.get('domain')
        self.name = data.get('name')
        self.version = data.get('version')
        self.documentation = data.get('documentation')

manifest = Manifest('ha_cloud_music')