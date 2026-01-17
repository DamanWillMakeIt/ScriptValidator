import requests
import json
from app.core.config import settings

class ResearchService:
    def search_videos(self, query: str):
        """
        Searches Google Videos.
        FALLBACK: If no API key is found, returns MOCK DATA for testing.
        """
        # --- MOCK MODE (For Testing/Demo) ---
        if not settings.SERPER_API_KEY:
            print("⚠️ DEV MODE: No Serper Key found. Returning Mock Data.")
            return [
                {
                    "title": f"How to Master {query} in 10 Minutes",
                    "link": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                    "channel": "Viral Academy"
                },
                {
                    "title": f"Top 5 Mistakes Beginners Make with {query}",
                    "link": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                    "channel": "Pro Creator Hub"
                },
                {
                    "title": f"The Ultimate Guide to {query} (2026 Updated)",
                    "link": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                    "channel": "Tech Explainers"
                }
            ]

        # --- REAL MODE (Production) ---
        url = "https://google.serper.dev/videos"
        payload = json.dumps({
            "q": f"{query} youtube",
            "num": 3 
        })
        
        headers = {
            'X-API-KEY': settings.SERPER_API_KEY,
            'Content-Type': 'application/json'
        }

        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            results = response.json().get("videos", [])
            
            cleaned_results = []
            for vid in results:
                cleaned_results.append({
                    "title": vid.get("title"),
                    "link": vid.get("link"),
                    "thumbnail": vid.get("imageUrl"),
                    "channel": vid.get("channel")
                })
            return cleaned_results
            
        except Exception as e:
            print(f"Search Error: {e}")
            return []