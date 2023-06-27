# Reddit Account-Migrator and Downloader
**Written in:** *python 3.10*  
**Required packages:** *praw*

# Description
Used to download all of users data (subscribed subreddits, saves, comments etc) and save them as txt/csv files to ease making a new account or when planning to delete account.

# Features
**Current:**  
-user account details and flags/settings are loaded from a json file  
-fetch subscribed subreddits of user and export to txt-file  
-fetch subscribed multireddits and belonging subreddits of user and export to txt-file  
-subscribe/unsubscribe and create multireddits from a given txt-file  
-fetch saved favorites of user and export to csv-file  
-fetch all comments made by user and export to csv-file  
-convert fetched comments and saves into a dictionary secluding relevant parts and changing format
-extract specified urls from fetched saves and export to csv-file  
-download specified urls if they lead to an image/video-file locally to disk
 currently supported fileformats: jpg, png, gif, mp4  
 currently supported websites: i.reddit.com, i.imgur.com, imgur.com (needs html crawl)  
-download all comments belonging to a saved link (only level 2 currently), idea is to get actual artist sources that way

**Planned:**  
-add crawler for imgur galleries  
-add crawler for reddit galleries and v.reddit videos
-add more other websites to extract and crawl for and download (twitter, giphy etc.)  
-option to download all posts/links from a subreddit/user  
-option to load favorites from a csv file (do I really need this?)  
-option to reverse convert the dicts into the praw formats  (do I really need this?)  
-option to unsave favorites from a list  (do I really need this?)  

# Installation
Download the *"reddit_account_migrator-downloader.py"* and the *"user_template.json"* file and put them together in a specific folder.  
Change the *user_template.json* file or better copy it and rename it to your username, e.g. *user_myredditaccount.json*.
Open the json file and enter the reddit API certifications of your account (see here: https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example#first-steps).  
Your environment needs the praw package as a base, so install it into your environment (e.g. from here: https://anaconda.org/conda-forge/praw).

# Usage
Open it in the python terminal with your json-file as argument, e.g. *"reddit_account_migrator-downloader.py user_myredditaccount.json"* (you can also give a full path).
Alternatively just start it if you used the *"user_template.json"* file or rename it in the main.  
If you don't want a function, change the appropriate *"fetch"* field to false in the json file.  
The *"limit"* field changes how many you want to fetch, Null means it will fetch all (you probably don't need to change this one).  
It asks you before you download one of the url lists if you are sure and shows you how many links it will attempt to download.  
If you want to only download a certain interval from the url-list, you can also change the json file for the sites to take a slice with (from, to).  
All csv and txt files are saved by default into a folder with the same name as the username.   
Downloaded images are saved into the folder in a 'downloads' subfolder by default, but you can also give the function a different folder in the json.  
Now also takes  some unique flags besides the json settings:  
"-s" "file": Give it a txt file with a subreddit's name on each line, and it will subscribe to all included subreddits.  
"-u" "file": Same as before, but now it unsubscribes you from the listed subreddits.  
"-m" "file": Give it a txt file where each line is formatted like "multireddit: subreddit1 subreddit2 subr..." and it will create the multireddits with the given subreddits in it.
I had some issue where subreddit names where not compatible, for now I only have a message warning you and removing it from the list beforehand.
Also I don't check (yet) if a subreddit actually exists and is not private or banned, praw will give you an error then.

# etc
**Author:** cebe89  
**Credits:** Thanks obviously to the praw devs, it made things a lot easier.  
**Disclaimer**: I take no responsibility for any and all damage that may be done by executing the included files, by doing so you are aware of the implications and accept this.  
