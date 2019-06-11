#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" pykemon.request

This is the request factory for pykemon
All API calls made to the PokeAPI website go from here.
"""
import requests
import requests_cache
import simplejson
from simplejson import JSONDecodeError

from drfujibot_pykemon.exceptions import ResourceNotFoundError
from drfujibot_pykemon.models import (
    Ability, Characteristic, Description, Egg, EvolutionChain, Game, Item,
    Location, LocationArea, LocationAreaEncounters, Move, Nature, Pokemon,
    PokemonSpecies, Sprite, Type)

BASE_URI = 'https://pokeapi.co/api/v2'

CHOICES = [
    'pokedex', 'pokedex_id', 'pokemon', 'pokemon_id', 'move', 'move_id',
    'ability', 'ability_id', 'type', 'type_id', 'egg', 'egg_id', 'description',
    'description_id', 'sprite', 'sprite_id', 'game', 'game_id', 'nature',
    'item', 'location', 'area', 'area_id', 'encounters', 'species',
    'evo_chain', 'characteristic', 'url'
]

CLASSES = {
    'pokemon': Pokemon,
    'move': Move,
    'type': Type,
    'ability': Ability,
    'egg': Egg,
    'description': Description,
    'sprite': Sprite,
    'game': Game,
    'nature': Nature,
    'item': Item,
    'location': Location,
    'area': LocationArea,
    'encounters': LocationAreaEncounters,
    'species': PokemonSpecies,
    'evo_chain': EvolutionChain,
    'characteristic': Characteristic
}


def _request(uri, url):
    """
    Just a wrapper around the request.get() function
    """

    one_year = 60 * 60 * 24 * 30 * 12

    cache_name = 'pokeapi_cache_3'

    requests_cache.install_cache(
        cache_name, backend='sqlite', expire_after=one_year)

    r = requests.get(uri)

    if r.status_code == 200:
        return _to_json(r.text)
    else:
        raise ResourceNotFoundError(
            'API responded with %s error' % str(r.status_code))


def _to_json(data):
    try:
        content = simplejson.loads(data)
        return content
    except JSONDecodeError:
        raise JSONDecodeError('Error decoding data', data, 0)


def _compose(choice, url):
    """
    Figure out exactly what resource we're requesting and return the correct
    class.
    """
    nchoice = list(choice.keys())[0]
    id = list(choice.values())[0]

    if '_id' in nchoice:
        nchoice = nchoice[:-3]
    nchoice_copy = ''
    if 'area' == nchoice:
        nchoice_copy = 'location-area'
    elif 'species' == nchoice:
        nchoice_copy = 'pokemon-species'
    elif 'evo_chain' == nchoice:
        nchoice_copy = 'evolution-chain'
    else:
        nchoice_copy = nchoice
    return ('/'.join([url, nchoice_copy, str(id), '']), nchoice)


def _compose_encounters(choice, url):
    """
    Figure out exactly what resource we're requesting and return the correct
    class.
    """
    pokemon_id = list(choice.values())[0]
    return ('/'.join([url, 'pokemon', pokemon_id, 'encounters']), 'encounters')


def make_request(choice):
    """
    The entry point from pykemon.api.
    Call _request and _compose to figure out the resource / class
    and return the correct constructed object
    """
    url = choice.get('url')
    if not url:
        url = BASE_URI
    else:
        if len(url) == 0:
            url = BASE_URI
        del choice['url']

    if 'encounters' == list(choice.keys())[0]:
        uri, nchoice = _compose_encounters(choice, url)
    else:
        uri, nchoice = _compose(choice, url)
    data = _request(uri, url)

    resource = CLASSES[nchoice]
    return resource(data)
