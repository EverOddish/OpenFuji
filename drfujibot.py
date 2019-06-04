import asyncio
import copy
import datetime
import glob
import json
import logging
import math
import multiprocessing
import operator
import os
import random
import re
import shutil
import socket
import sys
import threading
import time
import traceback
import types
import urllib
from collections import defaultdict
from datetime import timedelta

import discord
import iso8601
import requests
import wikipedia
from anagram import Anagram
#import requests_cache
from bs4 import BeautifulSoup
from whoosh.spelling import ListCorrector

import drfujibot_irc.bot
import drfujibot_irc.strings
import drfujibot_pykemon.api
import drfujibot_pykemon.exceptions
import drfujibot_pykemon.request

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    output = str(exc_type) + " " + str(exc_value) + " " + ''.join(traceback.format_tb(exc_traceback)) + "\n"
    output += '---------------------------------------------------------\n'
    with open('exceptions.log', 'a') as f:
        f.write(sys.argv[1] + "\n")
        f.write(output)

    os._exit(1)

def load_words(filename='/usr/share/dict/american-english'):
    with open(filename) as f:
        for word in f:
            yield word.rstrip()

g_words = load_words()

def get_anagrams(source=g_words):
    d = defaultdict(list)
    for word in source:
        key = "".join(sorted(word))
        d[key].append(word)
    return d

sys.excepthook = handle_exception

g_c = None
g_whisperMode = False
g_bot = None

def fix_pokemon_name(name):
    if name.lower() == "pumpkaboo":
        name = "pumpkaboo-average"
    elif name.lower() == "gourgeist":
        name = "gourgeist-average"
    elif name.lower() == "darmanitan":
        name = "darmanitan-standard"
    elif name.lower() == "deoxys":
        name = "deoxys-speed"
    elif name.lower() == "meowstic":
        name = "meowstic-male"
    elif name.lower() == "basculin":
        name = "basculin-red-striped"
    elif name.lower() == "wormadam":
        name = "wormadam-plant"
    elif name.lower() == "keldeo":
        name = "keldeo-ordinary"
    elif name.lower() == "wishiwashi":
        name = "wishiwashi-solo"
    elif name.lower() == "meloetta":
        name = "meloetta-aria"
    return name

def fix_z_move(name):
    if "breakneck-blitz" == name.lower():
        name = "breakneck-blitz--physical"
    elif "all-out-pummeling" == name.lower():
        name = "all-out-pummeling--physical"
    elif "supersonic-skystrike" == name.lower():
        name = "supersonic-skystrike--physical"
    elif "acid-downpour" == name.lower():
        name = "acid-downpour--physical"
    elif "tectonic-rage" == name.lower():
        name = "tectonic-rage--physical"
    elif "continental-crush" == name.lower():
        name = "continental-crush--physical"
    elif "savage-spin-out" == name.lower():
        name = "savage-spin-out--physical"
    elif "never-ending-nightmare" == name.lower():
        name = "never-ending-nightmare--physical"
    elif "corkscrew-crash" == name.lower():
        name = "corkscrew-crash--physical"
    elif "inferno-overdrive" == name.lower():
        name = "inferno-overdrive--physical"
    elif "hydro-vortex" == name.lower():
        name = "hydro-vortex--physical"
    elif "bloom-doom" == name.lower():
        name = "bloom-doom--physical"
    elif "gigavolt-havoc" == name.lower():
        name = "gigavolt-havoc--physical"
    elif "shattered-psyche" == name.lower():
        name = "shattered-psyche--physical"
    elif "subzero-slammer" == name.lower():
        name = "subzero-slammer--physical"
    elif "devastating-drake" == name.lower():
        name = "devastating-drake--physical"
    elif "black-hole-eclipse" == name.lower():
        name = "black-hole-eclipse--physical"
    elif "twinkle-tackle" == name.lower():
        name = "twinkle-tackle--physical"
    return name

def get_coin_balances(source_user):
    output = source_user + " : You have "

    with open('PokemonChallenges_coins.json', 'r') as coin_file:
        coin_info = json.load(coin_file)
        coins = coin_info.get('coins')
        if None != coins:
            if source_user in coins.keys():
                output += str(int(coins[source_user]))
                output += " coins"
            else:
                "0 coins"

    return output

def get_weaknesses(type1, type2):
    weaknesses = []
    try:
        t1 = drfujibot_pykemon.api.get(type=type1)
        t2 = None
        if type2:
            t2 = drfujibot_pykemon.api.get(type=type2)

        weaknesses = [w.get('name') for w in t1.double_damage_from]
        if t2:
            for w in t2.double_damage_from:
                weaknesses.append(w.get('name'))

        resistances = [r.get('name') for r in t1.half_damage_from]
        if t2:
            for r in t2.half_damage_from:
                resistances.append(r.get('name'))

        no_dmg_types = [t.get('name') for t in t1.no_damage_from]
        if t2:
            for t in t2.no_damage_from:
                no_dmg_types.append(t.get('name'))

        # Take out no-damage types outright.
        weaknesses = [w for w in weaknesses if w not in no_dmg_types]

        # Reduce weakness instance by one for each resistance.
        for r in resistances:
            if r in weaknesses:
                weaknesses.remove(r)

    except drfujibot_pykemon.exceptions.ResourceNotFoundError:
        print("Type(s) not found.")
    except:
        print("Unexpected error: " + str(sys.exc_info()[0]))

    return weaknesses

def get_resistances(type1, type2):
    resistances = []
    try:
        t1 = drfujibot_pykemon.api.get(type=type1)
        t2 = None
        if type2:
            t2 = drfujibot_pykemon.api.get(type=type2)

        weaknesses = [w.get('name') for w in t1.double_damage_from]
        if t2:
            for w in t2.double_damage_from:
                weaknesses.append(w.get('name'))

        resistances = [r.get('name') for r in t1.half_damage_from]
        if t2:
            for r in t2.half_damage_from:
                resistances.append(r.get('name'))

        no_dmg_types = [t.get('name') for t in t1.no_damage_from]
        if t2:
            for t in t2.no_damage_from:
                no_dmg_types.append(t.get('name'))

        # Take out no-damage types outright.
        resistances = [r for r in resistances if r not in no_dmg_types]

        # Reduce resistance instance by one for each weakness.
        for w in weaknesses:
            if w in resistances:
                resistances.remove(w)

    except drfujibot_pykemon.exceptions.ResourceNotFoundError:
        print("Type(s) not found.")
    except:
        print("Unexpected error: " + str(sys.exc_info()[0]))

    return resistances

def get_immunities(type1, type2):
    immunities = []
    try:
        t1 = drfujibot_pykemon.api.get(type=type1)
        t2 = None
        if type2:
            t2 = drfujibot_pykemon.api.get(type=type2)

        immunities = [t.get('name') for t in t1.no_damage_from]
        if t2:
            for t in t2.no_damage_from:
                immunities.append(t.get('name'))

    except drfujibot_pykemon.exceptions.ResourceNotFoundError:
        self.output_msg(c, "Type(s) not found.", source_user)
    except:
        print("Unexpected error: " + str(sys.exc_info()[0]))

    return immunities

def is_global_command(line):
    global_commands = [
        "!deaths",
        "!sprite",
        "!fallen",
        "!bet",
        "!coins",
        "!balance",
        "!honestly",
        "!realtime",
        "!daily",
        "!song",
        "!uptime",
        "!fixit",
        "!quote",
        "!latestquote",
        "!elo",
        "!leaderboard",
        "!shaq",
        "!combo",
        "!attempt",
        "!dab",
        "!rating",
    ]
    for c in global_commands:
        if line.startswith(c):
            return True
    return False

def parse_time(time_str):
    regex = re.compile(r'((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')
    parts = regex.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)

def sort_by_coverage(mv):
    super_effective_types = []
    types = ['normal', 'fire', 'fighting', 'water', 'flying', 'grass', 'poison', 'electric', 'ground', 'psychic', 'rock', 'ice', 'bug', 'dragon', 'ghost', 'dark', 'steel', 'fairy']
    try:
        for t in types:
            t1 = drfujibot_pykemon.api.get(type=t)
            weaknesses = [w.get('name') for w in t1.double_damage_from]
            if mv.type in weaknesses:
                super_effective_types.append(t)

    except drfujibot_pykemon.exceptions.ResourceNotFoundError:
        self.output_msg(c, "Type(s) not found.", source_user)
    except:
        print("Unexpected error: " + str(sys.exc_info()[0]))

    print(mv.name + " " + mv.type + " SE against " + str(super_effective_types))
    return len(super_effective_types)


def genNameToNum(name):
    gen = 0

    if "red-blue" in name or "yellow" in name:
        gen = 1
    elif "gold-silver" in name or "crystal" in name:
        gen = 2
    elif "ruby-sapphire" in name or "emerald" in name or "firered-leafgreen" in name:
        gen = 3
    elif "diamond-pearl" in name or "platinum" in name or "heartgold-soulsilver" in name:
        gen = 4
    elif "black-white" in name or "black-2-white-2" in name:
        gen = 5
    elif "x-y" in name or "omega-ruby-alpha-sapphire" in name:
        gen = 6
    elif "sun-moon" in name:
        gen = 7

    return gen

def getRegionForGame(game):
    region = ''

    if 'red' == game or 'blue' == game or 'yellow' == game or 'leaf-green' == game or 'fire-red' == game:
        region = 'kanto'
    elif 'gold' == game or 'silver' == game or 'crystal' == game or 'heart-gold' == game or 'soul-silver' == game:
        region = 'johto'
    elif 'ruby' == game or 'sapphire' == game or 'emerald' == game or 'omega-ruby' == game or 'alpha-sapphire' == game:
        region = 'hoenn'
    elif 'diamond' == game or 'pearl' == game or 'platinum' == game:
        region = 'sinnoh'
    elif 'black' == game or 'white' == game or 'black-2' == game or 'white-2' == game:
        region = 'unova'
    elif 'x' == game or 'y' == game:
        region = 'kalos'
    elif 'sun' == game or 'moon' == game:
        region = 'alola'

    return region

def find_chain(chain, name):
    if name == chain.get('species').get('name'):
        return chain
    else:
        for c in chain.get('evolves_to'):
            result = find_chain(c, name)
            if result:
                return result

def get_fuji_config_value(key):
    result = None
    with open('DrFujiBot_config.json', 'r') as f:
        config = json.load(f)
        result = config.get(key)
    return result

