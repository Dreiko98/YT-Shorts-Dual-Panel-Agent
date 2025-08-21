import yaml
from src.pipeline.db import PipelineDB

# Ruta al archivo YAML y a la base de datos
YAML_PATH = 'configs/channels.yaml'
DB_PATH = 'data/pipeline.db'

def main():
    db = PipelineDB(DB_PATH)
    with open(YAML_PATH, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    channels = data.get('channels', [])
    for ch in channels:
        channel_id = ch.get('id')
        name = ch.get('name')
        enabled = ch.get('enabled', True)
        # El método add_channel_manually requiere: channel_id, channel_name, channel_url, description, subscriber_count
        # El YAML no tiene url ni descripción ni subs, así que pasamos vacío/cero
        ok = db.add_channel_manually(channel_id, name, '', '', 0)
        if ok:
            print(f'Canal insertado: {name} ({channel_id})')
        else:
            print(f'Canal ya existente o error: {name} ({channel_id})')

if __name__ == '__main__':
    main()
