import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Set up your Spotify API credentials
client_id = "cd953ad18fa846d78a1d77851c920653"  # Replace with your Client ID
client_secret = "0581d9e44f74437d8d2708f6ba92bb76"  # Replace with your Client Secret

# Authenticate using the Client Credentials Flow
auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

def get_artist_genre(artist_name):
    try:
        # Search for the artist
        results = sp.search(q=artist_name, type='artist', limit=1)
        if results['artists']['items']:
            artist = results['artists']['items'][0]
            artist_name = artist['name']
            genres = artist['genres']
            return f"Genres for {artist_name}: {', '.join(genres) if genres else 'No genres found'}"
        else:
            return "Artist not found."
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Example usage
artist_name = "Drake"
print(get_artist_genre(artist_name))
