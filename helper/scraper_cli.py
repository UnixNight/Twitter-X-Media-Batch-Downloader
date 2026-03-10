#!/usr/bin/env python3
"""
Standalone CLI scraper that uses the same database and folder structure as the app.
Uses the embedded extractor.exe (gallery-dl) to extract tweets and downloads media to organized folders.

Usage:
    python scraper_cli.py <username> [options]

Examples:
    # Fetch timeline with auth token
    python scraper_cli.py uzsgsg --auth-token YOUR_TOKEN --download

    # Fetch bookmarks
    python scraper_cli.py @username --type bookmarks --auth-token TOKEN

    # Fetch with specific media type
    python scraper_cli.py @username --media-type photo --download
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

# Database location - same as the app
APP_DATA_HOME = Path.home() / ".twitterxmediabatchdownloader"
DB_PATH = APP_DATA_HOME / "accounts.db"
EXTRACTOR_PATH = APP_DATA_HOME / "extractor.exe"

@dataclass
class ScraperConfig:
    """Configuration for scraper operation."""
    username: str
    auth_token: Optional[str] = None
    media_type: str = "all"  # all, photo, video
    fetch_type: str = "timeline"  # timeline, bookmarks, likes
    output_dir: Path = Path.home() / "Downloads" / "Twitter_Media"
    download: bool = False
    retweets: str = "skip"  # skip, include, original
    verbose: bool = False


def init_database():
    """Initialize the database with the same schema as the app."""
    APP_DATA_HOME.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create accounts table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            name TEXT,
            profile_image TEXT,
            total_media INTEGER DEFAULT 0,
            last_fetched DATETIME,
            response_json TEXT,
            group_name TEXT DEFAULT '',
            group_color TEXT DEFAULT '',
            media_type TEXT DEFAULT 'all',
            cursor TEXT DEFAULT '',
            completed INTEGER DEFAULT 1,
            UNIQUE(username, media_type)
        )
    ''')
    
    conn.commit()
    conn.close()


def build_request_url(config: ScraperConfig) -> str:
    """Build the appropriate gallery-dl URL for the request."""
    username = config.username.lstrip('@')
    
    if config.fetch_type == "timeline":
        return f"https://x.com/{username}/tweets"
    elif config.fetch_type == "bookmarks":
        return f"https://x.com/{username}/bookmarks"
    elif config.fetch_type == "likes":
        return f"https://x.com/{username}/likes"
    else:
        return f"https://x.com/{username}/tweets"


def build_extractor_args(config: ScraperConfig) -> List[str]:
    """Build command-line arguments for extractor.exe."""
    args = [build_request_url(config)]
    
    # Add auth token or guest mode
    if config.auth_token:
        args.extend(["--auth-token", config.auth_token])
    else:
        args.append("--guest")
    
    # Force JSON output with metadata
    args.extend(["--json", "--metadata"])
    
    # Handle retweets
    if config.retweets != "skip":
        args.extend(["--retweets", "include" if config.retweets == "include" else "original"])
    else:
        args.extend(["--retweets", "skip"])
    
    # Handle media type filter
    if config.media_type != "all":
        args.extend(["--type", config.media_type])
    
    return args


def download_media(media_items: List[Dict], config: ScraperConfig, username: str) -> tuple[int, int, int]:
    """Download media files. Returns (downloaded, skipped, failed)."""
    if not config.download:
        print(f"Found {len(media_items)} media items. Use --download to download.")
        return 0, 0, 0
    
    # Create output directory structure: base/username/
    user_output_dir = config.output_dir / username.lstrip('@')
    user_output_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded = 0
    skipped = 0
    failed = 0
    
    print(f"\nDownloading to: {user_output_dir}")
    
    for idx, item in enumerate(media_items, 1):
        url = item.get("url")
        if not url:
            skipped += 1
            continue
        
        # Extract filename from URL
        path = urlparse(url).path
        filename = path.split('/')[-1]
        if not filename:
            filename = f"media_{idx}"
        
        filepath = user_output_dir / filename
        
        # Skip if already exists
        if filepath.exists():
            skipped += 1
            if config.verbose:
                print(f"  [{idx}/{len(media_items)}] SKIP {filename}")
            continue
        
        try:
            # Download with urllib
            urllib.request.urlretrieve(url, filepath)
            downloaded += 1
            if config.verbose:
                print(f"  [{idx}/{len(media_items)}] OK   {filename}")
        except Exception as e:
            failed += 1
            print(f"  [{idx}/{len(media_items)}] FAIL {filename}: {e}", file=sys.stderr)
    
    return downloaded, skipped, failed


def save_to_database(config: ScraperConfig, result, request_username: str):
    """Save results to the app's database."""
    init_database()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Build response JSON from result
    response_data = {
        "media": result.media,
        "metadata": result.metadata,
        "total": result.total,
        "completed": result.completed,
    }
    
    username = request_username.lstrip('@')
    
    # Try to insert or update
    try:
        cursor.execute('''
            INSERT INTO accounts (username, total_media, last_fetched, response_json, media_type, cursor, completed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            username,
            result.total,
            datetime.now().isoformat(),
            json.dumps(response_data),
            config.media_type,
            result.cursor or "",
            1 if result.completed else 0,
        ))
    except sqlite3.IntegrityError:
        # Update existing record
        cursor.execute('''
            UPDATE accounts 
            SET total_media = ?, last_fetched = ?, response_json = ?, cursor = ?, completed = ?
            WHERE username = ? AND media_type = ?
        ''', (
            result.total,
            datetime.now().isoformat(),
            json.dumps(response_data),
            result.cursor or "",
            1 if result.completed else 0,
            username,
            config.media_type,
        ))
    
    conn.commit()
    conn.close()
    print(f"✓ Saved to database: {username} ({result.total} media items)")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="CLI Twitter/X media scraper using the app's database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch timeline and save to database
  python scraper_cli.py uzsgsg --auth-token YOUR_TOKEN

  # Fetch timeline, download media, and save to database
  python scraper_cli.py uzsgsg --auth-token YOUR_TOKEN --download

  # Fetch bookmarks
  python scraper_cli.py @username --type bookmarks --auth-token TOKEN --download

  # Fetch with custom output directory
  python scraper_cli.py @username --download --output-dir "C:\\My Downloads"

  # Fetch photo-only with verbose output
  python scraper_cli.py @username --media-type photo --verbose --download
        """,
    )
    
    parser.add_argument("username", help="Twitter/X username (with or without @)")
    
    parser.add_argument("--auth-token", help="auth_token cookie value (required for private accounts)")
    parser.add_argument("--type", choices=["timeline", "bookmarks", "likes"], default="timeline",
                       help="Type of content to fetch (default: timeline)")
    parser.add_argument("--media-type", choices=["all", "photo", "video"], default="all",
                       help="Filter by media type (default: all)")
    parser.add_argument("--retweets", choices=["skip", "include", "original"], default="skip",
                       help="Control retweet handling (default: skip)")
    parser.add_argument("--download", action="store_true", help="Download media files")
    parser.add_argument("--output-dir", type=Path, help="Download directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Verify extractor exists
    if not EXTRACTOR_PATH.exists():
        print(f"Error: Extractor not found at {EXTRACTOR_PATH}", file=sys.stderr)
        print("Run the app once to extract the embedded binary, or copy extractor.exe manually", file=sys.stderr)
        sys.exit(1)
    
    # Build config
    config = ScraperConfig(
        username=args.username,
        auth_token=args.auth_token,
        media_type=args.media_type,
        fetch_type=args.type,
        output_dir=args.output_dir or (Path.home() / "Downloads" / "Twitter_Media"),
        download=args.download,
        retweets=args.retweets,
        verbose=args.verbose,
    )
    
    # Verify auth token if trying to access private content
    if not config.auth_token and config.fetch_type in ("likes", "bookmarks"):
        print("Error: --auth-token is required for likes and bookmarks", file=sys.stderr)
        sys.exit(1)
    
    print(f"Fetching {config.fetch_type} from {args.username}...")
    if config.auth_token:
        print("  (using auth_token)")
    else:
        print("  (guest mode - may be limited)")
    
    # Build extractor command
    extractor_args = build_extractor_args(config)
    
    # Run extractor
    try:
        result = subprocess.run(
            [str(EXTRACTOR_PATH)] + extractor_args,
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if result.returncode != 0:
            print(f"✗ Extractor error: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        
        # Parse JSON output
        output_data = json.loads(result.stdout)
        media_items = output_data.get("media", [])
        metadata = output_data.get("metadata", [])
        total = output_data.get("total", len(media_items))
        completed = output_data.get("completed", True)
        cursor = output_data.get("cursor")
        
        print(f"✓ Fetched {total} media items")
        if not completed:
            print(f"  (incomplete - cursor available for resume)")
            
    except subprocess.TimeoutExpired:
        print("✗ Extractor timed out", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print("✗ Failed to parse extractor output as JSON", file=sys.stderr)
        if result.stderr:
            print(f"Stderr: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n✗ Interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Download if requested
    if config.download and media_items:
        print(f"\nDownloading {len(media_items)} media files...")
        downloaded, skipped, failed = download_media(media_items, config, args.username)
        print(f"\nDownload Summary:")
        print(f"  Downloaded: {downloaded}")
        if skipped:
            print(f"  Skipped (already exist): {skipped}")
        if failed:
            print(f"  Failed: {failed}")
    
    # Save to database
    print()
    
    # Build result object to save
    class Result:
        def __init__(self, media, metadata, total, completed, cursor):
            self.media = media
            self.metadata = metadata
            self.total = total
            self.completed = completed
            self.cursor = cursor
    
    result = Result(media_items, metadata, total, completed, cursor)
    save_to_database(config, result, args.username)
    
    # Output results
    if args.json:
        output = {
            "username": args.username,
            "fetch_type": config.fetch_type,
            "media_type": config.media_type,
            "total": total,
            "media": media_items,
            "completed": completed,
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        print(f"\n✓ Done! {total} media items from {args.username}")
        if completed:
            print("  (fetch completed)")
        else:
            print("  (fetch incomplete - you can resume)")


if __name__ == "__main__":
    main()
