import os
import json
import requests
from weasyprint import HTML
import smtplib
from email.message import EmailMessage
from datetime import datetime, date

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
SENDER_EMAIL = os.environ.get("MY_EMAIL")
APP_PASSWORD = os.environ.get("MY_PASSWORD")

# Load the recipients from the JSON file
with open("recipients.json", "r") as file:
    RECIPIENTS_DATA = json.load(file)

BOOKS = [
    ("1nephi", 22), ("2nephi", 33), ("jacob", 7), ("enos", 1), 
    ("jarom", 1), ("omni", 1), ("wordsofmormon", 1), ("mosiah", 29), 
    ("alma", 63), ("helaman", 16), ("3nephi", 30), ("4nephi", 1), 
    ("mormon", 9), ("ether", 15), ("moroni", 10)
]

def get_chapter_list():
    chapters = []
    for book, num_chapters in BOOKS:
        for i in range(1, num_chapters + 1):
            chapters.append((book, i))
    return chapters

ALL_CHAPTERS = get_chapter_list()

def get_todays_chapter(start_date):
    days_since_start = (date.today() - start_date).days
    if days_since_start < 0:
        days_since_start = 0
    index = days_since_start % len(ALL_CHAPTERS)
    return ALL_CHAPTERS[index]

def fetch_chapter(book_slug, chapter_num):
    url = f"https://openscriptureapi.org/api/scriptures/v1/lds/en/volume/bookofmormon/{book_slug}/{chapter_num}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()['chapter']

def build_pdf(chapter_data, filename):
    book_title = chapter_data['bookTitle']
    chapter_num = chapter_data['number']
    summary = chapter_data.get('summary', '')
    verses = chapter_data.get('verses', [])

    verses_html = ""
    for i, verse in enumerate(verses, 1):
        text = verse['text'].strip()
        verses_html += f"""
        <div class="verse">
            <span class="verse-number">{i}</span>
            <span class="verse-text">{text}</span>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{ margin: 2.5cm 2cm; @bottom-center {{ content: "Page " counter(page); font-family: 'Helvetica', sans-serif; font-size: 10pt; color: #888; }} }}
            body {{ font-family: 'Georgia', serif; font-size: 13pt; line-height: 1.7; color: #222; }}
            h1 {{ text-align: center; font-size: 26pt; margin-bottom: 5px; color: #111; }}
            .summary {{ text-align: center; font-style: italic; color: #555; font-size: 11pt; margin-bottom: 30px; padding: 0 20px; }}
            .verse {{ margin-bottom: 12px; text-align: justify; }}
            .verse-number {{ font-family: 'Helvetica', sans-serif; font-weight: bold; font-size: 10pt; color: #999; vertical-align: super; margin-right: 6px; }}
        </style>
    </head>
    <body>
        <h1>{book_title} {chapter_num}</h1>
        <div class="summary">{summary}</div>
        <div class="content">{verses_html}</div>
    </body>
    </html>
    """
    HTML(string=html_content).write_pdf(filename)
    return filename

def send_email(recipient_email, pdf_path, book_title, chapter_num):
    msg = EmailMessage()
    msg['Subject'] = f"Today's Reading: {book_title} {chapter_num}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg.set_content(f"Here is your daily scripture reading for {book_title} {chapter_num}. Have a great day!")

    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=pdf_path)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(SENDER_EMAIL, APP_PASSWORD)
        smtp.send_message(msg)
    print(f"✅ Email sent successfully to {recipient_email}!")

if __name__ == "__main__":
    downloaded_chapters = {}

    for person in RECIPIENTS_DATA:
        email = person["email"]
        
        # Convert the string "2026-10-20" into a Python date object
        start_date = datetime.strptime(person["start_date"], "%Y-%m-%d").date()
        
        book_slug, chapter_num = get_todays_chapter(start_date)
        chapter_key = f"{book_slug}_{chapter_num}"
        
        print(f"\n--- Processing for {email} ---")
        print(f"Assigned reading: {book_slug.capitalize()} {chapter_num}")
        
        if chapter_key not in downloaded_chapters:
            chapter_data = fetch_chapter(book_slug, chapter_num)
            downloaded_chapters[chapter_key] = chapter_data
        else:
            chapter_data = downloaded_chapters[chapter_key]
            
        filename = f"{book_slug}_{chapter_num}.pdf"
        build_pdf(chapter_data, filename)
        send_email(email, filename, chapter_data['bookTitle'], chapter_data['number'])
