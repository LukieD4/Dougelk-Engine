# Dougelk Engine

Dougelk Engine is a 2D game engine written in Python. It was used to build retro-style games such as Space Invaders-inspired projects.

## Framework

The engine was initially derived from an earlier project:
- [SpaceInvadies](https://github.com/LukieD4/SpaceInvadies)

It was later adapted and expanded from:
- [PyPongOnline](https://github.com/LukieD4/PyPongOnline)

## Get started:

`py_app.py` lets you edit basic parameters.  
`py_client.py` hosts the main functionality of gameplay.  
`<Class: Sprite>.team` is used alot to process behaviour.  

`py_sprites.py` allows for the creation of custom entities.
`<Class: Sprite>.ticker()` increments per frame to provide tracking and movement throughout.  
  
`<Game>.exe` will unpack all assets to %TEMP%/< gamename> when ran. 


`assets/stages/spritemaker.py` to build Stages; a level maker.

## Credits

Created with credit to LukieD4 on GitHub.