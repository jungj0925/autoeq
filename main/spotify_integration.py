import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

load_dotenv()

class SpotifyIntegration:
    def __init__(self):
        self.spotify_oauth = SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
            scope="user-read-currently-playing"
        )
        self.token = None
        self.spotify = None

    def log_in(self):
        try:
            self.token = self.spotify_oauth.get_access_token(as_dict=False)
            self.spotify = spotipy.Spotify(auth=self.token)
            return True
        except Exception as e:
            print(f"Error during Spotify login: {e}")
            return False

    def get_current_song(self):
        if not self.spotify:
            return None
        try:
            current_playback = self.spotify.currently_playing()
            if current_playback and current_playback.get("item"):
                song_name = current_playback["item"]["name"]
                artist_name = current_playback["item"]["artists"][0]["name"]
                return f"{song_name} by {artist_name}"
            return None
        except Exception as e:
            print(f"Error fetching current song: {e}")
            return None
        
    def get_genre_from_spotify(self):
        """
        Fetch genre information for the currently playing song using Spotify API.
        """
        if not self.spotify:
            return None
        try:
            current_playback = self.spotify.currently_playing()
            if current_playback and current_playback.get("item"):
                artist_id = current_playback["item"]["artists"][0]["id"]
                artist_info = self.spotify.artist(artist_id)
                genres = artist_info.get("genres", [])
                return genres[0] if genres else "Unknown"
            return "Unknown"
        except Exception as e:
            print(f"Error fetching genre: {e}")
            return "Unknown"
