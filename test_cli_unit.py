import unittest
from unittest.mock import patch, MagicMock
import cli

class TestCli(unittest.TestCase):
    def setUp(self):
        print(f"\n[START] {self._testMethodName}")
        self.addCleanup(self._print_result)
        self._test_failed = False

    def _print_result(self):
        if self._test_failed:
            print(f"[FAIL]  {self._testMethodName}")
        else:
            print(f"[PASS]  {self._testMethodName}")

    def run(self, result=None):
        try:
            super().run(result)
        except Exception:
            self._test_failed = True
            raise
        if result and not result.wasSuccessful():
            self._test_failed = True

    def test_normalize_title(self):
        try:
            self.assertEqual(cli.normalize_title("The Matrix (1999)"), "thematrix")
            self.assertEqual(cli.normalize_title("Star Wars: A New Hope (1977)"), "starwarsanewhope")
            self.assertEqual(cli.normalize_title("Spider-Man & Mary Jane"), "spidermanandmaryjane")
        except Exception:
            self._test_failed = True
            raise

    def test_find_best_match_exact(self):
        try:
            candidates = ["The Matrix (1999)", "Star Wars: A New Hope (1977)", "Spider-Man & Mary Jane"]
            self.assertEqual(cli.find_best_match("The Matrix (1999)", candidates), "The Matrix (1999)")
        except Exception:
            self._test_failed = True
            raise

    def test_find_best_match_fuzzy(self):
        try:
            candidates = ["The Matrix (1999)", "Star Wars: A New Hope (1977)", "Spider-Man & Mary Jane"]
            self.assertEqual(cli.find_best_match("Matrix", candidates, threshold=60), "The Matrix (1999)")
        except Exception:
            self._test_failed = True
            raise

    def test_find_best_match_year(self):
        # Test find_best_match with year and candidate_years
        candidates = ["The Matrix (1999)", "Star Wars: A New Hope (1977)"]
        candidate_years = [1999, 1977]
        self.assertEqual(cli.find_best_match("The Matrix (1999)", candidates, year=1999, candidate_years=candidate_years), "The Matrix (1999)")
        self.assertIsNone(cli.find_best_match("The Matrix (1999)", candidates, year=2000, candidate_years=candidate_years))

    @patch("cli.plex_list_all_movies")
    @patch("cli.jellyfin_get_movies")
    def test_compare_titles_movies(self, mock_jellyfin_get_movies, mock_plex_list_all_movies):
        try:
            mock_plex_list_all_movies.return_value = [MagicMock(title="The Matrix (1999)", year=1999), MagicMock(title="Star Wars: A New Hope (1977)", year=1977)]
            mock_jellyfin_get_movies.return_value = [{"Name": "The Matrix (1999)", "ProductionYear": 1999}]
            cli.compare_titles("movies", "plex", "jellyfin", jellyfin_user_id="mockid", fuzzy=False)
        except Exception:
            self._test_failed = True
            raise

    def test_compare_titles_tv(self):
        # Test compare_titles for TV library, both plex and jellyfin as source/target
        with patch("cli.plex_list_all_shows") as mock_plex_list_all_shows, \
             patch("cli.jellyfin_get_tvshows") as mock_jellyfin_get_tvshows:
            mock_plex_list_all_shows.return_value = [MagicMock(title="The Matrix (1999)", year=1999), MagicMock(title="Star Wars: A New Hope (1977)", year=1977)]
            mock_jellyfin_get_tvshows.return_value = [{"Name": "The Matrix (1999)", "ProductionYear": 1999}]
            # plex -> jellyfin
            cli.compare_titles("tv", "plex", "jellyfin", jellyfin_user_id="mockid", fuzzy=False)
            # jellyfin -> plex
            cli.compare_titles("tv", "jellyfin", "plex", jellyfin_user_id="mockid", fuzzy=False)
            # invalid library
            cli.compare_titles("invalid", "plex", "jellyfin", jellyfin_user_id="mockid", fuzzy=False)

    def test_get_show_folder_from_episode(self):
        try:
            self.assertIn("ShowName", cli.get_show_folder_from_episode("/media/TV/ShowName/Season 01/Episode1.mkv"))
            self.assertIn("ShowName", cli.get_show_folder_from_episode("/media/TV/ShowName/Episode1.mkv"))
        except Exception:
            self._test_failed = True
            raise

    def test_get_show_folder_from_episode_variants(self):
        # Test more path variants for get_show_folder_from_episode
        self.assertIn("ShowName", cli.get_show_folder_from_episode("/media/TV/ShowName/S01/Episode1.mkv"))
        self.assertIn("ShowName", cli.get_show_folder_from_episode("/media/TV/ShowName/Season1/Episode1.mkv"))
        self.assertIn("ShowName", cli.get_show_folder_from_episode("/media/TV/ShowName/S1/Episode1.mkv"))

    @patch("cli.csv.writer")
    def test_print_with_path(self, mock_writer):
        try:
            items = [MagicMock(title="Spider-Man & Mary Jane", media=[MagicMock(parts=[MagicMock(file="/path/to/spiderman.mkv")])])]
            cli.print_with_path(items, "plex", "movies")
        except Exception:
            self._test_failed = True
            raise

    @patch("cli.csv.writer")
    def test_print_with_path_csv(self, mock_writer):
        # Test print_with_path with export_csv
        items = [MagicMock(title="Spider-Man & Mary Jane", media=[MagicMock(parts=[MagicMock(file="/path/to/spiderman.mkv")])])]
        cli.print_with_path(items, "plex", "movies", export_csv="dummy.csv")
        mock_writer.assert_called()

    def test_print_with_path_tv(self):
        # Test print_with_path for TV library for both plex and jellyfin
        with patch("cli.jellyfin_get_episodes") as mock_jellyfin_get_episodes:
            # Plex TV
            episode = MagicMock()
            episode.media = [MagicMock(parts=[MagicMock(file="/media/TV/ShowName/Season 01/Episode1.mkv")])]
            show = MagicMock(title="ShowName", episodes=MagicMock(return_value=[episode]))
            cli.print_with_path([show], "plex", "tv")
            # Jellyfin TV
            mock_jellyfin_get_episodes.return_value = [{"Path": "/media/TV/ShowName/Season 01/Episode1.mkv"}]
            cli.print_with_path([{"Name": "ShowName", "Id": "id1"}], "jellyfin", "tv", jellyfin_user_id="mockid")
            # Invalid server/library
            cli.print_with_path([show], "invalid", "invalid")

    @patch("cli.plex_list_all_movies")
    @patch("cli.plex_list_all_shows")
    @patch("cli.jellyfin_get_movies")
    @patch("cli.jellyfin_get_tvshows")
    @patch("cli.jellyfin_get_episodes")
    def test_list_duplicates(self, mock_get_episodes, mock_get_tvshows, mock_get_movies, mock_list_all_shows, mock_list_all_movies):
        try:
            movie = MagicMock(title="The Matrix (1999)", media=[1,2])
            mock_list_all_movies.return_value = [movie]
            cli.list_duplicates("movies", "plex")
            episode = MagicMock(title="Star Wars: A New Hope (1977)", media=[1,2], seasonNumber=1, index=1)
            show = MagicMock(title="Spider-Man & Mary Jane", episodes=MagicMock(return_value=[episode]))
            mock_list_all_shows.return_value = [show]
            cli.list_duplicates("tv", "plex")
            mock_get_movies.return_value = [{"Name": "The Matrix (1999)", "MediaSources": [1,2]}]
            cli.list_duplicates("movies", "jellyfin", jellyfin_user_id="mockid")
            mock_get_tvshows.return_value = [{"Name": "Spider-Man & Mary Jane", "Id": "id2"}]
            mock_get_episodes.return_value = [{"Name": "Star Wars: A New Hope (1977)", "MediaSources": [1,2]}]
            cli.list_duplicates("tv", "jellyfin", jellyfin_user_id="mockid")
        except Exception:
            self._test_failed = True
            raise

if __name__ == "__main__":
    print("Starting CLI unit tests...")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestCli)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print(f"\nSummary: {result.testsRun} run, {len(result.failures)} failed, {len(result.errors)} errors.")
    if result.wasSuccessful():
        print("All tests passed!\n")
    else:
        print("Some tests failed. See output above.\n")
