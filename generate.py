from requests import get
from datetime import datetime
from os import mkdir, getenv
from shutil import rmtree
from os.path import normpath, basename
from re import sub, DOTALL
from dotenv import load_dotenv
from string import ascii_letters

load_dotenv()
url = 'https://content.guardianapis.com/theguardian/mainsection'
now = datetime.utcnow() # Replace with datetime.now(UTC) for Python 3.12 and up
qs_params = {
    'api-key': getenv('GUARDIAN_API_KEY'),
    'from-date': now.strftime('%Y-%m-%d'),
    'to-date': now.strftime('%Y-%m-%d'),
    'use-date': 'newspaper-edition',
    'page-size': 50,
    'show-fields': 'headline,body,thumbnail,byline',
    'show-tags': 'newspaper-book-section'
}

news = []
news.append(get(url, params={**qs_params, **{'page': '1'}}).json()['response'])
for page in range(2, news[0]['pages'] + 1):
    news.append(get(url, params={**qs_params , **{'page': str(page)}}).json()['response'])

pillars = {}
for page in news:
    for article in page['results']:
        if article['pillarName'] in pillars:
            # Pillar and section both exist
            if article['tags'][0]['webTitle'] in pillars[article['pillarName']]:
                pillars[article['pillarName']][article['tags'][0]['webTitle']][article['fields']['headline']] = article
            # Pillar exists but section doesn't
            else:
                pillars[article['pillarName']][article['tags'][0]['webTitle']] = {article['fields']['headline']: article}
        else:
            # Neither pillar nor section exit
            pillars[article['pillarName']] = {article['tags'][0]['webTitle']: {article['fields']['headline']: article}}

# Tidy up
del news

paper = ''
tabs = '\t\t\t'

# Create listings for index file
paper += tabs + '<ul class=\"nav\">\n'
for pillar in sorted(pillars.keys()):
    paper += tabs + '\t<li><h2><a href=\"#' + pillar.replace(' ', '_') + '\">' + pillar + '</a></h2></li>\n'
paper += tabs + '</ul>\n'

for pillar in sorted(pillars.keys()):
    paper += tabs + '<h2 id=\"' + pillar.replace(' ', '_') + '\">' + pillar + '</h2>\n'

    # Order should be Top stories, UK news, Internation, everything else.
    for section in sorted( pillars[pillar].keys(), key=lambda d: 0 if d=='Top stories' else 1 if d=='UK news' else 2 if d=='International' else sorted(pillars[pillar].keys()).index(d)+3 ):
        paper += tabs + '<h3 id=\"' + section.replace(' ', '_') + '\">' + section + '</h3>\n'
        paper += tabs + '<dl>\n'
        for article in sorted(pillars[pillar][section].keys()):
            paper += tabs + '\t<item>\n'
            paper += tabs + '\t\t<dt><a href=\"' + basename(normpath(pillars[pillar][section][article]['id'])) + '.html\">' + pillars[pillar][section][article]['fields']['headline'] + '</a></dt>\n'
            paper += tabs + '\t\t<dd><img src=\"' + str(pillars[pillar][section][article]['fields'].get('thumbnail')) + '\" height=100 alt=\"Article thumbnail\" /></dd>\n'
            paper += tabs + '\t</item>\n'
        paper += tabs + '</dl>\n'

# Create articles for article files
articles = {}
for pillar in pillars:
    for section in pillars[pillar]:
        for _, article in pillars[pillar][section].items():
            id = basename(normpath(article['id']))
            pub_date = datetime.strftime(datetime.strptime(article['webPublicationDate'], '%Y-%m-%dT%H:%M:%SZ'), '%Y-%m-%d %H:%M:%S GMT')

            articles[id] = ''
            articles[id] += tabs + '<h2 class=\"article\">' + article['fields']['headline'] + '</h2>\n'

            if article['fields']['byline']:
                articles[id] += tabs + '<address class=\"author\">' + article['fields']['byline'] + '</address><br />'
            articles[id] += '<time pubdate datetime=\"' + article['webPublicationDate'] + '\">' + pub_date + '</time>&nbsp;&bull;&nbsp;<a href=\"' + article['webUrl'] + '\">permalink</a><br />\n'
            
            articles[id] += tabs + '<img src=\"' + str(article['fields'].get('thumbnail')) + '\" width=550 alt=\"Article thumbnail\" />\n'
            articles[id] += tabs + '<article>\n'
            articles[id] += tabs + '\t' + sub(r'<aside.*?<\/aside>', '', article['fields']['body'], flags=DOTALL) + '\n'
            articles[id] += tabs + '</article>\n'

# Create new files
## Remove old ones and re-create folder
rmtree('html')
mkdir('html')

## Load template
with open('template.html', 'r') as f:
    template = f.read()

## Variables to replace in template
replace_vars = {
    'today_date_normal': now.strftime('%-d %B %Y'),
    'retrieved_timestamp': now.strftime('%H:%M:%S GMT'),
    'today_year_normal': now.strftime('%Y'),
    'paper': paper
}

## Index file
index = template
for var in replace_vars:
    index = index.replace('<!-- ' + str(var) + ' -->', replace_vars[var])

with open('html/index.html', 'w') as f:
    f.write(index)

## Article files
for article in articles:
    page = template
    replace_vars['paper'] = articles[article]

    for var in replace_vars:
        page = page.replace('<!-- ' + str(var) + ' -->', replace_vars[var])

    with open('html/' + article + '.html', 'w') as f:
        f.write(page)
    
