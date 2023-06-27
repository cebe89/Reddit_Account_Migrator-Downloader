# Reddit_Account_Migrator-Downloader
# Written in: python 3.10
# Required packages: praw
# Author: cebe89
# Github: https://github.com/cebe89/Reddit_Account_Migrator-Downloader

import sys
import logging
import csv
import json
import requests
from pathlib import Path
from time import gmtime, strptime, strftime
from html.parser import HTMLParser
import pprint

import praw

LIMIT_FETCH = None
URL_DELIMITERS = [')', ']', ' ', '"', "'", '\\n', '\n', '\\']
URL_DELGARBAGERS = ['?', '#', '%', '&', '$']

reddit = None
username = ''
json_settings = {
            "download_subreddits": {"fetch": True, "limit": LIMIT_FETCH},
            "download_multireddits": {"fetch": True, "limit": LIMIT_FETCH},
            "download_comments": {"fetch": True, "limit": LIMIT_FETCH, "comments_level": 0},
            "download_saves":  {"fetch": True, "limit": LIMIT_FETCH, "ask": True,
                                "urls": [{"url": ["//"], "fetch": True,
                                         "download": True, "folder": "downloads", "slice": [0, None],
                                         "comments_level": 0}]
                                }
                 }
html_tags_start = []
html_tags_start_attrs = []
html_tags_endtags = []
html_data = []


class MyHTMLParser(HTMLParser):
    """Just a simple html parser, methods overwrite default ones and
    only act as setters.
    """
    def handle_starttag(self, tag, attrs):
        global html_tags_start
        html_tags_start.append(tag)
        html_tags_start_attrs.append(attrs)

    def handle_endtag(self, tag):
        global html_tags_endtags
        html_tags_endtags.append(tag)

    def handle_data(self, data):
        global html_data
        html_data.append(data)


def folder_create(folder):
    """Takes a stringpath and optional delimiter, creates a folder with
    it and returns the Path; returns same if already exists.
    """
    path = Path(__file__).parent
    if not folder:
        logging.debug('No folder given, saving to base directory')
        return path
    path = path / Path(folder)
    try:
        if Path.is_dir(path):
            logging.info(f'Directory "{path}" already exists')
            return path
            pass
        else:
            logging.debug(f'Creating directory "{path}"...')
            Path.mkdir(path)
            return path
    except IOError as exception:
        raise IOError('%s: %s' % (path, exception.strerror))


def file_text_read(file_path, delimiter='\n'):
    """Takes a string path and optional delimiter, attempts to read
    the file and returns content as a list, split at the delimiters.
    """
    if not file_path:
        logging.error("No text path given, text read aborted")
        return None
    path = Path(__file__).parent
    path = path / Path(file_path)
    try:
        if not Path.is_file(path):
            logging.error(f"Couldn't find file \"{path}\", aborted!")
            return None
        else:
            with open(path, 'r') as txtfile:
                logging.debug(f'Reading text file "{path}"...')
                # Get rid of endlines so I don't have an empty element.
                txt_content = txtfile.read().rstrip('\n\r')
                # Return list separated by delimiter (usually newline).
                return txt_content.split(delimiter)
    except IOError as exception:
        raise IOError('%s: %s' % (path, exception.strerror))


def file_text_write(file_content, file_path, newline='\n'):
    """Takes text content as lines in a list and writes them as
    specified file, using optional newline parameter.
    """
    if not file_content:
        logging.error("No content given, text file write aborted")
        return
    if not file_path:
        logging.error("No text path given, text read aborted")
        return
    try:
        path = Path(__file__).parent
        path = path / Path(file_path)
        if not path.is_file():
            folder_create(Path(path.resolve().parent))
        with open(file_path, 'w', newline=newline, encoding='utf-8') \
                as file_txt:
            logging.debug(f'Writing text file "{file_path}"...')
            # file_txt.writelines((line + '\n') for line in file_content)
            # file_txt.writelines(file_content)  # Misses \n.
            # Still rather do with a write in a for loop as it omits
            # newline at the end.
            for line_idx, file_line in enumerate(list(file_content)):
                file_newline = '\n'
                if line_idx == len(list(file_content)) - 1:
                    file_newline = ''
                file_txt.write(str(file_line) + file_newline)
    except IOError:
        raise IOError(f'Error: Failed to write txt file "{file_path}"!')


