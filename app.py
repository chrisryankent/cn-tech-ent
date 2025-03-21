import os
import requests
from flask import Flask, request, render_template, redirect, url_for, send_file, flash
import yt_dlp

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for flash messages
YOUTUBE_API_KEY = 'AIzaSyD9CPNuoMKVSY3v6A1KCIcnQg_7d0ZeScI'
YOUTUBE_SEARCH_URL = 'https://www.googleapis.com/youtube/v3/search'
YOUTUBE_TRENDING_URL = 'https://www.googleapis.com/youtube/v3/videos'
COOKIE_FILE_PATH = 'path_to_cookies.txt'  # Using your provided path

DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')

@app.route('/')
def index():
    page_token = request.args.get('page_token', '')
    trending_videos, next_page_token, prev_page_token = fetch_trending_videos(page_token)
    return render_template('index.html', trending_videos=trending_videos, next_page_token=next_page_token, prev_page_token=prev_page_token)

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    return redirect(url_for('search_results', query=query))

@app.route('/search_results')
def search_results():
    query = request.args.get('query')
    page_token = request.args.get('page_token', '')
    search_results, next_page_token, prev_page_token = fetch_search_results(query, page_token)
    return render_template('search_results.html', search_results=search_results, next_page_token=next_page_token, prev_page_token=prev_page_token, query=query)

@app.route('/video/<video_id>')
def video_detail(video_id):
    video = fetch_video_details(video_id)
    ydl_opts = {
        'cookiefile': COOKIE_FILE_PATH,
    }
    formats = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)
            formats = result.get('formats', [])
            print("Available formats:", formats)  # Print formats to console
    except yt_dlp.utils.DownloadError:
        flash('Error: Unable to fetch video formats. Please try again later.')
    if video:
        video_title = video['snippet']['title']
        video_owner = video['snippet']['channelTitle']
        related_videos = fetch_related_videos(video_title, video_owner)
    else:
        related_videos = []
    return render_template('video_detail.html', video=video, formats=formats, video_id=video_id, related_videos=related_videos)

@app.route('/download/<video_id>', methods=['POST'])
def download_video(video_id):
    format_code = request.form.get('format_code')
    video_filename = os.path.join(DOWNLOAD_FOLDER, f"{video_id}_video.mp4")
    audio_filename = os.path.join(DOWNLOAD_FOLDER, f"{video_id}_audio.m4a")
    output_filename = os.path.join(DOWNLOAD_FOLDER, f"{video_id}_output.mp4")

    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    # Download video
    ydl_opts = {
        'format': 'bestvideo',
        'outtmpl': video_filename,
        'noplaylist': True,
        'nocheckcertificate': True,
        'cookiefile': COOKIE_FILE_PATH,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36',
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f'https://www.youtube.com/watch?v={video_id}'])

        # Download audio
        ydl_opts['format'] = 'bestaudio'
        ydl_opts['outtmpl'] = audio_filename

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f'https://www.youtube.com/watch?v={video_id}'])

        # Merge video and audio
        os.system(f'ffmpeg -i "{video_filename}" -i "{audio_filename}" -c:v copy -c:a aac "{output_filename}"')

        # Remove intermediate files
        os.remove(video_filename)
        os.remove(audio_filename)

        return send_file(output_filename, as_attachment=True)
    except yt_dlp.utils.DownloadError as e:
        flash(f'Error: Unable to download video. Please try again later. {e}')
        return redirect(url_for('video_detail', video_id=video_id))

def fetch_trending_videos(page_token=''):
    params = {
        'part': 'snippet',
        'chart': 'mostPopular',
        'regionCode': 'US',
        'maxResults': 12,
        'pageToken': page_token,
        'key': YOUTUBE_API_KEY
    }
    response = requests.get(YOUTUBE_TRENDING_URL, params=params)
    data = response.json()
    return data.get('items', []), data.get('nextPageToken', ''), data.get('prevPageToken', '')

def fetch_search_results(query, page_token=''):
    params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'maxResults': 12,
        'pageToken': page_token,
        'key': YOUTUBE_API_KEY
    }
    response = requests.get(YOUTUBE_SEARCH_URL, params=params)
    data = response.json()
    return data.get('items', []), data.get('nextPageToken', ''), data.get('prevPageToken', '')

def fetch_video_details(video_id):
    params = {
        'part': 'snippet',
        'id': video_id,
        'key': YOUTUBE_API_KEY
    }
    response = requests.get(YOUTUBE_TRENDING_URL, params=params)
    data = response.json()
    return data['items'][0] if 'items' in data and len(data['items']) > 0 else None

def fetch_related_videos(video_title, video_owner):
    params = {
        'part': 'snippet',
        'q': f'{video_title} {video_owner}',
        'type': 'video',
        'maxResults': 6,
        'key': YOUTUBE_API_KEY
    }
    response = requests.get(YOUTUBE_SEARCH_URL, params=params)
    data = response.json()
    return data.get('items', [])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)



