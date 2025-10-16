import os
import re
import requests
from openai import OpenAI

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
def openai_with_timeout(timeout=120):
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )

client = openai_with_timeout()
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Create a Flask application instance.
app = Flask(__name__)


# Database configuration for SQLite (development)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///storyengine.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.urandom(24)  # Needed for session management

db = SQLAlchemy(app)

# --- MODELS ---

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True)
    stories = db.relationship('Story', backref='user', lazy=True)

class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    chapters = db.relationship('Chapter', backref='story', lazy=True)
    characters = db.relationship('Character', backref='story', lazy=True)
    plot_brainstorms = db.relationship('PlotBrainstorm', backref='story', lazy=True)
    # beatscenes and keyevents relationships removed; now tied to chapters

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False)
    title = db.Column(db.String(200))
    text = db.Column(db.Text)
    summary = db.Column(db.Text)
    beatscenes = db.relationship('BeatScene', backref='chapter', lazy=True)
    keyevents = db.relationship('KeyEvent', backref='chapter', lazy=True)

class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    traits = db.Column(db.Text)
    backstory = db.Column(db.Text)

class PlotBrainstorm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False)
    notes = db.Column(db.Text)

class BeatScene(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer)

class KeyEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer)

# --- WORLD BUILDING MODEL ---
class WorldBuildingElement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # One of: Settings, Cultures, Magic and Tech, History, Races
    description = db.Column(db.Text)

# Basic HTML template for the chat interface.
# We're embedding this directly in the Python file for simplicity.
# It includes a form for sending messages and a div to display responses.
HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenRouter Chat</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f3f4f6;
        }
    </style>
</head>
<body class="bg-gray-100 flex items-center justify-center min-h-screen p-4">
    <div class="bg-white rounded-xl shadow-lg w-full max-w-2xl p-6 flex flex-col space-y-4">
        <h1 class="text-2xl font-bold text-gray-800 text-center">OpenRouter Chat</h1>
        
        <!-- Chat output area -->
        <div id="chat-output" class="bg-gray-50 p-4 rounded-lg overflow-y-auto h-80 border border-gray-200">
            <div class="text-gray-500 italic text-center">
                Type a message and press Enter to start.
            </div>
        </div>

        <!-- Model selection and input form -->
        <form id="chat-form" class="flex flex-col space-y-2">
            <label for="model-select" class="font-medium text-gray-700">Select Model:</label>
            <select id="model-select" class="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="mistralai/mistral-7b-instruct:free">Mistral: Mistral 7B Instruct (free)</option>
                <option value="deepseek/deepseek-chat-v3.1:free">DeepSeek: DeepSeek Chat v3.1 (free)</option>
                <option value="deepseek/deepseek-r1-0528:free">DeepSeek: DeepSeek R1 0528 (free)</option>
                <option value="x-ai/grok-4-fast:free">Grok-4 Fast (free)</option>
                <option value="x-ai/grok-code-fast-1">Grok Code Fast</option>
                <option value="moonshotai/kimi-k2">MoonshotAI Kimi K2</option>
            </select>
            <textarea
                id="message-input"
                class="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                rows="3"
                placeholder="Enter your message here..."
            ></textarea>
            <button
                type="submit"
                class="bg-blue-600 text-white font-semibold py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors duration-200"
            >
                Send Message
            </button>
        </form>
    </div>

    <script>
        const chatForm = document.getElementById('chat-form');
        const messageInput = document.getElementById('message-input');
        const chatOutput = document.getElementById('chat-output');

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = messageInput.value.trim();
            const model = document.getElementById('model-select').value;
            if (!message) return;

            // Add user message to chat output
            appendMessage('user', message);

            // Clear input and show a typing indicator
            messageInput.value = '';
            const loadingIndicator = appendMessage('bot', '...', true);

            try {
                // Send the message and model to the Flask backend
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message, model: model }),
                });

                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }

                const data = await response.json();

                // Remove the loading indicator
                loadingIndicator.remove();

                // Add the bot's response to chat output
                appendMessage('bot', data.response);

            } catch (error) {
                console.error('Error:', error);
                loadingIndicator.remove();
                appendMessage('bot', 'Error: Failed to get a response.', false, true);
            }
        });

    function appendMessage(sender, text, isTyping = false, isError = false) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `p-3 rounded-lg max-w-xs transition-transform duration-300 ease-in-out transform scale-95 origin-bottom-left`;
            
            if (sender === 'user') {
                messageDiv.className += ' bg-blue-100 text-blue-900 self-end mb-2 ml-auto rounded-br-none';
                messageDiv.textContent = text;
            } else {
                messageDiv.className += ' bg-gray-200 text-gray-800 self-start mb-2 rounded-bl-none';
                messageDiv.textContent = text;
            }
            
            if (isTyping) {
                messageDiv.textContent = 'Thinking...';
                messageDiv.className = 'italic text-gray-500 text-center';
            }
            
            if (isError) {
                messageDiv.className = 'text-red-500 text-sm mt-1';
            }

            chatOutput.appendChild(messageDiv);
            chatOutput.scrollTop = chatOutput.scrollHeight;
            return messageDiv;
        }
    </script>
