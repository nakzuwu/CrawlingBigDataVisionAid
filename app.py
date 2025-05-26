import streamlit as st
from pymongo import MongoClient
from collections import Counter
import re
from datetime import datetime
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import numpy as np
import pandas as pd
from dateutil.parser import parse as date_parse
from matplotlib.ticker import MaxNLocator

# MongoDB setup from Streamlit secrets
MONGO_URI = st.secrets["mongo"]["uri"]
DB_NAME = 'notion_clone'
COLLECTION_NAME = 'crawled_data'

@st.cache_resource
def get_database_connection():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME][COLLECTION_NAME]

collection = get_database_connection()

def generate_wordcloud():
    contents = [doc.get('content', '') for doc in collection.find({}, {'content': 1}) if doc.get('content')]
    if not contents:
        return None
    
    all_text = ' '.join(contents)
    words = re.findall(r'\b[a-zA-Z]+\b', all_text.lower())
    
    stopwords = set(STOPWORDS)
    filtered_words = [word for word in words if word not in stopwords and len(word) > 2]

    wordcloud = WordCloud(
        width=1000,
        height=500,
        background_color='white',
        colormap='viridis',
        max_words=150,
        collocations=False,
        stopwords=stopwords  # ✅ Ini sudah benar
    ).generate(' '.join(filtered_words))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    return fig
def get_source_distribution():
    sources = [doc.get('source', 'Unknown') for doc in collection.find({}, {'source': 1})]
    source_counts = Counter(sources)
    labels, values = zip(*source_counts.items())

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, colors=plt.cm.Paired(np.linspace(0, 1, len(labels))))
    ax.set_title('Article Sources Distribution', pad=20)
    return fig

def get_timeline_data():
    dates = []
    for doc in collection.find({}):
        published = doc.get('published_at')
        if published:
            try:
                dates.append(date_parse(published).date())
            except Exception:
                continue

    if not dates:
        return None

    df = pd.DataFrame({'date': dates})
    df = df.value_counts().reset_index(name='count').rename(columns={0: 'count'})
    full_range = pd.date_range(start=df['date'].min(), end=df['date'].max())
    df = df.set_index('date').reindex(full_range, fill_value=0).reset_index().rename(columns={'index': 'date'})

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(df['date'], df['count'], marker='o', linestyle='-', color='#4f77aa')
    ax.set_title('Publication Timeline')
    ax.set_xlabel('Date')
    ax.set_ylabel('Articles Published')
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(True)
    plt.xticks(rotation=45)
    return fig

# ---- Streamlit Page Layout ----
st.title("📊 Notion Clone Dashboard")

# Wordcloud Section
st.subheader("🧠 Word Cloud")
wordcloud_fig = generate_wordcloud()
if wordcloud_fig:
    st.pyplot(wordcloud_fig)
else:
    st.info("No content available to generate wordcloud.")

# Source Distribution
st.subheader("📈 Source Distribution")
st.pyplot(get_source_distribution())

# Timeline Chart
st.subheader("🗓️ Publication Timeline")
timeline_fig = get_timeline_data()
if timeline_fig:
    st.pyplot(timeline_fig)
else:
    st.warning("No timeline data available.")

# Recent Articles
st.subheader("📰 Recent Articles")
recent_articles = list(collection.find({}, {'title': 1, 'url': 1, 'source': 1}).sort('processed_at', -1).limit(5))
for article in recent_articles:
    st.markdown(f"- [{article.get('title', 'Untitled')}]({article.get('url', '#')}) - *{article.get('source', 'Unknown')}*")

# Total Count
st.markdown(f"**Total articles:** {collection.count_documents({})}")
