import unittest
from unittest.mock import patch, MagicMock
import cli

class TestCli(unittest.TestCase):
    def test_normalize_title(self):
        print("Running: test_normalize_title")
        self.assertEqual(cli.normalize_title("The Matrix (1999)"), "thematrix")
        self.assertEqual(cli.normalize_title("Star Wars: A New Hope (1977)"), "starwarsanewhope")
        self.assertEqual(cli.normalize_title("Spider-Man & Mary Jane"), "spidermanandmaryjane")

    def test_find_best_match_exact(self):
        print("Running: test_find_best_match_exact")
        candidates = ["The Matrix", "Inception", "Interstellar"]
        self.assertEqual(cli.find_best_match("The Matrix", candidates), "The Matrix")

    def test_find_best_match_fuzzy(self):
        print("Running: test_find_best_match_fuzzy")
        candidates = ["The Matrix", "Inception", "Interstellar"]
        self.assertEqual(cli.find_best_match("Matrix", candidates, threshold=60), "The Matrix")

    @patch("cli.plex_list_all_movies")
    @patch("cli.jellyfin_get_movies")
    def test_compare_titles_movies(self, mock_jellyfin_get_movies, mock_plex_list_all_movies):
        print("Running: test_compare_titles_movies")
        mock_plex_list_all_movies.return_value = [MagicMock(title="Movie1", year=2020), MagicMock(title="Movie2", year=2021)]
        mock_jellyfin_get_movies.return_value = [{"Name": "Movie1", "ProductionYear": 2020}]
        cli.compare_titles("movies", "plex", "jellyfin", jellyfin_user_id="mockid", fuzzy=False)

    def test_get_show_folder_from_episode(self):
        print("Running: test_get_show_folder_from_episode")
        self.assertIn("ShowName", cli.get_show_folder_from_episode("/media/TV/ShowName/Season 01/Episode1.mkv"))
        self.assertIn("ShowName", cli.get_show_folder_from_episode("/media/TV/ShowName/Episode1.mkv"))

    @patch("cli.csv.writer")
    def test_print_with_path(self, mock_writer):
        print("Running: test_print_with_path")
        items = [MagicMock(title="Movie1", media=[MagicMock(parts=[MagicMock(file="/path/to/movie1.mkv")])])]
        cli.print_with_path(items, "plex", "movies")

    @patch("cli.plex_list_all_movies")
    @patch("cli.plex_list_all_shows")
    @patch("cli.jellyfin_get_movies")
    @patch("cli.jellyfin_get_tvshows")
    @patch("cli.jellyfin_get_episodes")
    def test_list_duplicates(self, mock_get_episodes, mock_get_tvshows, mock_get_movies, mock_list_all_shows, mock_list_all_movies):
        print("Running: test_list_duplicates")
        movie = MagicMock(title="Movie1", media=[1,2])
        mock_list_all_movies.return_value = [movie]
        cli.list_duplicates("movies", "plex")
        episode = MagicMock(title="Ep1", media=[1,2], seasonNumber=1, index=1)
        show = MagicMock(title="Show1", episodes=MagicMock(return_value=[episode]))
        mock_list_all_shows.return_value = [show]
        cli.list_duplicates("tv", "plex")
        mock_get_movies.return_value = [{"Name": "Movie2", "MediaSources": [1,2]}]
        cli.list_duplicates("movies", "jellyfin", jellyfin_user_id="mockid")
        mock_get_tvshows.return_value = [{"Name": "Show2", "Id": "id2"}]
        mock_get_episodes.return_value = [{"Name": "Ep2", "MediaSources": [1,2]}]
        cli.list_duplicates("tv", "jellyfin", jellyfin_user_id="mockid")

if __name__ == "__main__":
    print("Starting CLI unit tests...")
    unittest.main()
