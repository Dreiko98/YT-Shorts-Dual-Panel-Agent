
import os
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

class YouTubePublisher:
	"""
	Publicador real de Shorts en YouTube usando la API oficial y OAuth2.
	"""
	SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

	def __init__(self, credentials_path="youtube_credentials.json", token_path="token.pickle"):
		self.credentials_path = credentials_path
		self.token_path = token_path
		self.creds = None
		self.youtube = self._get_authenticated_service()

	def _get_authenticated_service(self):
		creds = None
		if os.path.exists(self.token_path):
			with open(self.token_path, "rb") as token:
				creds = pickle.load(token)
		if not creds or not creds.valid:
			if creds and creds.expired and creds.refresh_token:
				creds.refresh(Request())
			else:
				flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
				creds = flow.run_local_server(port=0)
			with open(self.token_path, "wb") as token:
				pickle.dump(creds, token)
		return build("youtube", "v3", credentials=creds)

	def upload_short(self, video_path, title, description=None, tags=None):
		body = {
			"snippet": {
				"title": title,
				"description": description or "",
				"tags": tags or ["Shorts"],
				"categoryId": "22"  # People & Blogs
			},
			"status": {
				"privacyStatus": "private"  # Cambia a "public" si quieres publicar directamente
			}
		}
		media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
		request = self.youtube.videos().insert(
			part=",".join(body.keys()),
			body=body,
			media_body=media
		)
		response = None
		try:
			print(f"Subiendo {video_path} a YouTube...")
			response = request.execute()
			video_id = response.get("id")
			url = f"https://youtube.com/shorts/{video_id}"
			print(f"Vídeo subido: {url}")
			return {"status": "success", "video_id": video_id, "url": url}
		except Exception as e:
			print(f"Error subiendo vídeo: {e}")
			return {"status": "error", "error": str(e)}
