# Reddit_Account_Migrator-Downloader
# written in: python 3.10
# required packages: praw
# author: cebe89
# github: https://github.com/cebe89/Reddit_Account_Migrator-Downloader

import sys
import csv
import json
import requests
from pathlib import Path
from time import gmtime, strptime, strftime
from html.parser import HTMLParser
import pprint

import praw

LIMIT_FETCH = None
URL_DELIMITERS = [')', ']', ' ', '"', "'", '\n', '\\']
COMMENT_LEVEL = 2

username = ''
settings = {"download_subreddits": {"fetch": True, "limit": LIMIT_FETCH},
            "download_multireddits": {"fetch": True},
            "download_comments": {"fetch": True, "limit": LIMIT_FETCH, "level":  0},
            "download_saves":  {"fetch": False, "limit": LIMIT_FETCH,
                            "urls": [{"url": ["//imgur", "//i.imgur"],
                                      "download":  True, "folder":  "downloads", "slice": [0, -1],
                                      "comments_level":  LIMIT_FETCH},
                                     {"url": ["//i.redd.it", "//v.redd.it"],
                                       "download":  True, "folder":  "downloads",  "slice": [0, -1],
                                       "comments_level":  LIMIT_FETCH}]
                            }
                }
html_starttags = []
html_starttags_attrs = []
html_endtags = []
html_data = []


class MyHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        global html_starttags
        html_starttags.append(tag)
        html_starttags_attrs.append(attrs)

    def handle_endtag(self, tag):
        global html_endtags
        html_endtags.append(tag)

    def handle_data(self, data):
        global html_data
        html_data.append(data)


def create_folder(folder):
    """just makes a folder with the given string and returns a path object, and skips if it already exists"""
    path = Path(__file__).parent
    path = path / folder
    if folder is None or '':
        print("Attention: No folder given, saving to base directory.")
        return path
    try:
        if Path.is_dir(path):
            print(f'Attention: Directory "{path}" already exists.')
            return path
            pass
        else:
            print(f'Creating directory "{path}"...')
            Path.mkdir(path)
            return path
    except IOError as exception:
        raise IOError('%s: %s' % (path, exception.strerror))


def dict_conversion(object_list):
    """replaces all newlines in body with a \n, so I don't have newlines from comments in the csv,
    and reformat the utc time to a format of Year-Month-Day-Seconds"""
    if not object_list:
        print("Warning: No list given, conversion aborted.")
        return
    print("Converting dictionary to preferred format...")
    for it_com in object_list:
        if it_com.get('body'):
            it_com['body'] = it_com.get('body').replace("\n", "\\n")
        time_utc = gmtime(it_com.get('date'))
        it_com['date'] = strftime("%Y-%m-%d-%M", time_utc)