def file_csv_write(object_list, file_suffix='_none'):
    """Writes a given dictionary to a file the with csv-writer, using
    given suffix as file type.
    """
    if not object_list:
        logging.error("No list given, csv save aborted")
        return
    csv_filename = ''.join((username, file_suffix))
    logging.debug(f'Writing csv file "{csv_filename}.csv"...')
    path = folder_create(username)
    try:
        with open(f'{path / Path(csv_filename)}.csv', 'w', newline='',
                  encoding='utf-8') as csvfile:
            file_header = list(object_list[0].keys())
            filewriter = csv.DictWriter(csvfile, fieldnames=file_header,
                                        delimiter=' ', quotechar='"')
            filewriter.writeheader()
            for line_it in object_list:
                filewriter.writerow(line_it)
    except IOError:
        raise IOError(f'Error: Failed to write csv file "{csv_filename}"!')


def dict_convert(object_list):
    """Replaces all newlines in body with a \\n, so I don't have newlines from comments in the csv,
    and reformat the utc time to a format of Year-Month-Day-Seconds.
    """
    if not object_list:
        logging.error("No list given, conversion aborted")
        return
    logging.debug("Converting dictionary to preferred format...")
    for it_com in object_list:
        if it_com.get('body'):
            it_com['body'] = it_com.get('body').replace("\n", "\\n")
        time_utc = gmtime(it_com.get('date'))
        it_com['date'] = strftime("%Y-%m-%d-%M", time_utc)


def dict_url_extract(object_list, urls):
    """Extracts urls from a given praw submission iterator list,
    and returns them in a dictionary.
    """
    if not (object_list or urls):
        logging.error("No url list given, conversion aborted")
        return
    print(f'Extracting {urls} urls...')
    logging.info(f'Extracting {urls} urls...')
    ext_list = []
    for it_obj in object_list:
        # If the url is from an actual reddit link, it's easy to isolate it.
        if it_obj.get('url'):
            # Then search for all given urls you want to add.
            for url in urls:
                if url in it_obj.get('url'):
                    # I already add a title here, but keep permalink if I wanna fetch its comments later
                    # to get a proper title from it without having to fetch, I just cut last part from permalink.
                    # So bla/reddit_title/ is the permalink and I partition between two / and take the middle.
                    ext_list.append({'subreddit': it_obj.get('subreddit'),
                                     'title': str(it_obj.get('permalink')).rsplit(sep='/', maxsplit=2)[1],
                                     'author': it_obj.get('author'), 'permalink': it_obj.get('permalink'),
                                     'id': it_obj.get('id'), 'url': it_obj.get('url')})
        # if it's from a comment, I have to do some stringsearch to properly isolate it
        elif it_obj.get('body'):
            for url in urls:
                if url in it_obj.get('body'):
                    # getting urls from comments is a bit harder, I just hack together something to isolate them
                    # start by finding https: and cut to it
                    url_ext = it_obj.get('body').partition(''.join(('https:', url)))
                    # if second return is empty, means it didn't find the string, so repeat with http
                    if url_ext[1] == '':
                        url_ext = url_ext.partition(''.join(('http:', url)))
                        if url_ext[1] == '':
                            logging.info(f'No http/https links found in "{url_ext}"')
                    # now add the https and all the right cut together
                    url_ext = ''.join((url_ext[1], url_ext[2]))
                    # Finding the end is hard, as it must be a character that's not allowed in urls, so I try various
                    # common ones. I'm sure there are some better methods for this
                    for i_del in URL_DELIMITERS:
                        url_ext = url_ext.split(i_del, maxsplit=1)[0]
                    # could maybe be done without a for loop?
                    # url_ext = map(lambda x: url_ext.split(x, maxsplit=- 1)[0], delimiters)
                    # this seemingly works with regex
                    # urls = re.findall(
                    #                   'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
                    #                   , # text)
                    ext_list.append({'subreddit': it_obj.get('subreddit'),
                                     'title': str(it_obj.get('permalink')).rsplit(sep='/', maxsplit=2)[0],
                                     'permalink': it_obj.get('permalink'), 'id': it_obj.get('id'), 'url': url_ext})
    if not ext_list:
        logging.warning("Found no relevant urls, returning...")
    return ext_list


