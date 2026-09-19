import pandas as pd
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# === CONFIG ===
REVIEW_CSV = "../data/raw/videogames_reviews_dataset.csv"
GAMES_CSV = "../data/raw/videogames_mined_last5years.csv"
OUTPUT_PDF = "../reports/steam_review_analysis.pdf"

# === LOAD DATA ===
print("Caricamento dataset in corso...")
df_reviews = pd.read_csv(
    REVIEW_CSV, 
    on_bad_lines="skip", 
    quoting=1, 
    encoding="utf-8", 
    low_memory=False
)
df_games = pd.read_csv(GAMES_CSV)

# === MERGE DATA ===
# Pulizia chiavi per il merge
df_reviews["appid"] = pd.to_numeric(df_reviews["appid"], errors="coerce")
df_games["AppID"] = pd.to_numeric(df_games["AppID"], errors="coerce")

df_reviews = df_reviews.dropna(subset=["appid"])
df_games = df_games.dropna(subset=["AppID"])

df_reviews["appid"] = df_reviews["appid"].astype("int64")
df_games["AppID"] = df_games["AppID"].astype("int64")

# Rimuoviamo 'Name' dal dataset dei giochi per evitare che Pandas crei Name_x e Name_y,
# mantenendo il 'Name' già presente nel dataset delle recensioni
if "Name" in df_games.columns:
    df_games = df_games.drop(columns=["Name"])

df = df_reviews.merge(df_games, left_on="appid", right_on="AppID", how="left")

# === CLEANING ===
df = df.dropna(subset=["review"])
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df["review_length"] = df["review"].astype(str).str.len()
df["word_count"] = df["review"].astype(str).str.split().str.len()
df["sentiment"] = df["voted_up"].map({True: "Positive", False: "Negative"})

if "IsFree" in df.columns:
    df["IsFree"] = df["IsFree"].fillna(False).astype(str).str.lower().map({"true": True, "false": False})

if "PriceUSD" in df.columns:
    df["PriceUSD"] = pd.to_numeric(df["PriceUSD"], errors="coerce")

if "MetacriticScore" in df.columns:
    df["MetacriticScore"] = pd.to_numeric(df["MetacriticScore"], errors="coerce")

if "release_year" in df.columns:
    df["release_year"] = pd.to_numeric(df["release_year"], errors="coerce").astype("Int64")

# === PREPARE PDF ===
print("Generazione report PDF...")
styles = getSampleStyleSheet()
report = []

def add_paragraph(text, style='BodyText', space=True):
    report.append(Paragraph(text, styles[style]))
    if space:
        report.append(Spacer(1, 12))

# === HEADER ===
add_paragraph("Steam Game Review Analysis", "Title")
add_paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "Normal")
report.append(PageBreak())

# === BASIC STATS ===
add_paragraph("Basic Review Statistics", "Heading2")
add_paragraph(f"Total reviews: {len(df)}")
add_paragraph(f"Unique games reviewed: {df['appid'].nunique()}")
add_paragraph(f"Review date range: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
add_paragraph(f"Avg review length (characters): {df['review_length'].mean():.2f}")
add_paragraph(f"Avg review length (words): {df['word_count'].mean():.2f}")
add_paragraph(f"Positive reviews: {df['voted_up'].sum()} ({df['voted_up'].mean() * 100:.2f}%)")
add_paragraph(f"Negative reviews: {(~df['voted_up']).sum()}")
report.append(PageBreak())

# === GAME METADATA STATS ===
add_paragraph("Game Metadata Statistics", "Heading2")
if "IsFree" in df.columns:
    add_paragraph(f"Free games reviewed: {df[df['IsFree'] == True]['appid'].nunique()}")
    add_paragraph(f"Paid games reviewed: {df[df['IsFree'] == False]['appid'].nunique()}")
if "PriceUSD" in df.columns:
    add_paragraph(f"Avg price (USD): {df['PriceUSD'].dropna().mean():.2f}")
if "MetacriticScore" in df.columns:
    add_paragraph(f"Avg Metacritic score: {df['MetacriticScore'].dropna().mean():.2f}")

# === GENRES ===
if "Genres" in df.columns:
    add_paragraph("Top 50 Genres", "Heading2")
    df["Genres"] = df["Genres"].fillna("Unknown").astype(str)
    top_genre_counts = df["Genres"].str.split(",").explode().str.strip().value_counts().head(50)
    for genre, count in top_genre_counts.items():
        add_paragraph(f"{genre}: {count} reviews")

# === TOP GAMES ===
if "Name" in df.columns:
    add_paragraph("Most Reviewed Games", "Heading2")
    top_games = df["Name"].dropna().value_counts().head(10)
    for name, count in top_games.items():
        add_paragraph(f"{name}: {count} reviews")

# === RELEASE YEARS ===
if "release_year" in df.columns:
    add_paragraph("Reviews by Game Release Year", "Heading2")
    year_counts = df["release_year"].dropna().astype(int).value_counts().sort_index()
    for year, count in year_counts.items():
        add_paragraph(f"{year}: {count} reviews")

# === EXPORT ===
SimpleDocTemplate(OUTPUT_PDF, pagesize=A4).build(report)
print(f"Report completato con successo: {OUTPUT_PDF}")