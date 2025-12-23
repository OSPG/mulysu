#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from functools import cmp_to_key

DB_FILE = "db.json"


@dataclass
class Resource:
    """Represents a resource (video, lyrics, etc.)"""
    type: str
    url: str
    language: str
    votes: int = 0
    content: Optional[str] = None


@dataclass
class Song:
    """Represents a song entry"""
    artist: str
    song: str
    artist_original: str
    song_original: str
    resources: List[Resource] = field(default_factory=list)


class SongDatabase:
    """Main database manager class"""
    
    def __init__(self):
        self.songs: List[Song] = []
        self.load()
    
    def load(self) -> None:
        """Load database from file"""
        if not os.path.exists(DB_FILE):
            self.save()
            return
        
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.songs = []
            for song_data in data:
                resources = [
                    Resource(**res) for res in song_data.get('resources', [])
                ]
                song = Song(
                    artist=song_data['artist'],
                    song=song_data['song'],
                    artist_original=song_data['artist_original'],
                    song_original=song_data['song_original'],
                    resources=resources
                )
                self.songs.append(song)
                
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading database: {e}")
            self.songs = []
    
    def save(self) -> None:
        """Save database to file"""
        data = []
        for song in self.songs:
            song_dict = asdict(song)
            # Convert resources
            song_dict['resources'] = [
                asdict(resource) for resource in song.resources
            ]
            data.append(song_dict)
        
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _sort_resources(self, resources: List[Resource]) -> List[Resource]:
        """Sort resources by votes (descending), then by type"""
        def compare(r1: Resource, r2: Resource) -> int:
            # First by votes (descending)
            if r1.votes != r2.votes:
                return r2.votes - r1.votes
            # Then by type alphabetically
            return (r1.type > r2.type) - (r1.type < r2.type)
        
        return sorted(resources, key=cmp_to_key(compare))
    
    def search(self, query: str) -> List[Song]:
        """Search for songs matching query"""
        query = query.lower()
        results = []
        
        for song in self.songs:
            if (query in song.artist.lower() or 
                query in song.song.lower() or 
                query in song.artist_original.lower() or
                query in song.song_original.lower()):
                results.append(song)
        
        return results
    
    def add_song(self) -> None:
        """Add a new song interactively"""
        print("\n=== Add New Song ===")
        
        artist = input("Artist name: ").strip()
        if not artist:
            print("Artist name is required.")
            return
        
        artist_original = input(f"Original artist name [{artist}]: ").strip() or artist
        song_name = input("Song name: ").strip()
        if not song_name:
            print("Song name is required.")
            return
        
        song_original = input(f"Original song name [{song_name}]: ").strip() or song_name
        
        resources = []
        while True:
            if input("\nAdd a resource? (y/n): ").lower() != 'y':
                break
            
            print("\n--- New Resource ---")
            res_type = input("Type (e.g., vid.subs, vid.lyrics): ").strip()
            url = input("URL: ").strip()
            language = input("Language code (en/es/ja/etc) [en]: ").strip() or "en"
            
            content = input("Content/notes (optional, press Enter to skip): ").strip()
            if not content:
                content = None
            
            resources.append(Resource(
                type=res_type,
                url=url,
                language=language,
                content=content,
                votes=0
            ))
            print("Resource added.")
        
        new_song = Song(
            artist=artist,
            song=song_name,
            artist_original=artist_original,
            song_original=song_original,
            resources=resources
        )
        
        self.songs.append(new_song)
        self.save()
        print(f"\n✓ Song '{song_name}' by '{artist}' has been added.")
    
    def display_song(self, song: Song, index: Optional[int] = None) -> None:
        """Display a single song with its resources"""
        prefix = f"{index}. " if index is not None else ""
        print(f"\n{prefix}{song.artist} - {song.song}")
        
        if song.song_original != song.song:
            print(f"   Original: {song.song_original}")
        
        if song.resources:
            sorted_resources = self._sort_resources(song.resources)
            print("   Resources (sorted by votes):")
            
            for i, resource in enumerate(sorted_resources, 1):
                vote_str = f"▲ {resource.votes}" if resource.votes > 0 else ""
                print(f"     {i}. [{resource.type}] {resource.language} {vote_str}")
                print(f"         URL: {resource.url}")
                if resource.content:
                    content = resource.content
                    if len(content) > 60:
                        content = content[:57] + "..."
                    print(f"         Content: {content}")
        else:
            print("   No resources available")
    
    def display_search_results(self, results: List[Song]) -> None:
        """Display search results"""
        if not results:
            print("No matches found.")
            return
        
        print(f"\nFound {len(results)} result(s):")
        for i, song in enumerate(results, 1):
            self.display_song(song, i)
    
    def vote_on_resource(self) -> None:
        """Vote on a specific resource"""
        if not self.songs:
            print("Database is empty.")
            return
        
        query = input("Search for song to vote on: ").strip().lower()
        if not query:
            return
        
        results = self.search(query)
        if not results:
            print("No matches found.")
            return
        
        print(f"\nFound {len(results)} result(s):")
        for i, song in enumerate(results, 1):
            print(f"{i}. {song.artist} - {song.song}")
        
        try:
            song_choice = int(input("\nSelect song number: ")) - 1
            if not (0 <= song_choice < len(results)):
                print("Invalid selection.")
                return
            
            selected_song = results[song_choice]
            
            # Find the actual song in database (not the search result copy)
            for i, song in enumerate(self.songs):
                if (song.artist == selected_song.artist and 
                    song.song == selected_song.song):
                    
                    if not song.resources:
                        print("This song has no resources.")
                        return
                    
                    # Display sorted resources
                    sorted_resources = self._sort_resources(song.resources)
                    print(f"\nResources for '{song.song}':")
                    for j, resource in enumerate(sorted_resources, 1):
                        vote_str = f"▲ {resource.votes}" if resource.votes > 0 else ""
                        print(f"  {j}. {resource.type} ({resource.language}) {vote_str}")
                    
                    # Get resource choice
                    resource_choice = int(input("Select resource to upvote: ")) - 1
                    if not (0 <= resource_choice < len(sorted_resources)):
                        print("Invalid selection.")
                        return
                    
                    # Find the actual resource in the original list
                    selected_resource = sorted_resources[resource_choice]
                    for k, resource in enumerate(song.resources):
                        if (resource.type == selected_resource.type and 
                            resource.url == selected_resource.url):
                            
                            song.resources[k].votes += 1
                            self.save()
                            print(f"\n✓ Vote added! Now has {song.resources[k].votes} votes.")
                            return
            
        except ValueError:
            print("Please enter a valid number.")
    
    def list_all(self) -> None:
        """List all songs in the database"""
        if not self.songs:
            print("Database is empty.")
            return
        
        print(f"\n=== All Songs ({len(self.songs)} total) ===")
        for i, song in enumerate(self.songs, 1):
            print(f"\n{i}. {song.artist} - {song.song}")
            if song.song_original != song.song:
                print(f"   Original: {song.song_original}")
            
            if song.resources:
                sorted_resources = self._sort_resources(song.resources)
                total_votes = sum(r.votes for r in song.resources)
                print(f"   Resources: {len(song.resources)} (Total votes: {total_votes})")
                # Show top 2 resources
                for j, resource in enumerate(sorted_resources[:2], 1):
                    vote_str = f"▲ {resource.votes}" if resource.votes > 0 else ""
                    print(f"     {j}. {resource.type} ({resource.language}) {vote_str}")


def main():
    """Main program loop"""
    print("🎵 Song Database Manager")
    print("Using dataclasses with full UTF-8 support")
    
    db = SongDatabase()
    
    while True:
        try:
            print("\nOptions:")
            print("  1. Search songs")
            print("  2. Add new song")
            print("  3. List all songs")
            print("  4. Vote on resource")
            print("  5. Exit")
            
            choice = input("\nYour choice: ").strip()
            
            if choice == "1":
                query = input("Search for song or artist: ").strip()
                results = db.search(query)
                db.display_search_results(results)
            
            elif choice == "2":
                db.add_song()
            
            elif choice == "3":
                db.list_all()
            
            elif choice == "4":
                db.vote_on_resource()
            
            elif choice == "5":
                print("Goodbye!")
                break
            
            else:
                print("Invalid option. Please choose 1-5.")
        
        except KeyboardInterrupt:
            print("\n\nInterrupted. Use option 5 to exit properly.")
            continue
        except EOFError:
            print("\n\nExiting...")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram terminated by user.")
        sys.exit(0)
