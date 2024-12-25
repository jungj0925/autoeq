import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import pickle
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
        self.token_info = None
        self.spotify = None

        # Load trained genre model
        with open("./genre/genre_model.pkl", "rb") as file:
            self.genre_model = pickle.load(file)

    def log_in(self):
        """Log in to Spotify and initialize the Spotify client."""
        try:
            self.token_info = self.spotify_oauth.get_access_token(as_dict=True)
            self.spotify = spotipy.Spotify(auth=self.token_info["access_token"])
            return True
        except Exception as e:
            print(f"Error during Spotify login: {e}")
            return False

    def refresh_token(self):
        """Refresh the access token if expired."""
        try:
            if self.spotify_oauth.is_token_expired(self.token_info):
                print("Refreshing Spotify access token...")
                self.token_info = self.spotify_oauth.refresh_access_token(self.token_info["refresh_token"])
                self.spotify = spotipy.Spotify(auth=self.token_info["access_token"])
                print("Spotify access token refreshed.")
        except Exception as e:
            print(f"Error refreshing token: {e}")

    def get_current_song(self):
        """Fetch the current song title and artist."""
        if not self.spotify:
            return None
        try:
            self.refresh_token()  # Ensure the token is fresh before making API calls
            current_playback = self.spotify.currently_playing()
            if current_playback and current_playback.get("item"):
                song_name = current_playback["item"]["name"]
                artist_name = current_playback["item"]["artists"][0]["name"]
                return f"{song_name} by {artist_name}"
            return None
        except Exception as e:
            print(f"Error fetching current song: {e}")
            return None

    def get_genres_for_song(self):
        """Fetch genre information for the currently playing song using Spotify API."""
        if not self.spotify:
            return []
        try:
            self.refresh_token()  # Ensure the token is fresh before making API calls
            current_playback = self.spotify.currently_playing()
            if current_playback and current_playback.get("item"):
                artist_id = current_playback["item"]["artists"][0]["id"]
                artist_info = self.spotify.artist(artist_id)
                genres = artist_info.get("genres", [])
                return genres
            return []
        except Exception as e:
            print(f"Error fetching genres: {e}")
            return []

    def predict_broad_genre(self, sub_genres):
        """Predict the broad genre using the trained model based on sub-genres."""
        if not sub_genres:
            return "Unknown"
        try:
            combined_text = " ".join(sub_genres)
            return self.genre_model.predict([combined_text])[0]
        except Exception as e:
            print(f"Error predicting broad genre: {e}")
            return "Unknown"
