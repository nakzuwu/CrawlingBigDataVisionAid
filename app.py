import streamlit as st
from mongoengine import connect
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
connect(
    db='notion_clone',
    host=st.secrets["mongo"]["uri"]
)
class Article(Document):
    title = StringField()
    content = StringField()
    source = StringField()
    url = StringField()
    published_at = StringField()
    processed_at = DateTimeField()

def generate_wordcloud():
    contents = [a.content for a in Article.objects if a.content]
    if not contents:
        return None

    all_text = ' '.join(contents)
    words = re.findall(r'\b[a-zA-Z]+\b', all_text.lower())
    stopwords = set(['yang', 'untuk', 'dari', 'dan', 'atau', 'pada', 'dengan', 'ini', 'itu', 'the', 'is', 'in', 'of', 'a', 'an', 'to'])
    filtered_words = [word for word in words if word not in stopwords and len(word) > 2]

    wordcloud = WordCloud(width=1000, height=500, background_color='white',
                          colormap='viridis', max_words=150, collocations=False).generate(' '.join(filtered_words))
    
    img_buffer = BytesIO()
    wordcloud.to_image().save(img_buffer, format='PNG')
    return img_buffer

def get_source_distribution():
    sources = [a.source for a in Article.objects if a.source]
    source_counts = Counter(sources)
    labels = list(source_counts.keys())
    values = list(source_counts.values())

    fig, ax = plt.subplots(figsize=(8, 6))
    colors = plt.cm.tab20.colors
    ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors)
    ax.set_title('Distribusi Sumber Artikel')
    return fig

def get_timeline_data():
    dates = []
    for a in Article.objects:
        if a.published_at:
            try:
                dt = date_parse(a.published_at)
                dates.append(dt.date())
            except:
                continue
    if not dates:
        return None

    df = pd.DataFrame({'date': dates})
    df = df.value_counts().reset_index(name='count')
    df = df.rename(columns={0: 'count'})

    full_range = pd.date_range(start=df['date'].min(), end=df['date'].max())
    df = df.set_index('date').reindex(full_range, fill_value=0)
    df.index.name = 'date'
    df = df.reset_index()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df['date'], df['count'], marker='o', color='teal')
    ax.set_title('Timeline Artikel')
    ax.set_xlabel('Tanggal')
    ax.set_ylabel('Jumlah')
    fig.autofmt_xdate()
    return fig

def render_dashboard():
    wordcloud_img = generate_wordcloud()
    source_fig = get_source_distribution()
    timeline_fig = get_timeline_data()

    st.title("📊 Dashboard Artikel")

    st.subheader("🔤 Wordcloud")
    if wordcloud_img:
        st.image(wordcloud_img.getvalue())
    else:
        st.warning("Tidak ada konten untuk ditampilkan.")

    st.subheader("📈 Timeline Publikasi")
    if timeline_fig:
        st.pyplot(timeline_fig)
    else:
        st.warning("Data timeline tidak ditemukan.")

    st.subheader("📊 Distribusi Sumber Artikel")
    if source_fig:
        st.pyplot(source_fig)

    st.subheader("📰 Artikel Terbaru")
    for a in Article.objects.order_by('-processed_at')[:5]:
        st.markdown(f"- [{a.title}]({a.url}) ({a.source})")

    st.markdown(f"**Total artikel:** {Article.objects.count()}")

if __name__ == '__main__':
    render_dashboard()