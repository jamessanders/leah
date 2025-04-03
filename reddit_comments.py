#!/usr/bin/env python3

"""
Reddit Comments Viewer - A script to fetch and display top comments from a Reddit post.
Usage: python reddit_comments.py <post_url>
"""

import sys
import json
import urllib.request
from urllib.parse import urlparse
from urllib.error import URLError, HTTPError

def get_post_id(url):
    """Extract the post ID from a Reddit URL."""
    # Parse the URL
    parsed = urlparse(url)
    
    # Split the path and get the post ID
    path_parts = parsed.path.strip('/').split('/')
    
    # Find the post ID (it's usually after 'comments')
    try:
        post_id_index = path_parts.index('comments') + 1
        return path_parts[post_id_index]
    except (ValueError, IndexError):
        print("Error: Could not extract post ID from URL")
        sys.exit(1)

def fetch_comments(post_id):
    """Fetch comments from a Reddit post."""
    # Construct the API URL
    api_url = f"https://www.reddit.com/comments/{post_id}.json"
    
    # Set a custom User-Agent to avoid rate limiting
    headers = {
        'User-Agent': 'RedditCommentsViewer/1.0'
    }
    
    # Create a request with custom headers
    req = urllib.request.Request(api_url, headers=headers)
    
    try:
        # Make the request
        with urllib.request.urlopen(req) as response:
            # Read and decode the response
            data = response.read().decode('utf-8')
            # Parse the JSON response
            return json.loads(data)
    except HTTPError as e:
        print(f"Error fetching comments: HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except URLError as e:
        print(f"Error fetching comments: {e.reason}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Invalid JSON response from Reddit")
        sys.exit(1)

def print_comments(comments_data, indent=0):
    """Recursively print comments and their replies."""
    for comment in comments_data:
        # Skip deleted or removed comments
        if comment.get('data', {}).get('body') in ['[deleted]', '[removed]']:
            continue
        
        # Print the comment
        body = comment['data'].get('body', '')
        author = comment['data'].get('author', '[deleted]')
        score = comment['data'].get('score', 0)
        
        # Print with proper indentation
        print(' ' * indent + f"u/{author} ({score} points):")
        print(' ' * indent + body)
        print(' ' * indent + '-' * 50)
        
        # Print replies if they exist
        if 'replies' in comment['data'] and comment['data']['replies'] != '':
            replies = comment['data']['replies']['data']['children']
            print_comments(replies, indent + 2)

def main():
    """Main function to run the script."""
    # Check if a URL was provided
    if len(sys.argv) != 2:
        print("Usage: python reddit_comments.py <post_url>")
        sys.exit(1)
    
    # Get the post URL from command line arguments
    post_url = sys.argv[1]
    
    # Extract the post ID
    post_id = get_post_id(post_url)
    
    # Fetch the comments
    data = fetch_comments(post_id)
    
    # The first item in the response is the post data, the second is the comments
    comments = data[1]['data']['children']
    
    # Print the post title
    post_title = data[0]['data']['children'][0]['data']['title']
    print(f"\nPost: {post_title}\n")
    print("Top Comments:")
    print("=" * 50)
    
    # Print the comments
    print_comments(comments)

if __name__ == "__main__":
    main() 