class DrFujiBot(drfujibot_irc.bot.SingleServerIRCBot):
    def __init__(self, username, permitted_users, moderators, whisperMode, game, bot_type):
        self.game = game
        self.bot_type = bot_type
        self.whisperMode = whisperMode

        twitch_oauth_token = get_fuji_config_value('twitch_oauth_token')
        twitch_username = get_fuji_config_value('twitch_username')

        drfujibot_irc.bot.SingleServerIRCBot.__init__(self, [("irc.chat.twitch.tv" if True == self.whisperMode else "irc.twitch.tv", 6667, twitch_oauth_token)], twitch_username, twitch_username)
        self.channel = "#" + username.lower()
        self.username = username
        self.start_time = datetime.datetime.now()

        self.previous_users = None
        if bot_type and bot_type == 'discord':
            users_file = 'whisper_discord_users.json'
        else:
            users_file = 'whisper_users.json'
        with open(users_file, 'r') as config_file2:
            self.previous_users = json.load(config_file2)

        self.bee = []
        with open('bee.txt', 'r') as bee_file:
            for line in bee_file:
                for word in line.split():
                    self.bee.append(word)
        self.shaq = []
        with open('shaq.txt', 'r') as shaq_file:
            for line in shaq_file:
                for word in line.split():
                    self.shaq.append(word)
        self.bee_index = 0
        self.shaq_index = 0
        self.deaths = 0

        # For betting
        self.open_events = {}
        self.open_event_rewards = {}
        self.closed_events = {}

        self.last_line = ""
        self.same_counter = 0

        configname = ""
        self.config = None
        if bot_type and bot_type == 'discord':
            configname = username + '_discord.json'
        else:
            configname = username + '.json'
            coins_config_name = username + '_coins.json'
        with open(configname, 'r') as config_file:
            self.config = json.load(config_file)
        if self.config:
            self.bee_index = self.config['bee_index']
            if self.config.get('shaq_index'):
                self.shaq_index = self.config['shaq_index']
            else:
                self.shaq_index = 0

            if self.config.get('handle_pcwe'):
                self.pcwe_thread = threading.Thread(target=self.pcwe_loop)
                self.pcwe_thread.start()

            if self.config.get('deaths'):
                self.deaths = self.config.get('deaths')

            self.meme_mode = False
            if self.config.get('meme_mode'):
                self.meme_mode = self.config.get('meme_mode')

            if self.config.get('fallen'):
                # Keys are names, values are number of respects paid
                self.fallen = self.config.get('fallen')
            else:
                self.fallen = {}

            if self.config.get('fallen_timestamps'):
                # Keys are names, values are timestamps of final respects
                self.fallen_timestamps = self.config.get('fallen_timestamps')
            else:
                self.fallen_timestamps = {}

            if self.config.get('open_events'):
                # event name, bet dict
                for (k, v) in self.config['open_events'].items():
                    self.open_events[k] = v

            if None == self.config.get('open_event_rewards'):
                self.config['open_event_rewards'] = {}
            if self.config.get('open_event_rewards'):
                # event name, reward
                for (k, v) in self.config['open_event_rewards'].items():
                    self.open_event_rewards[k] = v

            if self.config.get('closed_events'):
                # event name, bet dict
                for (k, v) in self.config['closed_events'].items():
                    self.closed_events[k] = v

            if None == self.config.get('extra_commands'):
                self.config['extra_commands'] = {}

            if None == self.config.get('extra_commands_on'):
                self.config['extra_commands_on'] = False

            if None == self.config.get('winners'):
                self.config['winners'] = {}

            if None != self.config.get('timed_messages'):
                self.timed_message_thread = threading.Thread(target=self.timed_message_loop)
                self.timed_message_thread.start()

            if None == self.config.get('pokeapi_url'):
                self.config['pokeapi_url'] = ''

            if None == self.config.get('auto_shoutout'):
                self.config['auto_shoutout'] = [] 

            if None == self.config.get('last_auto_shoutout'):
                self.config['last_auto_shoutout'] =  {}

            if None == self.config.get('shoutout_messages'):
                self.config['shoutout_message'] = [] 

            if None == self.config.get('command_whitelist'):
                self.config['command_whitelist'] = [] 

            if None == self.config.get('quotes'):
                self.config['quotes'] = {} 
            else:
                if isinstance(self.config['quotes'], list):
                    self.config['quotes'] = {} 

            if None == self.config.get('run_data'):
                self.config['run_data'] = {}

            if None == self.config.get('last_ruby_sighting'):
                self.config['last_ruby_sighting'] = 0

            if None == self.config.get('highest_combo'):
                pair = []
                pair.append(0)
                pair.append("")
                self.config['highest_combo'] = (0, "")

            if None == self.config.get('current_run'):
                self.config['current_run'] = ""
            else:
                if None != self.config['run_data'].get(self.config['current_run']):
                    if None != self.config['run_data'][self.config['current_run']].get('deaths'):
                        self.deaths = self.config['run_data'][self.config['current_run']]['deaths']
                    if None != self.config['run_data'][self.config['current_run']].get('closed_events'):
                        self.config['closed_events'] = self.config['run_data'][self.config['current_run']]['closed_events']

            if None == self.config.get('welcome_messages'):
                self.config['welcome_messages'] = {}

        self.bet_config = {}
        with open('bet_config.json', 'r') as config_file:
            self.bet_config = json.load(config_file)

        self.coin_data = {}
        self.foundCoinFile = True
        try:
            with open(coins_config_name, 'r') as config_file:
                self.coin_data = json.load(config_file)

                if None == self.coin_data.get('last_daily_bonus'):
                    self.coin_data['last_daily_bonus'] = {}
        except:
            self.foundCoinFile = False

        if self.foundCoinFile:
            self.coin_lock = threading.Lock()
            startCoinThread = False
            if False == self.whisperMode:
                if bot_type:
                    if bot_type != 'discord':
                        startCoinThread = True
                else:
                    startCoinThread = True
            if True == startCoinThread:
                self.coin_thread = threading.Thread(target=self.coin_loop)
                self.coin_thread.start()

        # Keys are names, values are lists of users that paid respects
        self.deaths_dict = {}

        # Keys are names, values are timestamps
        self.current_deaths = {}

        self.extra_command_cooldown = {}

        self.permissions = True
        self.permitted_users = []
        self.permitted_users.append(username.lower())
        for u in permitted_users:
            self.permitted_users.append(u.lower())

        self.moderators = []
        if None != moderators:
            for u in moderators:
                self.moderators.append(u.lower())

        self.pokemon_corrector = None
        with open('pokemon_dictionary.txt', 'r') as pokemon_dict:
            lines = pokemon_dict.readlines()
            lines = [line.replace('\n', '') for line in lines]
            self.pokemon_corrector = ListCorrector(lines)

        self.move_corrector = None
        with open('move_dictionary.txt', 'r') as move_dict:
            lines = move_dict.readlines()
            lines = [line.replace('\n', '') for line in lines]
            self.move_corrector = ListCorrector(lines)

        self.last_lines = []

        self.shoutouts_done = []

        self.pcce = {}
        self.pcce['coins'] = {}
        with open('PCCE.json', 'r') as config_file:
            self.pcce = json.load(config_file)

        self.battle_room = "" 

        self.ez = False
        self.ez_count = 0
        self.ez_start = time.time()

        # Username present in list means welcome message has been displayed
        self.welcome_message_displayed = []

        self.ratings = {}

    def get_current_run_data(self, key):
        result = None

        if None != self.config['current_run'] and None != self.config['run_data']:
            if None == self.config['run_data'].get(self.config['current_run']):
                self.config['run_data'][self.config['current_run']] = {}
            current_run_data = self.config['run_data'][self.config['current_run']]
            if None != current_run_data.get(key):
                result = current_run_data[key]

        return result

    def set_current_run_data(self, key, value):
        if None != self.config['current_run'] and None != self.config['run_data']:
            if None == self.config['run_data'].get(self.config['current_run']):
                self.config['run_data'][self.config['current_run']] = {}
            self.config['run_data'][self.config['current_run']][key] = value

    def is_setrun_command(self, command):
        setrun_commands = [
                "!howfar",
                "!lastrun",
                "!nickname",
                "!rules",
                ]
        if None != self.config['current_run'] and None != self.config['run_data']:
            return command in setrun_commands
        else:
            return False

    def coin_loop(self):
        while True:
            with self.coin_lock:
                try:
                    url = 'https://tmi.twitch.tv/group/user/' + self.username.lower() + '/chatters'
                    response = urllib.request.urlopen(url).read().decode('UTF-8')
                    user_data = json.loads(response)

                    user_list = []
                    for u in user_data['chatters']['moderators']:
                        user_list.append(u)
                    for u in user_data['chatters']['viewers']:
                        user_list.append(u)

                    for u in user_list:
                        more_coins = 1
                        if u in self.coin_data['coins'].keys():
                            self.coin_data['coins'][u] += more_coins
                        else:
                            self.coin_data['coins'][u] = more_coins
                            timestamp = time.mktime(datetime.datetime.now().timetuple())

                    self.update_coin_data()

                except Exception as e:
                    print("Coin loop exception: " + str(e))

            # Update coins every 10 minutes
            time.sleep(60 * 10)

    def pcwe_loop(self):
        print("Starting PCWE loop")
        path = os.path.join(os.sep, 'home', 'drfujibot', 'drfujibot', 'whispers')
        while True:
            try:
                for fn in os.listdir(path):
                    fullpath = os.path.join(path, fn)
                    if os.path.isfile(fullpath):
                        print("Processing file " + fullpath)
                        with open(fullpath, 'r') as f:
                            line = f.readlines()[0]
                            user = line.split(":")[0]
                            cmd = line.split(":", 1)[1]
                            self.processCommand(cmd, self.connection, user)
                        os.unlink(fullpath)
            except Exception as e:
                print("Exception: " + str(e))

            time.sleep(0.25)

    def timed_message_loop(self):
        message_list = self.config.get('timed_messages')
        if None != message_list:

            # Message -> last output timestamp
            last_output = {}

            # Add last output times now so they don't all display on startup
            now = datetime.datetime.now()
            now_timestamp = time.mktime(now.timetuple())
            for m in message_list:
                message = list(m.keys())[0]
                last_output[message] = now_timestamp

            while True:
                now = datetime.datetime.now()
                now_timestamp = time.mktime(now.timetuple())

                for m in message_list:

                    message = list(m.keys())[0]
                    interval = list(m.values())[0]

                    last_timestamp = last_output.get(message)
                    last_datetime = datetime.datetime.fromtimestamp(last_timestamp)
                    output_message = False

                    diff = now - last_datetime
                    if diff.seconds >= interval:
                        output_message = True

                    if True == output_message:
                        last_output[message] = now_timestamp
                        self.output_msg(self.connection, message, 'drfujibot')

                time.sleep(1)

    def do_shoutout_func(self, c, streamer, output_messages, source_user):
        output_messages_copy = output_messages[:]
        if len(output_messages_copy) == 0:
            output_messages_copy.append("Go check out @" + streamer + " at twitch.tv/" + streamer + " They make great content and if you enjoy us, you will enjoy them as well!")
        else:
            output_copy = []
            for m in output_messages_copy:
                output_copy.append(m.replace("STREAMER", streamer))
            output_messages_copy = output_copy
        for m in output_messages_copy:
            self.output_msg(c, m, source_user, 0)

    def do_shoutout(self, c, streamer, output_messages, delay_seconds, source_user):
        t = threading.Timer(delay_seconds, self.do_shoutout_func, [c, streamer, output_messages, source_user])
        t.start()

    def resolve_bet(self, c, line, source_user):
        if self.foundCoinFile:
            if len(line.split(" ")) >= 3:
                event_name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
                result = line.split(" ")[2].rstrip("\n").rstrip("\r").lower()

                if None != self.bet_config['events'].get(event_name):
                    if result in self.bet_config['events'][event_name]['outcomes'].keys():

                        payout = self.open_event_rewards[event_name]

                        # If it wasn't closed before resolve, close it now
                        if event_name in self.open_events.keys():
                            self.closed_events[event_name] = self.open_events[event_name]
                            del self.open_events[event_name]
                            del self.open_event_rewards[event_name]

                            self.config['open_events'] = self.open_events
                            self.config['open_event_rewards'] = self.open_event_rewards
                            self.config['closed_events'] = self.closed_events
                            self.update_config()

                        if event_name in self.closed_events.keys():
                            winners = []
                            all_users = []
                            pot = 0

                            log_msg = str(self.closed_events[event_name])
                            logname = self.username + ".log"
                            with open(logname, "a") as f:
                                f.write(log_msg + "\n")
                                f.flush()

                            # closed_events -> event_name: {user -> wager, user -> wager, ...}
                            for k in self.closed_events[event_name].keys():
                                pot += self.closed_events[event_name][k][1]
                                bet = self.closed_events[event_name][k][0]
                                event_mappings = self.bet_config['events'].get(event_name)
                                result_mappings = None
                                if None != event_mappings:
                                    result_mappings = event_mappings['mappings'].get(result)
                                if bet == result or ( None != result_mappings and bet in result_mappings ):
                                    winners.append(k)
                                all_users.append(k)

                            if len(winners) > 0:
                                if self.bet_config['events'].get(event_name):
                                    output = "'" + event_name + "' event winners get a payout! "
                            else:
                                output = "Unfortunately, there were no winners for the '" + event_name + "' event"

                            first_time_winners = []

                            if len(winners) == 0:
                                payout = 0
                            else:
                                # Pot is evenly split between winners
                                output += str(payout) + " coins are split between " + str(len(winners)) + " winners ("
                                payout = int(payout / len(winners))
                                output += str(payout) + " coins each)"

                            bet_info = self.bet_config['events'].get(event_name)

                            with self.coin_lock:
                                for w in winners:
                                    self.coin_data['coins'][w] += payout

                                    if None == self.config['winners'].get(w):
                                        self.coin_data['coins'][w] += 1000
                                        first_time_winners.append(w)
                                        self.config['winners'][w] = 1

                                self.update_coin_data()

                            self.output_msg(c, output, source_user)

                            if len(first_time_winners) > 0:
                                self.update_config()

                                output = "First-time bet winners awarded a 1000 coin bonus: "
                                output += ", ".join(first_time_winners)

                                self.output_msg(c, output, source_user)

                            del self.closed_events[event_name]
                            self.config['closed_events'] = self.closed_events

                            if None != self.config['current_run'] and None != self.config['run_data']:
                                if None != self.config['run_data'].get(self.config['current_run']):
                                    self.config['run_data'][self.config['current_run']]['closed_events'] = {}

                            self.update_config()
                        else:
                            self.output_msg(c, "Could not find active event '" + event_name + "'", source_user)
                    else:
                        self.output_msg(c, "Not a valid outcome: '" + result + "'", source_user)
                else:
                    self.output_msg(c, "Could not find active event '" + event_name + "'", source_user)
            else:
                self.output_msg(c, "Format: !resolve <event_name> <result>", source_user)
        else:
            self.output_msg(c, "Betting has not been configured", source_user)

    def new_bet(self, c, line, source_user):
        if self.foundCoinFile:
            if len(line.split(" ")) == 3:
                event_name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
                event_reward = 0
                try:
                    event_reward = int(line.split(" ")[2].rstrip("\n").rstrip("\r").lower())
                except:
                    self.output_msg(c, "Invalid reward", source_user)

                if event_reward > 0:
                    if len(self.open_events.keys()) == 0:
                        if event_name not in self.closed_events.keys():
                            self.open_events[event_name] = {}
                            self.open_event_rewards[event_name] = event_reward
                            output = "Betting has opened! Use '!bet <guess>' to play!"
                            self.output_msg(c, output, source_user)

                            self.config['open_events'] = self.open_events
                            self.config['open_event_rewards'] = self.open_event_rewards
                            self.update_config()
                        else:
                            self.output_msg(c, "Existing event '" + event_name + "' must be resolved", source_user)
                    else:
                        self.output_msg(c, "There is an open event already in progress: " + list(self.open_events.keys())[0], source_user)
            else:
                self.output_msg(c, "Format: !event <name> <reward>", source_user)
        else:
            self.output_msg(c, "Betting has not been configured", source_user)

    def get_game(self, username=None):
        if self.game and self.whisperMode == False:
            return self.game
        else:
            config = None
            game = None

            if self.bot_type and self.bot_type == 'discord':
                configname = 'whisper_discord.json'
            else:
                configname = 'whisper.json'
            with open(configname, 'r') as config_file:
                config = json.load(config_file)
            if config:
                if self.bot_type and self.bot_type == 'discord':
                    user = username
                else:
                    user = username.lower()
                game = config['games'].get(user)

            if None == game:
                game = "alpha-sapphire"
            return game

    def get_game_group(self, user):
        group = ''
        game = self.get_game(user).lower()

        if 'red' == game or 'blue' == game:
            group = 'red-blue'
        elif 'yellow' == game:
            group = 'yellow'
        elif 'gold' == game or 'silver' == game:
            group = 'gold-silver'
        elif 'crystal' == game:
            group = 'crystal'
        elif 'ruby' == game or 'sapphire' == game:
            group = 'ruby-sapphire'
        elif 'emerald' == game:
            group = 'emerald'
        elif 'leaf-green' == game or 'fire-red' == game:
            group = 'firered-leafgreen'
        elif 'diamond' == game or 'pearl' == game:
            group = 'diamond-pearl'
        elif 'platinum' == game:
            group = 'platinum'
        elif 'heart-gold' == game or 'soul-silver' == game:
            group = 'heartgold-soulsilver'
        elif 'black' == game or 'white' == game:
            group = 'black-white'
        elif 'black-2' == game or 'white-2' == game:
            group = 'black-2-white-2'
        elif 'x' == game or 'y' == game:
            group = 'x-y'
        elif 'omega-ruby' == game or 'alpha-sapphire' == game:
            group = 'omega-ruby-alpha-sapphire'
        elif 'sun' == game or 'moon' == game:
            group = 'sun-moon'

        return group

    def output_msg(self, c, output, user, sleeptime=2):
        MAX_MESSAGE_SIZE = 512
        chunk_size = MAX_MESSAGE_SIZE - 8
        if self.whisperMode:
            chunk_size = MAX_MESSAGE_SIZE - 8 - 5 - len(user)
        chunks = [ output[i:i+chunk_size] for i in range(0, len(output), chunk_size) ]
        j = 1
        for ch in chunks:
            if len(chunks) > 1:
                ch = "(" + str(j) + "/" + str(len(chunks)) + ") " + ch
            if self.whisperMode:
                c.privmsg("#" + user, "/w " + user + " " + ch)
            else:
                c.privmsg(self.channel, ch)
            print(ch)
            if True == self.whisperMode:
                logname = 'whisper.log'
            else:
                logname = self.username + ".log"
            with open(logname, "a") as f:
                f.write(ch + "\n")
                f.flush()
            j += 1
            time.sleep(sleeptime)

    def is_valid_command(self, cmd):
        cmd = cmd.lower()
        cmds = [
            "!commands",
            "!help",
            "!drfujihelp",
            "!uptime",
            "!bee",
            "!permissions",
            "!dab",
            "!sprite",
            "!shaq",
            "!fixit",
            "!lowkick",
            "!grassknot",
            "!raid",
            "!song",
            "!honestly",
            "!realtime",
            "!gender",
            "!pokemon",
            "!offen",
            "!defen",
            "!abilities",
            "!move",
            "!ability",
            "!nature",
            "!item",
            "!learnset",
            "!tmset",
            "!does",
            "!weak",
            "!resist",
            "!type",
            "!setgame",
            "!evolve",
            "!char",
            "!ev",
            "!faster",
            "!exp",
            "!remind",
            "!whisper",
            "!deaths",
            "!setdeaths",
            "!rip",
            "!ez",
            "!fallen",
            "!adduser",
            "!removeuser",
            "!addshoutout",
            "!removeshoutout",
            "!whatis",
            "!anagram",
            "!event",
            "!close",
            "!cancel",
            "!resolve",
            "!bet",
            "!daily",
            "!balance",
            "!leaderboard",
            "!coins",
            "!credit",
            "!riprun",
            "!resetcoins",
            "!addcom",
            "!editcom",
            "!delcom",
            "!so ",
            "!shoutout",
            "!notify",
            "!quote",
            "!latestquote",
            "!addquote",
            "!delquote",
            "!elo",
            "!smogon",
            "!chatbattle",
            "!forfeit",
            "!heavyslam",
            "!heatcrash",
            "!setrun",
            "!combo",
            "!attempt",
            "!swearjar",
            "!define",
            "!hiddenpower",
            "!rating",
        ]
        for c in cmds:
            if cmd.startswith(c):
                return True
        return False

    def is_extra_command(self, cmd):
        if True == self.config['extra_commands_on']:
            for c in self.config['extra_commands'].keys():
                if cmd.lower().startswith(c):
                    return True
            run_cmd = self.get_current_run_data(cmd)
            if None != run_cmd:
                return True
        return False

    def is_moderator_command(self, cmd):
        cmds = [
            "!rip",
            "!ez",
            "!event",
            "!close",
            "!cancel",
            "!resolve",
            "!riprun",
            "!resetcoins",
            "!setrun",
            "!addshoutout",
            "!removeshoutout",
            "!adduser",
            "!removeuser",
            "!addcom",
            "!editcom",
            "!delcom",
            "!setdeaths",
            "!remind",
            "!addquote",
            "!delquote",
            "!swearjar",
            "!define",
            "!credit",
            "!so ",
            "!shoutout",
        ]
        for c in cmds:
            if cmd.startswith(c):
                return True
        return False

    def log_cmd(self, cmd, sourcenick):
        if self.is_valid_command(cmd):
            if True == self.whisperMode:
                if self.bot_type and self.bot_type == "discord":
                    logname = 'whisper_discord.log'
                else:
                    logname = 'whisper.log'
            else:
                logname = self.username + ".log"
            with open(logname, "a") as f:
                f.write(sourcenick + " - " + cmd + "\n")
                f.flush()

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        g_c = c

        if True == self.whisperMode:
            c.cap('REQ', ':twitch.tv/commands')
            print("Ready for whisper mode")
        else:
            c.join(self.channel)
            print("Joined chat for %s" % (self.channel))
            c.cap('REQ', ":twitch.tv/tags")

    def on_privmsg(self, c, e):
        pass

    def on_whisper(self, c, e):
        line = e.arguments[0]
        self.log_cmd(line, e.source.nick)
        self.processCommand(line, c, e.source.nick)

        if e.source.nick.lower() not in self.previous_users:
            self.output_msg(c, "I see this may be your first time using DrFujiBot! Feel free to check out the documentation: http://goo.gl/JGG3LT", e.source.nick)

            self.previous_users[e.source.nick.lower()] = 1
            with open('whisper_users.json', 'w') as config_file:
                config_file.write(json.dumps(self.previous_users))

    def on_discord_msg(self, line, source_user, source_id):
        if source_user in self.permitted_users or self.permissions is False or is_global_command(line):
            self.log_cmd(line, source_user)
            c = None
            self.processCommand(line, c, source_user, source_id)

    def handle_raid_or_meme(self, c, line, source_user):
        if self.meme_mode:
            if "pokemonchallenges" == self.username.lower():
                if self.last_line == line and line != "F" and line != "f":
                    self.same_counter += 1
                else:
                    if self.same_counter >= 5 and self.last_line != "F" and self.last_line != "f":
                        self.output_msg(c, str(self.same_counter) + "x combo ( " + self.last_line + " )", "drfujibot")
                        if self.same_counter > self.config['highest_combo'][0]:
                            pair = []
                            pair.append(self.same_counter)
                            pair.append(self.last_line)
                            self.config['highest_combo'] = pair
                            self.update_config()
                    self.same_counter = 1
                    self.last_line = line

            line_dict = {}
            for e in self.last_lines:
                if e[1].lower() != 'drfujibot':
                    if line_dict.get(e[1]):
                        line_dict[e[1]] += 1
                    else:
                        line_dict[e[1]] = 1

            check_unique_users = False
            meme = ''
            for k in line_dict.keys():
                if line_dict[k] > 5:
                    check_unique_users = True
                    meme = k
                    break

            user_list = []
            if check_unique_users:
                for u in self.last_lines:
                    user_list.append(u)
            user_list = list(set(user_list))
            # if more than 3 unique users are spamming the same thing, participate in the raid/meme!
            if len(user_list) >= 3:
                if "f" != meme and "F" != meme and "pokemoF" != meme and "EZ" != meme:
                    #self.output_msg(c, meme, "drfujibot")
                    pass

    def handle_cheer(self, source_user, num_bits):
        print("Handling cheer for " + str(num_bits) + " bits from " + source_user)

    def handle_auto_shoutout(self, c, user):
        auto_shoutout_list = self.config.get('auto_shoutout')
        if None != auto_shoutout_list and user in auto_shoutout_list:
            now = datetime.datetime.now()
            if self.config['last_auto_shoutout'].get(user):
                last = datetime.datetime.fromtimestamp(self.config['last_auto_shoutout'][user])
            else:
                last = now - datetime.timedelta(hours=25)

            diff = now - last
            if diff.days >= 1:
                self.do_shoutout(c, user, self.config['shoutout_messages'], random.randint(5, 10), "drfujibot")
                timestamp = time.mktime(now.timetuple())
                self.config['last_auto_shoutout'][user] = timestamp
                self.update_config()

    def get_sub_tier(self, user_id):
        tier = 0
        #channel_id = self.config.get('channel_id')
        channel_id = 111971097
        if None != channel_id:
            CLIENT_ID = get_fuji_config_value('twitch_client_id')
            twitch_api_oauth_token = get_fuji_config_value('twitch_api_oauth_token')
            SUB_INFO_URL = 'https://api.twitch.tv/kraken/channels/' + str(channel_id) + '/subscriptions/' + str(user_id)
            print(SUB_INFO_URL)
            try:
                request = urllib.request.Request(SUB_INFO_URL)
                request.add_header('Accept', 'application/vnd.twitchtv.v5+json')
                request.add_header('Client-ID', CLIENT_ID)
                request.add_header('Authorization', 'OAuth ' + twitch_api_oauth_token)
                response = urllib.request.urlopen(request)
                data = json.loads(response.read().decode('utf-8'))
                sub_plan = data.get('sub_plan')
                if sub_plan:
                    tier = int(sub_plan) / 1000
                    print("Sub tier for user_id " + str(user_id) + " is " + str(tier))
            except urllib.error.HTTPError as http_error:
                msg = http_error.read()
                print(msg)
            except:
                print("Unexpected error: " + str(sys.exc_info()[0]))
        return tier

    def on_pubmsg(self, c, e):
        line = e.arguments[0]

        if "TwitchPlaysShowdown" in self.username and \
           ( "DrFujiBot won the battle" in line or \
             "DrFujiBot lost the battle" in line ) and \
             "drfujibot" in e.source.nick:
            print('match')
            self.output_msg(c, "!chatbattle", e.source.nick)
            return

        self.handle_respects(c, line, e.source.nick, discord=False)

        if len(self.last_lines) > 5:
            self.last_lines = self.last_lines[1:]
        self.last_lines.append((e.source.nick, line))
        self.handle_raid_or_meme(c, line, e.source.nick)

        #self.handle_auto_shoutout(c, e.source.nick)

        is_mod = False
        is_sub = False
        user_id = 0

        for tag in e.tags:
            if tag['key'] == 'user-id':
                user_id = int(tag['value'])

        for tag in e.tags:
            if tag['key'] == 'bits':
                self.handle_cheer(e.source.nick, int(tag['value']))
                break
            elif tag['key'] == 'badges':
                if tag['value']:
                    badges = tag['value'].split(',')
                    for b in badges:
                        if b.split('/')[0] == 'moderator':
                            is_mod = True
                        elif b.split('/')[0] == 'broadcaster':
                            is_mod = True
                            if None == self.config.get('channel_id'):
                                self.config['channel_id'] = str(user_id)
                                self.update_config()
                        elif b.split('/')[0] == 'subscriber':
                            is_sub = True

        if line.startswith("!"):
            pieces = line.split(" ")
            line = pieces[0].lower()
            if len(pieces) > 1:
                line += " " + " ".join(pieces[1:])
            print(line)

        if self.is_valid_command(line) or self.is_extra_command(line):
            if self.is_moderator_command(line):
                if e.source.nick.lower() in self.moderators or \
                   'drfujibot' == e.source.nick.lower() or \
                   is_mod:
                    self.log_cmd(line, e.source.nick)
                    self.processCommand(line, c, e.source.nick)
            else:
                if e.source.nick.lower() in self.permitted_users or \
                   (is_sub and (self.username.lower() == "pokemonchallenges" or self.username.lower() == "moshjarcus")) or \
                   self.permissions is False or \
                   is_global_command(line) or \
                   self.is_extra_command(line):
                    self.log_cmd(line, e.source.nick)
                    self.processCommand(line, c, e.source.nick)
                else:
                    if not ( line.startswith("!commands") or line.startswith("!so ") or line.startswith("!shoutout ") or line.startswith("!help") ):
                        if self.username.lower() == "pokemonchallenges":
                            self.output_msg(c, "Sorry, that command is only for mods or subs, but you can whisper me!", e.source.nick)
                        else:
                            self.output_msg(c, "Sorry, that command is only for mods, but you can whisper me!", e.source.nick)

        # Handle any subscriber-specific actions
        #is_sub = True
        #if is_sub:
        #    if e.source.nick not in self.welcome_message_displayed:
        #        tier = self.get_sub_tier(user_id)
        #        if tier >= 2:
        #            # 'welcome_messages' is a dict of username: message
        #            welcome_message = self.config['welcome_messages'][e.source.nick]
        #            self.output_msg(c, welcome_message, e.source.nick)
        #            self.welcome_message_displayed.append(e.source.nick)

        if "rubyquartzvisor" in e.source.nick.lower():
            now = datetime.datetime.now()
            now_timestamp = time.mktime(now.timetuple())
            last_ruby_sighting = self.config.get('last_ruby_sighting')
            last_ruby_datetime = datetime.datetime.fromtimestamp(last_ruby_sighting)

            diff = now - last_ruby_datetime
            if diff.seconds >= 24 * 60 * 60:
                self.output_msg(c, "OwO is that wuby? pokemoWo", e.source.nick)

            self.config['last_ruby_sighting'] = now_timestamp
            self.update_config()

    def handle_respects(self, c, line, source_user, discord):
        if self.ez:
            now = time.time()
            if now - self.ez_start >= 20:
                num_respects = self.ez_count
                self.output_msg(c, str(num_respects) + " EZ 's for PC", source_user)
                self.ez = False
            else:
                if line.startswith("EZ ") or line == "EZ" or line.startswith("pokemoEZ ") or line == "pokemoEZ":
                    self.ez_count += 1

        if len(self.current_deaths.keys()) > 0:
            now = time.time()

            names_to_delete = []

            # One F counts for all respects in progress
            for name in self.current_deaths.keys():
                if now - self.current_deaths[name] >= 20:
                    num_respects = len(self.deaths_dict[name])
                    self.fallen[name] = num_respects
                    self.fallen_timestamps[name] = now

                    self.output_msg(c, str(num_respects) + " respects for " + name, source_user)

                    self.config['fallen'] = self.fallen
                    self.config['fallen_timestamps'] = self.fallen_timestamps
                    self.update_config()

                    names_to_delete.append(name)
                else:
                    if line.upper() == "F" or line == "pokemoF":
                        if source_user not in self.deaths_dict[name]:
                            self.deaths_dict[name].append(source_user)

            for n in names_to_delete:
                del self.current_deaths[n]

    def update_config(self):
        configname = ""
        if self.bot_type and self.bot_type == 'discord':
            configname = self.username + '_discord.json'
        else:
            configname = self.username + '.json'
        with open(configname, 'w') as config_file:
            config_file.write(json.dumps(self.config))

    def update_pcce(self):
        with open('PCCE.json', 'w') as config_file:
            config_file.write(json.dumps(self.pcce))

    def update_coin_data(self):
        with open(self.username + '_coins.json', 'w') as config_file:
            config_file.write(json.dumps(self.coin_data))
        if "pokemonchallenges" == self.username.lower() or "pokemonrealtime" == self.username.lower():
            self.pcce['coins'] = self.coin_data['coins']
            self.update_pcce()

    def processCommand(self, line, c, source_user, source_id=None, prefix=None):

        if " " in line:
            line_start = ""
            for char in line:
                if " " != char:
                    line_start += char.lower()
                else:
                    break
            line = line_start + " " + line.split(" ", 1)[1]
        else:
            line = line.lower()
        print(line)

        if len(self.config['command_whitelist']) > 0:
            command = line
            if ' ' in command:
                command = command.split(' ')[0]

            if command not in self.config['command_whitelist']:
                return

        if line.startswith("!permissions") and len(line) >= len("!permissions ") + 2:
            toggle = line.split(" ")[1].rstrip("\n").rstrip("\r")
            if "on" in toggle:
                self.permissions = True
                self.output_msg(c, "Only permitted users can talk to me!", source_user)
            elif "off" in toggle:
                self.permissions = False
                self.output_msg(c, "Everyone can talk to me!", source_user)
            pass

        elif line.startswith("!commands") or line.startswith("!help") or line.startswith("!drfujihelp"):
            should_output = False
            if line.startswith("!commands"):
                if True == self.config['extra_commands_on']:
                    should_output = True
            else:
                should_output = True

            if should_output:
                output = "See the documentation for commands and help: http://goo.gl/JGG3LT"
                self.output_msg(c, output, source_user)

        elif line.startswith("!sprite "):
            if len(line.split(" ")) >= 2:
                pokemon = line.split(" ")[1].rstrip("\n").rstrip("\r")
                self.output_msg(c, pokemon.capitalize() + " sprite: http://everoddish.com/RedbYNv.png", source_user)
            else:
                self.output_msg(c, "Format: !sprite <pokemon>", source_user)
        elif line == "!dab":
                self.output_msg(c, "/timeout " + source_user + " 1", source_user, 0)
                self.output_msg(c, "No.", source_user, 0)
        elif line == "!bee":
            out = ""
            while len(out) < 12:
                out += self.bee[ self.bee_index ]
                self.bee_index += 1
                if len(out) <= 11:
                    out += " "
            while len(out) > 12:
                out = " ".join(out.split(" ")[:-1])
                self.bee_index -= 1
            self.output_msg(c, out, source_user)

            self.config['bee_index'] = self.bee_index
            self.update_config()

        elif line == "!shaq":
            out = ""
            while len(out) < 12:
                out += self.shaq[ self.shaq_index ]
                self.shaq_index += 1
                if self.shaq_index >= len(self.shaq):
                    self.shaq_index = 0
                if len(out) <= 11:
                    out += " "
            while len(out) > 12:
                out = " ".join(out.split(" ")[:-1])
                self.shaq_index -= 1
                if self.shaq_index <= 0:
                    self.shaq_index = len(self.shaq) - 1
            self.output_msg(c, out, source_user)

            self.config['shaq_index'] = self.shaq_index
            self.update_config()

        elif line.startswith("!honestly"):
            if self.username.lower() == "pokemonchallenges":
                if len(line.split(" ")) >= 3:
                    victim = line.split(" ")[1].rstrip("\n").rstrip("\r")
                    killer = line.split(" ")[2].rstrip("\n").rstrip("\r")
                else:
                    victim = "Medicham"
                    killer = "Tangrowth"

                output = "Honestly PC fuck you. That "
                output += victim
                output += " was the only mon I was ever attached to in this run and it did so much in the E4 and then you go and act all confident with it and keep it in on a "
                output += killer

                self.output_msg(c, output, source_user)

        elif line.startswith("!realtime"):
            if self.username.lower() == "pokemonchallenges":
                if len(line.split(" ")) >= 3:
                    subject = line.split(" ")[1].rstrip("\n").rstrip("\r")
                    name = line.split(" ")[2].rstrip("\n").rstrip("\r")

                    output = "When I met Realtime at Disneyland, he kept talking about "
                    output += subject
                    output += ". I started to laugh, but then he got really mad. I apologized, and then he called me a "
                    output += name

                    self.output_msg(c, output, source_user)

        elif line.startswith("!whisper"):
            output = "Only the following users have DrFujiBot permission: "
            output += ", ".join(self.permitted_users)
            output += " - If you want to use DrFujiBot yourself, send it a whisper!"
            self.output_msg(c, output, source_user)

        elif line.startswith("!pokemon"):
            if len(line.split(" ")) >= 2:
                name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
                name = fix_pokemon_name(name)
                try:
                    p = drfujibot_pykemon.api.get(pokemon=name,url=self.config['pokeapi_url'])
                    type1 = p.types[0].capitalize()
                    type2 = None
                    if len(p.types) > 1:
                        type2 = p.types[1].capitalize()
                    output = name.capitalize() + ": [" + type1
                    if type2:
                        output += ", " + type2 + "] "
                    else:
                        output += "] "

                    output += "HP(" + str(p.hp) + ") "
                    output += "Attack(" + str(p.attack) + ") "
                    output += "Defense(" + str(p.defense) + ") "
                    output += "Sp. Atk(" + str(p.sp_atk) + ") "
                    output += "Sp. Def(" + str(p.sp_def) + ") "
                    output += "Speed(" + str(p.speed) + ") "

                    output += "Abilities: "
                    for a in p.abilities:
                        output += a.replace('-', ' ').title()
                        output += ", "
                    current_gen = genNameToNum(self.get_game_group(source_user))
                    if len(p.hidden_ability) == 1 and current_gen >= 5:
                        output += p.hidden_ability[0].replace('-', ' ').title()
                        output += ' (HA)'
                    else:
                        output = output.rsplit(", ", 1 )[0]
                    self.output_msg(c, output, source_user)
                except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                    #output = "Pokemon '" + name + "' not found."
                    #suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=3)
                    #if len(suggestions) > 0:    
                    #    output += " Did you mean: "
                    #    output += ", ".join(suggestions)
                    #self.output_msg(c, output, source_user)
                    suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=3)
                    if len(suggestions) > 0:    
                        self.processCommand("!pokemon " + suggestions[0], c, source_user)
                    else:
                        self.output_msg(c, "Pokemon '" + name + "' not found", source_user)
                except:
                    print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!offen"):
            name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
            name = fix_pokemon_name(name)
            try:
                p = drfujibot_pykemon.api.get(pokemon=name,url=self.config['pokeapi_url'])
                output = name.capitalize() + ": "

                output += "Attack(" + str(p.attack) + ") "
                output += "Sp. Atk(" + str(p.sp_atk) + ") "
                output += "Speed(" + str(p.speed) + ") "

                self.output_msg(c, output, source_user)
            except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                #output = "Pokemon '" + name + "' not found."
                #suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=3)
                #if len(suggestions) > 0:    
                #    output += " Did you mean: "
                #    output += ", ".join(suggestions)
                #self.output_msg(c, output, source_user)
                suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=3)
                if len(suggestions) > 0:    
                    self.processCommand("!offen " + suggestions[0], c, source_user)
                else:
                    self.output_msg(c, "Pokemon '" + name + "' not found", source_user)
            except:
                print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!defen"):
            name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
            name = fix_pokemon_name(name)
            try:
                p = drfujibot_pykemon.api.get(pokemon=name,url=self.config['pokeapi_url'])
                output = name.capitalize() + ": "

                output += "HP(" + str(p.hp) + ") "
                output += "Defense(" + str(p.defense) + ") "
                output += "Sp. Def(" + str(p.sp_def) + ") "

                self.output_msg(c, output, source_user)
            except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                #output = "Pokemon '" + name + "' not found."
                #suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=3)
                #if len(suggestions) > 0:    
                #    output += " Did you mean: "
                #    output += ", ".join(suggestions)
                #self.output_msg(c, output, source_user)
                suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=3)
                if len(suggestions) > 0:    
                    self.processCommand("!defen " + suggestions[0], c, source_user)
                else:
                    self.output_msg(c, "Pokemon '" + name + "' not found", source_user)
            except:
                print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!abilities"):
            name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
            name = fix_pokemon_name(name)
            try:
                p = drfujibot_pykemon.api.get(pokemon=name,url=self.config['pokeapi_url'])
                output = name.capitalize() + ": "

                for a in p.abilities:
                    output += a.replace('-', ' ').title()
                    output += ", "
                current_gen = genNameToNum(self.get_game_group(source_user))
                if len(p.hidden_ability) == 1 and current_gen >= 5:
                    output += p.hidden_ability[0].replace('-', ' ').title()
                    output += ' (HA)'
                else:
                    output = output.rsplit(", ", 1 )[0]
                self.output_msg(c, output, source_user)
            except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                #output = "Pokemon '" + name + "' not found."
                #suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=3)
                #if len(suggestions) > 0:    
                #    output += " Did you mean: "
                #    output += ", ".join(suggestions)
                #self.output_msg(c, output, source_user)
                suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=3)
                if len(suggestions) > 0:    
                    self.processCommand("!abilities " + suggestions[0], c, source_user)
                else:
                    self.output_msg(c, "Pokemon '" + name + "' not found", source_user)
            except:
                print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!move"):
            name = line.split(" ", 1)[1].rstrip("\n").rstrip("\r").lower()
            try:
                name = name.replace(" ", "-")
                name = name.replace(",", "-")
                name = fix_z_move(name)
                m = drfujibot_pykemon.api.get(move=name,url=self.config['pokeapi_url'])

                # Go through all the past values, and apply any ones that are relevant.
                for pv in m.past_values:
                    if genNameToNum(self.get_game_group(source_user)) <= genNameToNum(pv.get('version_group').get('name')):
                        if pv.get('pp'):
                            m.pp = pv.get('pp')
                        elif pv.get('power'):
                            m.power = pv.get('power')
                        elif pv.get('accuracy'):
                            m.accuracy = pv.get('accuracy')
                        elif pv.get('type'):
                            m.type = pv.get('type')
                        elif pv.get('effect_chance'):
                            m.ailment_chance = pv.get('effect_chance')

                if prefix:
                    output = prefix
                else:
                    output = ""

                output += name.replace("-", " ").title() + ": "
                if type(m.type) is dict:
                    output += "[" + m.type['name'].capitalize() + "] "
                else:
                    output += "[" + m.type.capitalize() + "] "
                output += "BasePower(" + str(m.power) + ") Class(" + m.damage_class.capitalize() + ") "
                output += "Accuracy(" + str(m.accuracy) + ") PP(" + str(m.pp) + ") "

                if m.flinch_chance > 0:
                    output += "Flinch(" + str(m.flinch_chance) + "%) "

                if len(m.ailment) > 0 and m.ailment_chance > 0:
                    output += m.ailment.capitalize() + "(" + str(m.ailment_chance) + "%) "

                if m.crit_rate == 1:
                    output += "Crit(+) "

                if m.priority == 1:
                    output += "Priority(+) "

                for s in m.stat_changes:
                    stat = s[0].capitalize()
                    stat = stat.replace("Special-attack", "SpAtk")
                    stat = stat.replace("Special-defense", "SpDef")
                    output += "Stat(" + stat + " "
                    if s[1] < 0:
                        output += str(s[1])
                    else:
                        output += "+" + str(s[1])
                    if m.stat_chance > 0:
                        output += " " + str(m.stat_chance) + "%"
                    output += ") "

                m.description = m.description.replace("$effect_chance", str(m.stat_chance))
                output += m.description

                self.output_msg(c, output, source_user)
            except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                #output = "Move '" + name + "' not found."
                #suggestions = self.move_corrector.suggest(name.replace('-', ' ').title(), limit=3)
                #if len(suggestions) > 0:    
                #    output += " Did you mean: "
                #    output += ", ".join(suggestions)
                #self.output_msg(c, output, source_user)
                suggestions = self.move_corrector.suggest(name.replace('-', ' ').title(), limit=1)
                if len(suggestions) > 0:    
                    self.processCommand("!move " + suggestions[0], c, source_user)
                else:
                    self.output_msg(c, "Move '" + name + "' not found", source_user)
            except:
                print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!nature"):
            name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
            try:
                m = drfujibot_pykemon.api.get(nature=name)
                output = name.capitalize() + ": "
                m.inc_stat = m.inc_stat.capitalize()
                m.dec_stat = m.dec_stat.capitalize()

                if "None" in m.inc_stat:
                    output += "Neutral"
                else:
                    m.inc_stat = m.inc_stat.replace("Special-attack", "SpAtk")
                    m.inc_stat = m.inc_stat.replace("Special-defense", "SpDef")
                    output += "+" + m.inc_stat + " "

                    m.dec_stat = m.dec_stat.replace("Special-attack", "SpAtk")
                    m.dec_stat = m.dec_stat.replace("Special-defense", "SpDef")
                    output += "-" + m.dec_stat + " "

                self.output_msg(c, output, source_user)
            except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                self.output_msg(c, "Nature '" + name + "' not found.", source_user)
            except:
                print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!ability"):
            name = line.split(" ", 1)[1].rstrip("\n").rstrip("\r").lower()
            try:
                name = name.replace(" ", "-")
                a = drfujibot_pykemon.api.get(ability=name,url=self.config['pokeapi_url'])

                current_gen = genNameToNum(self.get_game_group(source_user))
                if current_gen >= a.gen_num:
                    if prefix:
                        output = prefix
                    else:
                        output = ""
                    output += name.replace('-', ' ').title() + ": "
                    output += a.effect
                else:
                    output = "Ability '" + name.title() + "' is not present in Gen " + str(current_gen)

                self.output_msg(c, output, source_user)
            except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                self.output_msg(c, "Ability '" + name + "' not found.", source_user)
            except Exception as e:
                print("Unexpected error: " + str(e))

        # !does <pokemon> learn <move>
        elif line.startswith("!does"):
            regex = re.compile("!does (.*) learn (.*)")
            result = regex.match(line)

            poke = None
            move = None

            if result:
                poke = result.group(1).lower()
                poke = fix_pokemon_name(poke)
                move = result.group(2).lower()
                move = move.replace(" ", "-")
            else:
                self.output_msg(c, "Invalid format. Usage: !does <pokemon> learn <move>", source_user)

            if poke and move:
                p = None
                try:
                    p = drfujibot_pykemon.api.get(pokemon=poke,url=self.config['pokeapi_url'])

                    try:
                        # Just for move name validation:
                        m = drfujibot_pykemon.api.get(move=move,url=self.config['pokeapi_url'])
                        info_list = [move_info for move_info in p.moves if move in move_info.get('move').get('name')]
                        info_list_by_gen = []
                        for i in info_list:
                            for version in i.get('version_group_details'):
                                gen_name = version.get('version_group').get('name')
                                if self.get_game_group(source_user) == gen_name:
                                    info_list_by_gen.append(version)
                        if len(info_list_by_gen) > 0:
                            output = poke.capitalize() + " learns " + move.replace("-", " ").title() + " "

                            output_chunks = []
                            for info in info_list_by_gen:
                                learn = info.get('move_learn_method').get('name')
                                if "machine" in learn:
                                    learn = "TM/HM"

                                if "level-up" in learn:
                                    output_chunks.append("by level up at level " + str(info.get('level_learned_at')))
                                else:
                                    output_chunks.append("by " + learn)

                            output_chunks_set = list(set(output_chunks))
                            if len(output_chunks_set) > 1:
                                output += ", ".join(output_chunks_set[:-1])
                                output += " and "
                                output += output_chunks_set[-1]
                            else:
                                output += output_chunks_set[0]
                        else:
                            output = poke.capitalize() + " does not learn " + move.replace("-", " ").title()

                        self.output_msg(c, output, source_user)
                    except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                        #self.output_msg(c, "Move '" + move + "' not found.", source_user)
                        #suggestions = self.move_corrector.suggest(move.replace('-', ' ').title(), limit=3)
                        #if len(suggestions) > 0:    
                        #    output += " Did you mean: "
                        #    output += ", ".join(suggestions)
                        #self.output_msg(c, output, source_user)
                        suggestions = self.move_corrector.suggest(move.replace('-', ' ').title(), limit=1)
                        if len(suggestions) > 0:    
                            self.processCommand("!does " + poke + " learn " + suggestions[0], c, source_user)
                        else:
                            self.output_msg(c, "Move '" + move + "' not found", source_user)
                    except:
                        print("Unexpected error: " + str(sys.exc_info()[0]))
                except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                    #output = "Pokemon '" + poke + "' not found."
                    #suggestions = self.pokemon_corrector.suggest(poke.capitalize(), limit=3)
                    #if len(suggestions) > 0:    
                    #    output += " Did you mean: "
                    #    output += ", ".join(suggestions)
                    #self.output_msg(c, output, source_user)
                    suggestions = self.pokemon_corrector.suggest(poke.capitalize(), limit=1)
                    if len(suggestions) > 0:    
                        self.processCommand("!does " + suggestions[0] + " learn " + move, c, source_user)
                    else:
                        self.output_msg(c, "Pokemon '" + poke + "' not found", source_user)
                except:
                    print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!item"):
            name = line.split(" ", 1)[1].rstrip("\n").rstrip("\r").lower()
            try:
                name = name.replace(" ", "-")
                i = drfujibot_pykemon.api.get(item=name,url=self.config['pokeapi_url'])

                output = name.replace('-', ' ').title() + ": " + i.description + " "

                held_dict = {}
                for detail in i.held_by_pokemon:
                    for ver in detail.get('version_details'):
                        if self.get_game(source_user) == ver.get('version').get('name'):
                            rarity = str(ver.get('rarity'))
                            poke = detail.get('pokemon').get('name').capitalize()
                            if held_dict.get(rarity):
                                held_dict[rarity].append(poke)
                            else:
                                held_dict[rarity] = [poke]

                for k in held_dict.keys():
                    output += "There is a " + k + "% chance of the following wild Pokemon holding this item: "
                    output += ", ".join(held_dict[k])
                    output += " "

                if len(held_dict.keys()) > 0:
                    output += ". "

                if i.value > 0:
                    output += "This item can be sold for $" + str(i.value) + " "

                self.output_msg(c, output, source_user)
            except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                self.output_msg(c, "Item '" + name + "' not found.", source_user)
            except:
                print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!weak"):
            type1 = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
            type2 = None
            if len(line.split(" ")) > 2:
                type2 = line.split(" ")[2]
                type2 = type2.rstrip("\n").rstrip("\r").lower()

            weaknesses = get_weaknesses(type1, type2)

            output = type1.capitalize()
            if type2:
                output += "/" + type2.capitalize()
            output += " is weak to: " 
            weak_strings = []
            for w in weaknesses:
                string = w.capitalize()
                if weaknesses.count(w) == 1:
                    string += " (2x)"
                elif weaknesses.count(w) == 2:
                    string += " (4x)"
                weak_strings.append(string)
            weak_strings = list(set(weak_strings))
            output += ", ".join(weak_strings)

            self.output_msg(c, output, source_user)

        elif line.startswith("!resist"):
            type1 = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
            type2 = None
            if len(line.split(" ")) > 2:
                type2 = line.split(" ")[2]
                type2 = type2.rstrip("\n").rstrip("\r").lower()

            resistances = get_resistances(type1, type2)

            # Print what's left
            output = type1.capitalize()
            if type2:
                output += "/" + type2.capitalize()
            output += " is resistant to: " 
            resist_strings = []
            for r in resistances:
                string = r.capitalize()
                if resistances.count(r) == 1:
                    string += " (0.5x)"
                elif resistances.count(r) == 2:
                    string += " (0.25x)"
                resist_strings.append(string)
            resist_strings = list(set(resist_strings))
            output += ", ".join(resist_strings)

            self.output_msg(c, output, source_user)

        elif line.startswith("!type"):
            regex = re.compile("!type (.*) against ([a-z]*) *([a-z]*)")
            result = regex.match(line)

            if result:
                attacking_type = result.group(1).lower()
                defending_type1 = result.group(2).lower()
                defending_type2 = result.group(3)
                if defending_type2:
                    defending_type2 = defending_type2.lower()

                try:
                    t1 = drfujibot_pykemon.api.get(type=defending_type1)
                    t2 = None
                    if defending_type2:
                        t2 = drfujibot_pykemon.api.get(type=defending_type2)

                    weaknesses = [w.get('name') for w in t1.double_damage_from]
                    if t2:
                        for w in t2.double_damage_from:
                            weaknesses.append(w.get('name'))

                    resistances = [r.get('name') for r in t1.half_damage_from]
                    if t2:
                        for r in t2.half_damage_from:
                            resistances.append(r.get('name'))

                    no_dmg_types = [t.get('name') for t in t1.no_damage_from]
                    if t2:
                        for t in t2.no_damage_from:
                            no_dmg_types.append(t.get('name'))

                    # Take out no-damage types outright.
                    weaknesses = [w for w in weaknesses if w not in no_dmg_types]
                    resistances = [r for r in resistances if r not in no_dmg_types]

                    weaknesses_copy = weaknesses[:]

                    # Reduce weakness instance by one for each resistance.
                    for r in resistances:
                        if r in weaknesses:
                            weaknesses.remove(r)

                    # Reduce resistance instance by one for each weakness.
                    for w in weaknesses_copy:
                        if w in resistances:
                            resistances.remove(w)

                    # Print the result
                    output = attacking_type.capitalize()

                    if attacking_type in no_dmg_types:
                        output += " does no damage"
                    elif attacking_type in weaknesses:
                        output += " is super effective ("
                        if weaknesses.count(attacking_type) == 1:
                            output += "2x)"
                        elif weaknesses.count(attacking_type) == 2:
                            output += "4x)"
                    elif attacking_type in resistances:
                        output += " is not very effective ("
                        if resistances.count(attacking_type) == 1:
                            output += "0.5x)"
                        elif resistances.count(attacking_type) == 2:
                            output += "0.25x)"
                    else:
                        output += " does normal damage"
                        
                    output += " against " + defending_type1.capitalize()
                    if defending_type2:
                        output += "/" + defending_type2.capitalize()

                    self.output_msg(c, output, source_user)
                except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                    self.output_msg(c, "Type(s) not found.", source_user)
                except:
                    print("Unexpected error: " + str(sys.exc_info()[0]))
            else:
                self.output_msg(c, "Invalid format. Usage: !type <attacking_type> against <defending_type1> <defending_type2>", source_user)

        elif line.startswith("!learnset"):
            regex = re.compile("!learnset (.*)")
            result = regex.match(line)

            poke = None
            group = None

            if result:
                poke = result.group(1).lower()
                poke = fix_pokemon_name(poke)
                group = self.get_game_group(source_user)
            else:
                self.output_msg(c, "Invalid format. Usage: !learnset <pokemon>", source_user)

            if poke and group:
                output = poke.capitalize() + " "
                try:
                    p = drfujibot_pykemon.api.get(pokemon=poke,url=self.config['pokeapi_url'])

                    entries = []
                    for move in p.moves:
                        for g in move.get('version_group_details'):
                            gen_name = g.get('version_group').get('name')
                            if group:
                                if group == gen_name:
                                    level = g.get('level_learned_at')
                                    if level > 0:
                                        entries.append("| " + str(level) + " " + move.get('move').get('name').replace("-", " ").title() + " ")

                    entries = list(set(entries))
                    entries = sorted(entries, key=lambda x: int(x.split(" ")[1]))

                    for en in entries:
                        output += en

                    self.output_msg(c, output, source_user)
                except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                    #output = "Pokemon '" + poke + "' not found."
                    #suggestions = self.pokemon_corrector.suggest(poke.capitalize(), limit=3)
                    #if len(suggestions) > 0:    
                    #    output += " Did you mean: "
                    #    output += ", ".join(suggestions)
                    #self.output_msg(c, output, source_user)
                    suggestions = self.pokemon_corrector.suggest(poke.capitalize(), limit=1)
                    if len(suggestions) > 0:    
                        self.processCommand("!learnset " + suggestions[0], c, source_user)
                    else:
                        self.output_msg(c, "Pokemon '" + poke + "' not found", source_user)
                except:
                    print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!tmset"):
            regex = re.compile("!tmset (.*)")
            result = regex.match(line)

            poke = None
            group = None

            if result:
                poke = result.group(1).lower()
                poke = fix_pokemon_name(poke)
                group = self.get_game_group(source_user)
            else:
                self.output_msg(c, "Invalid format. Usage: !tmset <pokemon>", source_user)

            if poke.lower() == "mew":
                self.output_msg(c, "Mew learns all the TMs. Stop trying to spam.", source_user)
            else:
                if poke and group:
                    output = poke.capitalize() + ": "
                    try:
                        p = drfujibot_pykemon.api.get(pokemon=poke,url=self.config['pokeapi_url'])

                        entries = []
                        for move in p.moves:
                            for g in move.get('version_group_details'):
                                gen_name = g.get('version_group').get('name')
                                if group:
                                    if group == gen_name:
                                        if 'machine' in g.get('move_learn_method').get('name'):
                                            entries.append(move.get('move').get('name').replace("-", " ").title())

                        entries = list(set(entries))

                        output += ", ".join(map(str, entries))

                        self.output_msg(c, output, source_user)
                    except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                        #output = "Pokemon '" + poke + "' not found."
                        #suggestions = self.pokemon_corrector.suggest(poke.capitalize(), limit=3)
                        #if len(suggestions) > 0:    
                        #    output += " Did you mean: "
                        #    output += ", ".join(suggestions)
                        #self.output_msg(c, output, source_user)
                        suggestions = self.pokemon_corrector.suggest(poke.capitalize(), limit=1)
                        if len(suggestions) > 0:    
                            self.processCommand("!tmset " + suggestions[0], c, source_user)
                        else:
                            self.output_msg(c, "Pokemon '" + poke + "' not found", source_user)
                    except:
                        print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!setgame"):
            regex = re.compile("!setgame (.*)")
            result = regex.match(line)

            if result:
                game = result.group(1)

                valid_games = [
                        'red',
                        'blue',
                        'yellow',
                        'gold',
                        'silver',
                        'crystal',
                        'ruby',
                        'sapphire',
                        'emerald',
                        'fire-red',
                        'leaf-green',
                        'diamond',
                        'pearl',
                        'platinum',
                        'heart-gold',
                        'soul-silver',
                        'black',
                        'white',
                        'black-2',
                        'white-2',
                        'x',
                        'y',
                        'omega-ruby',
                        'alpha-sapphire',
                        'rising-ruby',
                        'sun',
                        'moon'
                        ]

                game = game.replace(' ', '-').lower()
                if "ultra-sun" == game:
                    game = "sun"
                if "ultra-moon" == game:
                    game = "moon"

                original_game_str = game

                isRising = False
                isGen7 = False
                if game == 'firered':
                    game = 'fire-red'
                elif game == 'leafgreen':
                    game = 'leaf-green'
                elif game == 'heartgold':
                    game = 'heart-gold'
                elif game == 'soulsilver':
                    game = 'soul-silver'
                elif game == 'omegaruby' or game == 'rising-ruby' or game == 'risingruby':
                    game = 'omega-ruby'
                    isRising = True
                elif game == 'alphasapphire' or game == 'sinking-sapphire' or game == 'sinkingsapphire':
                    game = 'alpha-sapphire'
                    isRising = True
                elif game == 'sun' or game == 'moon':
                    isGen7 = True

                if game in valid_games:
                    config = None
                    if self.whisperMode == True:
                        if self.bot_type and self.bot_type == 'discord':
                            configname = 'whisper_discord.json'
                        else:
                            configname = 'whisper.json'
                        with open(configname, 'r') as config_file:
                            config = json.load(config_file)
                        if config:
                            config['games'][source_user] = game
                            if isRising:
                                config['pokeapi_url'] = 'http://localhost:8001/api/v2'
                                self.config['pokeapi_url'] = 'http://localhost:8001/api/v2'
                            else:
                                config['pokeapi_url'] = ''
                                self.config['pokeapi_url'] = ''
                            with open(configname, 'w') as config_file:
                                config_file.write(json.dumps(config))
                    else:
                        self.config['games'][self.username] = game
                        if isRising:
                            self.config['pokeapi_url'] = 'http://localhost:8001/api/v2'
                        else:
                            self.config['pokeapi_url'] = ''

                        if None != self.config.get('current_run') and len(self.config.get('current_run')) > 0 and None != self.config.get('run_data'):
                            self.config['run_data'][self.config['current_run']]['game'] = game

                        self.update_config()
                        self.game = game

                    output = "Set game to Pokemon " + original_game_str.replace('-', ' ').title() + " SeemsGood"

                    self.output_msg(c, output, source_user)
                else:
                    self.output_msg(c, "Invalid game. Usage: !setgame <game name>", source_user)
            else:
                self.output_msg(c, "Invalid format. Usage: !setgame <game name>", source_user)

        elif line.startswith("!evol"):
            name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
            name = fix_pokemon_name(name)
            try:
                species = drfujibot_pykemon.api.get(species=name,url=self.config['pokeapi_url'])
                chain_id = species.evolution_chain_url.split("/")[-2]
                ch = drfujibot_pykemon.api.get(evo_chain=chain_id,url=self.config['pokeapi_url'])

                this_chain = find_chain(ch.chain, name)
                output = ""

                if len(this_chain.get('evolves_to')) == 0:
                    found_mega = False
                    for var in species.varieties:
                        if var.get('pokemon').get('name').endswith('-mega'):
                            output += name.capitalize() + " mega evolves to Mega " + name.capitalize()
                            found_mega = True
                            break
                    if not found_mega:
                        output += name.capitalize() + " does not evolve any further."
                else:
                    for evo_chain in this_chain.get('evolves_to'):
                        if len(evo_chain.get('evolution_details')) == 1:
                            output += name.capitalize() + " evolves into " + evo_chain.get('species').get('name').capitalize() + " "
                            details = evo_chain.get('evolution_details')[0]

                            if details.get('min_level'):
                                output += "at level " + str(details.get('min_level'))
                                if details.get('gender'):
                                    output += ", if female."
                                elif details.get('relative_physical_stats') is not None:
                                    value = details.get('relative_physical_stats')
                                    if 0 == value:
                                        output += ", if Attack = Defense."
                                    elif 1 == value:
                                        output += ", if Attack > Defense."
                                    elif -1 == value:
                                        output += ", if Attack < Defense."
                                elif details.get('needs_overworld_rain'):
                                    output += ", if it's raining."
                                elif details.get('turn_upside_down'):
                                    output += ", if the 3DS is held upside down."
                                else:
                                    output += "."
                            elif details.get('min_beauty'):
                                output += "with beauty level " + str(details.get('min_beauty') + ".")
                            elif details.get('min_happiness'):
                                output += "with happiness level " + str(details.get('min_happiness'))
                                if details.get('time_of_day'):
                                    output += " when it is " + details.get('time_of_day') + "-time."
                                else:
                                    output += "."
                            elif details.get('time_of_day'):
                                output += "when it is " + details.get('time_of_day') + "-time."
                            elif details.get('item') and details.get('trigger'):
                                item = details.get('item').get('name').replace('-', ' ').title()
                                trigger = details.get('trigger').get('name')
                                if "use-item" == trigger: output += "when a " + item + " is used on it."
                            elif details.get('known_move_type') and details.get('min_affection'):
                                move_type = details.get('known_move_type').get('name').capitalize()
                                affection = details.get('min_affection')
                                output += "with affection level " + str(affection) + " and knowing a " + move_type + " type move."
                            elif details.get('known_move'):
                                output += "upon level-up when it knows " + details.get('known_move').get('name').replace('-', ' ').title()
                            elif details.get('trigger'):
                                if "trade" == details.get('trigger').get('name'):
                                    output += "when traded"
                                    if details.get('held_item'):
                                        output += " and holding a " + details.get('held_item').get('name').replace('-', ' ').title() + "."
                                    else:
                                        output += "."
                                elif "shed" == details.get('trigger').get('name'):
                                    output += "if an extra party slot is open and an extra PokeBall is available."
                        else:
                            for det in evo_chain.get('evolution_details'):
                                if det.get('location'):
                                    loc_id = det.get('location').get('url').split('/')[-2]
                                    try:
                                        loc = drfujibot_pykemon.api.get(location=loc_id)
                                        if loc.region == getRegionForGame(self.get_game(source_user)):
                                            output += name.capitalize() + " evolves into " + evo_chain.get('species').get('name').capitalize() + " "
                                            output += "at " + loc.name.replace('-', ' ').title()
                                            if det.get('trigger'):
                                                if "level-up" == det.get('trigger').get('name'):
                                                    output += " by level up."
                                    except:
                                        print("Unexpected error: " + str(sys.exc_info()[0]))

                        output += " "

                self.output_msg(c, output, source_user)
            except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                #output = "Pokemon '" + name + "' not found."
                #suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=3)
                #if len(suggestions) > 0:    
                #    output += " Did you mean: "
                #    output += ", ".join(suggestions)
                #self.output_msg(c, output, source_user)
                suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=1)
                if len(suggestions) > 0:    
                    self.processCommand("!evol " + suggestions[0], c, source_user)
                else:
                    self.output_msg(c, "Pokemon '" + name + "' not found", source_user)
            except:
                print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!char"):
            if len(line.split(" ")) >= 2:
                phrase = line.split(" ", 1)[1].rstrip("\n").rstrip("\r").lower()
                try:
                    # Can't query by name, just grab all 30 and loop through them.
                    characteristics = []
                    for i in range(30):
                        ch = drfujibot_pykemon.api.get(characteristic=(i+1))
                        characteristics.append(ch)

                    output = ""
                    for ch in characteristics:
                        if phrase.lower() == ch.description:
                            output += phrase.capitalize() + ": Highest IV is "
                            iv = ch.highest_stat.replace('-', ' ').title()
                            if iv == "Hp":
                                iv = "HP"
                            output += iv + ". Possible values are: "
                            str_values = []
                            for v in ch.possible_values:
                                str_values.append(str(v))
                            values = ", ".join(str_values)
                            output += values
                            break

                    if len(output) == 0:
                        output = "Characteristic '" + phrase + "' not found."

                    self.output_msg(c, output, source_user)
                except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                    self.output_msg(c, "Characteristic not found.", source_user)
                except:
                    print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!ev "):
            name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
            name = fix_pokemon_name(name)
            try:
                p = drfujibot_pykemon.api.get(pokemon=name,url=self.config['pokeapi_url'])
                output = name.capitalize() + " EV Yield: "

                evs = []
                for stat in p.stats:
                    if stat.get('effort') > 0:
                        evs.append(stat.get('stat').get('name').replace('-', ' ').title() + "(" + str(stat.get('effort')) + ")")

                output += " ".join(evs)

                self.output_msg(c, output, source_user)
            except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                #output = "Pokemon '" + name + "' not found."
                #suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=3)
                #if len(suggestions) > 0:    
                #    output += " Did you mean: "
                #    output += ", ".join(suggestions)
                #self.output_msg(c, output, source_user)
                suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=1)
                if len(suggestions) > 0:    
                    self.processCommand("!ev " + suggestions[0], c, source_user)
                else:
                    self.output_msg(c, "Pokemon '" + name + "' not found", source_user)
            except:
                print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!grassknot") or line.startswith("!lowkick"):
            name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
            name = fix_pokemon_name(name)
            try:
                p = drfujibot_pykemon.api.get(pokemon=name,url=self.config['pokeapi_url'])

                output = "Low Kick/Grass Knot has "

                if p.weight < 100:
                    bp = "20"
                elif p.weight < 250:
                    bp = "40"
                elif p.weight < 500:
                    bp = "60"
                elif p.weight < 1000:
                    bp = "80"
                elif p.weight < 2000:
                    bp = "100"
                else:
                    bp = "120"

                output += bp
                output += " base power against " + name.capitalize() + " ("
                output += str(float(p.weight) / 10)
                output += " kg)"

                self.output_msg(c, output, source_user)
            except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                #output = "Pokemon '" + name + "' not found."
                #suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=3)
                #if len(suggestions) > 0:    
                #    output += " Did you mean: "
                #    output += ", ".join(suggestions)
                #self.output_msg(c, output, source_user)
                suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=1)
                if len(suggestions) > 0:    
                    self.processCommand("!grassknot " + suggestions[0], c, source_user)
                else:
                    self.output_msg(c, "Pokemon '" + name + "' not found", source_user)
            except:
                print("Unexpected error: " + str(sys.exc_info()[0]))
        elif line.startswith("!heatcrash") or line.startswith("!heavyslam"):
            name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
            name = fix_pokemon_name(name)
            name2 = line.split(" ")[2].rstrip("\n").rstrip("\r").lower()
            name2 = fix_pokemon_name(name2)
            try:
                p1 = drfujibot_pykemon.api.get(pokemon=name,url=self.config['pokeapi_url'])
                p2 = drfujibot_pykemon.api.get(pokemon=name2, url=self.config['pokeapi_url'])

                output = "Heavy Slam/Heat Crash used by "

                bp = "40"
                if p1.weight > p2.weight:
                    relative = p2.weight / p1.weight

                    if relative > .5:
                        bp = "40"
                    elif relative > .3334:
                        bp = "60"
                    elif relative > .25:
                        bp = "80"
                    elif relative > .2:
                        bp = "100"
                    else:
                        bp = "120"

                output += name.capitalize() + " has " + bp + " base power against " + name2.capitalize()

                self.output_msg(c, output, source_user)
            except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                #output = "Pokemon '" + name + "' not found."
                #suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=3)
                #if len(suggestions) > 0:
                #    output += " Did you mean: "
                #    output += ", ".join(suggestions)
                #self.output_msg(c, output, source_user)
                suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=1)
                if len(suggestions) > 0:    
                    self.processCommand("!heatcrash " + suggestions[0], c, source_user)
                else:
                    self.output_msg(c, "Pokemon '" + name + "' not found", source_user)
            except:
                print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!gender"):
            name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
            name = fix_pokemon_name(name)
            try:
                p = drfujibot_pykemon.api.get(species=name,url=self.config['pokeapi_url'])

                output = name.capitalize() + ": "
                if -1 == p.gender_rate:
                    output += "Genderless"
                else:
                    percent_female = ( float(p.gender_rate) / float(8) ) * 100
                    percent_male = 100 - percent_female

                    output += "Male(" + str(percent_male) + "%) Female(" + str(percent_female) + "%)"

                self.output_msg(c, output, source_user)
            except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                #output = "Pokemon '" + name + "' not found."
                #suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=3)
                #if len(suggestions) > 0:    
                #    output += " Did you mean: "
                #    output += ", ".join(suggestions)
                #self.output_msg(c, output, source_user)
                suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=1)
                if len(suggestions) > 0:    
                    self.processCommand("!gender " + suggestions[0], c, source_user)
                else:
                    self.output_msg(c, "Pokemon '" + name + "' not found", source_user)
            except:
                print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!faster"):
            if len(line.split(" ")) > 2:
                pokemon1 = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
                pokemon2 = line.split(" ")[2].rstrip("\n").rstrip("\r").lower()
                pokemon1 = fix_pokemon_name(pokemon1)
                pokemon2 = fix_pokemon_name(pokemon2)

                try:
                    p1 = drfujibot_pykemon.api.get(pokemon=pokemon1,url=self.config['pokeapi_url'])

                    try:
                        p2 = drfujibot_pykemon.api.get(pokemon=pokemon2,url=self.config['pokeapi_url'])

                        if p1.speed > p2.speed:
                            output = pokemon1.capitalize() + " (" + str(p1.speed) + ") is faster than " + pokemon2.capitalize() + " (" + str(p2.speed) + ")"
                        elif p1.speed < p2.speed:
                            output = pokemon1.capitalize() + " (" + str(p1.speed) + ") is slower than " + pokemon2.capitalize() + " (" + str(p2.speed) + ")"
                        elif p1.speed == p2.speed:
                            output = pokemon1.capitalize() + " and " + pokemon2.capitalize() + " are tied for speed (" + str(p1.speed) + ")"

                        self.output_msg(c, output, source_user)

                    except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                        #output = "Pokemon '" + pokemon2 + "' not found."
                        #suggestions = self.pokemon_corrector.suggest(pokemon2.capitalize(), limit=3)
                        #if len(suggestions) > 0:    
                        #    output += " Did you mean: "
                        #    output += ", ".join(suggestions)
                        #self.output_msg(c, output, source_user)
                        suggestions = self.pokemon_corrector.suggest(pokemon2.capitalize(), limit=1)
                        if len(suggestions) > 0:    
                            self.processCommand("!faster " + pokemon1 + " " + suggestions[0], c, source_user)
                        else:
                            self.output_msg(c, "Pokemon '" + pokemon2 + "' not found", source_user)
                    except:
                        print("Unexpected error: " + str(sys.exc_info()[0]))

                except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                    #output = "Pokemon '" + pokemon1 + "' not found."
                    #suggestions = self.pokemon_corrector.suggest(pokemon1.capitalize(), limit=3)
                    #if len(suggestions) > 0:    
                    #    output += " Did you mean: "
                    #    output += ", ".join(suggestions)
                    #self.output_msg(c, output, source_user)
                    suggestions = self.pokemon_corrector.suggest(pokemon1.capitalize(), limit=1)
                    if len(suggestions) > 0:    
                        self.processCommand("!faster " + suggestions[0] + " " + pokemon2, c, source_user)
                    else:
                        self.output_msg(c, "Pokemon '" + pokemon1 + "' not found", source_user)
                except:
                    print("Unexpected error: " + str(sys.exc_info()[0]))
            else:
                self.output_msg(c, "Please input more than one pokemon.", source_user)

        elif line.startswith("!exp"):
            name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
            name = fix_pokemon_name(name)
            try:
                p = drfujibot_pykemon.api.get(pokemon=name,url=self.config['pokeapi_url'])
                output = name.capitalize() + ": " + str(p.base_experience) + " Base Exp."

                self.output_msg(c, output, source_user)
            except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                #output = "Pokemon '" + name + "' not found."
                #suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=3)
                #if len(suggestions) > 0:    
                #    output += " Did you mean: "
                #    output += ", ".join(suggestions)
                #self.output_msg(c, output, source_user)
                suggestions = self.pokemon_corrector.suggest(name.capitalize(), limit=1)
                if len(suggestions) > 0:    
                    self.processCommand("!exp " + suggestions[0], c, source_user)
                else:
                    self.output_msg(c, "Pokemon '" + name + "' not found", source_user)
            except:
                print("Unexpected error: " + str(sys.exc_info()[0]))

        elif line.startswith("!remind"):
            if len(line.split(" ")) > 2:
                timestring = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
                message = line.split(" ", 2)[2].rstrip("\n").rstrip("\r")

                delta = parse_time(timestring)
                if delta:
                    self.output_msg(c, "I will remind you in " + timestring + " to " + message, source_user)

                    reminder = ""
                    if self.bot_type and self.bot_type == "discord":
                        if source_id:
                            # Discord main channel mode
                            reminder = "Reminder <@!" + source_id + "> : " + message
                        else:
                            # Discord whisper mode
                            reminder = "Reminder: " + message
                    else:
                        # Twitch mode
                        reminder = "Reminder @" + source_user + " : " + message

                    t = threading.Timer(delta.total_seconds(), self.output_msg, [c, reminder, source_user])
                    t.start()
                else:
                    self.output_msg(c, "Invalid time string. Examples: 5m 5m30s 1h5m30s", source_user)
            else:
                self.output_msg(c, "Format: !remind <time> <message>", source_user)

        elif line.startswith("!deaths"):
            deaths = self.get_current_run_data('deaths')
            if None == deaths:
                deaths = str(self.deaths)
            else:
                deaths = str(deaths)
            sorted_fallen = sorted(self.fallen_timestamps.items(), key=operator.itemgetter(1), reverse=True)
            recent_deaths = []
            for i in range(min(3, len(sorted_fallen))):
                recent_deaths.append(sorted_fallen[i][0])
            self.output_msg(c, "There have been " + deaths + " deaths so far. Most recent deaths (latest first): " + ", ".join(recent_deaths), source_user)

        elif line.startswith("!setdeaths"):
            if len(line.split(" ")) == 2:
                try:
                    deaths = int(line.split(" ")[1].rstrip("\n").rstrip("\r"))
                    self.deaths = deaths

                    self.config['deaths'] = deaths

                    if None != self.config['current_run'] and None != self.config['run_data']:
                        if None != self.config['run_data'].get(self.config['current_run']):
                            self.config['run_data'][self.config['current_run']]['deaths'] = deaths

                    if 0 == deaths:
                        self.fallen = {}
                        self.fallen_timestamps = {}
                        self.config['fallen'] = []
                        self.config['fallen_timestamps'] = []

                    self.update_config()

                    self.output_msg(c, "Set death counter to " + str(self.deaths), source_user)
                except:
                    self.output_msg(c, "Format: !setdeaths <number>", source_user)
            else:
                self.output_msg(c, "Format: !setdeaths <number>", source_user)

        elif line.startswith("!rip") and not line.startswith("!riprun"):
            if len(line.split(" ")) > 1:
                pokemon = line.split(" ", 1)[1]
            else:
                pokemon = ""

            if self.meme_mode:
                if None == self.current_deaths.get(pokemon):
                    self.deaths += 1
                    self.config['deaths'] = self.deaths
                    if None != self.config['current_run'] and None != self.config['run_data']:
                        if None != self.config['run_data'].get(self.config['current_run']):
                            self.config['run_data'][self.config['current_run']]['deaths'] = self.deaths
                    self.update_config()

                    output = "Death counter: " + str(self.deaths) + " riPepperonis "
                    output += "Press F to pay respects to '" + pokemon + "'"
                    self.output_msg(c, output, source_user)

                    # Auto-marker
                    self.output_msg(c, '/marker Death of "' + pokemon + '"', source_user)

                    self.current_deaths[pokemon] = time.time()
                    self.deaths_dict[pokemon] = []

            else:
                self.deaths += 1

                output = "Death counter: " + str(self.deaths) + " riPepperonis "
                self.output_msg(c, output, source_user)

                self.config['deaths'] = self.deaths
                if None != self.config['current_run'] and None != self.config['run_data']:
                    if None != self.config['run_data'].get(self.config['current_run']):
                        self.config['run_data'][self.config['current_run']]['deaths'] = self.deaths
                self.update_config()

        elif line.startswith("!ez"):
            if self.meme_mode:
                self.ez = True
                self.ez_count = 0
                self.ez_start = time.time()
                output = "Type EZ to pay respects to PC"
                self.output_msg(c, output, source_user)

        elif line.startswith("!fallen"):

            sorted_pairs = sorted(self.fallen.items(), key=operator.itemgetter(1), reverse=True)

            output = "The most respected fallen: "
            if len(sorted_pairs) >= 1:
                output += sorted_pairs[0][0]
                output += " (" + str(sorted_pairs[0][1]) + ")"
            if len(sorted_pairs) >= 2:
                output += ", "
                output += sorted_pairs[1][0]
                output += " (" + str(sorted_pairs[1][1]) + ")"
            if len(sorted_pairs) >= 3:
                output += ", "
                output += sorted_pairs[2][0]
                output += " (" + str(sorted_pairs[2][1]) + ")"

            self.output_msg(c, output, source_user)

        elif line.startswith("!adduser"):
            if len(line.split(" ")) == 2:
                new_user = line.split(" ")[1].rstrip("\n").rstrip("\r")

                self.permitted_users.append(new_user.lower())

                save_users = self.permitted_users[:]
                if self.username.lower() in save_users:
                    save_users.remove(self.username.lower())

                self.config['permitted_users'] = save_users
                self.update_config()

                self.output_msg(c, "Added user '" + new_user + "' to permitted users.", source_user)
            else:
                self.output_msg(c, "Format: !adduser <username>", source_user)

        elif line.startswith("!removeuser"):
            if len(line.split(" ")) == 2:
                remove_user = line.split(" ")[1].rstrip("\n").rstrip("\r")

                if remove_user.lower() in self.permitted_users:
                    self.permitted_users.remove(remove_user.lower())

                    save_users = self.permitted_users[:]
                    if self.username.lower() in save_users:
                        save_users.remove(self.username.lower())

                    self.config['permitted_users'] = save_users
                    self.update_config()

                    self.output_msg(c, "Removed user '" + remove_user + "' from permitted users.", source_user)
                else:
                    self.output_msg(c, "User '" + remove_user + "' not found.", source_user)
            else:
                self.output_msg(c, "Format: !removeuser <username>", source_user)

        elif line.startswith("!addshoutout"):
            if len(line.split(" ")) == 2:
                new_user = line.split(" ")[1].rstrip("\n").rstrip("\r")

                if new_user not in self.config['auto_shoutout']:
                    self.config['auto_shoutout'].append(new_user.lower())
                    self.update_config()

                self.output_msg(c, "Added user '" + new_user + "' to auto-shoutout.", source_user)
            else:
                self.output_msg(c, "Format: !addshoutout <username>", source_user)

        elif line.startswith("!removeshoutout"):
            if len(line.split(" ")) == 2:
                remove_user = line.split(" ")[1].rstrip("\n").rstrip("\r")

                if remove_user.lower() in self.config['auto_shoutout']:
                    self.config['auto_shoutout'].remove(remove_user.lower())
                    self.update_config()

                    self.output_msg(c, "Removed user '" + remove_user + "' from auto-shoutout.", source_user)
                else:
                    self.output_msg(c, "User '" + remove_user + "' not found.", source_user)
            else:
                self.output_msg(c, "Format: !removeshoutout <username>", source_user)

        elif line.startswith("!whatis"):
            name = line.split(" ", 1)[1].rstrip("\n").rstrip("\r").lower()
            name = name.replace(" ", "-")

            try:
                m = drfujibot_pykemon.api.get(move=name,url=self.config['pokeapi_url'])
                self.processCommand("!move " + name, c, source_user, prefix="Move: ")

            except drfujibot_pykemon.exceptions.ResourceNotFoundError:

                try:
                    a = drfujibot_pykemon.api.get(ability=name,url=self.config['pokeapi_url'])

                    self.processCommand("!ability " + name, c, source_user, prefix="Ability: ")
                except drfujibot_pykemon.exceptions.ResourceNotFoundError:
                    self.output_msg(c, "Could not find '" + name + "'", source_user)

        elif line.startswith("!anagram"):
            #word = line.split(" ", 1)[1].rstrip("\n").rstrip("\r").lower()

            #if len(word) <= 10:
            #    #a = Anagram(word)

            #    #anagram_list = a.get_anagrams()
            #    #anagram_list = []
            #    #anagram_data = get_anagrams()
            #    #for key, anagrams in anagram_data.items():
            #    #    if len(anagrams) > 1:
            #    #        anagram_list.extend(anagrams)

            #    #output = "Anagrams: "
            #    #if len(anagram_list) > 1:
            #    #    output += ", ".join(anagram_list)
            #    #else:
            #    #    output += "(none)"

            #    #if len(output) > 240:
            #    #    output = output[:240]
            #    #    output = output.rsplit(", ", 1 )[0]
            #else:
            #    output = "Word too long, max 10 characters"

            #self.output_msg(c, output, source_user)
            self.output_msg(c, "The !anagram command is currently not working. Use this instead: https://ingesanagram.appspot.com/", source_user)

        elif line.startswith("!event"):
            self.new_bet(c, line, source_user)

        elif line.startswith("!close"):
            if self.foundCoinFile:
                if len(line.split(" ")) == 2:
                    event_name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()

                    if event_name in self.open_events.keys():
                        self.closed_events[event_name] = self.open_events[event_name]
                        del self.open_events[event_name]
                        self.output_msg(c, "Betting has closed for '" + event_name + "' event!", source_user)

                        self.config['open_events'] = self.open_events
                        self.config['closed_events'] = self.closed_events

                        if None != self.config['current_run'] and None != self.config['run_data']:
                            if None != self.config['run_data'].get(self.config['current_run']):
                                self.config['run_data'][self.config['current_run']]['closed_events'] = copy.deepcopy(self.closed_events)

                        self.update_config()
                    else:
                        self.output_msg(c, "Event '" + event_name + "' not found", source_user)
                else:
                    self.output_msg(c, "Event name must not contain spaces", source_user)
            else:
                self.output_msg(c, "Betting has not been configured", source_user)

        elif line.startswith("!cancel"):
            if self.foundCoinFile:
                if len(line.split(" ")) == 2:
                    event_name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()

                    if event_name in self.open_events.keys():
                        wager = self.open_event_rewards[event_name]
                        for user in self.open_events[event_name].keys():
                            self.coin_data['coins'][user] += wager
                        self.update_coin_data()

                        del self.open_events[event_name]
                        del self.open_event_rewards[event_name]
                        self.output_msg(c, "Event '" + event_name + "' has been cancelled, and all bets refunded", source_user)

                        self.config['open_events'] = self.open_events
                        self.config['open_event_rewards'] = self.open_event_rewards
                        self.update_config()
                    elif event_name in self.closed_events.keys():
                        for user in self.closed_events[event_name].keys():
                            wager = self.open_event_rewards[event_name]
                            self.coin_data['coins'][user] += wager
                        self.update_coin_data()

                        del self.closed_events[event_name]
                        del self.open_event_rewards[event_name]
                        self.output_msg(c, "Event '" + event_name + "' has been cancelled, and all bets refunded", source_user)

                        self.config['closed_events'] = self.closed_events
                        self.config['open_event_rewards'] = self.open_event_rewards
                        self.update_config()
                    else:
                        self.output_msg(c, "Event '" + event_name + "' not found", source_user)
                else:
                    self.output_msg(c, "Event name must not contain spaces", source_user)
            else:
                self.output_msg(c, "Betting has not been configured", source_user)

        elif line.startswith("!resolve"):
            self.resolve_bet(c, line, source_user)

        elif line.startswith("!bet"):
            if len(line.split(" ")) == 2:
                guess = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
                try:
                    if len(self.open_events.keys()) == 1:
                        event_name = list(self.open_events.keys())[0]
                        coins = self.open_event_rewards[event_name]
                        if guess in self.bet_config['events'][event_name]['outcomes'].keys():
                            with self.coin_lock:
                                if None == self.coin_data['coins'].get(source_user):
                                    # If it's a new user and the coin loop hasn't run yet
                                    self.coin_data['coins'][source_user] = 0

                                refund = 0
                                previous = self.open_events[event_name].get(source_user)
                                if None != previous:
                                    refund = previous[1]

                                self.open_events[event_name][source_user] = (guess, coins)
                                self.config['open_events'] = self.open_events
                                self.update_config()
                        else:
                            self.output_msg(c, "@" + source_user + " Not a valid outcome!", source_user)
                    else:
                        self.output_msg(c, "Could not find active event", source_user)
                except:
                    self.output_msg(c, "Format: !bet <guess>", source_user)
            else:
                self.output_msg(c, "Format: !bet <guess>", source_user)

        elif line.startswith("!daily"):
            if not self.whisperMode and self.username != 'everoddish':
                now = datetime.datetime.now()
                if self.coin_data['last_daily_bonus'].get(source_user):
                    last = datetime.datetime.fromtimestamp(self.coin_data['last_daily_bonus'][source_user])
                else:
                    last = now - datetime.timedelta(hours=25)

                if last < self.start_time:
                    last = now - datetime.timedelta(hours=25)

                output = ""

                diff = now - last
                if diff.days >= 1:
                    more_coins = random.randint(0, 100)

                    crit = 0
                    if more_coins >= 50:
                        crit = random.randint(1, 16)

                    if 1 == crit and 0 != more_coins:
                        more_coins *= 2

                    output = "@" + source_user + " You received a daily bonus of " + str(more_coins) + " coins! "

                    if 1 == crit and 0 != more_coins:
                        output += "A critical hit! "

                    if 0 == more_coins:
                        output += "It missed! "

                    timestamp = time.mktime(now.timetuple())
                    self.coin_data['last_daily_bonus'][source_user] = timestamp
                    self.update_config()

                    with self.coin_lock:
                        if None == self.coin_data['coins'].get(source_user):
                            # If it's a new user and the coin loop hasn't run yet
                            self.coin_data['coins'][source_user] = 0
                        self.coin_data['coins'][source_user] += more_coins
                        self.update_coin_data()
                        output += " You now have " + str(int(self.coin_data['coins'][source_user])) + " coins."
                else:
                    diff2 = datetime.timedelta(hours=24) - diff
                    output = "@" + source_user
                    output += " You can receive another daily bonus in "
                    output += str(diff2.seconds//3600) + " hours and "
                    output += str((diff2.seconds//60)%60) + " minutes"

                self.output_msg(c, output, source_user)

        elif line.startswith("!riprun"):
            # Streamer only
            if source_user.lower() == self.username.lower():
                if self.foundCoinFile:
                    if len(line.split(" ")) >= 3:

                        # Set deaths to zero
                        self.deaths = 0
                        self.config['deaths'] = 0

                        if None != self.config['current_run'] and None != self.config['run_data']:
                            if None != self.config['run_data'].get(self.config['current_run']):
                                self.config['run_data'][self.config['current_run']]['deaths'] = self.deaths

                        self.update_config()

                        try:
                            num_badges = int(line.split(" ")[1].rstrip("\n").rstrip("\r").lower())
                            message = line.split(" ", 2)[2].rstrip("\n").rstrip("\r")

                            # Resolve badge bets
                            command = "!resolve badges " + str(num_badges)
                            self.resolve_bet(c, command, source_user)

                            # Start a new badge bet
                            command = "!event badges 10000"
                            self.new_bet(c, command, source_user)

                            if None != self.config['current_run'] and None != self.config['run_data']:
                                if None != self.config['run_data'].get(self.config['current_run']):
                                    self.config['run_data'][self.config['current_run']]['!lastrun'] = message
                                    self.config['run_data'][self.config['current_run']]['attempt'] += 1
                            if None != self.config['extra_commands'].get('!lastrun'):
                                self.config['extra_commands']['!lastrun'] = message
                            self.update_config()

                            self.output_msg(c, "Rip run BibleThump", source_user)

                        except Exception as e:
                            print("Exception: " + str(e))
                    else:
                        self.output_msg(c, "Format: !riprun <num_badges_obtained> <new_!lastrun_message>", source_user)
                else:
                    self.output_msg(c, "Betting has not been configured", source_user)

        elif line.startswith("!notify "):
            # Streamer only (or me nathanPepe)
            if "pokemonchallenges" == self.username.lower() or "pokemonrealtime" == source_user.lower():
                message = line.split(" ", 1)[1].rstrip("\n").rstrip("\r")
                timestamp = int(time.time())
                self.pcce["notification"] = str(timestamp) + ":" + message
                self.update_pcce()
                self.output_msg(c, "Notification sent to PCCE users", source_user)

        elif line.startswith("!resetcoins"):
            if "pokemonchallenges" == self.username.lower() or "pokemodrealtime" == source_user.lower() or "moshjarcus" == source_user.lower():
                with self.coin_lock:
                    current_date = datetime.date.today().strftime("%Y-%m-%d")
                    shutil.copyfile("PokemonChallenges_coins.json", "PokemonChallenges_coins_" + current_date + ".json")
                    self.coin_data['coins'] = {}
                    self.coin_data['last_daily_bonus'] = {}
                    self.update_coin_data()

                    self.output_msg(c, "Backup created (compressed with Middle-Out) - ALL COINS HAVE BEEN RESET!", source_user)

        elif line.startswith("!leaderboard"):
            if "pokemonchallenges" == self.username.lower() or "moshjarcus" == self.username.lower():

                with open(self.username + '_coins.json', 'r') as coin_file:
                    coin_info = json.load(coin_file)
                    coins = coin_info.get('coins')
                    if None != coins:
                        sorted_data = sorted(coins.items(), key=operator.itemgetter(1))
                        i = 0
                        output = "Leaderboard: "
                        for e in reversed(sorted_data):
                            #print(e[0] + " - " + str(e[1]))
                            output += e[0] + "(" + str(int(e[1])) + ") "
                            if i >= 2:
                                break
                            i += 1

                        self.output_msg(c, output, source_user)

        elif line.startswith("!balance"):
            if self.whisperMode:

                output = get_coin_balances(source_user)

                self.output_msg(c, output, source_user)
            else:
                self.output_msg(c, 'The !balance command has returned to whisper-only mode! Type "/w DrFujiBot !balance" to see your coins!', source_user)

        elif line.startswith("!credit"):
            if len(line.split(" ")) >= 3:
                arg1 = line.split(" ")[1]
                arg2 = line.split(" ")[2]
                success = False

                try:
                    coins = int(arg1)
                    user = arg2
                    success = True
                except:
                    pass

                try:
                    coins = int(arg2)
                    user = arg1
                    success = True
                except:
                    pass

                if success:
                    with self.coin_lock:
                        if None == self.coin_data['coins'].get(user):
                            self.coin_data['coins'][user] = coins
                        else:
                            self.coin_data['coins'][user] += coins
                        self.update_coin_data()

                    output = "Credited " + str(coins) + " coins to @" + user

                    self.output_msg(c, output, source_user)
                else:
                    self.output_msg(c, "Format: !credit <user> <coins>", source_user)

        elif line.startswith("!coins"):
            if self.whisperMode:

                output1 = "You're earning coins while sitting in chat! Make sure to use the !daily command every 24 hours to get a daily coin reward! "
                output2 = "You can check your savings at any time by using the !balance command. "
                output3 = "A mod will start a betting event in chat, and you can joing by typing !bet <outcome> after the event has started! "
                output4 = "For example: '!bet 1' to bet 1 death in a gym battle. For a full list of betting commands and what they do, click here: https://goo.gl/i8slEk"
                output5 = get_coin_balances(source_user)

                self.output_msg(c, output1, source_user)
                time.sleep(1)
                self.output_msg(c, output2, source_user)
                time.sleep(1)
                self.output_msg(c, output3, source_user)
                time.sleep(1)
                self.output_msg(c, output4, source_user)
                time.sleep(1)
                self.output_msg(c, output5, source_user)
            else:
                output = "You're currently earning coins and can use them to bet on what might happen during the stream! "
                output += "Whisper !balance to DrFujiBot to see your current savings!"
                self.output_msg(c, output, source_user)

        elif line.startswith("!addcom"):
            if True == self.config['extra_commands_on']:
                if len(line.split(" ")) >= 3:
                    command = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
                    message = line.split(" ", 2)[2].rstrip("\n").rstrip("\r")

                    if command.startswith("!"):
                        if not message.startswith("!"):
                            if False == self.is_valid_command(command):
                                if None == self.config['extra_commands'].get(command):
                                    if self.is_setrun_command(command):
                                        self.set_current_run_data(command, message)
                                    else:
                                        self.config['extra_commands'][command] = message
                                    self.update_config()

                                    self.output_msg(c, command + " command added", source_user)
                                else:
                                    self.output_msg(c, "Command already exists", source_user)
                            else:
                                self.output_msg(c, "Cannot override existing DrFujiBot command", source_user)
                        else:
                            self.output_msg(c, "Message cannot start with !", source_user)
                    else:
                        self.output_msg(c, "Command must start with !", source_user)
                else:
                    self.output_msg(c, "Format: !addcom <!command> <message>", source_user)

        elif line.startswith("!editcom"):
            if True == self.config['extra_commands_on']:
                if len(line.split(" ")) >= 3:
                    command = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
                    message = line.split(" ", 2)[2].rstrip("\n").rstrip("\r")

                    if command.startswith("!"):
                        if not message.startswith("!"):
                            exists = False

                            if self.is_setrun_command(command):
                                exists = True
                            else:
                                # Not using !setrun
                                if None != self.config['extra_commands'].get(command):
                                    exists = True

                            if exists:
                                if self.is_setrun_command(command):
                                    self.set_current_run_data(command, message)
                                else:
                                    self.config['extra_commands'][command] = message
                                self.update_config()

                                self.output_msg(c, command + " command updated", source_user)
                            else:
                                self.output_msg(c, "Command '" + command + "' not found", source_user)
                        else:
                            self.output_msg(c, "Message cannot start with !", source_user)
                    else:
                        self.output_msg(c, "Command must start with !", source_user)
                else:
                    self.output_msg(c, "Format: !editcom <!command> <message>", source_user)

        elif line.startswith("!delcom"):
            if True == self.config['extra_commands_on']:
                if len(line.split(" ")) == 2:
                    command = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()

                    if None != self.config['extra_commands'].get(command):
                        del self.config['extra_commands'][command]
                        self.update_config()

                        self.output_msg(c, command + " command deleted", source_user)
                    else:
                        self.output_msg(c, "Command '" + command + "' not found", source_user)
                else:
                    self.output_msg(c, "Format: !delcom <!command>", source_user)

        elif line.startswith("!so ") or line.startswith("!shoutout"):
            if True == self.config['extra_commands_on']:
                streamer = ""
                if len(line.split(" ")) >= 2:
                    streamer = line.split(" ")[1].rstrip("\n").rstrip("\r")
                else:
                    streamer = self.username

                self.do_shoutout(c, streamer, self.config['shoutout_messages'], 0, source_user)

        elif line.startswith("!raid"):
            # Streamer only
            if source_user.lower() == self.username.lower():
                if len(line.split(" ")) == 2:
                    streamer = line.split(" ")[1].rstrip("\n").rstrip("\r")

                    output = self.config.get('raid_message')
                    if None != output:
                        for i in range(5):
                            self.output_msg(c, output, source_user, 0)

                    output = "twitch.tv/" + streamer
                    for i in range(5):
                        self.output_msg(c, output, source_user, 0)

        elif line.startswith("!uptime"):
            if True == self.config['extra_commands_on']:
                output = ""
                CLIENT_ID = get_fuji_config_value('twitch_client_id')
                STREAM_INFO_URL = 'https://api.twitch.tv/kraken/streams?channel=' + self.username
                try:
                    request = urllib.request.Request(STREAM_INFO_URL)
                    request.add_header('Client-ID', CLIENT_ID)
                    response = urllib.request.urlopen(request)
                    data = json.loads(response.read().decode('utf-8'))
                    if len(data['streams']) > 0:
                        created_at = data['streams'][0]['created_at']
                        live_datetime = iso8601.parse_date(created_at)
                        now = datetime.datetime.now(datetime.timezone.utc)
                        diff = now - live_datetime

                        output = "Uptime: "
                        output += str((diff.seconds//3600)) + " hours and "
                        output += str((diff.seconds//60)%60) + " minutes"
                    else:
                        output = "This channel is offline"
                except:
                    print("Unexpected error: " + str(sys.exc_info()[0]))
                    output = "Error getting uptime from Twitch server"

                self.output_msg(c, output, source_user)

        elif line.startswith("!song"):
            lastfm_user = self.config.get('lastfm_user')
            LASTFM_API_KEY = get_fuji_config_value('lastfm_api_key')
            if None != lastfm_user: 
                lastfm_url = "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user="
                lastfm_url += lastfm_user
                lastfm_url += "&api_key="
                lastfm_url += LASTFM_API_KEY
                lastfm_url += "&format=json"

                try:
                    response = urllib.request.urlopen(lastfm_url).read().decode('UTF-8')
                    lastfm_data = json.loads(response)

                    #for track in lastfm_data['recenttracks']['track']:
                    #    print(track['name'] + " - " + track['artist']['#text'])

                    most_recent_track = lastfm_data['recenttracks']['track'][0]
                    output = most_recent_track['name'] + " - " + most_recent_track['artist']['#text']

                    spotify_user = self.config.get('spotify_user')
                    if None != spotify_user:
                        output += " | Check out my playlists here: https://open.spotify.com/user/" + spotify_user

                    self.output_msg(c, output, source_user)

                except Exception as e:
                    print("!song exception: " + str(e))

        elif line.startswith("!quote"):
            if True == self.config['extra_commands_on']:
                if len(self.config['quotes'].keys()) > 0:
                    # Cooldown
                    last_output = self.extra_command_cooldown.get("!quote")

                    should_output = False
                    current_time = datetime.datetime.now()

                    if None == last_output:
                        should_output = True
                    else:
                        diff = current_time - last_output
                        if diff.seconds >= 10:
                            should_output = True

                    if should_output:
                        key = ""
                        quote = ""
                        is_int = False

                        if len(line.split(" ")) > 1:
                            key = line.split(" ")[1]

                            try:
                                key_int = int(key)
                                is_int = True
                            except:
                                pass
                        else:
                            key = random.choice(list(self.config['quotes'].keys()))
                            is_int = True

                        if is_int:
                            if self.config['quotes'].get(key):
                                quote = 'Quote #' + key + ' "'
                                quote += self.config['quotes'][key]
                                quote += '" -' + self.username
                            else:
                                self.output_msg(c, "Quote #" + key + " not found", source_user)
                        else:
                            matches = [q for q in self.config['quotes'].values() if key.lower() in q.lower()]
                            if len(matches) > 0:
                                selected_match = random.choice(matches)
                                for k, v in self.config['quotes'].items():
                                    if v == selected_match:
                                        quote = 'Quote #' + k + ' "'
                                        quote += self.config['quotes'][k]
                                        quote += '" -' + self.username
                            else:
                                self.output_msg(c, "Quote containing '" + key + "' not found", source_user)

                        if len(quote) > 0:
                            self.output_msg(c, quote, source_user)

                        # Update last output time
                        self.extra_command_cooldown["!quote"] = current_time
                else:
                    self.output_msg(c, "No quotes available", source_user)

        elif line.startswith("!latestquote"):
            if True == self.config['extra_commands_on']:
                if len(self.config['quotes'].keys()) > 0:
                    # Cooldown
                    last_output = self.extra_command_cooldown.get("!latestquote")

                    should_output = False
                    current_time = datetime.datetime.now()

                    if None == last_output:
                        should_output = True
                    else:
                        diff = current_time - last_output
                        if diff.seconds >= 10:
                            should_output = True

                    if should_output:
                        quote = ""

                        key_list = list(self.config['quotes'].keys())
                        # Convert from strings to integers
                        key_list = list(map(int, key_list))
                        key_list.sort()
                        key = key_list[-1]
                        key = str(key)

                        if self.config['quotes'].get(key):
                            quote = 'Quote #' + key + ' "'
                            quote += self.config['quotes'][key]
                            quote += '" -' + self.username
                        else:
                            self.output_msg(c, "Quote #" + key + " not found", source_user)

                        if len(quote) > 0:
                            self.output_msg(c, quote, source_user)

                        # Update last output time
                        self.extra_command_cooldown["!latestquote"] = current_time
                else:
                    self.output_msg(c, "No quotes available", source_user)

        elif line.startswith("!addquote"):
            if True == self.config['extra_commands_on']:
                quote = line.split(" ", 1)[1].rstrip("\n").rstrip("\r")

                key = 1
                while self.config['quotes'].get(str(key)):
                    key += 1
                key = str(key)

                self.config['quotes'][key] = quote
                self.update_config()
                self.output_msg(c, "Quote #" + key + " added", source_user)

        elif line.startswith("!delquote"):
            if True == self.config['extra_commands_on']:
                if len(line.split(" ")) == 2:
                    quoteNum = line.split(" ")[1].rstrip("\n").rstrip("\r")
                    if self.config['quotes'].get(quoteNum):
                        del self.config['quotes'][quoteNum]
                        self.update_config()
                        self.output_msg(c, "Quote #" + quoteNum + " deleted", source_user)
                    else:
                        self.output_msg(c, "Quote #" + quoteNum + " not found", source_user)
                else:
                    self.output_msg(c, "Format: !delquote <quote number>", source_user)

        elif line.startswith("!elo"):
            if len(line.split(" ")) == 2:
                ladder = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
            else:
                ladder = "gen7ou"
            output = ""

            result = requests.get("https://pokemonshowdown.com/users/" + self.username)
            if result.status_code == 200:
                soup = BeautifulSoup(result.content)
                rows = soup.find_all("tr")

                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        if ladder == cells[0].text:
                            output = "Showdown '" + ladder + "' ELO: " + cells[1].text
                            break

            if len(output) == 0:
                output = "Showdown ladder '" + ladder + "' not found"

            self.output_msg(c, output, source_user)

        elif line.startswith("!smogon "):
            if len(line.split(" ")) == 2:
                pkmn = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()

                one_month = 60 * 60 * 24 * 30
                #requests_cache.install_cache("smogon", backend='sqlite', expire_after=one_month)

                result = requests.get("http://www.smogon.com/dex/sm/pokemon/" + pkmn)
                if result.status_code == 200:
                    data_re = re.compile(r'dexSettings = (\{.*\})')
                    text_content = result.content.decode('utf-8')
                    matches = data_re.search(text_content)

                    output = ""

                    if matches:
                        json_data = matches.group(1)
                        data = json.loads(json_data)
                        inject_rpcs = data["injectRpcs"]
                        for inj in inject_rpcs:
                            if "dump-pokemon" in inj[0]:
                                data_dict = inj[1]
                                if len(data_dict["strategies"]) > 0:
                                    strat = data_dict["strategies"][0]
                                    movesets = strat["movesets"]
                                    tier = strat["format"]
                                    for moveset in movesets:
                                        output = "(" + tier + ") "
                                        output += moveset["name"] 
                                        output += ": "
                                        for moveslot in moveset["moveslots"]:
                                            output += moveslot[0]
                                            output += ", "
                                        output = output.rsplit(", ", 1)[0]
                                        output += " - "
                                        output += moveset["abilities"][0]
                                        output += " - "
                                        output += moveset["items"][0]
                                        self.output_msg(c, output, source_user, 0)
                                break

                    if len(output) == 0:
                        self.output_msg(c, "Could not find Smogon information for '" + pkmn + "'", source_user)

                #requests_cache.uninstall_cache()
            else:
                self.output_msg(c, "Format: !smogon <pokemon>", source_user)

        elif line.startswith("!chatbattle"):
            # Streamer only
            #if source_user.lower() == self.username.lower():
            if source_user.lower() == "drfujibot":
                try:
                    server_address = '/tmp/fuji_to_node.sock'
                    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    sock.connect(server_address)
                    node_command = ".searchbattle gen7randombattle"
                    msg = json.dumps({"line": node_command}).encode('UTF-8')
                    sock.send(msg)
                    sock.send(b"\r\n")
                    sock.close()

                    print("Sent command")

                    server_address = '/tmp/node_to_fuji.sock'
                    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    sock.bind(server_address)
                    sock.listen(5)
                    conn, addr = sock.accept()
                    print("Waiting for response")
                    response = conn.recv(1024)
                    if response:
                        response = response.decode('utf-8')
                    sock.close()
                    os.remove('/tmp/node_to_fuji.sock')
                    print("Closing socket")

                    if response:
                        self.battle_room = response
                        self.output_msg(c, "Click here to spectate: http://play.pokemonshowdown.com/" + response, source_user)
                    else:
                        print("No response")
                except:
                    self.output_msg(c, "Error, Showdown component not running", source_user)

        elif line.startswith("!forfeit"):
            # Streamer only
            if source_user.lower() == self.username.lower():
                if len(self.battle_room) > 0:
                    try:
                        server_address = '/tmp/fuji_to_node.sock'
                        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        sock.connect(server_address)
                        node_command = ".leave " + self.battle_room
                        msg = json.dumps({"line": node_command}).encode('UTF-8')
                        sock.send(msg)
                        sock.send(b"\r\n")
                        sock.close()

                        self.output_msg(c, "Forfeited " + self.battle_room, source_user)
                        self.battle_room = ""
                    except:
                        self.output_msg(c, "Error, Showdown component not running", source_user)
                else:
                    self.output_msg(c, "Not currently in a battle", source_user)

        elif line.startswith("!setrun"):
            if len(line.split(" ")) >= 2:
                run_name = line.split(" ", 1)[1].rstrip("\n").rstrip("\r").lower()

                self.config['current_run'] = run_name

                if None == self.config['run_data'].get(run_name):
                    # Run doesn't exist yet, so create it
                    self.config['run_data'][run_name] = {}
                    self.config['run_data'][run_name]['game'] = self.game
                    self.config['run_data'][run_name]['deaths'] = self.deaths
                    self.config['run_data'][run_name]['closed_events'] = {}
                    self.config['run_data'][run_name]['attempt'] = 1

                    # Clear closed_events, since this is a new run.
                    # Old closed_events should already be saved for previous run.
                    self.closed_events = {}
                    self.config['closed_events'] = {}
                else:
                    # Run exists
                    if None != self.config['run_data'][run_name].get('game'):
                        # Get current game from run data, if it exists
                        self.game = self.config['run_data'][run_name].get('game')
                    # Sync run data game, in case it didn't exist
                    self.config['run_data'][run_name]['game'] = self.game
                    # Set config file game
                    self.config['games'][self.username] = self.game

                    if None != self.config['run_data'][run_name].get('deaths'):
                        # Get current deaths from run data, if it exists
                        self.deaths = self.config['run_data'][run_name].get('deaths')
                    # Sync run data deaths, in case it didn't exist
                    self.config['run_data'][run_name]['deaths'] = self.deaths
                    # Set config file deaths
                    self.config['deaths'] = self.deaths

                    if None != self.config['run_data'][run_name].get('closed_events'):
                        # Get current closed_events from run data, if it exists
                        self.closed_events = copy.deepcopy(self.config['run_data'][run_name].get('closed_events'))
                    # Sync run data closed_events, in case it didn't exist
                    self.config['run_data'][run_name]['closed_events'] = copy.deepcopy(self.closed_events)
                    # Set config file closed_events
                    self.config['closed_events'] = copy.deepcopy(self.closed_events)

                self.update_config()

                self.output_msg(c, "Set current run to '" + run_name + "'", source_user)
            else:
                self.output_msg(c, "Format: !setrun <run name>", source_user)

        elif line.startswith("!combo"):
            if self.config.get('highest_combo'):
                self.output_msg(c, "Highest combo: " + str(self.config['highest_combo'][0]) + "x ( " + self.config['highest_combo'][1] + " )", source_user)

        elif line.startswith("!attempt"):
            if None != self.config.get('run_data') and None != self.config.get('current_run'):
                if None != self.config['run_data'][self.config['current_run']].get('attempt'):
                    attempt = self.config['run_data'][self.config['current_run']].get('attempt')
                    self.output_msg(c, "This is attempt #" + str(attempt), source_user)

        elif line.startswith("!swearjar"):
            if len(line.split(" ")) >= 2:
                try:
                    swearjar = int(line.split(" ", 1)[1].rstrip("\n").rstrip("\r"))
                    self.config['swearjar'] = swearjar
                    self.update_config()
                    self.output_msg(c, "Swear jar: " + str(swearjar), source_user)
                except:
                    self.output_msg(c, "Invalid swearjar value", source_user)
            else:
                swearjar = self.config.get('swearjar')
                if swearjar:
                    swearjar += 1
                else:
                    swearjar = 1
                self.config['swearjar'] = swearjar
                self.update_config()
                self.output_msg(c, "Swear jar: " + str(swearjar), source_user)

        elif line.startswith("!define"):
            if len(line.split(" ")) >= 2:
                replacement = line.split(" ", 1)[1].rstrip("\n").rstrip("\r")
            else:
                replacement = 'Nuzlocke'
            success = False
            while not success:
                try:
                    random_title = wikipedia.random()
                    print(random_title)
                    summary = wikipedia.summary(random_title)
                    if '(' in random_title:
                        random_title = random_title[:random_title.index('(')]
                    summary = summary.replace('\n', ' ')
                    if len(summary) > 248:
                        summary = summary[:248]
                    nuzlocke_re = re.compile(random_title, re.IGNORECASE)
                    summary = nuzlocke_re.sub(replacement, summary)
                    self.output_msg(c, summary, source_user)
                    success = True
                except:
                    pass

        elif line.startswith("!hiddenpower"):
            print_usage = True
            tokens = line.split(" ")
            if len(tokens) == 7:
                try:
                    unused, value_a, value_b, value_c, value_e, value_f, value_d = [i for i in tokens]

                    value_u = 1 if int(value_a) % 4 == 2 or int(value_a) % 4 == 3 else 0
                    value_v = 1 if int(value_b) % 4 == 2 or int(value_b) % 4 == 3 else 0
                    value_w = 1 if int(value_c) % 4 == 2 or int(value_c) % 4 == 3 else 0
                    value_x = 1 if int(value_d) % 4 == 2 or int(value_d) % 4 == 3 else 0
                    value_y = 1 if int(value_e) % 4 == 2 or int(value_e) % 4 == 3 else 0
                    value_z = 1 if int(value_f) % 4 == 2 or int(value_f) % 4 == 3 else 0

                    value_a = int(value_a) % 2
                    value_b = int(value_b) % 2
                    value_c = int(value_c) % 2
                    value_d = int(value_d) % 2
                    value_e = int(value_e) % 2
                    value_f = int(value_f) % 2

                    hidden_power_types = ["Fighting", "Flying", "Poison", "Ground", "Rock", "Bug", "Ghost", "Steel", "Fire", "Water", "Grass", "Electric", "Psychic", "Ice", "Dragon", "Dark"]
                    hidden_power_type_index = int( math.floor( ( ( value_a + (2 * value_b) + (4 * value_c) + (8 * value_d) + (16 * value_e) + (32 * value_f) ) * 15 ) / 63 ) )
                    hidden_power_base_power = int( math.floor( ( ( ( value_u + (2 * value_v) + (4 * value_w) + (8 * value_x) + (16 * value_y) + (32 * value_z) ) * 40 ) / 63 ) + 30 ) )
                    self.output_msg(c, "The Pokemon's Hidden Power type is " + hidden_power_types[ hidden_power_type_index ] + ". In Generations 3 to 5, its Base Power is " + str(hidden_power_base_power) + ".", source_user)
                    print_usage = False
                except:
                    pass
            if print_usage:
                self.output_msg(c, "Format: !hiddenpower <HP IV> <Atk IV> <Def IV> <Sp. Atk IV> <Sp. Def IV> <Speed IV>", source_user)

        elif line.startswith("!rating"):
            if len(self.ratings.keys()) == 0:
                try:
                    SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1gTbX1k6rLSf65i9Yv_Ddq2mRLcSFDevNK7AkThD1TBA/gviz/tq?tqx=out:csv&sheet=Tabellenblatt1"
                    response = urllib.request.urlopen(SPREADSHEET_URL).read().decode('UTF-8')
                    skipped_first = False
                    for data_line in response.split("\n"):
                        if False == skipped_first:
                            skipped_first = True
                            continue
                        values = data_line.split(",")
                        pokemon_name = values[1].replace("\"", "").lower()
                        if len(values[2].replace("\"", "")) == 0:
                            pokemon_rating = 0
                        else:
                            pokemon_rating = int(values[2].replace("\"", ""))
                        self.ratings[pokemon_name] = pokemon_rating
                except:
                    self.output_msg(c, "There was a problem retrieving data from the spreadsheet. @pokemodrealtime", source_user)

            if len(line.split(" ")) >= 2:
                name = line.split(" ")[1].rstrip("\n").rstrip("\r").lower()
                name = fix_pokemon_name(name)
            else:
                name = random.choice(list(self.ratings.keys()))

            rating = self.ratings.get(name.lower())
            if rating:
                self.output_msg(c, "PC's rating for '" + name + "' is: " + str(rating), source_user)
            else:
                self.output_msg(c, "Could not find rating for Pokemon '" + name + "'", source_user)

        # NEW COMMANDS GO HERE ^^^

        else:
            if True == self.config['extra_commands_on']:
                if len(line.split(" ")) >= 2:
                    cmd = line.split(" ")[0].rstrip("\n").rstrip("\r").lower()
                else:
                    cmd = line.rstrip("\n").rstrip("\r").lower()

                print(cmd)

                last_output = self.extra_command_cooldown.get(cmd)

                should_output = False
                current_time = datetime.datetime.now()

                if None == last_output:
                    should_output = True
                else:
                    diff = current_time - last_output
                    if diff.seconds >= 30:
                        should_output = True

                if should_output:

                    if self.is_setrun_command(cmd):
                        message = self.get_current_run_data(cmd)
                        if None == message:
                            message = self.config['extra_commands'].get(cmd)
                    else:
                        message = self.config['extra_commands'].get(cmd)

                    if None != message:
                        self.output_msg(c, message, source_user)

                    # Update last output time
                    self.extra_command_cooldown[cmd] = current_time

    def on_dccmsg(self, c, e):
        pass

    def on_dccchat(self, c, e):
        pass

    def do_command(self, e, cmd):
        pass

class DrFujiBotDiscord(discord.Client):
    def __init__(self):
        super().__init__()
        self.user_ids = {}

    async def send_channel_wrapper(self, output):
        await self.send_message(self.get_channel(self.channel_id), output)

    async def send_dm_wrapper(self, output, user):
        user_object = await self.get_user_info(self.user_ids[user])
        if user_object:
            msg = await self.send_message(user_object, output)
        else:
            print('User not found: ' + user)

    def discord_output(self, drfujibot, c, output, user, sleeptime=0):
        if self.whisper:
            asyncio.run_coroutine_threadsafe(self.send_dm_wrapper(output, user), self.loop)
        else:
            asyncio.run_coroutine_threadsafe(self.send_channel_wrapper(output), self.loop)
        print(output)
        with open(self.logname, "a") as f:
            f.write(output + "\n")
            f.flush()

    def setProperties(self, username, permitted_users, moderators, g_whisperMode, game, channel_id, logname, bot_type):
        self.channel_id = channel_id
        self.logname = logname
        self.whisper = g_whisperMode
        self.bot = DrFujiBot(username, permitted_users, moderators, g_whisperMode, game, bot_type)
        self.bot.permissions = False
        self.bot.output_msg = types.MethodType(self.discord_output, self.bot)

    def on_discord_msg(self, line, source_user, source_id):
        self.bot.log_cmd(line, source_user)
        c = None
        self.bot.handle_respects(line, source_user, discord=True)
        self.bot.processCommand(line, c, source_user, source_id)

    def on_discord_direct_message(self, line, source_user, author_id):
        if source_user not in self.user_ids:
            self.user_ids[source_user] = author_id

        if source_user not in self.bot.previous_users:
            c = None
            self.bot.output_msg(c, "I see this may be your first time using DrFujiBot! Feel free to check out the documentation: http://goo.gl/JGG3LT You can also follow me on Twitter! https://twitter.com/drfujibot", source_user)

            self.bot.previous_users[source_user] = 1
            with open('whisper_discord_users.json', 'w') as config_file:
                config_file.write(json.dumps(self.bot.previous_users))

        self.bot.log_cmd(line, source_user)
        c = None
        self.bot.processCommand(line, c, source_user)


g_discordClient = DrFujiBotDiscord()

@g_discordClient.event
async def on_ready():
    print('Connected to Discord')
    await g_discordClient.change_presence(game=discord.Game(name='with genetic memes'))

@g_discordClient.event
async def on_message(message):
    if g_discordClient.whisper:
        if message.channel.is_private:
            line = message.content
            source_user = str(message.author)
            g_discordClient.on_discord_direct_message(line, source_user, message.author.id)
    else:
        if message.channel.id == g_discordClient.channel_id:
            line = message.content
            source_user = message.author.name
            source_id = message.author.id
            g_discordClient.on_discord_msg(line, source_user, source_id)

def main():
    #logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    config = None
    with open(sys.argv[1]) as config_file:
        config = json.load(config_file)

    if config:
        permitted_users = config.get('permitted_users')
        moderators = config.get('moderators')
        username = config.get('streamer')
        logname = username + '.log'
        g_whisperMode = config.get('whisper')
        bot_type = config.get('bot_type')
        channel_id = config.get('channel_id')
        game = None
        if False == g_whisperMode:
            game = config.get('games').get(username)

        if len(username) >= 1:
            print("Welcome to DrFujiBot, %s!" % (username))

            users = []
            for u in permitted_users:
                users.append(u.lower())
            users.insert(0, 'drfujibot')
            users.insert(0, username.lower())
            print("Permitted users are: " + ", ".join(users))
            if None != moderators:
                print("Moderators are: " + ", ".join(moderators))

            random.seed()
            
            with open(username + ".log", "a") as f:
                f.write("BOT STARTUP\n")
                f.flush()

            if bot_type and "discord" == bot_type:
                print('Starting Discord mode')
                g_discordClient.setProperties(username, permitted_users, moderators, g_whisperMode, game, channel_id, logname, bot_type)
                discord_key = get_fuji_config_value('discord_key')
                g_discordClient.run(discord_key)
            else:
                g_bot = DrFujiBot(username, permitted_users, moderators, g_whisperMode, game, bot_type)
                g_bot.start()

if "__main__" == __name__:
    main()
