import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class SpotifyIntegration:
    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
        self.scope = "user-read-playback-state user-read-currently-playing"
        self.sp = self.authenticate()

    def authenticate(self):
        """
        Authenticate the user with Spotify and return a Spotipy client instance.
        """
        try:
            sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=self.scope
            ))
            return sp
        except Exception as e:
            print(f"Spotify authentication failed: {e}")
            return None

    def get_current_song(self):
        """
        Fetch the currently playing song on Spotify.
        """
        if self.sp is None:
            print("Spotify authentication not initialized.")
            return None

        try:
            current_track = self.sp.currently_playing()
            if current_track and current_track["is_playing"]:
                track_name = current_track["item"]["name"]
                artists = ", ".join(artist["name"] for artist in current_track["item"]["artists"])
                return f"{track_name} by {artists}"
            else:
                return "No song is currently playing."
        except Exception as e:
            print(f"Failed to fetch currently playing track: {e}")
            return None
