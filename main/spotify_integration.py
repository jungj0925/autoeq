import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
import os
import pickle
import sys
from dotenv import load_dotenv

load_dotenv()

def get_resource_path(relative_path):
    """
    Get the absolute path to a resource, works for PyInstaller bundled environments.
    """
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller extracts resources to a temporary folder
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

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
        self.auth_manager = SpotifyClientCredentials(os.getenv("SPOTIFY_CLIENT_ID"), os.getenv("SPOTIFY_CLIENT_SECRET"))
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)

        # Load trained genre model
        with open(get_resource_path("./genre/genre_model.pkl"), "rb") as file:
            self.genre_model = pickle.load(file)

        # Automatically log in
        self.auto_log_in()

    def auto_log_in(self):
        """Automatically log in using stored token."""
        try:
            self.token = self.spotify_oauth.get_access_token(as_dict=False)
            self.spotify = spotipy.Spotify(auth=self.token)
        except Exception as e:
            print(f"Error during automatic login: {e}")

    def get_current_song(self):
        """Fetch the current song title and artist."""
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
        
    def get_genres_for_song(self, artist_name):
        """
        Fetch genre information for the currently playing song using Spotify API.
        """
        if not self.spotify:
            return []
        try:
            # Search for the artist
            results = self.sp.search(q=artist_name, type='artist', limit=1)
            if results['artists']['items']:
                artist = results['artists']['items'][0]
                artist_name = artist['name']
                genres = artist['genres']
                return genres
            else:
                return "Artist not found."
        except Exception as e:
            return f"An error occurred: {str(e)}"

    def predict_broad_genre(self, sub_genres):
        """
        Predict the broad genre using the trained model based on sub-genres.
        """
        if not sub_genres:
            return "Unknown"
        try:
            combined_text = " ".join(sub_genres)
            return self.genre_model.predict([combined_text])[0]
        except Exception as e:
            print(f"Error predicting broad genre: {e}")
            return "Unknown"
