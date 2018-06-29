#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" pykemon.api

User interaction with this package is done through this file.
"""

import drfujibot_pykemon.request

from drfujibot_pykemon.request import CHOICES

def get(**kwargs):
    """
    Make a request to the PokeAPI server and return the requested resource

    Resource choices:

    pokedex_id
    pokemon
    pokemon_id
    move_id
    ability_id
    type_id
    egg_id
    description_id
    sprite_id
    game_id
    nature
    item

    """
    if len(kwargs.keys()) > 2:
        raise ValueError('Too many arguments. Only pass 1 argument')

    if list(kwargs.keys())[0] in CHOICES:
        return drfujibot_pykemon.request.make_request(kwargs)

    else:
        raise ValueError('An invalid argument was passed')
