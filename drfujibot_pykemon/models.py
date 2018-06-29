#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" pykemon.models

This files holds all the class definitions representing resources from PokeAPI.
"""


def buildr(bundle, key):
    " Builds a dict of NAME:URI for each item in the bundle "
    #return {f['name']: f.get('resource_uri') for f in bundle.get(key)}
    pass


class DateTimeObject(object):

    def __init__(self, bundle):
        self.name = bundle.get('name')
        self.resource_uri = bundle.get('resource_uri')
        self.created = bundle.get('created')
        self.modified = bundle.get('modified')


class Pokemon(DateTimeObject):
    """
    This class represents a single Pokemon resource
    """

    def __init__(self, bundle):
        super(Pokemon, self).__init__(bundle)
        self.id = bundle.get('national_id')
        self.abilities = [n.get('ability').get('name') for n in bundle.get('abilities') if not n.get('is_hidden')]
        self.hidden_ability = [n.get('ability').get('name') for n in bundle.get('abilities') if n.get('is_hidden')]
        self.egg_groups = buildr(bundle, 'egg_groups')
        #self.evolutions = {
        #    f['to']: f['resource_uri'] for f in bundle.get('evolutions')}
        self.descriptions = buildr(bundle, 'descriptions')
        self.moves = bundle.get('moves')
        self.types = [n.get('type').get('name') for n in bundle.get('types')]
        self.catch_rate = bundle.get('catch_rate')
        self.species = bundle.get('species')
        self.hp = [s.get('base_stat') for s in bundle.get('stats') if 'hp' in s.get('stat').get('name')][0]
        self.attack = [s.get('base_stat') for s in bundle.get('stats') if 'attack' in s.get('stat').get('name') and 'special' not in s.get('stat').get('name')][0]
        self.defense = [s.get('base_stat') for s in bundle.get('stats') if 'defense' in s.get('stat').get('name') and 'special' not in s.get('stat').get('name')][0]
        self.sp_atk = [s.get('base_stat') for s in bundle.get('stats') if 'special-attack' in s.get('stat').get('name')][0]
        self.sp_def = [s.get('base_stat') for s in bundle.get('stats') if 'special-defense' in s.get('stat').get('name')][0]
        self.speed = [s.get('base_stat') for s in bundle.get('stats') if 'speed' in s.get('stat').get('name')][0]
        self.stats = bundle.get('stats')
        self.total = bundle.get('total')
        self.egg_cycles = bundle.get('egg_cycles')
        self.ev_yield = bundle.get('ev_yield')
        self.exp = bundle.get('exp')
        self.growth_rate = bundle.get('growth_rate')
        self.height = bundle.get('height')
        self.weight = bundle.get('weight')
        self.happiness = bundle.get('happiness')
        self.male_female_ratio = bundle.get('male_female_ratio')
        self.sprites = buildr(bundle, 'sprites')
        self.location_area_encounters_url = bundle.get('location_area_encounters')
        self.base_experience = bundle.get('base_experience')

    def __repr__(self):
        return '<Pokemon - %s>' % self.name.capitalize()


class Move(DateTimeObject):
    """
    This class represents a single Move resource
    """

    def __init__(self, bundle):
        super(Move, self).__init__(bundle)
        self.id = bundle.get('id')
        self.accuracy = bundle.get('accuracy')
        self.category = bundle.get('category')
        self.power = bundle.get('power')
        self.pp = bundle.get('pp')
        self.type = bundle.get('type').get('name')
        self.ailment = bundle.get('meta').get('ailment').get('name')
        self.ailment_chance = bundle.get('meta').get('ailment_chance')
        self.stat_changes = [(s.get('stat').get('name'), s.get('change')) for s in bundle.get('stat_changes')]
        self.effect = bundle.get('effect_changes')
        self.machines = bundle.get('machines')
        self.priority = bundle.get('priority')
        self.damage_class = bundle.get('damage_class').get('name')
        self.stat_chance = bundle.get('meta').get('stat_chance')
        self.flinch_chance = bundle.get('meta').get('flinch_chance')
        self.crit_rate = bundle.get('meta').get('crit_rate')
        self.description = bundle.get('effect_entries')[0].get('short_effect')
        self.past_values = bundle.get('past_values')

    def __repr__(self):
        return '<Move - %s>' % self.name.capitalize()


class Type(DateTimeObject):
    """
    This class represents a single Type Resource
    """

    def __init__(self, bundle):
        super(Type, self).__init__(bundle)
        self.id = bundle.get('id')
        self.name = bundle.get('name')
        #self.ineffective = buildr(bundle, 'ineffective')
        #self.resistance = buildr(bundle, 'resistance')
        #self.super_effective = buildr(bundle, 'super_effective')
        #self.weakness = buildr(bundle, 'weakness')
        self.double_damage_from = bundle.get('damage_relations').get('double_damage_from')
        self.half_damage_from = bundle.get('damage_relations').get('half_damage_from')
        self.no_damage_from = bundle.get('damage_relations').get('no_damage_from')

    def __repr__(self):
        return '<Type - %s>' % self.name.capitalize()


class Ability(DateTimeObject):
    """
    This class represents a single Ability resource
    """

    def __init__(self, bundle):
        super(Ability, self).__init__(bundle)
        self.id = bundle.get('id')
        self.description = bundle.get('description')
        if bundle.get('effect_entries') and len(bundle.get('effect_entries')) >= 1:
            self.effect = bundle.get('effect_entries')[0].get('short_effect')
        else:
            if bundle.get('flavor_text_entries'):
                for fl in bundle.get('flavor_text_entries'):
                    if "en" == fl['language']['name']:
                        self.effect = fl['flavor_text']
                        self.effect = self.effect.replace('\n', ' ')
                        break
        generation = bundle.get('generation').get('name')
        self.gen_num = 0
        if 'generation-i' == generation:
            self.gen_num = 1
        elif 'generation-ii' == generation:
            self.gen_num = 2
        elif 'generation-iii' == generation:
            self.gen_num = 3
        elif 'generation-iv' == generation:
            self.gen_num = 4
        elif 'generation-v' == generation:
            self.gen_num = 5
        elif 'generation-vi' == generation:
            self.gen_num = 6
        elif 'generation-vii' == generation:
            self.gen_num = 7

    def __repr__(self):
        return '<Ability - %s>' % self.name.capitalize()


class Egg(DateTimeObject):
    """
    This class represents a single Egg group resource
    """

    def __init__(self, bundle):
        super(Egg, self).__init__(bundle)
        self.id = bundle.get('id')
        self.pokemon = buildr(bundle, 'pokemon')

    def __repr__(self):
        return '<Egg - %s>' % self.name.capitalize()


class Description(DateTimeObject):
    """
    This class represents a single Description resource
    """

    def __init__(self, bundle):
        super(Description, self).__init__(bundle)
        self.id = bundle.get('id')
        self.description = bundle.get('description')
        self.pokemon = bundle.get('pokemon')
        self.games = buildr(bundle, 'games')

    def __repr__(self):
        return '<Description - %s>' % self.name.capitalize()


class Sprite(DateTimeObject):
    """
    This class represents a single Sprite resource
    """

    def __init__(self, bundle):
        super(Sprite, self).__init__(bundle)
        self.id = bundle.get('id')
        self.pokemon = bundle.get('pokemon')
        self.image = bundle.get('image')

    def __repr__(self):
        return '<Sprite - %s>' % self.name.capitalize()


class Game(DateTimeObject):
    """
    This class represents a single Game resource
    """

    def __init__(self, bundle):
        super(Game, self).__init__(bundle)
        self.id = bundle.get('id')
        self.generation = bundle.get('generation')
        self.release_year = bundle.get('release_year')

    def __repr__(self):
        return '<Game - %s>' % self.name.capitalize()

class Nature(DateTimeObject):
    """
    This class represents a single Nature resource
    """

    def __init__(self, bundle):
        super(Nature, self).__init__(bundle)
        self.id = bundle.get('id')
        inc_stat = bundle.get('increased_stat')
        dec_stat = bundle.get('decreased_stat')
        if inc_stat:
            self.inc_stat = inc_stat.get('name')
        else:
            self.inc_stat = 'None'
        if dec_stat:
            self.dec_stat = dec_stat.get('name')
        else:
            self.dec_stat = 'None'

    def __repr__(self):
        return '<Nature - %s>' % self.name.capitalize()

class Item(DateTimeObject):
    """
    This class represents a single Item resource
    """

    def __init__(self, bundle):
        super(Item, self).__init__(bundle)
        self.id = bundle.get('id')
        self.description = bundle.get('effect_entries')[0].get('short_effect')
        self.held_by_pokemon = bundle.get('held_by_pokemon')
        self.value = int(bundle.get('cost') / 2)

    def __repr__(self):
        return '<Item - %s>' % self.name.capitalize()

class Location(DateTimeObject):
    """
    This class represents a single Location resource
    """

    def __init__(self, bundle):
        super(Location, self).__init__(bundle)
        self.id = bundle.get('id')
        self.areas = bundle.get('areas')
        self.region = bundle.get('region').get('name')
        self.name = bundle.get('name')

    def __repr__(self):
        return '<Location - %s>' % self.name.capitalize()

class LocationArea(DateTimeObject):
    """
    This class represents a single LocationArea resource
    """

    def __init__(self, bundle):
        super(LocationArea, self).__init__(bundle)
        self.id = bundle.get('id')
        self.pokemon_encounters = bundle.get('pokemon_encounters')
        self.name = bundle.get('name')

    def __repr__(self):
        return '<LocationArea - %s>' % self.name.capitalize()

class LocationAreaEncounters():
    """
    This class represents a single LocationAreaEncounters resource
    """

    def __init__(self, bundle):
        self.location_list = bundle

    def __repr__(self):
        return '<LocationAreaEncounters - %s>' % self.name.capitalize()

class PokemonSpecies():
    """
    This class represents a single PokemonSpecies resource
    """

    def __init__(self, bundle):
        self.evolution_chain_url = bundle.get('evolution_chain').get('url')
        self.varieties = bundle.get('varieties')
        self.egg_groups = bundle.get('egg_groups')
        self.is_baby = bundle.get('is_baby')
        self.gender_rate = bundle.get('gender_rate')

    def __repr__(self):
        return '<PokemonSpecies>'

class EvolutionChain():
    """
    This class represents a single EvolutionChain resource
    """

    def __init__(self, bundle):
        self.chain = bundle.get('chain')

    def __repr__(self):
        return '<EvolutionChain>'

class Characteristic():
    """
    This class represents a single Characteristic resource
    """

    def __init__(self, bundle):
        for d in bundle.get('descriptions'):
            if d.get('language').get('name') == 'en':
                self.description = d.get('description').lower()
        self.highest_stat = bundle.get('highest_stat').get('name')
        self.possible_values = bundle.get('possible_values')

    def __repr__(self):
        return '<Characteristic>'