</body>
</html>
"""

# The OpenRouter API endpoint
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- HOMEPAGE ---
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('stories'))
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to Story Engine</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gradient-to-br from-blue-100 to-purple-200 min-h-screen flex flex-col items-center justify-center p-6">
        <div class="bg-white rounded-xl shadow-lg w-full max-w-lg p-8 space-y-6 text-center">
            <h1 class="text-4xl font-extrabold text-gray-800 mb-2">Welcome to Story Engine</h1>
            <p class="text-lg text-gray-600 mb-4">Create, organize, and brainstorm your stories with AI-powered tools.</p>
            <div class="flex justify-center space-x-4">
                <a href="/login" class="bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-blue-700 transition">Login</a>
                <a href="/signup" class="bg-purple-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-purple-700 transition">Sign Up</a>
            </div>
        </div>
    </body>
    </html>
    ''')
# --- END HOMEPAGE ---

@app.route('/stories')
@login_required
def stories():
    user_stories = Story.query.filter_by(user_id=current_user.id).all()
    return render_template_string(f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your Stories</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gradient-to-br from-blue-100 to-purple-200 min-h-screen flex flex-col items-center p-6">
        <div class="bg-white rounded-xl shadow-lg w-full max-w-2xl p-8 space-y-6">
            <h2 class="text-3xl font-bold text-gray-800 mb-2 text-center">Your Stories</h2>
            <ul class="space-y-2">
                {''.join([f'<li class="flex justify-between items-center border-b py-2"><span class="font-semibold">{s.title}</span> <a href="/story/{s.id}" class="text-blue-600 hover:underline">Open</a></li>' for s in user_stories]) or '<li>No stories yet.</li>'}
            </ul>
            <div class="flex justify-center mt-6">
                <a href="/story/new" class="bg-green-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-green-700 transition">Create New Story</a>
            </div>
        </div>
    </body>
    </html>
    ''')

@app.route('/story/new', methods=['GET', 'POST'])
@login_required
def new_story():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        story = Story(user_id=current_user.id, title=title, description=description)
        db.session.add(story)
        db.session.commit()
        # Create first chapter
        chapter = Chapter(story_id=story.id, title='Chapter 1', text='', summary='')
        db.session.add(chapter)
        db.session.commit()
        return redirect(url_for('story_dashboard', story_id=story.id))
    return '''<form method="post">Title: <input name="title"><br>Description: <input name="description"><br><input type="submit"></form>'''

@app.route('/story/<int:story_id>')
@login_required
def story_dashboard(story_id):
    story = Story.query.get_or_404(story_id)
    if story.user_id != current_user.id:
        return 'Unauthorized', 403
    chapters = Chapter.query.filter_by(story_id=story_id).all()
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ story.title }} - Story Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gradient-to-br from-blue-100 to-purple-200 min-h-screen flex flex-col items-center p-6">
        <div class="bg-white rounded-xl shadow-lg w-full max-w-2xl p-8 space-y-6">
            <h2 class="text-3xl font-bold text-gray-800 mb-2 text-center">{{ story.title }}</h2>
            <p class="text-lg text-gray-600 mb-4 text-center">{{ story.description }}</p>
            <ul class="space-y-2">
                <li><a href="/story/{{ story.id }}/chapters" class="text-blue-600 hover:underline font-semibold">Chapters</a></li>
                <li><a href="/story/{{ story.id }}/characters" class="text-blue-600 hover:underline font-semibold">Characters</a></li>
                <li><a href="/story/{{ story.id }}/plot" class="text-blue-600 hover:underline font-semibold">Plot Brainstorm</a></li>
                <li><a href="/story/{{ story.id }}/beats" class="text-blue-600 hover:underline font-semibold">Beats/Scenes</a></li>
            </ul>
            <div class="mt-8">
                <h3 class="text-xl font-bold text-gray-700 mb-2">Key Events by Chapter</h3>
                <ul class="space-y-2">
                    {% for chapter in chapters %}
                        <li class="flex justify-between items-center border-b py-2">
                            <span class="font-semibold">{{ chapter.title }}</span>
                            <a href="/story/{{ story.id }}/chapter/{{ chapter.id }}/events" class="text-blue-600 hover:underline font-semibold">Key Events</a>
                        </li>
                    {% else %}
                        <li>No chapters yet.</li>
                    {% endfor %}
                </ul>
            </div>
            <div class="flex justify-center mt-6">
                <a href="/stories" class="bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-blue-700 transition">Back to Library</a>
            </div>
        </div>
    </body>
    </html>
    ''', story=story, chapters=chapters)

# --- CREATIVE TOOL ROUTES (basic stubs) ---
@app.route('/story/<int:story_id>/chapters')
@login_required
def chapters(story_id):
    story = Story.query.get_or_404(story_id)
    chapters = Chapter.query.filter_by(story_id=story_id).all()
    next_chapter_num = len(chapters) + 1
    return render_template_string(f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chapters</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen flex flex-col items-center p-6">
        <div class="bg-white rounded-xl shadow-lg w-full max-w-2xl p-6 space-y-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-2">Chapters for {story.title}</h2>
            <ul class="space-y-2">
                {''.join([
                    f'<li class="flex justify-between items-center border-b py-2">'
                    f'<span class="font-semibold">{c.title}</span>'
                    f'<div>'
                    f'<a href="/story/{story_id}/chapter/{c.id}" class="text-blue-600 hover:underline mr-2">Edit</a>'
                    f'<form method="post" action="/story/{story_id}/chapter/{c.id}/delete" style="display:inline;" onsubmit="return confirm(\'Delete this chapter?\');">'
                    f'<button type="submit" class="bg-red-600 text-white px-2 py-1 rounded hover:bg-red-700">Delete</button>'
                    f'</form>'
                    f'</div>'
                    f'</li>' for c in chapters
                ]) or '<li>No chapters yet.</li>'}
            </ul>
            <form method="post" action="/story/{story_id}/chapter/new" class="mt-6 space-y-2">
                <label class="block font-semibold">Add Chapter:</label>
                <input name="title" value="Chapter {next_chapter_num}" class="w-full p-2 border rounded-lg">
                <button type="submit" class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700">Add Chapter</button>
            </form>
            <a href="/story/{story_id}" class="inline-block mt-6 text-blue-600 hover:underline">Back to Story</a>
        </div>
    </body>
    </html>
    ''')
# --- ADD CHAPTER ROUTE ---
@app.route('/story/<int:story_id>/chapter/new', methods=['POST'])
@login_required
def add_chapter(story_id):
    story = Story.query.get_or_404(story_id)
    title = request.form.get('title', f'Chapter {len(story.chapters)+1}')
    chapter = Chapter(story_id=story_id, title=title, text='', summary='')
    db.session.add(chapter)
    db.session.commit()
    return redirect(url_for('chapters', story_id=story_id))

# --- DELETE CHAPTER ROUTE ---
@app.route('/story/<int:story_id>/chapter/<int:chapter_id>/delete', methods=['POST'])
@login_required
def delete_chapter(story_id, chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    if chapter.story_id != story_id:
        return 'Unauthorized', 403
    db.session.delete(chapter)
    db.session.commit()
    return redirect(url_for('chapters', story_id=story_id))

@app.route('/story/<int:story_id>/characters', methods=['GET', 'POST'])
@login_required
def characters(story_id):
    story = Story.query.get_or_404(story_id)
    # Handle add character
    if request.method == 'POST' and request.form.get('add_character'):
        name = request.form.get('char_name', '').strip()
        traits = request.form.get('char_traits', '').strip()
        backstory = request.form.get('char_backstory', '').strip()
        if name:
            char = Character(story_id=story_id, name=name, traits=traits, backstory=backstory)
            db.session.add(char)
            db.session.commit()
        return redirect(url_for('characters', story_id=story_id))
    # Handle edit character
    if request.method == 'POST' and request.form.get('edit_character_id'):
        char_id = int(request.form.get('edit_character_id'))
        char = Character.query.get_or_404(char_id)
        char.name = request.form.get('char_name', char.name)
        char.traits = request.form.get('char_traits', char.traits)
        char.backstory = request.form.get('char_backstory', char.backstory)
        db.session.commit()
        return redirect(url_for('characters', story_id=story_id))
    # Handle delete character
    if request.method == 'POST' and request.form.get('delete_character_id'):
        char_id = int(request.form.get('delete_character_id'))
        char = Character.query.get_or_404(char_id)
        db.session.delete(char)
        db.session.commit()
        return redirect(url_for('characters', story_id=story_id))
    chars = Character.query.filter_by(story_id=story_id).all()
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Characters</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen flex flex-col items-center p-6">
        <div class="bg-white rounded-xl shadow-lg w-full max-w-2xl p-6 space-y-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-2">Characters for {{ story.title }}</h2>
            <ul class="space-y-2">
                {% for ch in chars %}
                    <li class="border-b py-2 flex flex-col">
                        <span class="font-semibold">{{ ch.name }}</span>
                        <button type="button" onclick="document.getElementById('edit-char-{{ ch.id }}').classList.toggle('hidden')" class="bg-gray-200 text-gray-800 px-3 py-1 rounded-lg font-semibold mb-2 hover:bg-gray-300">Edit</button>
                        <form id="edit-char-{{ ch.id }}" method="post" class="space-y-2 mb-2 hidden">
                            <input type="hidden" name="edit_character_id" value="{{ ch.id }}">
                            <label class="block font-semibold">Name:</label>
                            <input name="char_name" value="{{ ch.name }}" class="w-full p-2 border rounded-lg">
                            <label class="block font-semibold">Traits:</label>
                            <textarea name="char_traits" rows="2" class="w-full p-2 border rounded-lg">{{ ch.traits or '' }}</textarea>
                            <label class="block font-semibold">Backstory:</label>
                            <textarea name="char_backstory" rows="2" class="w-full p-2 border rounded-lg">{{ ch.backstory or '' }}</textarea>
                            <button type="submit" class="bg-blue-600 text-white px-3 py-1 rounded-lg hover:bg-blue-700">Save</button>
                        </form>
                        <form method="post" class="inline-block">
                            <input type="hidden" name="delete_character_id" value="{{ ch.id }}">
                            <button type="submit" class="bg-red-600 text-white px-3 py-1 rounded-lg hover:bg-red-700 ml-2">Delete</button>
                        </form>
                    </li>
                {% else %}
                    <li>No characters yet.</li>
                {% endfor %}
            </ul>
            <form method="post" class="space-y-4 mb-4">
                <input type="hidden" name="add_character" value="1">
                <label class="block font-semibold">Name:</label>
                <input name="char_name" class="w-full p-2 border rounded-lg">
                <label class="block font-semibold">Traits:</label>
                <textarea name="char_traits" rows="2" class="w-full p-2 border rounded-lg"></textarea>
                <label class="block font-semibold">Backstory:</label>
                <textarea name="char_backstory" rows="2" class="w-full p-2 border rounded-lg"></textarea>
                <button type="submit" class="bg-green-600 text-white px-3 py-1 rounded-lg hover:bg-green-700">Add Character</button>
            </form>
            <a href="/story/{{ story.id }}" class="inline-block mt-6 text-blue-600 hover:underline">Back to Story</a>
        </div>
    </body>
    </html>
    ''', story=story, chars=chars)

@app.route('/story/<int:story_id>/plot')
@login_required
def plot_brainstorm(story_id):
    story = Story.query.get_or_404(story_id)
    plot = PlotBrainstorm.query.filter_by(story_id=story_id).first()
    notes = plot.notes if plot else ''
    return render_template_string(f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Plot Brainstorm</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen flex flex-col items-center p-6">
        <div class="bg-white rounded-xl shadow-lg w-full max-w-2xl p-6 space-y-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-2">Plot Brainstorm for {story.title}</h2>
            <div class="border rounded-lg">
                <button type="button" onclick="document.getElementById('plot_notes').classList.toggle('hidden')" class="w-full text-left px-4 py-2 font-semibold bg-gray-200 hover:bg-gray-300 rounded-t-lg">Plot Notes</button>
                <div id="plot_notes" class="hidden px-4 py-2">
                    <p>{notes or "No notes yet."}</p>
                    <a href="/story/{story_id}/plot/edit" class="text-blue-600 hover:underline">Edit Plot</a>
                </div>
            </div>
            <a href="/story/{story_id}" class="inline-block mt-6 text-blue-600 hover:underline">Back to Story</a>
        </div>
    </body>
    </html>
    ''')

@app.route('/story/<int:story_id>/beats')
@login_required
def beatscenes(story_id):
    story = Story.query.get_or_404(story_id)
    beats = BeatScene.query.filter_by(story_id=story_id).all()
    return render_template_string(f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Beats/Scenes</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen flex flex-col items-center p-6">
        <div class="bg-white rounded-xl shadow-lg w-full max-w-2xl p-6 space-y-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-2">Beats/Scenes for {story.title}</h2>
            <ul class="space-y-2">
                {''.join([f'<li class="border-b py-2 flex justify-between items-center"><span>{b.description}</span> <a href="/story/{story_id}/beat/{b.id}/edit" class="text-blue-600 hover:underline">Edit</a></li>' for b in beats]) or '<li>No beats/scenes yet.</li>'}
            </ul>
            <a href="/story/{story_id}/beat/new" class="inline-block text-green-600 hover:underline">Add Beat/Scene</a>
            <a href="/story/{story_id}" class="inline-block mt-6 text-blue-600 hover:underline">Back to Story</a>
        </div>
    </body>
    </html>
    ''')

@app.route('/story/<int:story_id>/chapter/<int:chapter_id>/events')
@login_required
def keyevents(story_id, chapter_id):
    story = Story.query.get_or_404(story_id)
    chapter = Chapter.query.get_or_404(chapter_id)
    events = KeyEvent.query.filter_by(chapter_id=chapter_id).order_by(KeyEvent.order.asc()).all()
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Key Events</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen flex flex-col items-center p-6">
        <div class="bg-white rounded-xl shadow-lg w-full max-w-2xl p-6 space-y-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-2">Key Events for {{ story.title }} - {{ chapter.title }}</h2>
            <ol class="list-decimal ml-6 space-y-2">
                {% for e in events %}
                    <li class="flex flex-col border-b py-2">
                        <span>{{ e.description }}</span>
                        <button type="button" onclick="document.getElementById('edit-event-{{ e.id }}').classList.toggle('hidden')" class="bg-gray-200 text-gray-800 px-3 py-1 rounded-lg font-semibold mb-2 hover:bg-gray-300">Edit</button>
                        <form id="edit-event-{{ e.id }}" method="post" class="space-y-2 mb-2 hidden">
                            <input type="hidden" name="edit_keyevent_id" value="{{ e.id }}">
                            <label class="block font-semibold">Description:</label>
                            <textarea name="event_description" rows="2" class="w-full p-2 border rounded-lg">{{ e.description }}</textarea>
                            <label class="block font-semibold">Order:</label>
                            <input name="event_order" type="number" value="{{ e.order }}" class="w-full p-2 border rounded-lg">
                            <button type="submit" class="bg-blue-600 text-white px-3 py-1 rounded-lg hover:bg-blue-700">Save</button>
                        </form>
                        <form method="post" class="inline-block">
                            <input type="hidden" name="delete_keyevent_id" value="{{ e.id }}">
                            <button type="submit" class="bg-red-600 text-white px-3 py-1 rounded-lg hover:bg-red-700 ml-2">Delete</button>
                        </form>
                    </li>
                {% else %}
                    <li>No key events yet.</li>
                {% endfor %}
            </ol>
            <form method="post" class="space-y-4 mb-4">
                <input type="hidden" name="add_keyevent" value="1">
                <label class="block font-semibold">Description:</label>
                <textarea name="event_description" rows="2" class="w-full p-2 border rounded-lg"></textarea>
                <label class="block font-semibold">Order:</label>
                <input name="event_order" type="number" value="1" class="w-full p-2 border rounded-lg">
                <button type="submit" class="bg-green-600 text-white px-3 py-1 rounded-lg hover:bg-green-700">Add Key Event</button>
            </form>
            <a href="/story/{{ story.id }}/chapter/{{ chapter.id }}" class="inline-block mt-6 text-blue-600 hover:underline">Back to Chapter</a>
        </div>
    </body>
    </html>
    ''', story=story, chapter=chapter, events=events)
# --- END STORY MANAGEMENT & TOOLS ---

# --- CHAPTER ADD/EDIT ---
@app.route('/story/<int:story_id>/chapter/<int:chapter_id>', methods=['GET', 'POST'])
@login_required
def edit_chapter(story_id, chapter_id):
    # Always fetch chapter and story first
    chapter = Chapter.query.get_or_404(chapter_id)
    story = Story.query.get_or_404(story_id)
    # Handle Save Chapter
    if request.method == 'POST' and not any([
        'query_prose_deepseek' in request.form,
        'query_prose_free_deepseek' in request.form,
        'query_prose_grok4' in request.form,
        'query_prose_grok_code' in request.form,
        'query_prose_kimi' in request.form,
        'query_prose_selected' in request.form,
        'query_beat_deepseek' in request.form,
        'query_beat_free_deepseek' in request.form,
        'query_beat_grok4' in request.form,
        'query_beat_grok_code' in request.form,
        'query_beat_kimi' in request.form,
        'query_beat_selected' in request.form,
        'query_summary_ai' in request.form,
        'add_beat' in request.form,
        'add_world_element' in request.form
    ]):
        chapter.title = request.form.get('title', chapter.title)
        chapter.summary = request.form.get('summary', chapter.summary)
        chapter.text = request.form.get('text', chapter.text)
        db.session.commit()

    # Handle Add Beat/Scene
    if request.method == 'POST' and 'add_beat' in request.form:
        beat_description = request.form.get('beat_description', '').strip()
        beat_order = request.form.get('beat_order', 1)
        if beat_description:
            new_beat = BeatScene(chapter_id=chapter_id, description=beat_description, order=beat_order)
            db.session.add(new_beat)
            db.session.commit()
        return redirect(url_for('edit_chapter', story_id=story_id, chapter_id=chapter_id))
    # Handle Add World Element
    if request.method == 'POST' and 'add_world_element' in request.form:
        category = request.form.get('world_category', 'Settings')
        description = request.form.get('world_description', '')
        if description:
            element = WorldBuildingElement(chapter_id=chapter_id, category=category, description=description)
            db.session.add(element)
            db.session.commit()
        return redirect(url_for('edit_chapter', story_id=story_id, chapter_id=chapter_id))
    # Ensure 'characters' is a list of Character objects, not a function
    characters = Character.query.filter_by(story_id=story_id).all()
    # Ensure all variables used in the template are defined
    extracted_characters_prose = []  # TODO: Replace with actual extraction logic if needed
    world_elements = WorldBuildingElement.query.filter_by(chapter_id=chapter_id).all()
    characters = Character.query.filter_by(story_id=story_id).all()
    key_events = KeyEvent.query.filter_by(chapter_id=chapter_id).order_by(KeyEvent.order.asc()).all()
    world_elements = WorldBuildingElement.query.filter_by(chapter_id=chapter_id).all()
    beats = BeatScene.query.filter_by(chapter_id=chapter_id).order_by(BeatScene.order.asc()).all()
    # Characters in Scene Autocomplete Logic
    all_characters = Character.query.filter_by(story_id=story_id).all()
    beat_input = request.form.get('beat_description', '')
    if beat_input:
        detected_characters = [c.name for c in all_characters if re.search(r'\b' + re.escape(c.name) + r'\b', beat_input, re.IGNORECASE)]
    else:
        detected_characters = [c.name for c in all_characters]
    characters_in_scene = request.form.getlist('characters_in_scene') or detected_characters
    default_prose_preset = (
        "You are a narrative designer. Your task is to expand the provided series of beats into a complete, action-oriented scene.\n\n"
        "Instructions\n"
        "Scene Generation: Write the entire scene in the third person. Expand each provided beat into a specific action, an unfolding event, or a piece of purposeful dialogue. The final output must be a unified, cohesive scene, not a simple list of expanded points.\n\n"
        "Dialogue Rules: Dialogue must be direct and consistent with established character traits. It will be concise, moving the plot forward without unnecessary exposition or filler. Use of purple prose and flowery language is strictly forbidden.\n\n"
        "Action Rules: Prioritize physical actions and tangible events. Describe characters' movements and reactions to show their state of mind and propel the narrative.\n\n"
        "Narrative Flow: Ensure smooth, logical transitions between beats. The scene must unfold in a continuous and believable sequence."
    )
    prose_preset = request.form.get('prose_preset', default_prose_preset)
    ai_prose = request.form.get('ai_prose', '')
    ai_prose_free_deepseek = request.form.get('ai_prose_free_deepseek', '')
    ai_beat_scene_free_deepseek = request.form.get('ai_beat_scene_free_deepseek', '')
    default_beat_preset = (
        "Your role: You are a narrative designer.\n\n"
        "Your task: Take the single beat provided and expand it into a detailed, action-oriented sequence of events. Do not simply describe the beat; show the steps, decisions, and consequences that unfold within that moment.\n\n"
        "Instructions:\n\n"
        "Identify the core action: First, pinpoint the central action or decision within the given beat. What is the one key thing that happens?\n\n"
        "Break it down: Unpack that single action into a series of smaller, sequential beats. Think about the 'before,' 'during,' and 'after' of the moment.\n\n"
        "Setup/Inciting Event: What leads directly to this beat? What decision or discovery is made?\n\n"
        "The Action: What are the specific, physical or verbal actions that unfold? Who does what to whom?\n\n"
        "Immediate Consequence: What is the direct result of this action? How does the situation change for the character(s)?\n\n"
        "Translate to action: Use active, event-driven language. For example, if the beat is 'Maya gets caught,' your expansion should include beats like: 'Maya sees the security team enter the room,' 'She dives for the server rack,' and 'She is tackled just before she can hit the upload key.'\n\n"
        "Maintain intent: Ensure the expanded sequence remains true to the original story's tone and character motivations. If the original beat is tense, the sequence should build tension. If it's a moment of triumph, the sequence should reflect that.\n\n"
        "Example Beat (for you to provide):"
    )
    beat_preset = request.form.get('beat_preset', default_beat_preset)
    ai_beat_scene = request.form.get('ai_beat_scene', '')
    ai_prose = request.form.get('ai_prose', '')
    # Handle AI prose generator (Free DeepSeek)
    if request.method == 'POST' and 'query_prose_free_deepseek' in request.form:
        print("Free DeepSeek prose button clicked")
        prose_preset = request.form.get('prose_preset', default_prose_preset)
        scene_text = request.form.get('text', '')
        selected_characters = request.form.getlist('selected_characters_prose')
        char_str = ', '.join(selected_characters) if selected_characters else 'no characters'
        chapter_text = chapter.text or ''
        chapter_words = chapter_text.split()
        last_2000 = ' '.join(chapter_words[-2000:]) if len(chapter_words) > 0 else ''
        world_elements_str = '\n'.join([f"- {w.category}: {w.description}" for w in world_elements]) if world_elements else 'None'
        prompt = (
            f"{prose_preset}\n\nCharacters in scene: {char_str}\nScene: {scene_text}\n\nRecent chapter context (last 2000 words):\n{last_2000}\n\nWorld Building Elements:\n{world_elements_str}"
        )
        try:
            response = client.chat.completions.create(
                model="deepseek/deepseek-r1-0528:free",
                messages=[{"role": "user", "content": prompt}],
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5000"),
                    "X-Title": os.getenv("SITE_NAME", "StoryEngine")
                },
                extra_body={}
            )
            ai_prose_free_deepseek = response.choices[0].message.content.strip()
        except Exception as e:
            ai_prose_free_deepseek = f"[AI Error: {e}]"
    # Handle Beat/Scene AI generator (Free DeepSeek)
    if request.method == 'POST' and 'query_beat_free_deepseek' in request.form:
        print("Free DeepSeek beat button clicked")
        beat_preset = request.form.get('beat_preset', default_beat_preset)
        beat_scene_input = request.form.get('beat_scene_input', '')
        selected_characters_beat = request.form.getlist('selected_characters_beat')
        char_str_beat = ', '.join(selected_characters_beat) if selected_characters_beat else 'no characters'
        chapter_text = chapter.text or ''
        chapter_words = chapter_text.split()
        last_2000 = ' '.join(chapter_words[-2000:]) if len(chapter_words) > 0 else ''
        world_elements_str = '\n'.join([f"- {w.category}: {w.description}" for w in world_elements]) if world_elements else 'None'
        beat_prompt = (
            f"{beat_preset}\n\nCharacters in scene: {char_str_beat}\nBeat/Scene Input: {beat_scene_input}\n\nRecent chapter context (last 2000 words):\n{last_2000}\n\nWorld Building Elements:\n{world_elements_str}"
        )
        try:
            response = client.chat.completions.create(
                model="deepseek/deepseek-r1-0528:free",
                messages=[{"role": "user", "content": beat_prompt}],
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5000"),
                    "X-Title": os.getenv("SITE_NAME", "StoryEngine")
                },
                extra_body={}
            )
            ai_beat_scene_free_deepseek = response.choices[0].message.content.strip()
        except Exception as e:
            ai_beat_scene_free_deepseek = f"[AI Error: {e}]"
    # Handle AI query form submission for prose (Grok-4)
    if request.method == 'POST' and 'query_prose_grok4' in request.form:
        print("Grok-4 prose button clicked")
        prose_preset = request.form.get('prose_preset', default_prose_preset)
        scene_text = request.form.get('text', '')
        selected_characters = request.form.getlist('selected_characters_prose')
        char_str = ', '.join(selected_characters) if selected_characters else 'no characters'
        chapter_text = chapter.text or ''
        chapter_words = chapter_text.split()
        last_2000 = ' '.join(chapter_words[-2000:]) if len(chapter_words) > 0 else ''
        world_elements_str = '\n'.join([f"- {w.category}: {w.description}" for w in world_elements]) if world_elements else 'None'
        prompt = (
            f"{prose_preset}\n\nCharacters in scene: {char_str}\nScene: {scene_text}\n\nRecent chapter context (last 2000 words):\n{last_2000}\n\nWorld Building Elements:\n{world_elements_str}"
        )
        try:
            response = client.chat.completions.create(
                model="x-ai/grok-4-fast:free",
                messages=[{"role": "user", "content": prompt}],
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5000"),
                    "X-Title": os.getenv("SITE_NAME", "StoryEngine")
                },
                extra_body={}
            )
            ai_prose_grok4 = response.choices[0].message.content.strip()
        except Exception as e:
            ai_prose_grok4 = f"[AI Error: {e}]"
    # Handle AI query form submission for prose (Grok Code)
    if request.method == 'POST' and 'query_prose_grok_code' in request.form:
        print("Grok Code prose button clicked")
        prose_preset = request.form.get('prose_preset', default_prose_preset)
        scene_text = request.form.get('text', '')
        selected_characters = request.form.getlist('selected_characters_prose')
        char_str = ', '.join(selected_characters) if selected_characters else 'no characters'
        chapter_text = chapter.text or ''
        chapter_words = chapter_text.split()
        last_2000 = ' '.join(chapter_words[-2000:]) if len(chapter_words) > 0 else ''
        world_elements_str = '\n'.join([f"- {w.category}: {w.description}" for w in world_elements]) if world_elements else 'None'
        prompt = (
            f"{prose_preset}\n\nCharacters in scene: {char_str}\nScene: {scene_text}\n\nRecent chapter context (last 2000 words):\n{last_2000}\n\nWorld Building Elements:\n{world_elements_str}"
        )
        try:
            response = client.chat.completions.create(
                model="x-ai/grok-code-fast-1",
                messages=[{"role": "user", "content": prompt}],
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5000"),
                    "X-Title": os.getenv("SITE_NAME", "StoryEngine")
                },
                extra_body={}
            )
            ai_prose_grok_code = response.choices[0].message.content.strip()
        except Exception as e:
            ai_prose_grok_code = f"[AI Error: {e}]"
    # Handle AI query form submission for prose (Kimi)
    if request.method == 'POST' and 'query_prose_kimi' in request.form:
        print("Kimi prose button clicked")
        prose_preset = request.form.get('prose_preset', default_prose_preset)
        scene_text = request.form.get('text', '')
        selected_characters = request.form.getlist('selected_characters_prose')
        char_str = ', '.join(selected_characters) if selected_characters else 'no characters'
        chapter_text = chapter.text or ''
        chapter_words = chapter_text.split()
        last_2000 = ' '.join(chapter_words[-2000:]) if len(chapter_words) > 0 else ''
        world_elements_str = '\n'.join([f"- {w.category}: {w.description}" for w in world_elements]) if world_elements else 'None'
        prompt = (
            f"{prose_preset}\n\nCharacters in scene: {char_str}\nScene: {scene_text}\n\nRecent chapter context (last 2000 words):\n{last_2000}\n\nWorld Building Elements:\n{world_elements_str}"
        )
        try:
            response = client.chat.completions.create(
                model="moonshotai/kimi-k2",
                messages=[{"role": "user", "content": prompt}],
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5000"),
                    "X-Title": os.getenv("SITE_NAME", "StoryEngine")
                },
                extra_body={}
            )
            ai_prose_kimi = response.choices[0].message.content.strip()
        except Exception as e:
            ai_prose_kimi = f"[AI Error: {e}]"
    beat_preset = request.form.get('beat_preset', default_beat_preset)
    ai_beat_scene = request.form.get('ai_beat_scene', '')
    ai_summary = request.form.get('ai_summary', '')
    ai_prose_deepseek = request.form.get('ai_prose_deepseek', '')
    ai_beat_scene_deepseek = request.form.get('ai_beat_scene_deepseek', '')
    ai_prose_grok4 = request.form.get('ai_prose_grok4', '')
    ai_prose_grok_code = request.form.get('ai_prose_grok_code', '')
    ai_prose_kimi = request.form.get('ai_prose_kimi', '')
    ai_beat_scene_grok4 = request.form.get('ai_beat_scene_grok4', '')
    ai_beat_scene_grok_code = request.form.get('ai_beat_scene_grok_code', '')
    ai_beat_scene_kimi = request.form.get('ai_beat_scene_kimi', '')
    ai_prose_selected = request.form.get('ai_prose_selected', '')
    ai_beat_scene_selected = request.form.get('ai_beat_scene_selected', '')

    # Handle AI query form submission for prose
    if request.method == 'POST' and 'query_prose_deepseek' in request.form:
        prose_preset = request.form.get('prose_preset', default_prose_preset)
        scene_text = request.form.get('text', '')
        selected_characters = request.form.getlist('selected_characters_prose')
        char_str = ', '.join(selected_characters) if selected_characters else 'no characters'
        chapter_text = chapter.text or ''
        chapter_words = chapter_text.split()
        last_2000 = ' '.join(chapter_words[-2000:]) if len(chapter_words) > 0 else ''
        world_elements_str = '\n'.join([f"- {w.category}: {w.description}" for w in world_elements]) if world_elements else 'None'
        prompt = (
            f"{prose_preset}\n\nCharacters in scene: {char_str}\nScene: {scene_text}\n\nRecent chapter context (last 2000 words):\n{last_2000}\n\nWorld Building Elements:\n{world_elements_str}"
        )
        try:
            response = client.chat.completions.create(
                model="deepseek/deepseek-chat-v3.1",
                messages=[{"role": "user", "content": prompt}],
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5000"),
                    "X-Title": os.getenv("SITE_NAME", "StoryEngine")
                },
                extra_body={}
            )
            ai_prose_deepseek = response.choices[0].message.content.strip()
        except Exception as e:
            ai_prose = f"[AI Error: {e}]"
    # Handle Beat/Scene AI generator
    if request.method == 'POST' and 'query_beat_deepseek' in request.form:
        beat_preset = request.form.get('beat_preset', '')
        beat_scene_input = request.form.get('beat_scene_input', '')
        # Use only the characters selected in the beat/scene form
        selected_characters_beat = request.form.getlist('selected_characters_beat')
        all_characters = Character.query.filter_by(story_id=story_id).all()
        detected_characters_beat = [c.name for c in all_characters if re.search(r'\b' + re.escape(c.name) + r'\b', beat_scene_input, re.IGNORECASE)] if beat_scene_input else [c.name for c in all_characters]
        char_str_beat = ', '.join(selected_characters_beat) if selected_characters_beat else 'no characters'
        chapter_text = chapter.text or ''
        chapter_words = chapter_text.split()
        last_2000 = ' '.join(chapter_words[-2000:]) if len(chapter_words) > 0 else ''
        # World building elements for this chapter
        world_elements = WorldBuildingElement.query.filter_by(chapter_id=chapter_id).all()
        world_elements_str = '\n'.join([f"- {w.category}: {w.description}" for w in world_elements]) if world_elements else 'None'
        beat_prompt = (
            f"{beat_preset}\n\nCharacters in scene: {char_str_beat}\nBeat/Scene Input: {beat_scene_input}\n\nRecent chapter context (last 2000 words):\n{last_2000}\n\nWorld Building Elements:\n{world_elements_str}"
        )
        try:
            response = client.chat.completions.create(
                model="deepseek/deepseek-chat-v3.1",
                messages=[{"role": "user", "content": beat_prompt}],
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5000"),
                    "X-Title": os.getenv("SITE_NAME", "StoryEngine")
                },
                extra_body={}
            )
            ai_beat_scene_deepseek = response.choices[0].message.content.strip()
        except Exception as e:
            ai_beat_scene = f"[AI Error: {e}]"
    # Handle Beat/Scene AI generator (Grok-4)
    if request.method == 'POST' and 'query_beat_grok4' in request.form:
        print("Grok-4 beat button clicked")
        beat_preset = request.form.get('beat_preset', default_beat_preset)
        beat_scene_input = request.form.get('beat_scene_input', '')
        selected_characters_beat = request.form.getlist('selected_characters_beat')
        char_str_beat = ', '.join(selected_characters_beat) if selected_characters_beat else 'no characters'
        chapter_text = chapter.text or ''
        chapter_words = chapter_text.split()
        last_2000 = ' '.join(chapter_words[-2000:]) if len(chapter_words) > 0 else ''
        world_elements_str = '\n'.join([f"- {w.category}: {w.description}" for w in world_elements]) if world_elements else 'None'
        beat_prompt = (
            f"{beat_preset}\n\nCharacters in scene: {char_str_beat}\nBeat/Scene Input: {beat_scene_input}\n\nRecent chapter context (last 2000 words):\n{last_2000}\n\nWorld Building Elements:\n{world_elements_str}"
        )
        try:
            response = client.chat.completions.create(
                model="x-ai/grok-4-fast:free",
                messages=[{"role": "user", "content": beat_prompt}],
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5000"),
                    "X-Title": os.getenv("SITE_NAME", "StoryEngine")
                },
                extra_body={}
            )
            ai_beat_scene_grok4 = response.choices[0].message.content.strip()
        except Exception as e:
            ai_beat_scene_grok4 = f"[AI Error: {e}]"
    # Handle Beat/Scene AI generator (Grok Code)
    if request.method == 'POST' and 'query_beat_grok_code' in request.form:
        print("Grok Code beat button clicked")
        beat_preset = request.form.get('beat_preset', default_beat_preset)
        beat_scene_input = request.form.get('beat_scene_input', '')
        selected_characters_beat = request.form.getlist('selected_characters_beat')
        char_str_beat = ', '.join(selected_characters_beat) if selected_characters_beat else 'no characters'
        chapter_text = chapter.text or ''
        chapter_words = chapter_text.split()
        last_2000 = ' '.join(chapter_words[-2000:]) if len(chapter_words) > 0 else ''
        world_elements_str = '\n'.join([f"- {w.category}: {w.description}" for w in world_elements]) if world_elements else 'None'
        beat_prompt = (
            f"{beat_preset}\n\nCharacters in scene: {char_str_beat}\nBeat/Scene Input: {beat_scene_input}\n\nRecent chapter context (last 2000 words):\n{last_2000}\n\nWorld Building Elements:\n{world_elements_str}"
        )
        try:
            response = client.chat.completions.create(
                model="x-ai/grok-code-fast-1",
                messages=[{"role": "user", "content": beat_prompt}],
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5000"),
                    "X-Title": os.getenv("SITE_NAME", "StoryEngine")
                },
                extra_body={}
            )
            ai_beat_scene_grok_code = response.choices[0].message.content.strip()
        except Exception as e:
            ai_beat_scene_grok_code = f"[AI Error: {e}]"
    # Handle Beat/Scene AI generator (Kimi)
    if request.method == 'POST' and 'query_beat_kimi' in request.form:
        print("Kimi beat button clicked")
        beat_preset = request.form.get('beat_preset', default_beat_preset)
        beat_scene_input = request.form.get('beat_scene_input', '')
        selected_characters_beat = request.form.getlist('selected_characters_beat')
        char_str_beat = ', '.join(selected_characters_beat) if selected_characters_beat else 'no characters'
        chapter_text = chapter.text or ''
        chapter_words = chapter_text.split()
        last_2000 = ' '.join(chapter_words[-2000:]) if len(chapter_words) > 0 else ''
        world_elements_str = '\n'.join([f"- {w.category}: {w.description}" for w in world_elements]) if world_elements else 'None'
        beat_prompt = (
            f"{beat_preset}\n\nCharacters in scene: {char_str_beat}\nBeat/Scene Input: {beat_scene_input}\n\nRecent chapter context (last 2000 words):\n{last_2000}\n\nWorld Building Elements:\n{world_elements_str}"
        )
        try:
            response = client.chat.completions.create(
                model="moonshotai/kimi-k2",
                messages=[{"role": "user", "content": beat_prompt}],
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5000"),
                    "X-Title": os.getenv("SITE_NAME", "StoryEngine")
                },
                extra_body={}
            )
            ai_beat_scene_kimi = response.choices[0].message.content.strip()
        except Exception as e:
            ai_beat_scene_kimi = f"[AI Error: {e}]"
    # Handle selected prose model
    if request.method == 'POST' and 'query_prose_selected' in request.form:
        selected_model = request.form.get('prose_model', 'deepseek/deepseek-chat-v3.1')
        print(f"Selected prose model: {selected_model}")
        prose_preset = request.form.get('prose_preset', default_prose_preset)
        scene_text = request.form.get('text', '')
        selected_character_names = request.form.getlist('selected_characters_prose')

        # Get full character details from database
        selected_characters = Character.query.filter_by(story_id=story_id).filter(Character.name.in_(selected_character_names)).all() if selected_character_names else []
        char_details = []
        for char in selected_characters:
            details = f"Name: {char.name}"
            if char.traits:
                details += f"\nTraits: {char.traits}"
            if char.backstory:
                details += f"\nBackstory: {char.backstory}"
            char_details.append(details)

        char_str = '\n\n'.join(char_details) if char_details else 'no characters'
        chapter_text = chapter.text or ''
        chapter_words = chapter_text.split()
        last_2000 = ' '.join(chapter_words[-2000:]) if len(chapter_words) > 0 else ''
        world_elements_str = '\n'.join([f"- {w.category}: {w.description}" for w in world_elements]) if world_elements else 'None'
        prompt = (
            f"{prose_preset}\n\nCharacter Information:\n{char_str}\n\nScene: {scene_text}\n\nRecent chapter context (last 2000 words):\n{last_2000}\n\nWorld Building Elements:\n{world_elements_str}"
        )
        print(f"DEBUG - Selected prose model {selected_model}: Characters selected: {len(selected_characters)}, Chapter context length: {len(last_2000)} chars, World elements present: {len(world_elements) > 0}")
        try:
            response = client.chat.completions.create(
                model=selected_model,
                messages=[{"role": "user", "content": prompt}],
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5000"),
                    "X-Title": os.getenv("SITE_NAME", "StoryEngine")
                },
                extra_body={}
            )
            ai_prose_selected = response.choices[0].message.content.strip()
        except Exception as e:
            ai_prose_selected = f"[AI Error: {e}]"
    # Handle selected beat model
    if request.method == 'POST' and 'query_beat_selected' in request.form:
        selected_model = request.form.get('beat_model', 'deepseek/deepseek-chat-v3.1')
        print(f"Selected beat model: {selected_model}")
        beat_preset = request.form.get('beat_preset', default_beat_preset)
        beat_scene_input = request.form.get('beat_scene_input', '')
        selected_character_names_beat = request.form.getlist('selected_characters_beat')

        # Get full character details from database
        selected_characters_beat = Character.query.filter_by(story_id=story_id).filter(Character.name.in_(selected_character_names_beat)).all() if selected_character_names_beat else []
        char_details_beat = []
        for char in selected_characters_beat:
            details = f"Name: {char.name}"
            if char.traits:
                details += f"\nTraits: {char.traits}"
            if char.backstory:
                details += f"\nBackstory: {char.backstory}"
            char_details_beat.append(details)

        char_str_beat = '\n\n'.join(char_details_beat) if char_details_beat else 'no characters'
        chapter_text = chapter.text or ''
        chapter_words = chapter_text.split()
        last_2000 = ' '.join(chapter_words[-2000:]) if len(chapter_words) > 0 else ''
        world_elements_str = '\n'.join([f"- {w.category}: {w.description}" for w in world_elements]) if world_elements else 'None'
        beat_prompt = (
            f"{beat_preset}\n\nCharacter Information:\n{char_str_beat}\n\nBeat/Scene Input: {beat_scene_input}\n\nRecent chapter context (last 2000 words):\n{last_2000}\n\nWorld Building Elements:\n{world_elements_str}"
        )
        print(f"DEBUG - Selected beat model {selected_model}: Characters selected: {len(selected_characters_beat)}, Chapter context length: {len(last_2000)} chars, World elements present: {len(world_elements) > 0}")
        try:
            response = client.chat.completions.create(
                model=selected_model,
                messages=[{"role": "user", "content": beat_prompt}],
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5000"),
                    "X-Title": os.getenv("SITE_NAME", "StoryEngine")
                },
                extra_body={}
            )
            ai_beat_scene_selected = response.choices[0].message.content.strip()
        except Exception as e:
            ai_beat_scene_selected = f"[AI Error: {e}]"
    if request.method == 'POST' and 'query_summary_ai' in request.form:
        summary_text = request.form.get('text', '')
        summary_prompt = (
            "Break down the following text into a list of key events in strict chronological order. Use strict and concise language. Each event should be a single, clear sentence. Do not add commentary or extra description.\n\nText:\n" + summary_text
        )
        try:
            response = client.chat.completions.create(
                model="deepseek/deepseek-chat-v3.1",
                messages=[{"role": "user", "content": summary_prompt}],
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5000"),
                    "X-Title": os.getenv("SITE_NAME", "StoryEngine")
                },
                extra_body={}
            )
            ai_summary = response.choices[0].message.content.strip()
        except Exception as e:
            ai_summary = f"[AI Error: {e}]"


    # Modern chapter edit UI with character selection, AI integration, and all features
    # Add link to chapter selection page
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Edit Chapter</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen flex flex-col items-center p-6">
        <div class="bg-white rounded-xl shadow-lg w-full max-w-4xl p-6 space-y-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-2">Edit Chapter: {{ chapter.title }}</h2>
            <a href="/story/{{ story_id }}/chapters" class="inline-block mb-4 text-blue-600 hover:underline">&larr; Back to Chapters</a>
            <form method="post" class="space-y-4">
                <label class="block font-semibold">Title:</label>
                <input name="title" value="{{ chapter.title }}" class="w-full p-2 border rounded-lg">
                <label class="block font-semibold">Summary:</label>
                <textarea name="summary" rows="2" class="w-full p-2 border rounded-lg">{{ ai_summary if ai_summary else chapter.summary }}</textarea>
                <label class="block font-semibold">Chapter Text:</label>
                <textarea name="text" rows="6" class="w-full p-2 border rounded-lg">{{ chapter.text }}</textarea>
                <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">Save Chapter</button>
            </form>
            <form method="post" class="space-y-2 mb-4">
                <input type="hidden" name="query_summary_ai" value="1">
                <label class="block font-semibold">Text to Summarize:</label>
                <textarea name="text" rows="6" class="w-full p-2 border rounded-lg">{{ chapter.text }}</textarea>
                <button type="submit" class="bg-yellow-600 text-white px-4 py-2 rounded-lg hover:bg-yellow-700 mt-2">Query AI for Key Events</button>
            </form>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <!-- AI Prose Generator -->
                <div>
                    <h3 class="text-xl font-bold text-gray-700 mb-2">AI Prose Generator</h3>
                    <form method="post" class="space-y-4">
                        <input type="hidden" name="query_prose_ai" value="1">
                        <label class="block font-semibold">Prompt (edit as needed):</label>
                        <textarea name="prose_preset" rows="4" class="w-full p-2 border rounded-lg">{{ prose_preset }}</textarea>
                        <label class="block font-semibold">Scene Input:</label>
                        <textarea name="text" rows="4" class="w-full p-2 border rounded-lg" placeholder="Paste or type your chapter text here..."></textarea>
                        <label class="block font-semibold">Characters Detected (edit/remove/add):</label>
                        <div class="flex flex-wrap gap-2 mb-2">
                            {% for name in detected_characters %}
                                <label class="bg-gray-200 px-2 py-1 rounded-lg flex items-center">
                                    <input type="checkbox" name="selected_characters_prose" value="{{ name }}"> {{ name }}
                                </label>
                            {% endfor %}
                        </div>
                        <input type="text" name="character_search" placeholder="Add character by name..." class="w-full p-2 border rounded-lg mb-2" oninput="autocompleteCharacter(this.value)">
                        <div id="autocomplete-results" class="flex flex-wrap gap-2 mb-2"></div>
                        <script>
                        function autocompleteCharacter(query) {
                            fetch('/story/{{ story_id }}/character_search?query=' + encodeURIComponent(query))
                                .then(function(response) { return response.json(); })
                                .then(function(data) {
                                    const resultsDiv = document.getElementById('autocomplete-results');
                                    resultsDiv.innerHTML = '';
                                    data.forEach(function(name) {
                                        const label = document.createElement('label');
                                        label.className = 'bg-green-200 px-2 py-1 rounded-lg flex items-center cursor-pointer';
                                        label.innerHTML = "<input type='checkbox' name='selected_characters_prose' value='" + name + "'> " + name;
                                        resultsDiv.appendChild(label);
                                    });
                                });
                        }
                        </script>
                        <textarea rows="6" class="w-full p-2 border rounded-lg bg-gray-100" readonly>{{ ai_prose | e }}</textarea>
                        <label class="block font-semibold">Select AI Model:</label>
                        <select name="prose_model" class="w-full p-2 border rounded-lg mb-2">
                            <option value="deepseek/deepseek-chat-v3.1">DeepSeek Chat v3.1</option>
                            <option value="deepseek/deepseek-r1-0528:free">DeepSeek R1 (Free)</option>
                            <option value="x-ai/grok-4-fast:free">Grok-4 Fast (Free)</option>
                            <option value="x-ai/grok-code-fast-1">Grok Code Fast</option>
                            <option value="moonshotai/kimi-k2">MoonshotAI Kimi K2</option>
                        </select>
                        <button type="submit" name="query_prose_selected" value="1" class="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 mt-2">Generate Prose</button>
                        <textarea rows="6" class="w-full p-2 border rounded-lg bg-purple-100" readonly>{{ ai_prose_selected | e }}</textarea>
                    </form>
                </div>
                <!-- Beat/Scene AI Generator -->
                <div>
                    <h3 class="text-xl font-bold text-gray-700 mb-2">Beat/Scene AI Generator</h3>
                    <form method="post" class="space-y-4">
                        <input type="hidden" name="query_beat_ai" value="1">
                        <label class="block font-semibold">Prompt (edit as needed):</label>
                        <textarea name="beat_preset" rows="10" class="w-full p-2 border rounded-lg">{{ beat_preset }}</textarea>
                        <label class="block font-semibold">Beat/Scene Input:</label>
                        <textarea name="beat_scene_input" rows="4" class="w-full p-2 border rounded-lg" placeholder="Paste or type your beats/scenes here..."></textarea>
                        <label class="block font-semibold">Characters Detected (edit/remove/add):</label>
                        <div class="flex flex-wrap gap-2 mb-2">
                            {% for name in detected_characters %}
                                <label class="bg-gray-200 px-2 py-1 rounded-lg flex items-center">
                                    <input type="checkbox" name="selected_characters_beat" value="{{ name }}"> {{ name }}
                                </label>
                            {% endfor %}
                        </div>
                        <input type="text" name="character_search_beat" placeholder="Add character by name..." class="w-full p-2 border rounded-lg mb-2" oninput="autocompleteCharacterBeat(this.value)">
                        <div id="autocomplete-results-beat" class="flex flex-wrap gap-2 mb-2"></div>
                        <script>
                        function autocompleteCharacterBeat(query) {
                            fetch('/story/{{ story_id }}/character_search?query=' + encodeURIComponent(query))
                                .then(function(response) { return response.json(); })
                                .then(function(data) {
                                    const resultsDiv = document.getElementById('autocomplete-results-beat');
                                    resultsDiv.innerHTML = '';
                                    data.forEach(function(name) {
                                        const label = document.createElement('label');
                                        label.className = 'bg-green-200 px-2 py-1 rounded-lg flex items-center cursor-pointer';
                                        label.innerHTML = "<input type='checkbox' name='selected_characters_beat' value='" + name + "'> " + name;
                                        resultsDiv.appendChild(label);
                                    });
                                });
                        }
                        </script>
                        <textarea rows="6" class="w-full p-2 border rounded-lg bg-gray-100" readonly>{{ ai_beat_scene | e }}</textarea>
                        <label class="block font-semibold">Select AI Model:</label>
                        <select name="beat_model" class="w-full p-2 border rounded-lg mb-2">
                            <option value="deepseek/deepseek-chat-v3.1">DeepSeek Chat v3.1</option>
                            <option value="deepseek/deepseek-r1-0528:free">DeepSeek R1 (Free)</option>
                            <option value="x-ai/grok-4-fast:free">Grok-4 Fast (Free)</option>
                            <option value="x-ai/grok-code-fast-1">Grok Code Fast</option>
                            <option value="moonshotai/kimi-k2">MoonshotAI Kimi K2</option>
                        </select>
                        <button type="submit" name="query_beat_selected" value="1" class="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 mt-2">Expand Beat/Scene</button>
                        <textarea rows="6" class="w-full p-2 border rounded-lg bg-indigo-100" readonly>{{ ai_beat_scene_selected | e }}</textarea>
                    </form>
                </div>
            </div>
            <hr>
            <!-- Beats/Scenes Section -->
            <h3 class="text-xl font-bold text-gray-700 mb-2">Beats/Scenes</h3>
            <ul class="space-y-2">
                {% for b in beats %}
                    <li class="border-b py-2 flex justify-between items-center">
                        <span>{{ b.description }}</span>
                        <a href="/story/{{ story_id }}/beat/{{ b.id }}/edit" class="text-blue-600 hover:underline">Edit</a>
                    </li>
                {% else %}
                    <li>No beats/scenes yet.</li>
                {% endfor %}
            </ul>
            <form method="post" class="space-y-4 mb-4">
                <input type="hidden" name="add_beat" value="1">
                <label class="block font-semibold">Beat Number:</label>
                <input name="beat_order" type="number" value="1" class="w-full p-2 border rounded-lg">
                <label class="block font-semibold">Description:</label>
                <textarea name="beat_description" rows="2" class="w-full p-2 border rounded-lg"></textarea>
                <button type="submit" class="bg-green-600 text-white px-3 py-1 rounded-lg hover:bg-green-700">Add Beat/Scene</button>
            </form>
            <hr>
            <!-- World Building Elements Section -->
            <h3 class="text-xl font-bold text-gray-700 mb-2">World Building Elements</h3>
            <form method="post" class="space-y-4 mb-4">
                <input type="hidden" name="add_world_element" value="1">
                <label class="block font-semibold">Category:</label>
                <select name="world_category" class="w-full p-2 border rounded-lg">
                    <option value="Settings">Settings</option>
                    <option value="Cultures">Cultures</option>
                    <option value="Magic and Tech">Magic and Tech</option>
                    <option value="History">History</option>
                    <option value="Races">Races</option>
                </select>
                <label class="block font-semibold">Description:</label>
                <textarea name="world_description" rows="2" class="w-full p-2 border rounded-lg"></textarea>
                <button type="submit" class="bg-green-600 text-white px-3 py-1 rounded-lg hover:bg-green-700">Add Element</button>
            </form>
            <ul class="space-y-2">
                {% for w in world_elements %}
                    <li class="border-b py-2 flex justify-between items-center">
                        <span>{{ w.category }}: {{ w.description }}</span>
                        <a href="/story/{{ story_id }}/world_element/{{ w.id }}/edit" class="text-blue-600 hover:underline">Edit</a>
                    </li>
                {% else %}
                    <li>No world building elements yet.</li>
                {% endfor %}
            </ul>
            <hr>
            <!-- Characters Section -->
            <h3 class="text-xl font-bold text-gray-700 mb-2">Characters</h3>
            <form method="post" class="space-y-4 mb-4">
                <input type="hidden" name="add_character" value="1">
                <label class="block font-semibold">Name:</label>
                <input name="char_name" class="w-full p-2 border rounded-lg">
                <label class="block font-semibold">Traits:</label>
                <textarea name="char_traits" rows="2" class="w-full p-2 border rounded-lg"></textarea>
                <label class="block font-semibold">Backstory:</label>
                <textarea name="char_backstory" rows="2" class="w-full p-2 border rounded-lg"></textarea>
                <button type="submit" class="bg-green-600 text-white px-3 py-1 rounded-lg hover:bg-green-700">Add Character</button>
            </form>
            <ul class="space-y-2">
                {% for c in characters %}
                    <li class="border-b py-2 flex flex-col">
                        <button type="button" onclick="document.getElementById('edit-char-{{ c.id }}').classList.toggle('hidden')" class="bg-gray-200 text-gray-800 px-3 py-1 rounded-lg font-semibold mb-2 hover:bg-gray-300">Edit {{ c.name }}</button>
                        <form id="edit-char-{{ c.id }}" method="post" class="space-y-2 mb-2 hidden">
                            <input type="hidden" name="edit_character_id" value="{{ c.id }}">
                            <label class="block font-semibold">Name:</label>
                            <input name="char_name" value="{{ c.name }}" class="w-full p-2 border rounded-lg">
                            <label class="block font-semibold">Traits:</label>
                            <textarea name="char_traits" rows="2" class="w-full p-2 border rounded-lg">{{ c.traits or '' }}</textarea>
                            <label class="block font-semibold">Backstory:</label>
                            <textarea name="char_backstory" rows="2" class="w-full p-2 border rounded-lg">{{ c.backstory or '' }}</textarea>
                            <button type="submit" class="bg-blue-600 text-white px-3 py-1 rounded-lg hover:bg-blue-700">Save</button>
                        </form>
                        <form method="post" class="inline-block">
                            <input type="hidden" name="delete_character_id" value="{{ c.id }}">
                            <button type="submit" class="bg-red-600 text-white px-3 py-1 rounded-lg hover:bg-red-700 ml-2">Delete</button>
                        </form>
                    </li>
                {% else %}
                    <li>No characters yet.</li>
                {% endfor %}
            </ul>
            <hr>
            <!-- Key Events Section -->
            <h3 class="text-xl font-bold text-gray-700 mb-2">Key Events</h3>
            <form method="post" class="space-y-4 mb-4">
                <input type="hidden" name="add_keyevent" value="1">
                <label class="block font-semibold">Description:</label>
                <textarea name="event_description" rows="2" class="w-full p-2 border rounded-lg"></textarea>
                <label class="block font-semibold">Order:</label>
                <input name="event_order" type="number" value="1" class="w-full p-2 border rounded-lg">
                <button type="submit" class="bg-green-600 text-white px-3 py-1 rounded-lg hover:bg-green-700">Add Key Event</button>
            </form>
            <ul class="space-y-2">
                {% for e in key_events %}
                    <li class="border-b py-2 flex flex-col">
                        <form method="post" class="space-y-2 mb-2">
                            <input type="hidden" name="edit_keyevent_id" value="{{ e.id }}">
                            <label class="block font-semibold">Description:</label>
                            <textarea name="event_description" rows="2" class="w-full p-2 border rounded-lg">{{ e.description }}</textarea>
                            <label class="block font-semibold">Order:</label>
                            <input name="event_order" type="number" value="{{ e.order }}" class="w-full p-2 border rounded-lg">
                            <button type="submit" class="bg-blue-600 text-white px-3 py-1 rounded-lg hover:bg-blue-700">Save</button>
                        </form>
                        <form method="post" class="inline-block">
                            <input type="hidden" name="delete_keyevent_id" value="{{ e.id }}">
                            <button type="submit" class="bg-red-600 text-white px-3 py-1 rounded-lg hover:bg-red-700 ml-2">Delete</button>
                        </form>
                    </li>
                {% else %}
                    <li>No key events yet.</li>
                {% endfor %}
            </ul>
            <hr>
            <!-- Key Events Section -->
            <h3 class="text-xl font-bold text-gray-700 mb-2">Key Events</h3>
            <form method="post" class="space-y-4 mb-4">
                <input type="hidden" name="add_keyevent" value="1">
                <label class="block font-semibold">Description:</label>
                <textarea name="event_description" rows="2" class="w-full p-2 border rounded-lg"></textarea>
                <label class="block font-semibold">Order:</label>
                <input name="event_order" type="number" value="1" class="w-full p-2 border rounded-lg">
                <button type="submit" class="bg-green-600 text-white px-3 py-1 rounded-lg hover:bg-green-700">Add Key Event</button>
            </form>
            <ul class="space-y-2">
                {% for e in key_events %}
                    <li class="border-b py-2 flex flex-col">
                        <form method="post" class="space-y-2 mb-2">
                            <input type="hidden" name="edit_keyevent_id" value="{{ e.id }}">
                            <label class="block font-semibold">Description:</label>
                            <textarea name="event_description" rows="2" class="w-full p-2 border rounded-lg">{{ e.description }}</textarea>
                            <label class="block font-semibold">Order:</label>
                            <input name="event_order" type="number" value="{{ e.order }}" class="w-full p-2 border rounded-lg">
                            <button type="submit" class="bg-blue-600 text-white px-3 py-1 rounded-lg hover:bg-blue-700">Save</button>
                        </form>
                        <form method="post" class="inline-block">
                            <input type="hidden" name="delete_keyevent_id" value="{{ e.id }}">
                            <button type="submit" class="bg-red-600 text-white px-3 py-1 rounded-lg hover:bg-red-700 ml-2">Delete</button>
                        </form>
                    </li>
                {% else %}
                    <li>No key events yet.</li>
                {% endfor %}
            </ul>
        </div>
    </body>
    </html>
    ''',
    chapter=chapter,
    story_id=story_id,
    beats=beats,
    world_elements=world_elements,
    characters=characters,
    detected_characters=detected_characters,
    prose_preset=prose_preset,
    ai_prose=ai_prose,
    ai_summary=ai_summary,
    beat_preset=beat_preset,
    ai_beat_scene=ai_beat_scene,
    ai_prose_deepseek=ai_prose_deepseek,
    ai_prose_free_deepseek=ai_prose_free_deepseek,
    ai_prose_grok4=ai_prose_grok4,
    ai_prose_grok_code=ai_prose_grok_code,
    ai_prose_kimi=ai_prose_kimi,
    ai_prose_selected=ai_prose_selected,
    ai_beat_scene_deepseek=ai_beat_scene_deepseek,
    ai_beat_scene_free_deepseek=ai_beat_scene_free_deepseek,
    ai_beat_scene_grok4=ai_beat_scene_grok4,
    ai_beat_scene_grok_code=ai_beat_scene_grok_code,
    ai_beat_scene_kimi=ai_beat_scene_kimi,
    ai_beat_scene_selected=ai_beat_scene_selected)
    edit_beat_id = request.form.get('edit_beat_id') if request.method == 'POST' else None

    # Characters in Scene Autocomplete Logic
    all_characters = Character.query.filter_by(story_id=story_id).all()
    beat_input = request.form.get('beat_description', '')
    if beat_input:
        detected_characters = [c.name for c in all_characters if re.search(r'\b' + re.escape(c.name) + r'\b', beat_input, re.IGNORECASE)]
    else:
        detected_characters = [c.name for c in all_characters]
    characters_in_scene = request.form.getlist('characters_in_scene') or detected_characters
    prose_preset = request.form.get('prose_preset', '')
    ai_prose = request.form.get('ai_prose', '')
    beat_preset = request.form.get('beat_preset', '')
    ai_beat_scene = request.form.get('ai_beat_scene', '')
    extracted_characters_prose = []  # TODO: Replace with actual extraction logic if needed

    chapter = Chapter.query.get_or_404(chapter_id)
    story = Story.query.get_or_404(story_id)
    characters = Character.query.filter_by(story_id=story_id).all()
    key_events = KeyEvent.query.filter_by(chapter_id=chapter_id).order_by(KeyEvent.order.asc()).all()
    edit_beat_id = request.form.get('edit_beat_id') if request.method == 'POST' else None
    world_elements = WorldBuildingElement.query.filter_by(chapter_id=chapter_id).all()

# --- Character Search API Endpoint ---
@app.route('/story/<int:story_id>/character_search')
@login_required
def character_search(story_id):
    query = request.args.get('query', '')
    all_characters = Character.query.filter_by(story_id=story_id).all()
    matches = [c.name for c in all_characters if query.lower() in c.name.lower()]
    return jsonify(matches)
    # ...existing code...

# --- CHARACTER ADD/EDIT ---
@app.route('/story/<int:story_id>/character/new', methods=['GET', 'POST'])
@login_required
def new_character(story_id):
    if request.method == 'POST':
        name = request.form['name']
        traits = request.form['traits']
        backstory = request.form['backstory']
        char = Character(story_id=story_id, name=name, traits=traits, backstory=backstory)
        db.session.add(char)
        db.session.commit()
        return redirect(url_for('characters', story_id=story_id))
    return f'''
    <form method="post">
        Name: <input name="name"><br>
        Traits: <textarea name="traits"></textarea><br>
        Backstory: <textarea name="backstory"></textarea><br>
        <input type="submit" value="Add Character">
    </form>
    <a href="/story/{story_id}/characters">Back</a>
    '''

@app.route('/story/<int:story_id>/character/<int:char_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_character(story_id, char_id):
    char = Character.query.get_or_404(char_id)
    if request.method == 'POST':
        char.name = request.form['name']
        char.traits = request.form['traits']
        char.backstory = request.form['backstory']
        db.session.commit()
        return redirect(url_for('characters', story_id=story_id))
    return f'''
    <form method="post">
        Name: <input name="name" value="{char.name}"><br>
        Traits: <textarea name="traits">{char.traits}</textarea><br>
        Backstory: <textarea name="backstory">{char.backstory}</textarea><br>
        <input type="submit" value="Save">
    </form>
    <a href="/story/{story_id}/characters">Back</a>
    '''

# --- PLOT BRAINSTORM ADD/EDIT ---
@app.route('/story/<int:story_id>/plot/edit', methods=['GET', 'POST'])
@login_required
def edit_plot_brainstorm(story_id):
    plot = PlotBrainstorm.query.filter_by(story_id=story_id).first()
    if request.method == 'POST':
        notes = request.form['notes']
        if plot:
            plot.notes = notes
        else:
            plot = PlotBrainstorm(story_id=story_id, notes=notes)
            db.session.add(plot)
        db.session.commit()
        return redirect(url_for('plot_brainstorm', story_id=story_id))
    notes_val = plot.notes if plot else ''
    return f'''
    <form method="post">
        Notes: <textarea name="notes">{notes_val}</textarea><br>
        <input type="submit" value="Save">
    </form>
    <a href="/story/{story_id}/plot">Back</a>
    '''

# --- BEAT/SCENE ADD/EDIT ---
@app.route('/story/<int:story_id>/beat/new', methods=['GET', 'POST'])
@login_required
def new_beat(story_id):
    if request.method == 'POST':
        description = request.form['description']
        order = request.form.get('order', 1)
        beat = BeatScene(story_id=story_id, description=description, order=order)
        db.session.add(beat)
        db.session.commit()
        return redirect(url_for('beatscenes', story_id=story_id))
    return f'''
    <form method="post">
        Description: <textarea name="description"></textarea><br>
        Order: <input name="order" type="number" value="1"><br>
        <input type="submit" value="Add Beat">
    </form>
    <a href="/story/{story_id}/beats">Back</a>
    '''

@app.route('/story/<int:story_id>/beat/<int:beat_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_beat(story_id, beat_id):
    beat = BeatScene.query.get_or_404(beat_id)
    if request.method == 'POST':
        beat.description = request.form['description']
        beat.order = request.form.get('order', beat.order)
        db.session.commit()
        return redirect(url_for('beatscenes', story_id=story_id))
    return f'''
    <form method="post">
        Description: <textarea name="description">{beat.description}</textarea><br>
        Order: <input name="order" type="number" value="{beat.order}"><br>
        <input type="submit" value="Save">
    </form>
    <a href="/story/{story_id}/beats">Back</a>
    '''

# --- EDIT WORLD BUILDING ELEMENT ---
@app.route('/story/<int:story_id>/world_element/<int:element_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_world_element(story_id, element_id):
    element = WorldBuildingElement.query.get_or_404(element_id)
    chapter = Chapter.query.get(element.chapter_id)
    if chapter.story_id != story_id:
        return 'Unauthorized', 403
    if request.method == 'POST':
        element.category = request.form.get('category', element.category)
        element.description = request.form.get('description', element.description)
        db.session.commit()
        return redirect(url_for('edit_chapter', story_id=story_id, chapter_id=element.chapter_id))
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Edit World Building Element</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen flex flex-col items-center p-6">
        <div class="bg-white rounded-xl shadow-lg w-full max-w-lg p-6 space-y-6">
            <h2 class="text-xl font-bold text-gray-800">Edit World Building Element</h2>
            <form method="post" class="space-y-4">
                <label class="block font-semibold">Category:</label>
                <select name="category" class="w-full p-2 border rounded-lg">
                    <option value="Settings" {% if element.category == 'Settings' %}selected{% endif %}>Settings</option>
                    <option value="Cultures" {% if element.category == 'Cultures' %}selected{% endif %}>Cultures</option>
                    <option value="Magic and Tech" {% if element.category == 'Magic and Tech' %}selected{% endif %}>Magic and Tech</option>
                    <option value="History" {% if element.category == 'History' %}selected{% endif %}>History</option>
                    <option value="Races" {% if element.category == 'Races' %}selected{% endif %}>Races</option>
                </select>
                <label class="block font-semibold">Description:</label>
                <textarea name="description" rows="4" class="w-full p-2 border rounded-lg">{{ element.description }}</textarea>
                <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">Save</button>
            </form>
            <a href="/story/{{ story_id }}/chapter/{{ element.chapter_id }}" class="text-blue-600 hover:underline">Back to Chapter</a>
        </div>
    </body>
    </html>
    ''', element=element, story_id=story_id)

# --- KEY EVENT ADD/EDIT ---
@app.route('/story/<int:story_id>/event/new', methods=['GET', 'POST'])
@login_required
def new_event(story_id):
    if request.method == 'POST':
        description = request.form['description']
        order = request.form.get('order', 1)
        event = KeyEvent(story_id=story_id, description=description, order=order)
        db.session.add(event)
        db.session.commit()
        return redirect(url_for('keyevents', story_id=story_id))
    return f'''
    <form method="post">
        Description: <textarea name="description"></textarea><br>
        Order: <input name="order" type="number" value="1"><br>
        <input type="submit" value="Add Event">
    </form>
    <a href="/story/{story_id}/events">Back</a>
    '''

@app.route('/story/<int:story_id>/event/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(story_id, event_id):
    event = KeyEvent.query.get_or_404(event_id)
    if request.method == 'POST':
        event.description = request.form['description']
        event.order = request.form.get('order', event.order)
        db.session.commit()
        return redirect(url_for('keyevents', story_id=story_id))
    return f'''
    <form method="post">
        Description: <textarea name="description">{event.description}</textarea><br>
        Order: <input name="order" type="number" value="{event.order}"><br>
        <input type="submit" value="Save">
    </form>
    <a href="/story/{story_id}/events">Back</a>
    '''
# --- END FORMS & EDITING ---

# --- SIGNUP PAGE ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password2 = request.form['password2']
        if password != password2:
            return 'Passwords do not match!'
        if User.query.filter_by(username=username).first():
            return 'Username already exists!'
        if User.query.filter_by(email=email).first():
            return 'Email already registered!'
        hashed_pw = generate_password_hash(password)
        user = User(username=username, email=email, password_hash=hashed_pw)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('stories'))
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sign Up</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen flex flex-col items-center justify-center p-6">
        <div class="bg-white rounded-xl shadow-lg w-full max-w-md p-8 space-y-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-2 text-center">Sign Up</h2>
            <form method="post" class="space-y-4">
                <input name="username" placeholder="Username" class="w-full p-2 border rounded-lg">
                <input name="email" placeholder="Email" class="w-full p-2 border rounded-lg">
                <input name="password" type="password" placeholder="Password" class="w-full p-2 border rounded-lg">
                <input name="password2" type="password" placeholder="Confirm Password" class="w-full p-2 border rounded-lg">
                <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 w-full">Sign Up</button>
            </form>
            <div class="text-center mt-4">
                <a href="/login" class="text-blue-600 hover:underline">Already have an account? Login</a>
            </div>
        </div>
    </body>
    </html>
    ''')
# --- END SIGNUP PAGE ---

# --- LOGIN PAGE ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('stories'))
        return 'Invalid credentials!'
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen flex flex-col items-center justify-center p-6">
        <div class="bg-white rounded-xl shadow-lg w-full max-w-md p-8 space-y-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-2 text-center">Login</h2>
            <form method="post" class="space-y-4">
                <input name="username" placeholder="Username" class="w-full p-2 border rounded-lg">
                <input name="password" type="password" placeholder="Password" class="w-full p-2 border rounded-lg">
                <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 w-full">Login</button>
            </form>
            <div class="text-center mt-4">
                <a href="/signup" class="text-blue-600 hover:underline">Need an account? Sign up</a>
            </div>
        </div>
    </bodyTHI>
    </html>
    ''')
# --- END LOGIN PAGE ---

# Example protected route
@app.route('/dashboard')
@login_required
def dashboard():
    return f"Welcome, {current_user.username}!"

if __name__ == '__main__':
    # Automatically create tables for SQLite if they don't exist
    with app.app_context():
        db.create_all()
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port, threaded=True, use_reloader=False)