def edit_remove_duos(contents, checkers):
    """Checks if given strings are contained in given contents
    and returns cleaned contents, gives warning if faulty one found.
    """
    contents_cleaned = []
    # print("\nChecking for invalid names...")
    # print(f'Check if {checkers} in {contents}...')
    for content in contents:
        valid_name = True
        for faulty in checkers:
            if faulty in content:
                logging.error(f'"{content}" does not fit valid '
                      f'naming system, skipping it')
                valid_name = False
                continue
        if valid_name is False:
            continue
        contents_cleaned.append(content)
    if not contents_cleaned:
        return contents
    return contents_cleaned


def edit_remove(text_orig, text_remove):
    """Checks if given string is contained in given contents
    and returns cleaned contents, gives warning if faulty one found.
    """
    if not (text_orig and text_remove):
        logging.error("given lines don't contain any text")
        return text_orig

    logging.debug("Finding duplicate lines and removing them...")
    text_cleaned = []
    for line_orig in text_orig:
        if line_orig in text_remove:
            continue
        else:
            text_cleaned.append(line_orig)
    if len(text_orig) - len(text_cleaned) == 0:
        logging.debug('No duplicates found')
        return text_orig
    logging.debug(f'I have removed {len(text_orig) - len(text_cleaned)} '
          f'given lines from {len(text_remove)} possible ones')
    return text_cleaned


def praw_comments_download(url_cur, file_name, comments_level=2):
    """Fetches and downloads comments equal to the comment-level given,
    and saves them into a txt-file.
    """
    logging.debug("Fetching belonging comments...")
    comments = []
    # url_cur = url_object.get('permalink')
    # url_cur = 'https://reddit.com' + url_cur
    submission = reddit.submission(url=url_cur)
    comments_forest = submission.comments
    comments_forest.replace_more(limit=None)
    comments_top = []
    for top_level_comment in comments_forest:
        # print(top_level_comment.body)
        comments_top.append(top_level_comment.body.replace("\n", "\\n"))
        if comments_level > 1:
            for sub_level_comment in top_level_comment.replies:
                comments_top.append('    ' + sub_level_comment.body.replace("\n", "\\n"))
        # todo add more than two comment_levels in a more elegant way
        comments_top.append("")
    file_text_write(comments_top, file_name, newline='\n')


def url_html_crawler_attr(tag_idx, attr_conditions, attr_searches, urls_final):
    """Searches through a given single html tag a props, and
    returns the content and property if found.
    """
    logging.debug(f'condition: {attr_conditions} search: {attr_searches}')
    if not (attr_conditions and attr_searches):
        logging.error("No prop given, crawl aborted")
        return

    for html_attrs_ in html_tags_start_attrs[tag_idx]:
        logging.debug(f'searching in: {html_attrs_}')
        if html_attrs_[0] == '':
            logging.warning("empty attributes, skipping to next one")
            continue
        for attr_conditions_ in attr_conditions:
            logging.debug(f'searching for {attr_conditions_}')
            if list(html_attrs_) == attr_conditions_:
                logging.debug(f'property has been found, now scanning for searches')
                for html_searches_ in html_tags_start_attrs[tag_idx]:
                    logging.debug(f'scanning in {html_searches_}')
                    for attr_searches_ in attr_searches:
                        logging.debug(f'scanning for {attr_searches_}')
                        if attr_searches_ == html_searches_[0]:
                            logging.info(f'found search {html_searches_[0]} and returning source {html_searches_[1]}')
                            url_found = html_searches_[1]
                            # remove url garbage like everything from ? and #
                            for sep_garb in URL_DELGARBAGERS:
                                url_found = url_found.rsplit(sep=sep_garb, maxsplit=1)[0]
                            logging.debug(f'new url is {url_found}')
                            urls_final.append(url_found)
                            # # return early if you found maximum amount of attributes,
                            # # so I don't run through the rest if I already found the number of attributes
                            # # todo could also make the same for searches
                            # if len(attr_conditions_) >= len(urls_found):
                            #     return urls_found


