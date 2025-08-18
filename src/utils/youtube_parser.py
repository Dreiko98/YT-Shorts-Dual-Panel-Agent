"""
🎬 Utilidades para gestión manual de canales y videos de YouTube
Extrae información automáticamente de URLs para facilitar la adición manual
"""

import re
import requests
import json
import logging
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

class YouTubeURLParser:
    """Parser para URLs de YouTube que extrae IDs y metadatos básicos"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extraer video ID de cualquier URL de YouTube"""
        
        # Patrones comunes de URLs de YouTube
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Si la URL ya es solo el ID
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url.strip()):
            return url.strip()
        
        return None

    def extract_channel_id(self, url: str) -> Optional[str]:
        """Extraer channel ID de URL de canal"""
        
        # Patrones para canales
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/channel/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/c/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/user/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/@([a-zA-Z0-9_.-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Si la URL ya es solo el ID
        if re.match(r'^UC[a-zA-Z0-9_-]{22}$', url.strip()):
            return url.strip()
        
        return None

    def get_video_info_from_page(self, video_id: str) -> Dict:
        """Obtener información básica del video desde la página (sin API)"""
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            html = response.text
            
            # Extraer información básica usando regex
            info = {
                'video_id': video_id,
                'title': self._extract_title(html),
                'channel_name': self._extract_channel_name(html),
                'channel_id': self._extract_channel_id_from_page(html),
                'duration_seconds': self._extract_duration(html),
                'description': self._extract_description(html),
                'published_at': self._extract_publish_date(html),
                'url': url
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Error obteniendo info del video {video_id}: {e}")
            return {
                'video_id': video_id,
                'title': f"Video {video_id}",
                'channel_name': "Canal desconocido",
                'channel_id': None,
                'duration_seconds': 0,
                'description': "",
                'published_at': None,
                'url': url,
                'error': str(e)
            }

    def get_channel_info_from_page(self, channel_identifier: str) -> Dict:
        """Obtener información básica del canal desde la página"""
        
        # Determinar el tipo de URL del canal
        if channel_identifier.startswith('UC') and len(channel_identifier) == 24:
            url = f"https://www.youtube.com/channel/{channel_identifier}"
        elif channel_identifier.startswith('@'):
            url = f"https://www.youtube.com/{channel_identifier}"
        else:
            url = f"https://www.youtube.com/c/{channel_identifier}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            html = response.text
            
            # Extraer información del canal
            info = {
                'channel_id': self._extract_channel_id_from_page(html) or channel_identifier,
                'name': self._extract_channel_title(html),
                'description': self._extract_channel_description(html),
                'subscriber_count': self._extract_subscriber_count(html),
                'url': url
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Error obteniendo info del canal {channel_identifier}: {e}")
            return {
                'channel_id': channel_identifier,
                'name': f"Canal {channel_identifier}",
                'description': "",
                'subscriber_count': 0,
                'url': url,
                'error': str(e)
            }

    def _extract_title(self, html: str) -> str:
        """Extraer título del video"""
        patterns = [
            r'<title>(.+?) - YouTube</title>',
            r'"title":"([^"]+)"',
            r'<meta name="title" content="([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                title = match.group(1)
                # Decodificar entidades HTML básicas
                title = title.replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                return title
        
        return "Título no encontrado"

    def _extract_channel_name(self, html: str) -> str:
        """Extraer nombre del canal"""
        patterns = [
            r'"author":"([^"]+)"',
            r'"ownerChannelName":"([^"]+)"',
            r'<link itemprop="name" content="([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        
        return "Canal desconocido"

    def _extract_channel_id_from_page(self, html: str) -> Optional[str]:
        """Extraer channel ID de la página"""
        patterns = [
            r'"channelId":"([^"]+)"',
            r'"ownerChannelId":"([^"]+)"',
            r'/channel/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                channel_id = match.group(1)
                if channel_id.startswith('UC') and len(channel_id) == 24:
                    return channel_id
        
        return None

    def _extract_duration(self, html: str) -> int:
        """Extraer duración en segundos"""
        patterns = [
            r'"lengthSeconds":"(\d+)"',
            r'"approxDurationMs":"(\d+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                if 'lengthSeconds' in pattern:
                    return int(match.group(1))
                elif 'approxDurationMs' in pattern:
                    return int(match.group(1)) // 1000
        
        return 0

    def _extract_description(self, html: str) -> str:
        """Extraer descripción del video"""
        patterns = [
            r'"shortDescription":"([^"]*)"',
            r'<meta name="description" content="([^"]*)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                desc = match.group(1)
                # Decodificar secuencias de escape básicas
                desc = desc.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                return desc[:500] + ('...' if len(desc) > 500 else '')
        
        return ""

    def _extract_publish_date(self, html: str) -> Optional[str]:
        """Extraer fecha de publicación"""
        patterns = [
            r'"publishDate":"([^"]+)"',
            r'"datePublished":"([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        
        return None

    def _extract_channel_title(self, html: str) -> str:
        """Extraer título/nombre del canal"""
        patterns = [
            r'<title>([^-]+) - YouTube</title>',
            r'"title":"([^"]+)"',
            r'<meta property="og:title" content="([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                title = match.group(1).strip()
                if title and title != "YouTube":
                    return title
        
        return "Canal sin nombre"

    def _extract_channel_description(self, html: str) -> str:
        """Extraer descripción del canal"""
        patterns = [
            r'<meta name="description" content="([^"]*)"',
            r'"description":"([^"]*)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                desc = match.group(1)
                return desc[:300] + ('...' if len(desc) > 300 else '')
        
        return ""

    def _extract_subscriber_count(self, html: str) -> int:
        """Extraer número aproximado de suscriptores"""
        patterns = [
            r'(\d+(?:.\d+)?[KMB]?)\s*subscribers?',
            r'(\d+(?:.\d+)?[KMB]?)\s*suscriptores?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                count_str = match.group(1)
                return self._parse_count(count_str)
        
        return 0

    def _parse_count(self, count_str: str) -> int:
        """Convertir string con K/M/B a número entero"""
        count_str = count_str.replace(',', '').replace('.', '')
        
        if count_str[-1].upper() == 'K':
            return int(float(count_str[:-1]) * 1000)
        elif count_str[-1].upper() == 'M':
            return int(float(count_str[:-1]) * 1000000)
        elif count_str[-1].upper() == 'B':
            return int(float(count_str[:-1]) * 1000000000)
        else:
            try:
                return int(count_str)
            except ValueError:
                return 0

def parse_youtube_url(url: str) -> Dict:
    """Función de conveniencia para parsear cualquier URL de YouTube"""
    parser = YouTubeURLParser()
    
    # Detectar si es video o canal
    video_id = parser.extract_video_id(url)
    if video_id:
        return {
            'type': 'video',
            'data': parser.get_video_info_from_page(video_id)
        }
    
    channel_id = parser.extract_channel_id(url)
    if channel_id:
        return {
            'type': 'channel', 
            'data': parser.get_channel_info_from_page(channel_id)
        }
    
    return {
        'type': 'unknown',
        'data': {'error': 'URL no reconocida como video o canal de YouTube'}
    }

def demo():
    """Demostración del parser"""
    print("🎬 Demo del Parser de YouTube URLs")
    print("=" * 50)
    
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ", 
        "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
        "https://www.youtube.com/@MrBeast"
    ]
    
    for url in test_urls:
        print(f"\n🔍 Analizando: {url}")
        result = parse_youtube_url(url)
        print(f"   Tipo: {result['type']}")
        
        if 'error' not in result['data']:
            if result['type'] == 'video':
                data = result['data']
                print(f"   📺 Título: {data['title']}")
                print(f"   📺 Canal: {data['channel_name']}")
                print(f"   ⏱️  Duración: {data['duration_seconds']}s")
            elif result['type'] == 'channel':
                data = result['data']
                print(f"   📺 Nombre: {data['name']}")
                print(f"   👥 Suscriptores: {data['subscriber_count']}")
        else:
            print(f"   ❌ Error: {result['data']['error']}")

if __name__ == '__main__':
    demo()