def url_extract(object_list, urls):
    if not (object_list or urls):
        print("Attention: No url list given, conversion aborted.")
        return
    print(f'Extracting {urls} urls...')
    ext_list = []
    for it_obj in object_list:
        # if the url is from an actual reddit link, it's easy to isolate it
        if it_obj.get('url'):
            # then search for all given urls you want to add
            for url in urls:
                if (url in it_obj.get('url')) is True:
                    # I already add a title here, but keep permalink if I wanna fetch its comments later
                    # to get a proper title from it without having to fetch, I just cut last part from permalink
                    # so bla/reddit_title/ is the permalink and I partition between two / and take the middle
                    ext_list.append({'subreddit': it_obj.get('subreddit'),
                                     'title': str(it_obj.get('permalink')).rsplit(sep='/', maxsplit=2)[1],
                                     'permalink': it_obj.get('permalink'), 'id': it_obj.get('id'),
                                     'url': it_obj.get('url')})
        # if it's from a comment, I have to do some stringsearch to properly isolate it
        elif it_obj.get('body'):
            for url in urls:
                if (url in it_obj.get('body')) is True:
                    # getting urls from comments is a bit harder, I just hack together something to isolate them
                    # start by finding https: and cut to it
                    url_ext = it_obj.get('body').partition('https:' + url)
                    # if second return is empty, means it didn't find the string, so repeat with http
                    if url_ext[1] == '':
                        url_ext = url_ext.partition('http:' + url)
                        if url_ext[1] == '':
                            print(f'Warning: No http/https links found in "{url_ext}".')
                    # now add the https and all the right cut together
                    url_ext = url_ext[1] + url_ext[2]
                    # Finding the end is hard, as it must be a character that's not allowed in urls, so I try various
                    # common ones. I'm sure there are some better methods for this
                    for i_del in URL_DELIMITERS:
                        url_ext = url_ext.split(i_del, maxsplit=1)[0]
                    # could maybe be done without a for loop?
                    # url_ext = map(lambda x: url_ext.split(x, maxsplit=- 1)[0], delimiters)
                    # this seemingly works with regex
                    # urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                                      # text)
                    ext_list.append({'subreddit': it_obj.get('subreddit'),
                                     'title': str(it_obj.get('permalink')).rsplit(sep='/', maxsplit=2)[0],
                                     'permalink': it_obj.get('permalink'), 'id': it_obj.get('id'), 'url': url_ext})
    if not ext_list:
        print("   Warning: Found no relevant urls, returning...")
    return ext_list


def url_filetype (content_type)->str:
    if not content_type:
        print("Warning: No content-type given, craw aborted.")
        return
    print('Detecting filetype:')
    type_list = content_type.split(sep='/', maxsplit=1)
    # todo add reddit.gallery, v.reddit, redgifs
    match type_list[0]:
        case 'text':
            print('detected "text" type')
            type_text = type_list[-1].split(sep=';')
            match type_text[0]:
                case 'html':
                    print('   detected "html" subtype')
                    text_charset = type_text[-1].partition('charset=')
                    match text_charset[-1]:
                        case 'UTF-8':
                            print('      detected "UTF-8" charset, maybe a gifv?')
                            return 'html'
                        case _:
                            return 'html'
                case _:
                    return ''
        case 'image':
            print('detected image type')
            match type_list[1]:
                case 'jpeg':
                    print('   detected "jpeg" subtype')
                    return 'jpg'
                case 'png':
                    print('   detected "png" subtype')
                    return 'png'
                case 'gif':
                    print('   detected "gif" subtype')
                    return 'gif'
                case _:
                    return ''
        case _:
            return ''

def url_html_crawler_prop(tag_idx, prop):
    if not prop:
        print("Attention: No prop given, crawl aborted.")
        return
    found_property = False
    for search_attr in html_starttags_attrs[tag_idx]:
        # print(f'   Attr: {search_attr}')
        if search_attr[0] == '':
            "Warning: Could not find proper attribute, skipping html crawl."
            return ''
        if found_property is True and search_attr[0] == 'content':
            print('   found content and returning source!')
            # remove url garbage like everything from ? and #
            url_found = search_attr[1].rsplit(sep='?', maxsplit=1)[0]
            url_found = url_found.rsplit(sep='#', maxsplit=1)[0]
            return url_found
        elif search_attr[0] == 'property':
            # print('      property found!')
            if search_attr[1] == prop:
                print(f'         property is {prop}!')
                found_property = True
                continue
    return ''

def url_html_crawler(file_html, props):
    if not (file_html or props):
        print("Warning: No html and props given, crawl aborted.")
        return
    global html_starttags
    global html_starttags_attrs
    global html_endtags
    global html_data
    html_starttags = []
    html_starttags_attrs = []
    html_endtags = []
    html_data = []
    parser = MyHTMLParser()
    parser.feed(str(file_html))

    # search through all the starttags, and if they apply search through the attributes
    print("_" * 100)
    print(f"Starting html crawler and crawling for {props}...")
    url_final = ''
    for prop in props:
        print(f"Crawling for '{prop}'")
        for idx, search_tag in enumerate(html_starttags):
            # print(f'Tag: {search_tag}')
            if search_tag.find('meta') != -1:
                # print('meta found!')
                url = url_html_crawler_prop(idx, prop)
                if url != '':
                    print(f'Found url "{url}" for prop {prop}!')
                    url_final = url
    print(f'Returning url "{url}" for props {props}.')
    return url_final