def url_html_crawler(file_html, url):
    """Uses html parser and crawls for given properties, extracting
    the content and returning it.
    """
    if not (file_html or url):
        logging.error("No html and props given, crawl aborted")
        return
    global html_tags_start
    global html_tags_start_attrs
    global html_tags_endtags
    global html_data
    html_tags_start = []
    html_tags_start_attrs = []
    html_tags_endtags = []
    html_data = []
    parser = MyHTMLParser()
    parser.feed(str(file_html))

    logging.debug(html_tags_start)
    logging.debug(html_tags_start_attrs)

    obj_tag = []
    attr_condition = []
    attr_search = []
    if url.find('imgur'):
        logging.debug('using imgur tags and attributes')
        obj_tag.append('meta')
        obj_tag.append('img src=')
        attr_condition.append(['property', 'og:image'])
        attr_condition.append(['property', 'og:video'])
        attr_search.append('content')

    # search through all the starttags, and if they apply search through the attributes
    # logging.info(f"starting html crawler and crawling for tag ...")
    urls_final = []
    if not [obj_tag and attr_condition and attr_search]:
        logging.error(f'no tag, condition or search given')
        return urls_final
    for tag_idx, tag_ in enumerate(html_tags_start):
        for obj_tag_ in obj_tag:
            logging.debug(f'crawling for tag {obj_tag_}')
            if tag_ == obj_tag_:
                logging.debug(f'found tag {tag_}')
                url_html_crawler_attr(tag_idx, attr_condition, attr_search, urls_final)
    return urls_final


def url_filetype(content_type):
    """Checks a given html content_type tag, and returns simplified
    version if it finds one.
    """
    if not content_type:
        logging.error("No content-type given, crawl aborted")
        return
    logging.info('Detecting filetype...')
    logging.debug(f'content type {content_type}')
    type_list = content_type.split(sep='/', maxsplit=1)
    # todo add reddit.gallery, v.reddit, giphy/redgifs, twitter, etc.
    match type_list[0]:
        case 'text':
            logging.debug('detected "text" type')
            type_text = type_list[-1].split(sep=';')
            match type_text[0]:
                case 'html':
                    logging.debug('detected "html" subtype')
                    text_charset = type_text[-1].partition('charset=')
                    match text_charset[-1]:
                        case 'UTF-8':
                            logging.debug('detected "UTF-8" charset, maybe a gifv?')
                            return 'html'
                        case _:
                            return 'html'
                case _:
                    return ''
        case 'image':
            logging.debug('detected image type')
            match type_list[1]:
                case 'jpg':
                    logging.debug('detected "jpg" subtype')
                    return 'jpg'
                case 'jpeg':
                    logging.debug('detected "jpeg" subtype')
                    return 'jpeg'
                case 'png':
                    logging.debug('detected "png" subtype')
                    return 'png'
                case 'gif':
                    logging.debug('detected "gif" subtype')
                    return 'gif'
        case 'video':
            logging.debug('detected video type')
            match type_list[1]:
                case 'mp4':
                    logging.debug('detected "mp4" subtype')
                    return 'mp4'
                case 'webm':
                    logging.debug('detected "webm" subtype')
                    return 'webm'
                case _:
                    return ''
        case _:
            return ''

def url_filename_create(url_dict):
    file_name = ''
    name_id = ''
    if 'id' in url_dict:
        name_id = url_dict['id']
    logging.debug(f"id: {url_dict.get('id')}")
    logging.debug(f"author: {url_dict.get('author')}")
    # Author names given can have whack characters like ò that aren't valid in filenames,
    # first encoding them as ascii and then decoding back to utf-8 should remove those.
    name_author = ''
    if 'author' in url_dict:
        name_author = str((url_dict['author'].encode("ascii")).decode("utf-8"))
    logging.debug(f"new_author: {name_author}")
    name_title = ''
    if 'title' in url_dict:
        name_title = url_dict['title'].rsplit(sep='/', maxsplit=1)[-1]
    logging.debug(f"title: {name_title}")
    name_subreddit = ''
    if 'subreddit' in url_dict:
        name_subreddit = url_dict['subreddit']
    file_name = '_'.join([name_subreddit, name_author, name_title, name_id])
    if file_name == '___':
        file_name = (url_dict['url'].rsplit(sep='/')[-1]).rsplit(sep='.', maxsplit=1)[0]
        logging.debug(f'filename concatenated is "{file_name}"')
    return file_name

