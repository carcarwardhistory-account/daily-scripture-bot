import os
import csv
import io
import requests
from weasyprint import HTML
import smtplib
from email.message import EmailMessage
from datetime import datetime, date, timezone, timedelta

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
SENDER_EMAIL = os.environ.get("MY_EMAIL")
APP_PASSWORD = os.environ.get("MY_PASSWORD")

# PASTE YOUR GOOGLE SHEET CSV LINK HERE
SHEET_CSV_URL = "PASTE_YOUR_CSV_LINK_HERE"

PHT = timezone(timedelta(hours=8))

VOLUMES = {
    "Book of Mormon": {
        "api_slug": "bookofmormon",
        "books": [("1nephi", 22), ("2nephi", 33), ("jacob", 7), ("enos", 1), ("jarom", 1), ("omni", 1), ("wordsofmormon", 1), ("mosiah", 29), ("alma", 63), ("helaman", 16), ("3nephi", 30), ("4nephi", 1), ("mormon", 9), ("ether", 15), ("moroni", 10)]
    },
    "New Testament": {
        "api_slug": "newtestament",
        "books": [("matthew", 28), ("mark", 16), ("luke", 24), ("john", 21), ("acts", 28), ("romans", 16), ("1corinthians", 16), ("2corinthians", 13), ("galatians", 6), ("ephesians", 6), ("philippians", 4), ("colossians", 4), ("1thessalonians", 5), ("2thessalonians", 3), ("1timothy", 6), ("2timothy", 4), ("titus", 3), ("philemon", 1), ("hebrews", 13), ("james", 5), ("1peter", 5), ("2peter", 3), ("1john", 5), ("2john", 1), ("3john", 1), ("jude", 1), ("revelation", 22)]
    },
    "Old Testament": {
        "api_slug": "oldtestament",
        "books": [("genesis", 50), ("exodus", 40), ("leviticus", 27), ("numbers", 36), ("deuteronomy", 34), ("joshua", 24), ("judges", 21), ("ruth", 4), ("1samuel", 31), ("2samuel", 24), ("1kings", 22), ("2kings", 25), ("1chronicles", 29), ("2chronicles", 36), ("ezra", 10), ("nehemiah", 13), ("esther", 10), ("job", 42), ("psalms", 150), ("proverbs", 31), ("ecclesiastes", 12), ("songofsolomon", 8), ("isaiah", 66), ("jeremiah", 52), ("lamentations", 5), ("ezekiel", 48), ("daniel", 12), ("hosea", 14), ("joel", 3), ("amos", 9), ("obadiah", 1), ("jonah", 4), ("micah", 7), ("nahum", 3), ("habakkuk", 3), ("zephaniah", 3), ("haggai", 2), ("zechariah", 14), ("malachi", 4)]
    },
    "Doctrine and Covenants": {
        "api_slug": "dc-testament",
        "books": [("dc", 138)]
    },
    "Pearl of Great Price": {
        "api_slug": "pgp",
        "books": [("moses", 8), ("abraham", 5), ("jsm", 1), ("aoff", 1)]
    }
}

def get_all_chapters(volume_name):
    chapters = []
    volume_data = VOLUMES[volume_name]
    for book, num_chapters in volume_data["books"]:
        for i in range(1, num_chapters + 1):
            chapters.append((book, i))
    return chapters

def get_todays_chapter(start_date, volume_name):
    today_pht = datetime.now(PHT).date()
    days_since_start = (today_pht - start_date).days
    if days_since_start < 0:
        days_since_start = 0
        
    all_chapters = get_all_chapters(volume_name)
    index = days_since_start % len(all_chapters)
    return all_chapters[index]

def fetch_chapter(volume_name, book_slug, chapter_num):
    api_slug = VOLUMES[volume_name]["api_slug"]
    url = f"https://openscriptureapi.org/api/scriptures/v1/lds/en/volume/{api_slug}/{book_slug}/{chapter_num}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()['chapter']