def url_download(list_urls, reddit=None, folder='downloads', restriction=(0, -1)):
    if not list_urls:
        print("Warning: No urls given, downloads aborted.\n")
        return
    if restriction[1] != -1:
        if (restriction[1] - restriction[0]) < 0 or restriction[1] > len(list_urls):
            restriction = (0, -1)
    restriction = slice(restriction[0], restriction[1])

    inp = input(f'You are about to download {len(list_urls[restriction])} files, are you sure? [y/yes, n/no]: ')
    # if inp != 'c' or 'choose':
    #     restriction = input(f'Type in the image where you want to start and where you want to end in the form (s, e):')
    #     if restriction[0] < 0 or restriction[0] > len(list_urls) - 1 \
    #             or restriction[1] < restriction[0] or restriction[1] > len(list_urls):
    #         print('Error: Wrong restrictions, aborting download')
    #         return
    if (inp == 'n' or inp == 'no' or inp == 'N' or inp == 'No'):
        print('Attention: Download aborted by user.\n')
        return
    elif (inp != 'y' and inp != 'yes' and inp != 'Y' and inp != 'Yes'):
        print("Warning: Invalid input, aborted.\n")
        return

    print(f'Downloading {len(list_urls[restriction])} files...')
    p_dl = create_folder(username + '/' + folder)

    for url_index, url_object in enumerate(list_urls[restriction]):
        url_cur = url_object['url']
        # request the url and save the content
        req = requests.get(url_cur, allow_redirects=True)
        url_cont = req.content
        content_type = req.headers.get('content-type')
        # if url_index == 0:
        #     print(req.headers) # just for me to see what's in the header
        print(f'\n{url_index + 1}/{len(list_urls[restriction])}:')
        print(f'URL: {url_cur}')
        print(f'Content-type: {content_type}')

        filename = url_object['subreddit'] + '_' + url_object['id'] \
                   + '_' + url_object['title'].rsplit(sep='/', maxsplit=1)[-1]
        # check for the filetype
        filetype = url_filetype(content_type)
        # if can't fetch it skip, if html try to crawl for an url
        if filetype == '':
            print('Warning: Unable to find proper filetype, skipping download.')
            continue
        elif filetype == 'html':
            # todo I could make this also recursively
            print(f'Starting html crawler for \"{url_cur}\"')
            url_sub = url_html_crawler(url_cont, ('og:image', 'og:video'))
            if not url_sub :
                print('Warning: Unable to find proper filetype from html, downloading only html.')
            else:
                # if a new url was found with proper filetype, request again but with new link now
                url_cur = url_sub
                req = requests.get(url_cur, allow_redirects=True)
                url_cont = req.content
                content_type = req.headers.get('content-type')
                print(content_type)
                print(url_cur)
                filetype = url_cur.rsplit(sep='.', maxsplit=1)[-1]
                # print(filetype)
            # if COMMENT_LEVEL > 0:
            # submissions = reddit.submission(url_cur)
        # elif COMMENT_LEVEL > 0 and reddit:
        #     # todo implement a submission comment saver with adjustable level (to get sources from comments)
        #     print(f'Fetching level {COMMENT_LEVEL} comments of url...')
        #     s_filefull = filename + '.txt'
        #     s_p_full = p_dl / 'comments' / s_filefull
        #     print(s_p_full)
        #     # with open(s_p_full, 'wb') as urlcomfile:
        #     #     urlcomfile.write(url_cont)
        #     submission = reddit.submission(url_cur)
        #     print(str(reddit.user.me()))
        #     # print(submission.comments)
        #     # for top_level in submission.comments:
        #     #     print(top_level)

        filefull = filename + '.' + filetype
        p_full = p_dl / filefull
        if Path.is_file(p_full):
            print(f"Attention: File \"{filefull}\" already exists, won't overwrite.")
            continue

        # if ('/' in content_type) is True:
        #     # url_part = str(url_cont).partition('<meta itemprop="embedURL" content="')
        #     url_cont_idx = str(url_cont).find('<meta itemprop="embedURL" content="')
        #     print(url_cont_idx)
        #     # print(url_part[0])
        #     # if url_part[1] != 0:
        #     #     url_curr = url_part[0].split('"', maxsplit=1)
        #     #     print(url_curr)

        # print('content-type: {}'.format(req.headers.get('content-type').rsplit(sep=';', maxsplit=1)))
        # my_filetype = str(url_curr).rsplit(sep='.', maxsplit=1)[1]
        # print(f'my filetype: {my_filetype}')
        # if '/' in my_filetype:
        #     print(f"Warning: Did not find proper filetype in url: {url_object['url']}")
        #     continue
        print(f'Downloading "{url_cur}" to "{p_full}"...')
        with open(p_full, 'wb') as urlfile:
            urlfile.write(url_cont)