def url_download(list_urls, folder='downloads', restriction=(0, None), comments_level=0):
    """Takes given dictionary of urls,
    and downloads them to given folder.
    """
    if not list_urls:
        logging.error("No urls given, downloads aborted")
        return
    if restriction[1] is not None:
        if (restriction[1] - restriction[0]) < 0 or restriction[1] > len(list_urls):
            restriction = (0, None)
    restriction = slice(restriction[0], restriction[1])
    logging.debug(restriction)
    logging.debug(list_urls)
    logging.debug(list_urls[restriction])

    if json_settings["download_saves"]["ask"]:
        inp = input(f'You are about to download {len(list_urls[restriction])} files, are you sure? [y/yes, n/no]: ')
        # if inp != 'c' or 'choose':
        #  restriction =
        #  input(f'Type in the image where you want to start and where you want to end in the form (s, e):')
        #  if restriction[0] < 0 or restriction[0] > len(list_urls) - 1 \
        #           or restriction[1] < restriction[0] or restriction[1] > len(list_urls):
        #  print('Error: Wrong restrictions, aborting download')
        #  return
        if inp == 'n' or inp == 'no' or inp == 'N' or inp == 'No':
            logging.info('Download aborted by user.')
            return
        elif inp != 'y' and inp != 'yes' and inp != 'Y' and inp != 'Yes':
            logging.error("Invalid input, aborted.")
            return

    logging.info(f'Downloading {len(list_urls[restriction])} files...')
    p_dl = folder_create(username + '/' + folder)

    for url_index, url_object in enumerate(list_urls[restriction]):
        url_cur = url_object['url']
        logging.info(f"fetching: {url_object['url']}")

        # request the url and save the content
        req = requests.get(url_cur, allow_redirects=True)
        url_cont = [req.content]
        content_type = req.headers.get('content-type')
        # # just for me to see what's in the header
        # if url_index == 0:
        #     logging.debug(req.headers)
        print(f'{url_index + 1}/{len(list_urls[restriction])}')
        logging.debug(f'URL: {url_cur}')
        logging.debug(f'Content-type: {content_type}')
        # filename = '_'.join((url_object['subreddit'], url_object['id'])) \
        #         ''.join(('_', url_object['title'].rsplit(sep='/', maxsplit=1)[-1]))
        # check for the filetype
        file_type = [url_filetype(content_type)]
        logging.debug(f'file type: {file_type}')
        # if can't fetch it skip, if html try to crawl for an url
        if file_type[0] == '':
            logging.error('Unable to find proper filetype, skipping download')
            continue
        elif file_type[0] == 'html':
            # todo I could make this also recursively but probably never needed
            logging.debug(f'Starting html crawler for \"{url_cur}\"')
            urls_sub = url_html_crawler(url_cont[0], url_cur)
            logging.info(f'crawler returned {len(urls_sub)} urls which are {urls_sub}')
            if not urls_sub:
                logging.info('unable to find proper filetype from html, downloading only html')
            else:
                file_type.clear()
                url_cont.clear()
                dl_only_vid = False
                for urls_sub_ in urls_sub:
                    logging.info(f"now fetching: {urls_sub_}")
                    # if a new url was found with proper filetype, request again but with new link now
                    req_new = requests.get(urls_sub_, allow_redirects=True)
                    content_type = req_new.headers.get('content-type')
                    logging.debug(content_type)
                    url_cont.append(req_new.content)
                    file_type.append(url_filetype(content_type))
                    logging.debug(f'new file_type {file_type}')
                    if content_type == 'video/mp4':
                        dl_only_vid = True
                        break
                # if there is a video somethere in there, I don't want to download thumbnails and such,
                # therefore I delete those urls and only use the vid urls
                if dl_only_vid:
                    file_type = [file_type[-1]]
                    url_cont = [url_cont[-1]]

        # saving all found files
        file_name = url_filename_create(url_object)
        logging.debug(f'now have {file_name} file name, and {len(url_cont)} url contents, and {len(file_type)} file types')
        for url_cont_idx_, url_cont_ in enumerate(url_cont):
            if url_cont_idx_ == 0 and len(url_cont) == 1:
                file_full = '.'.join((file_name, file_type[url_cont_idx_]))
            else:
                file_full = '.'.join((file_name + '_' +
                                      str(url_cont_idx_ + 1), file_type[url_cont_idx_]))
            p_full = p_dl / Path(file_full)
            if Path.is_file(p_full):
                logging.info(f"File \"{file_full}\" already exists, won't overwrite")
                continue
            logging.info(f'Downloading "{file_full}" to "{p_full}"...')
            with open(p_full, 'wb') as urlfile:
                urlfile.write(url_cont_)

        # download comments too
        if comments_level > 0:
            p_dl_com = folder_create(p_dl / Path('comments'))
            file_com = file_name + '.txt'
            p_full = p_dl_com / Path(file_com)
            praw_comments_download('https://reddit.com' + url_object['permalink'], p_full,
                                   comments_level=comments_level)


