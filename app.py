from flask import Flask, render_template
from pymongo import MongoClient
from collections import Counter
import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from io import BytesIO
import base64
from wordcloud import WordCloud
import numpy as np

app = Flask(__name__)

# Configuration
MONGO_URI = 'mongodb+srv://nakzuwu:Nakzuwu1!@cluster0.yqfbchb.mongodb.net/'
DB_NAME = 'notion_clone'
COLLECTION_NAME = 'crawled_data'

def get_database_connection():
    """Establish connection to MongoDB"""
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    return db[COLLECTION_NAME]

def generate_wordcloud():
    """Generate word cloud from article content"""
    try:
        # Get database connection
        collection = get_database_connection()
        
        # Safely get content from all documents
        contents = []
        for doc in collection.find({}, {'content': 1}):
            if 'content' in doc and doc['content']:
                contents.append(doc['content'])
        
        if not contents:
            return None  # Return None if no content found
        
        all_text = ' '.join(contents)
        
        # Enhanced text cleaning
        words = re.findall(r'\b[a-zA-Z]+\b', all_text.lower())  # Only alphabetic words
        stopwords = {
            'the', 'and', 'to', 'of', 'a', 'in', 'is', 'it', 'that', 'for', 'on', 'with', 'as', 'at', 'by', 
            'this', 'be', 'are', 'was', 'were', 'an', 'or', 'you', 'your', 'we', 'our', 'us', 'they', 'them',
            'their', 'has', 'have', 'had', 'but', 'so', 'if', 'can', 'will', 'would', 'should', 'could', 'about',
            'from', 'how', 'what', 'when', 'where', 'which', 'who', 'whom', 'why', 'notion', 'todoist', 'evernote'
        }
        
        filtered_words = [word for word in words if word not in stopwords and len(word) > 2 and word.isalpha()]
        
        # Configure word cloud with better parameters
        wordcloud = WordCloud(
            width=1000,
            height=500,
            background_color='white',
            colormap='viridis',
            max_words=150,
            collocations=False,  # Better for meaningful word combinations
            stopwords=stopwords,
            min_font_size=10,
            max_font_size=150,
            random_state=42  # For reproducible results
        ).generate(' '.join(filtered_words))
        
        # Convert to base64
        img_buffer = BytesIO()
        wordcloud.to_image().save(img_buffer, format='PNG', quality=95)
        img_str = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        # Explicit cleanup
        plt.close('all')
        return img_str
        
    except Exception as e:
        print(f"Error generating wordcloud: {str(e)}")
        plt.close('all')  # Ensure cleanup even on error
        return None
def get_source_distribution():
    """Generate source distribution pie chart"""
    collection = get_database_connection()
    sources = [doc['source'] for doc in collection.find({}, {'source': 1})]
    source_counts = Counter(sources)
    
    # Prepare data
    labels = list(source_counts.keys())
    values = list(source_counts.values())
    
    # Create chart
    plt.figure(figsize=(10, 8))
    colors = plt.cm.Paired(np.linspace(0, 1, len(labels)))
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors)
    plt.title('Article Sources Distribution', pad=20)
    
    # Convert to base64
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='PNG', bbox_inches='tight')
    plt.close()
    return base64.b64encode(img_buffer.getvalue()).decode('utf-8')

def get_timeline_data():
    """Generate collection timeline"""
    collection = get_database_connection()
    
    # Get documents that have the processed_at field
    dates = []
    for doc in collection.find({}):
        if 'processed_at' in doc:
            dates.append(doc['processed_at'])
        # Fallback to _id generation time if processed_at doesn't exist
        elif '_id' in doc:
            dates.append(doc['_id'].generation_time)
    
    if not dates:
        return None
    
    # Process dates
    date_counts = Counter([date.strftime('%Y-%m-%d') for date in dates])
    sorted_dates = sorted(date_counts.items(), key=lambda x: x[0])
    days = [date[0] for date in sorted_dates]
    counts = [date[1] for date in sorted_dates]
    
    # Create chart
    plt.figure(figsize=(12, 6))
    plt.bar(days, counts, color='#4f77aa')
    plt.xlabel('Date')
    plt.ylabel('Articles Collected')
    plt.title('Collection Timeline')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert to base64
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='PNG', bbox_inches='tight')
    plt.close()
    return base64.b64encode(img_buffer.getvalue()).decode('utf-8')

@app.route('/')
def dashboard():
    """Main dashboard route"""
    collection = get_database_connection()
    
    # Generate visualizations
    wordcloud_img = generate_wordcloud()
    source_dist_img = get_source_distribution()
    timeline_img = get_timeline_data()
    
    # Get recent articles
    recent_articles = list(collection.find({}, {'title': 1, 'url': 1, 'source': 1})
                          .sort('processed_at', -1)
                          .limit(5))
    
    return render_template('dashboard.html',
                         wordcloud_img=wordcloud_img,
                         source_dist_img=source_dist_img,
                         timeline_img=timeline_img,
                         recent_articles=recent_articles,
                         total_articles=collection.count_documents({}))

if __name__ == '__main__':
    app.run(debug=True)