# def url_download_comments(reddit, saves, comment_level=0):
#     if not (reddit or saves):
#         print("Attention: No saves given, comment download aborted")
#         return
#     for entry in saves:
#         submission = reddit.submission(entry['id'])
#         for top_level_comment in submission.comments:
#             print(top_level_comment.body)


def csv_write(object_list, filesuffix='_noobjectgiven'):
    """write dictionary to file with given strings"""
    if not object_list:
        print("Warning: No list given, csv save aborted.")
        return
    csv_filename = username + filesuffix
    print(f'Writing file "{csv_filename}.csv"...')
    p_dl = create_folder(username)
    try:
        with open(f'{p_dl / csv_filename}.csv', 'w', newline='', encoding='utf-8') as csvfile:
            file_header = list(object_list[0].keys())
            filewriter = csv.DictWriter(csvfile, fieldnames=file_header, delimiter=' ', quotechar='"')
            filewriter.writeheader()
            for line_it in object_list:
                filewriter.writerow(line_it)
    except IOError:
        print("Error: Failed to write csv file!")


def main() -> int:
    print('Welcome to my reddit account migrator and downloader!')

    # read in json file given as argument or try to get template file otherwise
    if len(sys.argv) == 2:
        json_filepath = Path(sys.argv[1])
    elif len(sys.argv) == 1:
        path = Path(__file__).parent
        json_filepath = path / 'user_template.json'  # change me if you don't want to use arguments
    else:
        print(f"Error: Takes only one argument!")
    try:
        with open(json_filepath) as json_file:
            user_json = json.load(json_file)
            print(f"Loaded json file '{json_filepath}.'")
    except IOError:
        print(f"Error: Can't read json file '{json_filepath}'!")
        raise

    # check if minimum login-settings are given
    if (user_json["user_agent"] and user_json["client_id"] and user_json["client_secret"] and
        user_json["username"] and user_json["password"]) == '' or None:
        print("Error: Json file misses necessary login data!")
        return 1

    # log in as the user and save global username and json settings
    try:
        reddit = praw.Reddit(
            user_agent=user_json["user_agent"],
            # visit https://old.reddit.com/prefs/apps/ to add a new script
            # choose http://localhost:8080 as a random and unused callback url
            client_id=user_json["client_id"],
            client_secret=user_json["client_secret"],
            username=user_json["username"],
            password=user_json["password"]
        )
        global username
        username = str(reddit.user.me())
        print(f"Successfully connected to reddit user '{username}'.")
        if "settings" in user_json:
            global settings
            settings = user_json["settings"]
    except Exception as err:
        print(F"ERROR: Couldn't create praw reddit user {err}, {type(err)=}!")
        raise

    # fetch all subscribed subs of my user
    if settings["download_subreddits"]["fetch"] is True:
        print('\nFetching subscribed subreddits...')
        my_subreddits = reddit.user.subreddits(limit=settings["download_subreddits"]["limit"])
        if my_subreddits != []:
            p_usr = create_folder(username)
            with open(p_usr / (username + '_subreddits' + '.txt'), 'w') as txtfile:
                print("Writing subreddit file...")
                for subreddit in my_subreddits:
                    txtfile.write(subreddit.display_name + '\n')
        else:
            print("Attention: No user subscribed subreddits found.")

    # fetch all multireddits and belonging subs of my user
    if settings["download_multireddits"]["fetch"] is True:
        print('\nFetching multireddits...')
        my_multireddits = reddit.user.me().multireddits()
        # pprint.pprint(my_multireddits) # vars()
        if my_multireddits != []:
            p_usr = create_folder(username)
            with open(p_usr / (username + '_multireddits' + '.txt'), 'w') as txtfile:
                print("Writing multireddit file...")
                for multireddit in my_multireddits:
                    txtfile.write(multireddit.display_name + ': ')
                    for subreddit in multireddit.subreddits:
                        txtfile.write(subreddit.display_name + ' ')
                    txtfile.write('\n')
            print()
        else:
            print("Attention: No user multireddits found.")

    # fetch all comments of my user
    if settings["download_comments"]["fetch"] is True:
        print('\nFetching users comments...')
        my_comments = reddit.user.me().comments.new(limit=settings["download_comments"]["limit"])
        if my_comments != []:
            print('Converting users comments to dictionary...')
            # save them into dictionary of my preferred format
            redditor_comments = [{'date': comment.created_utc, 'subreddit': comment.subreddit.display_name,
                                  'id': comment.id, 'permalink': comment.permalink,
                                  'body': comment.body} for comment in my_comments]
            dict_conversion(redditor_comments)
            csv_write(redditor_comments, ('_comments_l' + str(settings["download_comments"]["level"])))
        else:
            print("Attention: No user comments found.")

    # fetch all saves of my user
    if settings["download_saves"]["fetch"] is True:
        print('\nFetching users saved submissions...')
        my_saves = reddit.user.me().saved(limit=settings["download_saves"]["limit"])
        print('Converting users saved submissions to dictionary...')
        # redditor_saves = [{'date': save.created_utc, 'subreddit': save.subreddit.display_name, 'id': save.id,
        #                    'permalink': save.permalink, 'url': save.url} for save in my_saves]
        # Hmm, dunno how or even if I can do that in one lne, so I just do it in an extended for-loop instead
        redditor_saves = []
        # todo Dang, this needs kinda long, I should probably optimize that one
        for save in my_saves:
            if hasattr(save, 'url'):
                # print("this is a saved url")
                redditor_saves.append({'date': save.created_utc, 'subreddit': save.subreddit.display_name,
                                       'id': save.id, 'permalink': save.permalink, 'url': save.url, 'body': None})
            elif hasattr(save, 'body'):
                # print("this is a saved comment")
                redditor_saves.append({'date': save.created_utc, 'subreddit': save.subreddit.display_name,
                                       'id': save.id, 'permalink': save.permalink, 'url': None, 'body': save.body})
            else:
                "Error: Save doesn't contain url or body field!"
        dict_conversion(redditor_saves)
        csv_write(redditor_saves, '_saves')
        print()

        # extracting urls, // before them otherwise it will find sth like imgur twice (in //imgur and in //i.imgur
        if settings["download_saves"]["urls"] is not []:
            for urlidx in settings["download_saves"]["urls"]:
                if urlidx["download"] is not True:
                    continue
                saves_url = url_extract(redditor_saves, urlidx["url"])
                csv_write(saves_url, ('_saves_' + str(urlidx["url"][0]).strip('//')))
                print()
                # download files from a fetched urls
                # takes optional slice parameter that defaults to slice(0, -1)
                url_download(saves_url, folder=urlidx["folder"], restriction=urlidx["slice"])
                # url_download_comments(reddit, saves_imgur, 0)

    return 0

if __name__ == '__main__':
    sys.exit(main())