import praw
import OAuth2Util
import urllib
import atom
import atom.service
import gdata
import gdata.photos.service
import gdata.geo
import gdata.gauth
import time
import os
import httplib2
import webbrowser
from datetime import datetime, timedelta
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage

def OAuth2Login(client_secrets, credential_store, email):
    scope='https://picasaweb.google.com/data/'
    user_agent='picasawebuploader'

    storage = Storage(credential_store)
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        flow = flow_from_clientsecrets(client_secrets, scope=scope, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
        uri = flow.step1_get_authorize_url()
        webbrowser.open(uri)
        code = raw_input('Enter the authentication code: ').strip()
        credentials = flow.step2_exchange(code)

    if (credentials.token_expiry - datetime.utcnow()) < timedelta(minutes=5):
        http = httplib2.Http()
        http = credentials.authorize(http)
        credentials.refresh(http)
    storage.put(credentials)
    gd_client = gdata.photos.service.PhotosService(source=user_agent,email=email,additional_headers={'Authorization' : 'Bearer %s' % credentials.access_token})

    return gd_client

def login(email):
    configdir = os.path.expanduser('./')
    client_secrets = os.path.join(configdir, 'client_secrets.json')
    credential_store = os.path.join(configdir, 'credentials.dat')
    return OAuth2Login(client_secrets, credential_store, email)

def get_album_by_title(title,gd_client):
    albums = gd_client.GetUserFeed(user=gd_client.email)
    album = None
    for entry in albums.entry:
        if entry.title.text == title:
            album = entry
    return album

def get_photos(path):
    items = os.listdir(path)
    photos = []
    for i in items:
        item_path = path+'\\'+i
        if os.path.isfile(item_path):
            photos.append(item_path)
    return photos

def delete_photos(album,gd_client):
    photos = gd_client.GetFeed('/data/feed/api/user/%s/albumid/%s?kind=photo' % (gd_client.email, album.gphoto_id.text))
    for photo in photos.entry:
        gd_client.Delete(photo)

def format_url(url):
    image_formats = ['jpg','png','gif','jpeg','jpe','gifv']
    link = url
    extension = link.split('.')[-1]
    if extension in image_formats:
        link = link[:link.rfind('.')]
    link += '.gif'
    return link

def create_title(title):
    invalid_tokens = ['\\','/',':','*','?','"','<','>','|']
    new_title = title
    for token in invalid_tokens:
        if token in new_title:
            new_title = new_title.replace(token,'')
    return new_title

gd_client = login('')
album = get_album_by_title("ScanSafe Space",gd_client)
album_id = album.gphoto_id.text
album_url = '/data/feed/api/user/%s/albumid/%s' % (gd_client.email, album_id)
test_path = "C:/Users/Tommy/Downloads/Abstract1.jpg"

delete_photos(album,gd_client)

user_agent = "test saving pics"
r = praw.Reddit(user_agent=user_agent)
o = OAuth2Util.OAuth2Util(r)
o.refresh()

intervals = 18
interval = 0
interval_time = 1200
already_posted = []
just_posted = []
num_posts = 100
f = open('posted.txt','r+')
for line in f:
    already_posted.append(line.rstrip())

subreddit = r.get_subreddit('all')
while interval<intervals:
    gd_client = login('')
    o.refresh()
    posts = [x for x in subreddit.get_hot(limit=num_posts)]
    posts.reverse()

    for post in posts:
        if 'imgur' in post.domain and post.id not in already_posted and '/a/' not in post.url and '/gallery/' not in post.url:
            print 'posting', post.title
            url = format_url(post.url)
            title = create_title(post.title)
            path = 'pics/temp.gif'
            urllib.urlretrieve(url, path)
            file_size = os.path.getsize(path)
            if file_size<70000000:
                uploaded = gd_client.InsertPhotoSimple(album_url, title, 'Uploaded using the API', path, content_type='image/gif')
                link = uploaded.content.src
                try:
                    r.submit('ScanSafeSpace', post.title, url=link)
                except:
                    print 'An error occured on post:', post.title
                just_posted.append(post.id)
                f.write(post.id)
                f.write("\n")
                os.remove(path)

    print '\n\nEnd of iteratoin.', interval,'\n\n'
    already_posted.extend(just_posted)
    interval+=1
    time.sleep(interval_time)

f.close()
