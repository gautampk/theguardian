from requests import get
from datetime import datetime
from os import mkdir, getenv
from shutil import rmtree
from os.path import normpath, basename
from re import sub
from dotenv import load_dotenv

load_dotenv()
url = 'https://content.guardianapis.com/search'
now = datetime.utcnow() # Replace with datetime.now(UTC) for Python 3.12 and up
qs_params = {
    'api-key': getenv('GUARDIAN_API_KEY'),
    'from-date': now.strftime('%Y-%m-%d'),
    'to-date': now.strftime('%Y-%m-%d'),
    'use-date': 'newspaper-edition',
    'page-size': 50,
    'show-fields': 'headline,body,thumbnail'
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
            if article['sectionName'] in pillars[article['pillarName']]:
                pillars[article['pillarName']][article['sectionName']][article['fields']['headline']] = article
            # Pillar exists but section doesn't
            else:
                pillars[article['pillarName']][article['sectionName']] = {article['fields']['headline']: article}
        else:
            # Neither pillar nor section exit
            pillars[article['pillarName']] = {article['sectionName']: {article['fields']['headline']: article}}

# Tidy up
del news

paper = ''
tabs = '\t\t\t'

# Create listings for index file
for pillar in sorted(pillars.keys()):
    paper += tabs + '<h2 id=\"' + pillar + '\">' + pillar + '</h2>\n'
    for section in sorted(pillars[pillar].keys()):
        paper += tabs + '<h3 id=\"' + section + '\">' + section + '</h3>\n'
        paper += tabs + '<dl>\n'
        for article in sorted(pillars[pillar][section].keys()):
            paper += tabs + '\t<item>\n'
            paper += tabs + '\t\t<dt><a href=\"' + basename(normpath(pillars[pillar][section][article]['id'])) + '.html\">' + pillars[pillar][section][article]['fields']['headline'] + '</a></dt>\n'
            paper += tabs + '\t\t<dd><img src=\"' + str(pillars[pillar][section][article]['fields'].get('thumbnail')) + '\" height=100 /></dd>\n'
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
            articles[id] += tabs + '<h2>' + article['fields']['headline'] + '</h2>\n'
            articles[id] += tabs + '<em>' + pub_date + '&nbsp;&bull;&nbsp;<a href=\"' + article['webUrl'] + '\">permalink</a></em><br />\n'
            articles[id] += tabs + '<img src=\"' + str(article['fields'].get('thumbnail')) + '\" width=550 alt=\"Article thumbnail\" />\n'
            articles[id] += tabs + '<article>\n'
            articles[id] += tabs + '\t' + sub(r'<aside.*<\/aside>', '', article['fields']['body']) + '\n'
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
    