def main() -> int:
    print('Welcome to my reddit account migrator and downloader!')

    logging.basicConfig(filename='ramd.log', filemode='w', encoding='utf-8', level=logging.DEBUG)
    logger = logging.getLogger('base')
    # # for debugging html crawler
    # logging.basicConfig(filename='ramd.log', filemode='w', encoding='utf-8', level=logging.INFO)
    # saves_url = [{'date': '2023-06-11-20', 'subreddit': '196', 'author': 'Frigid_Metal', 'id': '146qcqg',
    #               'permalink': '/r/196/comments/146qcqg/one_last_hornypost_before_the_sub_goes_dark_rule/',
    #               'url': 'https://i.redd.it/jrmn1vdd7d5b1.jpg', 'body': '', 'title': 'test'},
    #              {'url': 'https://imgur.com/a/lDy36fM'},
    #              {'url': 'https://i.imgur.com/XVmWPe3.gifv'},
    #              {'date': '', 'subreddit': 'OnePunchMan', 'author': '', 'id': 'jaqtqq9',
    #               'permalink': '/r/OnePunchMan/comments/11gw74d/tatsumaki_simps/jaqtqq9/',
    #               'url': 'https://imgur.com/a/AmVAOuS', 'body': '', 'title': 'test'}]
    # url_download(saves_url, folder=('testdownloads'), comments_level=0)
    # # todo make default folder always file folder at start
    # # todo make it so you can give the downloader any dictionary and it only tries to get the keys
    # return 0

    # read in json file given as argument or try to get template file otherwise
    # read in arguments and save them as dicts
    json_filepath = Path(__file__).parent / Path('user_template.json')  # change me if you don't want to use arguments
    args_add = dict()

    # first argument (except program-name) should be
    if len(sys.argv) >= 2:
        if len(sys.argv) == 2 or len(sys.argv) % 2 == 0:
            json_filepath = Path(sys.argv[1])
        # check for additional arguments and save them into a dict (if they are even)
        rest_args = sys.argv[slice(2, len(sys.argv))]
        if rest_args:
            rest_args = sys.argv[slice(2, len(sys.argv))]
            # for add_args in sys.argv[slice(2, len(sys.argv))]:
            # Creating list containing keys alone by slicing
            lk = rest_args[::2]
            # todo add check to see if flags are valid, or make a for loop in general...
            # in general I'm pretty sure there are easier methos or even built-in functions
            # Creating list containing values alone by slicing
            lv = rest_args[1::2]
            # merging two lists using zip()
            z = zip(lk, lv)
            # Converting zip object to dict using dict() constructor.
            args_add = dict(z)
    elif len(sys.argv) != 1:
        print(f"Error: Argument error!")
        logging.critical('Argument error')
        raise SystemExit(2)
    logging.info(f'Successfully loaded arguments {args_add}')

    try:
        with open(json_filepath) as json_file:
            user_json = json.load(json_file)
            print(f"Loaded json file '{json_filepath}.'")
            logging.info(f"Loaded json file '{json_filepath}'")
    except IOError:
        print(f"Error: Can't read json file '{json_filepath}'!")
        logging.error(f"Couldn't read json file '{json_filepath}'")
        raise

    # check if minimum login-settings are given
    # todo this has to be possible to make more concise, right? Right?
    if not (user_json and ("user_agent" in user_json) and ("client_id" in user_json)
            and ("client_secret" in user_json) and ("username" in user_json) and ("password" in user_json)):
        print("Error: Json file misses necessary login data fields!")
        logging.critical("Json file misses necessary login data fields")
        return 1
    elif not (user_json["user_agent"] and user_json["client_id"] and user_json["client_secret"]
              and  user_json["username"] and user_json["password"]):
        print("Error: Json file misses necessary login data!")
        logging.critical("Json file misses necessary login data fields")
        return 1
    # overwrite settings if given in json-file
    if "settings" in user_json:
        global json_settings
        json_settings = user_json["settings"]
        logging.debug("Overwriting json settings")

    # log in as the user and save global username and json settings
    try:
        logging.info("Trying praw connection")
        global reddit
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
        logging.info(f"Successfully connected to reddit user '{username}'")
    except Exception as err:
        print(F"ERROR: Couldn't create praw reddit user {err}, {type(err)=}!")
        logging.critical(f"Couldn't create praw reddit user {err}, {type(err)=}")
        raise
    print()

    # check additional flags and execute the functions
    # I should probably put this all in its own function.
    for flag, value in args_add.items():
        if not (flag in ('-s', '-u', '-m', '-l')):
            print(f'Error: Flag "{flag}" is not an option!')
            logging.critical(f'Flag "{flag}" is not an option!')
            continue
        if not value:
            logging.error(f'argument value missing')
            continue
        if flag != '-l':
            txt_content = file_text_read(Path(username) / Path(value))
            if flag != '-m':
                txt_content = edit_remove_duos(txt_content,
                                          URL_DELGARBAGERS + URL_DELIMITERS)
        # Naive approach, I should check if the subs exist and isn't
        # private or banned first!
        # I had the txt_line loop first, but it made things more
        # complicate even if more efficient.
        match flag:
            case '-s':
                print('Subscribing to given subreddits...')
                logging.info('Subscribing to given subreddits...')
                for txt_line in txt_content:
                    reddit.subreddit(txt_line).subscribe()
                    logging.info(f'Subscribed to subreddit {txt_line}')
                # print(f'Subscribed to "{txt_line}".')
            case '-u':
                print('Unsubscribing from given subreddits...')
                logging.info('Unsubscribing from given subreddits...')
                for txt_line in txt_content:
                    reddit.subreddit(txt_line).unsubscribe()
                    logging.info(f'Unsubscribed from subreddit {txt_line}')
            case '-m':
                print('Creating given multireddits...')
                logging.info('Creating given multireddits...')
                for txt_line in txt_content:
                    spaced = txt_line.split(' ')
                    multiname = spaced[0].rstrip(':')
                    multisubs = spaced[1:-1]
                    multisubs_new = []
                    # for sub in multisubs:
                    #     multisubs_new.append(reddit.subreddit(display_name=sub))
                    logging.debug(f'Creating multireddit {multiname} with {len(multisubs)} subs')
                    multiname_cleaned = edit_remove(multiname, URL_DELGARBAGERS + URL_DELIMITERS + ['/', '//'])
                    multisubs_cleaned = edit_remove_duos(multisubs, URL_DELGARBAGERS + URL_DELIMITERS + ['/', '//'])
                    if not (multiname and multisubs):
                        # print(f"Error: no multireddit name or subreddits given!")
                        break
                    reddit.multireddit.create(display_name=multiname_cleaned, subreddits=multisubs_cleaned)
                    # print(f'Created multireddit "{multiname}"')
                    # print(f'  with multisubs: {multisubs_cleaned}')
                    # todo could add also an option to delete multireddits and/or subs from it
            case '-l':
                # print(value)
                # print(getattr(logging, value.upper(), None))
                if not (value in ('DEBUG', 'INFO', 'WARNING', 'CRITICAL', 'ERROR')):
                    logging.error('invalid logging value')
                    continue
                logging.info(f'logging mode set to {value}')
                logger.setLevel(getattr(logging, value.upper(), None))
                # todo this doesn't work yet

    # fetch all subscribed subs of my user
    if json_settings["download_subreddits"]["fetch"]:
        print('Fetching subscribed subreddits...')
        logging.info('Fetching subscribed subreddits...')
        my_subreddits = reddit.user.subreddits(limit=json_settings["download_subreddits"]["limit"])
        # my_subreddits_names = []
        # for subreddit in my_subreddits:
        #     my_subreddits_names.append(subreddit.fullname)
        if my_subreddits:
            file_text_write(my_subreddits, Path(username) / Path(username + '_sub' + '.txt'))
        else:
            logging.info("No user subscribed subreddits found")

    # fetch all multireddits and belonging subs of my user
    if json_settings["download_multireddits"]["fetch"]:
        print('Fetching multireddits...')
        logging.info('Fetching multireddits...')
        my_multireddits = reddit.user.me().multireddits()
        # pprint.pprint(my_multireddits) # vars()
        if my_multireddits:
            multireddits_txt = []
            for multireddit in my_multireddits:
                multi_line = multireddit.display_name + ':'
                logging.info(f'found multireddit {multi_line}')
                for subreddit in multireddit.subreddits:
                    logging.debug(f'subreddit display name is {subreddit.display_name}')
                    multi_line = multi_line + ' ' + subreddit.display_name
                multireddits_txt.append(multi_line)
            file_text_write(multireddits_txt, Path(username) /
                            Path(username + '_multireddits' + '.txt'))
        else:
            logging.info("No user multireddits found")

    # fetch all comments of my user
    if json_settings["download_comments"]["fetch"]:
        print('Fetching users comments...')
        logging.info('Fetching users comments...')
        my_comments = reddit.user.me().comments.new(limit=json_settings["download_comments"]["limit"])
        if my_comments:
            # save them into dictionary of my preferred format
            redditor_comments = [{'date': comment.created_utc, 'subreddit': comment.subreddit.display_name,
                                  'id': comment.id, 'permalink': comment.permalink,
                                  'body': comment.body} for comment in my_comments]
            dict_convert(redditor_comments)
            file_csv_write(redditor_comments,
                           ('_comments_l' + str(json_settings["download_comments"]["comments_level"])))
        else:
            logging.info('No user comments found.')

    # fetch all saves of my user
    if json_settings["download_saves"]["fetch"]:
        print('Fetching users saved submissions...')
        my_saves = reddit.user.me().saved(limit=json_settings["download_saves"]["limit"])
        # redditor_saves = [{'date': save.created_utc, 'subreddit': save.subreddit.display_name, 'id': save.id,
        #                    'permalink': save.permalink, 'url': save.url} for save in my_saves]
        # Hmm, dunno how or even if I can do that in one lne, so I just do it in an extended for-loop instead

        # todo Dang, this needs kinda long, I should probably optimize that one
        redditor_saves = []
        for save in my_saves:
            if hasattr(save, 'url'):
                redditor_saves.append({'date': save.created_utc, 'subreddit': save.subreddit.display_name,
                                       'author': str(save.author), 'id': save.id, 'permalink': save.permalink,
                                       'url': save.url, 'body': None})
            elif hasattr(save, 'body'):
                redditor_saves.append({'date': save.created_utc, 'subreddit': save.subreddit.display_name,
                                       'author': str(save.author), 'id': save.id, 'permalink': save.permalink,
                                       'url': None, 'body': save.body})
            else:
                logging.error("Save doesn't contain url or body field!")
        dict_convert(redditor_saves)
        file_csv_write(redditor_saves, '_saves')

        # Extracting urls; use // before them otherwise it will find sth like imgur twice (in //imgur and in //i.imgur.
        if json_settings["download_saves"]["urls"]:
            for url_cur in json_settings["download_saves"]["urls"]:
                if not url_cur["fetch"]:
                    continue
                saves_url = dict_url_extract(redditor_saves, url_cur["url"])
                saves_url_names = []
                if saves_url_names == '':
                    saves_url_names = 'all'
                else:
                    for url_idx in url_cur["url"]:
                        saves_url_names.append(url_idx.strip('//'))
                    # saves_url_filename = [str.join(name) for name in saves_url_names]
                file_csv_write(saves_url, ('_saves_' + '-'.join(saves_url_names)))
                if url_cur["download"]:
                    # download files from a fetched urls
                    # takes optional slice parameter that defaults to slice(0, -1)
                    url_download(saves_url, folder=url_cur["folder"], restriction=url_cur["slice"],
                                 comments_level=url_cur["comments_level"])
                    # url_download_comments(reddit, saves_imgur, 0)

    return 0


if __name__ == '__main__':
    sys.exit(main())
