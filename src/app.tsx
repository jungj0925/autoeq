interface SpotifyTrack {
  artists?: { uri: string }[];
}

async function main() {
  while (!Spicetify?.Platform) {
    await new Promise(resolve => setTimeout(resolve, 100));
  }

  Spicetify.Player.addEventListener("songchange", () => {
    // Correct way to access current track data
    const currentTrack = Spicetify.Player.data.item; // Changed from .track to .item
    if (currentTrack) {
      detectGenreAndSetEqualizer(currentTrack);
    }
  });
}

async function detectGenreAndSetEqualizer(track: SpotifyTrack) {
  try {
    // Get track metadata including artists
    const artistUri = track.artists?.[0].uri;
    const artistData = await Spicetify.Platform.getArtistData(artistUri);
    
    // Extract genres from artist data
    const genres = artistData?.genres || [];
    
    console.log(genres);
    if (genres.length > 0) {
      // Use the first genre as primary genre
      const primaryGenre = genres[0].toLowerCase();
      setEqualizerForGenre(primaryGenre);
    } else {
      // Fallback to default equalizer settings if no genre is found
      setEqualizerForGenre('default');
    }
  } catch (error) {
    console.error('Error detecting genre:', error);
    setEqualizerForGenre('default');
  }
}

function setEqualizerForGenre(genre: string) {
  // Define equalizer presets for different genres
  const presets = {
    rock: [4, 3, 2, 0, -1, -1, 2, 3, 3, 4],
    electronic: [4, 3, 1, 0, -2, -2, 0, 2, 4, 5],
    classical: [0, 0, 0, 0, 0, 0, -2, -3, -3, -4],
    jazz: [2, 1, 0, 1, 2, -1, -2, -1, 1, 2],
    hiphop: [5, 4, 2, 1, -1, -1, 2, 1, 2, 3],
    default: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
  } as const;

  const eqSettings = presets[genre as keyof typeof presets] || presets.default;

  // Apply equalizer settings using Spicetify API
  try {
    // Assuming Spicetify provides an API to adjust equalizer
    // This is a placeholder - actual implementation would depend on Spicetify's equalizer API
    Spicetify.Platform.PlaybackAPI.setEqualizer(eqSettings);
  } catch (error) {
    console.error('Error setting equalizer:', error);
  }
}
