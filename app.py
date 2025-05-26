import streamlit as st
from pymongo import MongoClient
from collections import Counter
import re
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from io import BytesIO
from wordcloud import WordCloud
from dateutil.parser import parse as date_parse
import numpy as np
import pandas as pd
from PIL import Image

# Configuration
MONGO_URI = 'mongodb+srv://nakzuwu:Nakzuwu1!@cluster0.yqfbchb.mongodb.net/'
DB_NAME = 'notion_clone'
COLLECTION_NAME = 'crawled_data'

# Database connection
@st.cache_resource
def get_collection():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    return db[COLLECTION_NAME]

# Word cloud generation
def generate_wordcloud(collection):
    contents = []
    for doc in collection.find({}, {'content': 1}):
        if 'content' in doc and doc['content']:
            contents.append(doc['content'])

    if not contents:
        return None

    all_text = ' '.join(contents)
    words = re.findall(r'\b[a-zA-Z]+\b', all_text.lower())
    stopwords = set([
        'the', 'and', 'to', 'of', 'a', 'in', 'is', 'it', 'that', 'for', 'on', 'with',
        'as', 'at', 'by', 'this', 'be', 'are', 'was', 'were', 'an', 'or', 'you', 'your',
        'we', 'our', 'us', 'they', 'them', 'their', 'has', 'have', 'had', 'but', 'so',
        'if', 'can', 'will', 'would', 'should', 'could', 'about', 'from', 'how', 'what',
        'when', 'where', 'which', 'who', 'whom', 'why', 'notion', 'todoist', 'evernote',
        'i', 'me', 'my', 'mine', 'myself', 'he', 'him', 'his', 'herself', 'itself',
        'still', 'just', 'also', 'even', 'always', 'almost'
    ])

    filtered_words = [word for word in words if word not in stopwords and len(word) > 2 and word.isalpha()]

    wordcloud = WordCloud(
        width=1000,
        height=500,
        background_color='white',
        colormap='viridis',
        max_words=150,
        collocations=False
    ).generate(' '.join(filtered_words))

    img_buffer = BytesIO()
    wordcloud.to_image().save(img_buffer, format='PNG')
    img_buffer.seek(0)
    return img_buffer

# Source distribution
def get_source_distribution(collection):
    sources = [doc.get('source', 'Unknown') for doc in collection.find({}, {'source': 1})]
    source_counts = Counter(sources)
    labels = list(source_counts.keys())
    values = list(source_counts.values())

    fig, ax = plt.subplots(figsize=(8, 6))
    colors = plt.cm.Paired(np.linspace(0, 1, len(labels)))
    ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors)
    ax.set_title('Article Sources Distribution')
    return fig

# Timeline chart
def get_timeline_data(collection):
    dates = []

    for doc in collection.find({}):
        published = doc.get('published_at')
        if published:
            try:
                parsed = date_parse(published) if isinstance(published, str) else published
                dates.append(parsed.date())
            except Exception:
                continue

    if not dates:
        return None

    df = pd.DataFrame({'date': dates})
    df = df.value_counts().reset_index(name='count').rename(columns={0: 'count'})
    full_range = pd.date_range(start=df['date'].min(), end=df['date'].max())
    df = df.set_index('date').reindex(full_range, fill_value=0).reset_index()
    df.columns = ['date', 'count']

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df['date'], df['count'], marker='o', color='blue')
    ax.set_title('Publication Timeline')
    ax.set_xlabel('Date')
    ax.set_ylabel('Articles Published')
    ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=8))
    ax.grid(True)
    plt.xticks(rotation=45)
    return fig

# Streamlit App
def main():
    st.set_page_config(page_title="Notion Dashboard", layout="wide")
    st.title("📊 Notion Clone Dashboard")
    collection = get_collection()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Word Cloud from Articles")
        wc_img = generate_wordcloud(collection)
        if wc_img:
            st.image(wc_img, use_column_width=True)
        else:
            st.warning("No content available for word cloud.")

    with col2:
        st.subheader("Source Distribution")
        fig1 = get_source_distribution(collection)
        st.pyplot(fig1)

    st.subheader("🕒 Article Publication Timeline")
    fig2 = get_timeline_data(collection)
    if fig2:
        st.pyplot(fig2)
    else:
        st.info("No valid publication dates found.")

    st.subheader("📰 Recent Articles")
    recent = list(collection.find({}, {'title': 1, 'url': 1, 'source': 1}).sort('processed_at', -1).limit(5))
    for article in recent:
        st.markdown(f"- [{article.get('title', 'No Title')}]({article.get('url', '#')}) | *{article.get('source', 'Unknown')}*")

    st.markdown(f"**Total Articles**: {collection.count_documents({})}")

if __name__ == "__main__":
    main()