def build_pdf(chapter_data, filename, user_name):
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
            .greeting {{ text-align: center; font-size: 12pt; color: #555; margin-bottom: 20px; }}
            .summary {{ text-align: center; font-style: italic; color: #555; font-size: 11pt; margin-bottom: 30px; padding: 0 20px; }}
            .verse {{ margin-bottom: 12px; text-align: justify; }}
            .verse-number {{ font-family: 'Helvetica', sans-serif; font-weight: bold; font-size: 10pt; color: #999; vertical-align: super; margin-right: 6px; }}
        </style>
    </head>
    <body>
        <div class="greeting">Good morning, {user_name}!</div>
        <h1>{book_title} {chapter_num}</h1>
        <div class="summary">{summary}</div>
        <div class="content">{verses_html}</div>
    </body>
    </html>
    """
    HTML(string=html_content).write_pdf(filename)
    return filename

def send_email(recipient_email, user_name, pdf_path, book_title, chapter_num):
    msg = EmailMessage()
    msg['Subject'] = f"{user_name}, here is your daily reading: {book_title} {chapter_num}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg.set_content(f"Good morning, {user_name}!\n\nHere is your daily scripture reading for {book_title} {chapter_num}. Have a great day!")

    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=pdf_path)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(SENDER_EMAIL, APP_PASSWORD)
        smtp.send_message(msg)
    print(f"✅ Email sent successfully to {user_name} ({recipient_email})!")

def get_recipients_from_sheet():
    print("Downloading subscriber list from Google Sheets...")
    response = requests.get(SHEET_CSV_URL)
    response.raise_for_status()
    csv_data = csv.DictReader(io.StringIO(response.text))
    
    recipients = []
    
    EMAIL_HEADER = "Email Address"
    DATE_HEADER = "What date would you like to start reading?"
    NAME_HEADER = "What is your name?"
    VOLUME_HEADER = "Which volume would you like to read?"
    TIME_HEADER = "What time would you like to receive your daily email? (Philippine Time)"
    
    for row in csv_data:
        if EMAIL_HEADER in row and DATE_HEADER in row and row[EMAIL_HEADER]:
            status = row.get("Status", "").strip().lower()
            if status == "paused":
                continue

            email = row[EMAIL_HEADER].strip()
            date_str = row.get(DATE_HEADER, "").strip()
            
            # Handle missing data (for old form submissions) gracefully
            name = row.get(NAME_HEADER, "").strip()
            if not name:
                name = "Friend"
                
            volume = row.get(VOLUME_HEADER, "").strip()
            if volume not in VOLUMES:
                volume = "Book of Mormon"
                
            time_str = row.get(TIME_HEADER, "").strip()
            
            try:
                start_date = datetime.strptime(date_str, "%m/%d/%Y").date()
                
                # Robust AM/PM time parsing
                if not time_str:
                    preferred_hour = 6 # Default to 6 AM if blank
                else:
                    # Example: "10:00 PM" becomes 22
                    time_obj = datetime.strptime(time_str, "%I:%M %p")
                    preferred_hour = time_obj.hour
                    
                recipients.append({
                    "email": email, 
                    "start_date": start_date,
                    "name": name,
                    "volume": volume,
                    "hour": preferred_hour
                })
            except Exception as e:
                print(f"Skipping row for {email}, error: {e}")
                
    return recipients

if __name__ == "__main__":
    current_hour = datetime.now(PHT).hour
    print(f"Current Hour in PHT: {current_hour}")

    downloaded_chapters = {}
    RECIPIENTS_DATA = get_recipients_from_sheet()

    for person in RECIPIENTS_DATA:
        if person["hour"] != current_hour:
            continue
            
        email = person["email"]
        name = person["name"]
        volume = person["volume"]
        start_date = person["start_date"]
        
        book_slug, chapter_num = get_todays_chapter(start_date, volume)
        chapter_key = f"{volume}_{book_slug}_{chapter_num}"
        
        print(f"\n--- Processing for {name} ({email}) ---")
        print(f"Volume: {volume} | Assigned reading: {book_slug.capitalize()} {chapter_num}")
        
        if chapter_key not in downloaded_chapters:
            chapter_data = fetch_chapter(volume, book_slug, chapter_num)
            downloaded_chapters[chapter_key] = chapter_data
        else:
            chapter_data = downloaded_chapters[chapter_key]
            
        filename = f"{book_slug}_{chapter_num}.pdf"
        build_pdf(chapter_data, filename, name)
        send_email(email, name, filename, chapter_data['bookTitle'], chapter_data['number'])
