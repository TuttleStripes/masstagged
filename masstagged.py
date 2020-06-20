"""This program finds how many clicks it takes to get from one subreddit
to a subreddit listed under the MassTagger
"""
import re
import sys
from collections import defaultdict, deque

import praw
from prawcore.exceptions import Forbidden, NotFound, Redirect

reddit = praw.Reddit(client_id=os.environ['CLIENT_ID'],
                     client_secret=os.environ['CLIENT_SECRET'],
                     password=os.environ['REDDIT_PASS'],
                     username=os.environ['REDDIT_USER'],
                     user_agent=os.environ['USER_AGENT'])

with open('tagged.txt') as f:
    TAGGED = f.read().split('\n')

CACHE = set()
TIER = 0
TIERLIST = defaultdict(set)
TREE = defaultdict(set)

def read_sidebar(subreddit):
    """Returns all subreddits in the sidebar

    Params
    ------
    subreddit: praw Subreddit

    Yields
    ------
    praw Subreddit
    """
    global CACHE, TAGGED
    sidebar = subreddit.description_html
    if sidebar is None:
        return None
    children = re.finditer(r'href="(?:[^"]*?reddit\.com)?/?r/(\w+)">(?!</a>)', sidebar)
    for child in children:
        try:
            child = child[1].lower()
            if child not in CACHE:
                CACHE.add(child)
                childsub = reddit.subreddit(child)
                #checks if subreddit exists/can be accessed, else throws error
                childsub.fullname
                yield childsub
        except (Forbidden, NotFound, Redirect, TypeError):
            if child in TAGGED:
                yield childsub
            CACHE.add(child)


def scrape(tierlevel: set):
    """Builds cache, tierlist and tree.
    Returns a masstaggeed subreddit if one is found, else None
    Params
    ------
    tierlevel:
        The subs from TIERLIST[TIER] that will be scraped

    Returns
    -------
    praw.subreddit or None
    """
    global TAGGED, TIER, TIERLIST, TREE
    TIER += 1
    for sub in tierlevel:
        for child in read_sidebar(sub):
            print(f'\r{sub.display_name.ljust(21)}: {child.display_name.ljust(21)}', end='', flush=True)
            TIERLIST[TIER].add(child)
            TREE[sub].add(child)
            if child.display_name.lower() in TAGGED:
                return child
    return None


def pathing(subreddit) -> deque:
    """Builds the path from the start sub to the param subreddit

    Params
    ------
    subreddit: praw.subreddit
        the last subreddit in the path

    Returns
    -------
    deque:
        path from start sub to end sub
    """
    global STARTSUB, TIER, TIERLIST, TREE
    queue = deque([subreddit.display_name])
    while TIER:
        for sub in TIERLIST[TIER]:
            if subreddit in TREE[sub]:
                queue.appendleft(sub.display_name)
                subreddit = sub
        TIER -= 1
    queue.appendleft(STARTSUB.display_name)
    return queue


def main(subreddit) -> deque:
    """Scrapes and builds path
    """
    global TIER, TIERLIST
    print(f'{"Parent".ljust(21)}: Child')
    while TIERLIST[TIER]:
        branch = scrape(TIERLIST[TIER])
        if branch is not None:
            path = pathing(branch)
            return path
    return deque()


if __name__ == '__main__':
    STARTSUB = sys.argv[1].lower()
    if STARTSUB == 'random':
        STARTSUB = reddit.random_subreddit().display_name.lower()
    elif STARTSUB == 'randnsfw':
        STARTSUB = reddit.random_subreddit(nsfw=True).display_name.lower()
    CACHE.add(STARTSUB)
    STARTSUB = reddit.subreddit(STARTSUB)
    TIERLIST[0].add(STARTSUB)
    print(STARTSUB)
    PATH = main(STARTSUB)
    if PATH:
        print(f'\nPathed in {len(PATH) - 1} click{"s" * (PATH != 1)}!')
        print(' -> '.join(PATH))
    else:
        print('\nFailed to path')
