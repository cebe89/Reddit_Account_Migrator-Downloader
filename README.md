# Reddit_Account_Migrator-Downloader
# Written in python 3.10
# required packages: praw

Description:
A program I've written for myself with (intially) the goal to be able to save all my subscribed subreddits to a file, and I can auto-subsribe to a list when I have one.
Because after a while it becomes no longer feasable doing it all by hand.
I also saved a ton of links on my accounts, and it would become a nightmare finding something I once found interesting enough to save it. So additionally I added a download option for all my saved favorites
Also with recently added restrictions to a certain website regarding specific content, I thought why not getting the download-links from my favorites and put them in one file, so I added that.
And then I thought, hey why not just download them right there? So lastly I added a html crawler and a download method that finds the files and downloads them locally.
Considering how reddit plans to increase their monetization by making the API no longer free, and the changing site-policies of imgur, I figured there is no better time than now to finally realise it.
It also helped me to get more compfortable with python, how it handles files, it's string capabilities and also how to use it to scramble sites and download stuff with it.
And I got to deal with github properly finally, and made a proper one where I will hopefully upload more of little programs I might code in the future.

Features (currently):
-fetch subscribed subreddits of user
-fetch subscribed multireddits and belonging subreddits of user
-save subscribed subreddits and multireddits locally to disk in a txt format
-fetch saved favorites of user
-fetch all comments made by user
-convert fetched comments and favorites into a dictionary secluding relevant parts and changing format
-save comments and favorites locally to disk in a csv format
-extract specified urls from fetched favorites and save them locally in a csv format
-download a given list of urls where the program tries to find the actual files in case of a html-link
 currently supported fileformats: jpg, png, gif, mp4
 currently supported websites: i.reddit.com, i.imgur.com, imgur.com (crawls for i.imgur.com links)

Features (planned):
-option to load subreddit and multireddit list from a local txt file
-option to subscribe/unsubscribe from a list
-option to create multireddits and add belonging subreddits from a list
-option to load favorites from a csv file 
-option to reverse convert the dicts into the praw formats
-option to unsave favorites from a list
-add crawler for reddit galleries
-add crawler for imgur galleries
-add more other websites to extract and crawl for and download (redgifs etc) 
-option to load posts (and extract links and download them) from any user
-add a proper option to turn on/off options when executing (arguments, CLI?)

Installation:
Just download the reddit_account_migrator-downloader.py and the user_template.json file and put them together in a specific folder.
Use the json file to enter the reddit API certifications of your account (see here: https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example#first-steps)
It needs the praw package as a base, so install it into your environment (e.g. from here: https://anaconda.org/conda-forge/praw)

Usage:
Right now the only way to use it is the classic way of manipulating the main and just executing the whole thing.
Right at the start of the main you can find the line "json_name = 'user_template.json'", enter the name of the json file mentioned above and you should get logged in.
There are also no flags yet, so if you don't want something of the current features, you have to outcomment them in the main.
I have implemented some failsaves so the whole thing doesn't die when one function relies on another, but you still better take care.
All csv and txt files are saved by default into a folder with the same name as the username. 
Downloaded images are saved into the folder in a 'downloads' subfolder by default, but you can also give the function a different option.
It asks you before you download one of the url lists if you are sure and shows you how many links it will attempt to download, which you can skip if you write n/no. 
If you want to only download a certain intervall from the url-list, you can also give the download method a slice with (from, to).
The main does in order: 
read json > log-in > fetch subreddits > fetch multireddits > save subreddits locally > save multireddits locally >
fetch saved favorites > fetch user comments > convert both into dict > save favorites to csv file > 
extract urls (imgur and i.reddit) from dict > save extracted urls to csv file > download extracted urls (webcrawls if not direct link)

https://anaconda.org/conda-forge/praw

Credits: Thanks obviously to the praw devs, it made things a lot easier.

Disclaimer: I take no responsibility for any and all damage that may be done by executing the included files, by doing so you are aware of the implications and accept this.
