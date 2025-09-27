
"""
USCF ID to Chess.com/Lichess Game Downloader
Complete implementation for automated chess game collection based on USCF ID
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import re
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PlayerProfile:
    uscf_id: str = ""
    full_name: str = ""
    first_name: str = ""
    last_name: str = ""
    state: str = ""
    rating: str = ""
    chesscom_username: str = ""
    lichess_username: str = ""

class USCFScraper:
    """Scrapes USCF database to extract player information"""

    def __init__(self):
        self.base_url = "http://www.uschess.org/msa"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_player_by_id(self, uscf_id: str) -> Optional[PlayerProfile]:
        """Get player information by USCF ID"""
        url = f"{self.base_url}/MbrDtlMain.php"
        params = {'12': uscf_id}  # USCF uses parameter '12' for member ID

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            return self._parse_player_details(soup, uscf_id)

        except Exception as e:
            logger.error(f"Error fetching USCF data for ID {uscf_id}: {e}")
            return None

    def search_player_by_name(self, first_name: str, last_name: str, state: str = None) -> List[PlayerProfile]:
        """Search for players by name"""
        url = f"{self.base_url}/MbrDtlMain.php"
        params = {
            'lastname': last_name,
            'firstname': first_name
        }
        if state:
            params['state'] = state

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            return self._parse_search_results(soup)

        except Exception as e:
            logger.error(f"Error searching USCF for {first_name} {last_name}: {e}")
            return []

    def _parse_player_details(self, soup: BeautifulSoup, uscf_id: str) -> Optional[PlayerProfile]:
        """Parse player details from USCF HTML response"""
        try:
            profile = PlayerProfile(uscf_id=uscf_id)

            # Extract name (typically in a table or header)
            name_element = soup.find('b') or soup.find('h1') or soup.find('h2')
            if name_element:
                full_name = name_element.get_text().strip()
                profile.full_name = full_name

                # Split name into first and last
                name_parts = full_name.split()
                if len(name_parts) >= 2:
                    profile.first_name = name_parts[0]
                    profile.last_name = name_parts[-1]

            # Extract rating (look for rating tables)
            rating_cells = soup.find_all('td')
            for cell in rating_cells:
                text = cell.get_text().strip()
                if text.isdigit() and len(text) == 4:  # USCF ratings are typically 4 digits
                    profile.rating = text
                    break

            # Extract state information
            state_pattern = re.compile(r'\b[A-Z]{2}\b')  # Two letter state codes
            page_text = soup.get_text()
            state_match = state_pattern.search(page_text)
            if state_match:
                profile.state = state_match.group()

            logger.info(f"Extracted USCF profile: {profile.full_name} (ID: {uscf_id})")
            return profile

        except Exception as e:
            logger.error(f"Error parsing USCF player details: {e}")
            return None

    def _parse_search_results(self, soup: BeautifulSoup) -> List[PlayerProfile]:
        """Parse multiple player results from search"""
        profiles = []

        # Look for table rows or list items containing player information
        rows = soup.find_all('tr') + soup.find_all('li')

        for row in rows:
            text = row.get_text().strip()
            # Look for patterns like "Name (ID: 12345)"
            id_match = re.search(r'ID:\s*(\d+)', text)
            if id_match:
                uscf_id = id_match.group(1)
                profile = PlayerProfile(uscf_id=uscf_id)

                # Extract name from the same text
                name_match = re.search(r'^([A-Za-z\s]+)', text)
                if name_match:
                    profile.full_name = name_match.group(1).strip()

                profiles.append(profile)

        return profiles

class ChessComAPI:
    """Chess.com API integration for game downloads"""

    def __init__(self):
        self.base_url = "https://api.chess.com/pub"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'chess-analyzer/1.0 (contact: your-email@example.com)'
        })

    def search_player_by_name(self, full_name: str) -> List[str]:
        """Search for potential Chess.com usernames based on player name"""
        # Chess.com doesn't have a public search API, so we'll try common username patterns
        name_parts = full_name.lower().replace(" ", "").replace(".", "")
        first = full_name.split()[0].lower()
        last = full_name.split()[-1].lower()

        potential_usernames = [
            name_parts,
            f"{first}{last}",
            f"{first}_{last}",
            f"{first}-{last}",
            first,
            last,
            f"{first}{last[0]}",
            f"{first[0]}{last}",
            name_parts.replace(" ", "_"),
            name_parts.replace(" ", "-")
        ]

        found_usernames = []
        for username in potential_usernames:
            if self.check_user_exists(username):
                found_usernames.append(username)
                logger.info(f"Found Chess.com user: {username}")

        return found_usernames

    def check_user_exists(self, username: str) -> bool:
        """Check if a Chess.com username exists"""
        try:
            url = f"{self.base_url}/player/{username}"
            response = self.session.get(url)
            return response.status_code == 200
        except:
            return False

    def get_player_profile(self, username: str) -> Optional[Dict]:
        """Get Chess.com player profile"""
        try:
            url = f"{self.base_url}/player/{username}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting Chess.com profile for {username}: {e}")
            return None

    def download_all_games(self, username: str, max_months: int = 12) -> List[str]:
        """Download PGN games for a Chess.com user"""
        try:
            # Get list of available archives
            archives_url = f"{self.base_url}/player/{username}/games/archives"
            response = self.session.get(archives_url)
            response.raise_for_status()

            archives = response.json().get('archives', [])
            all_pgn_data = []

            # Limit to recent months to avoid overwhelming the API
            recent_archives = archives[-max_months:] if len(archives) > max_months else archives

            for archive_url in recent_archives:
                pgn_url = archive_url + "/pgn"
                time.sleep(1)  # Rate limiting

                try:
                    pgn_response = self.session.get(pgn_url)
                    pgn_response.raise_for_status()

                    if pgn_response.text.strip():
                        all_pgn_data.append(pgn_response.text)
                        logger.info(f"Downloaded games from {archive_url}")

                except Exception as e:
                    logger.warning(f"Failed to download from {archive_url}: {e}")
                    continue

            return all_pgn_data

        except Exception as e:
            logger.error(f"Error downloading Chess.com games for {username}: {e}")
            return []

class LichessAPI:
    """Lichess API integration for game downloads"""

    def __init__(self, api_token: str = None):
        self.base_url = "https://lichess.org/api"
        self.session = requests.Session()

        headers = {'User-Agent': 'chess-analyzer/1.0'}
        if api_token:
            headers['Authorization'] = f'Bearer {api_token}'

        self.session.headers.update(headers)

    def search_player_by_name(self, full_name: str) -> List[str]:
        """Search for potential Lichess usernames based on player name"""
        # Similar to Chess.com, generate potential usernames
        name_parts = full_name.lower().replace(" ", "").replace(".", "")
        first = full_name.split()[0].lower()
        last = full_name.split()[-1].lower()

        potential_usernames = [
            name_parts,
            f"{first}{last}",
            f"{first}_{last}",
            f"{first}-{last}",
            first,
            last,
            f"{first}{last[0]}",
            f"{first[0]}{last}",
        ]

        found_usernames = []
        for username in potential_usernames:
            if self.check_user_exists(username):
                found_usernames.append(username)
                logger.info(f"Found Lichess user: {username}")

        return found_usernames

    def check_user_exists(self, username: str) -> bool:
        """Check if a Lichess username exists"""
        try:
            url = f"{self.base_url}/user/{username}"
            response = self.session.get(url)
            return response.status_code == 200
        except:
            return False

    def get_player_profile(self, username: str) -> Optional[Dict]:
        """Get Lichess player profile"""
        try:
            url = f"{self.base_url}/user/{username}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting Lichess profile for {username}: {e}")
            return None

    def download_user_games(self, username: str, max_games: int = 1000) -> str:
        """Download PGN games for a Lichess user"""
        try:
            url = f"{self.base_url}/games/user/{username}"
            params = {
                'format': 'pgn',
                'max': min(max_games, 5000),  # Lichess API limit
                'clocks': 'true',
                'opening': 'true'
            }

            response = self.session.get(url, params=params, stream=True)
            response.raise_for_status()

            pgn_data = ""
            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                pgn_data += chunk

            logger.info(f"Downloaded {max_games} games for Lichess user {username}")
            return pgn_data

        except Exception as e:
            logger.error(f"Error downloading Lichess games for {username}: {e}")
            return ""

class PlayerMatcher:
    """Matches players across different chess platforms using fuzzy matching"""

    def __init__(self):
        self.name_similarity_threshold = 80
        self.rating_tolerance = 200

    def find_best_username_match(self, target_name: str, candidate_usernames: List[str], 
                                platform_profiles: Dict[str, Dict]) -> Optional[str]:
        """Find the best matching username based on name similarity and profile data"""

        best_match = None
        best_score = 0

        for username in candidate_usernames:
            profile = platform_profiles.get(username, {})

            # Calculate name similarity score
            profile_name = profile.get('name', '') or profile.get('title', '') or username
            name_score = fuzz.token_sort_ratio(target_name.lower(), profile_name.lower())

            # Boost score if the profile seems legitimate (has games, reasonable join date, etc.)
            legitimacy_bonus = 0
            if profile.get('count', {}).get('all', 0) > 10:  # Has played games
                legitimacy_bonus += 10

            total_score = name_score + legitimacy_bonus

            if total_score > best_score and name_score >= self.name_similarity_threshold:
                best_score = total_score
                best_match = username

        return best_match

    def verify_rating_compatibility(self, uscf_rating: str, platform_rating: int) -> bool:
        """Check if USCF and platform ratings are compatible"""
        if not uscf_rating or not uscf_rating.isdigit():
            return True  # Can't verify, assume compatible

        uscf_int = int(uscf_rating)
        # Allow for rating differences between platforms
        return abs(uscf_int - platform_rating) <= self.rating_tolerance

class USCFToGameDownloader:
    """Main class that orchestrates the entire process"""

    def __init__(self, lichess_token: str = None):
        self.uscf_scraper = USCFScraper()
        self.chesscom_api = ChessComAPI()
        self.lichess_api = LichessAPI(lichess_token)
        self.matcher = PlayerMatcher()

    def download_games_by_uscf_id(self, uscf_id: str, output_dir: str = "games") -> Dict:
        """Main method: Download games from all platforms based on USCF ID"""

        logger.info(f"Starting game collection for USCF ID: {uscf_id}")

        # Step 1: Get player information from USCF
        uscf_profile = self.uscf_scraper.get_player_by_id(uscf_id)
        if not uscf_profile or not uscf_profile.full_name:
            logger.error(f"Could not find USCF player with ID {uscf_id}")
            return {"error": "USCF player not found"}

        logger.info(f"Found USCF player: {uscf_profile.full_name}")

        result = {
            "uscf_profile": uscf_profile,
            "chesscom": {"found": False, "games": []},
            "lichess": {"found": False, "games": ""}
        }

        # Step 2: Search Chess.com
        try:
            chesscom_candidates = self.chesscom_api.search_player_by_name(uscf_profile.full_name)

            if chesscom_candidates:
                # Get profiles for all candidates
                chesscom_profiles = {}
                for username in chesscom_candidates:
                    profile = self.chesscom_api.get_player_profile(username)
                    if profile:
                        chesscom_profiles[username] = profile

                # Find best match
                best_chesscom = self.matcher.find_best_username_match(
                    uscf_profile.full_name, chesscom_candidates, chesscom_profiles
                )

                if best_chesscom:
                    logger.info(f"Matched Chess.com username: {best_chesscom}")
                    uscf_profile.chesscom_username = best_chesscom

                    # Download games
                    games = self.chesscom_api.download_all_games(best_chesscom)
                    result["chesscom"] = {
                        "found": True,
                        "username": best_chesscom,
                        "games": games,
                        "profile": chesscom_profiles[best_chesscom]
                    }
        except Exception as e:
            logger.error(f"Error processing Chess.com: {e}")

        # Step 3: Search Lichess
        try:
            lichess_candidates = self.lichess_api.search_player_by_name(uscf_profile.full_name)

            if lichess_candidates:
                # Get profiles for all candidates
                lichess_profiles = {}
                for username in lichess_candidates:
                    profile = self.lichess_api.get_player_profile(username)
                    if profile:
                        lichess_profiles[username] = profile

                # Find best match
                best_lichess = self.matcher.find_best_username_match(
                    uscf_profile.full_name, lichess_candidates, lichess_profiles
                )

                if best_lichess:
                    logger.info(f"Matched Lichess username: {best_lichess}")
                    uscf_profile.lichess_username = best_lichess

                    # Download games
                    games = self.lichess_api.download_user_games(best_lichess)
                    result["lichess"] = {
                        "found": True,
                        "username": best_lichess,
                        "games": games,
                        "profile": lichess_profiles[best_lichess]
                    }
        except Exception as e:
            logger.error(f"Error processing Lichess: {e}")

        # Step 4: Save results
        self._save_results(result, uscf_id, output_dir)

        return result

    def _save_results(self, result: Dict, uscf_id: str, output_dir: str):
        """Save downloaded games and metadata to files"""
        import os

        os.makedirs(output_dir, exist_ok=True)

        # Save Chess.com games
        if result["chesscom"]["found"]:
            chesscom_file = os.path.join(output_dir, f"{uscf_id}_chesscom.pgn")
            with open(chesscom_file, 'w') as f:
                for game_batch in result["chesscom"]["games"]:
                    f.write(game_batch)
                    f.write('\n\n')
            logger.info(f"Saved Chess.com games to {chesscom_file}")

        # Save Lichess games
        if result["lichess"]["found"]:
            lichess_file = os.path.join(output_dir, f"{uscf_id}_lichess.pgn")
            with open(lichess_file, 'w') as f:
                f.write(result["lichess"]["games"])
            logger.info(f"Saved Lichess games to {lichess_file}")

        # Save metadata
        metadata_file = os.path.join(output_dir, f"{uscf_id}_metadata.json")
        metadata = {
            "uscf_id": uscf_id,
            "full_name": result["uscf_profile"].full_name,
            "chesscom_username": result["chesscom"].get("username"),
            "lichess_username": result["lichess"].get("username"),
            "chesscom_found": result["chesscom"]["found"],
            "lichess_found": result["lichess"]["found"]
        }

        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        logger.info(f"Saved metadata to {metadata_file}")

# Example usage and testing
def main():
    """Example usage of the USCF to game downloader"""

    # Initialize the downloader
    downloader = USCFToGameDownloader(lichess_token=None)  # Add your Lichess token here

    # Example USCF ID (replace with actual ID)
    uscf_id = "12345678"  # Replace with actual USCF ID

    # Download games
    result = downloader.download_games_by_uscf_id(uscf_id)

    # Print summary
    print(f"\n=== Results for USCF ID {uscf_id} ===")
    print(f"Player Name: {result.get('uscf_profile', {}).full_name if 'uscf_profile' in result else 'Not found'}")

    if result["chesscom"]["found"]:
        print(f"Chess.com: Found user '{result['chesscom']['username']}' with {len(result['chesscom']['games'])} game archives")
    else:
        print("Chess.com: No matching user found")

    if result["lichess"]["found"]:
        game_count = len([g for g in result["lichess"]["games"].split("\n\n") if g.strip()])
        print(f"Lichess: Found user '{result['lichess']['username']}' with approximately {game_count} games")
    else:
        print("Lichess: No matching user found")

if __name__ == "__main__":
    main()
