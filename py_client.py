from __future__ import annotations

import pygame, time, os

from py_prompt import dlg
dlg.show()
from py_app import app # // Initialise first

import py_sprites

from py_stager import Stager
from py_config import config
from py_input import inputManager
from py_ui_sprites import render_text
from py_soundmixer import soundMixer
from py_resource import resource


from hashlib import sha256
from socket import gethostname



class ClientGame:

    def __init__(self):
    
        self.__BUILD_VER = f"{app.build_version_solve()}"

        # --- entities ---
        self.entities = {
            "actors": [],
            "ui": [],
            "decor": [],
            "particles": [],
            "__internal_mouse__": [],
            "__debug__": [],
        }
        # blacklisted teams are ignored in entity processes
        self.ENTITIES_BLACKLIST = {"__internal_mouse__"}

        # initialise pygame
        dlg.close()
        
        self.pygame_init = pygame.init()
        display_info = pygame.display.Info()
        self.desktop_res_x, self.desktop_res_y = display_info.current_w, display_info.current_h

        self.screen = pygame.display.set_mode(
            (config.res_x, config.res_y),
            pygame.DOUBLEBUF | pygame.HWSURFACE
        )

        self.clock = pygame.time.Clock()
        self.window_current_scale = config.resolution_scale
        self.window_best_scale = config.calculate_scale_against_pc_resolution(desktop_res_x=self.desktop_res_x, desktop_res_y=self.desktop_res_y)

        # call set_window_icon() in Sprite
        py_sprites.set_window_icon()

        # Set stage
        self.stager = Stager(self.screen,self.entities)

        # --- user unique id ---
        self.client_id_hash = sha256(gethostname().encode()).hexdigest()


        # --- mode ---
        self.mode = None
        self.__mode_old = None
        self._mode_previous = None # updated via -> `def newMode():`
        self.newMode("menu-init")

        # --- input block ---
        self.input_epoch = 0
        self.input_cooldown = .09

        # Main loop (while running:)
        self.debug = True
        # self.debug = False
        self.debug_input_epoch = 0
        self.debug_overlay, self.debug_whole_overlay = False, False
        self.main_loop_frame_time = 0
        self.main_loop_frame_count = 0
        self.main_loop_fps_last_epoch = time.time()
        self.main_loop_fps_tracking = 0
        self.main_loop_fps = 0
        self.__fps_impact = 0

        # Caching
        self.__cache_frame__ = -1
        self.__entitiesAllReturn_cache = []
        self.__entitiesFilterOutByTeam_cache__ = {}
        self.__entitiesBlacklist_cache__ = {}
        self._entity_membership_sets = {k: set() for k in self.entities.keys()}
        self.__client_ui_cached_text = ""
        self.__debug_ui_cached_text = ""


        # Main Menu
        self.main_menu_tick = 0
        self.main_menu_invoke_resolution_changed = False

        # Reserve values below, and Load game settings
        self._game_settings_window_scale = None
        self._game_settings_volume_multiplier = 1

        self.loadGameSettings()

        

        # Mode dispatch
        self.update_methods = {
            # menus
            "menu-init": self.initMainMenu,
            "menu": self.updateMainMenu
        }


    # ========================================================
    # Menu Actions
    #region Actions

    def action_screen(self, scale_increment=1):
        self.rescaleWindow(scale_increment=scale_increment)
        self.saveGameSettings()
    
    def action_quit(self):
        # errorless exit because I think I'm ocd
        try:
            quit()
        finally:
            exit()

    # ========================================================
    # Main Menu
    #region MainMenu

    def initMainMenu(self):
        self.main_menu_tick = 0
        self.newMode("menu")
        self.entities_delete_all()
        self._invalidate_ui_caches()

        self.main_menu_dog_clicks = 0

        soundMixer.stop("select")
        soundMixer.play("select", "assets/audio/select.ogg", vol_mult=self._game_settings_volume_multiplier*.1, loops=0)


    def updateMainMenu(self):
        from random import randint

        self.main_menu_tick += 1
        keys = pygame.key.get_pressed()
        now = time.time()

        # -- First frame setup --
        if self.main_menu_tick == 1 or self.main_menu_invoke_resolution_changed == True:
            self.main_menu_invoke_resolution_changed = False

            # Load stage and entities
            self.entities = self.entities_append(self.stager.load_stage(resource.resource_path("assets/stages/example.stage")))
            
            pass
        
        
        # --- Gameplay ---
        entity60: py_sprites.Sprite # // entity60 just means it checks every 60fps
        for entity60 in self.entities["actors"]:
            entity60.ticker()
            entity60.task()

            if entity60.mark_mouse_clicked:
                entity60.task_upon_click()
                entity60.mark_mouse_clicked = False
                self.main_menu_dog_clicks += 1
                soundMixer.play("bark","assets/audio/woof.mp3")
            
            if hasattr(entity60, 'mark_to_drop') and entity60.mark_to_drop:
                self.entities["actors"].append(
                    py_sprites.Browning().summon(
                        target_col=entity60.pos_col,
                        target_row=entity60.pos_row,
                        screen=self.screen
                    )
                )
                entity60.mark_to_drop = False
                soundMixer.play("drop", f"assets/audio/immature{randint(1, 2)}.mp3", vol_mult=self._game_settings_volume_multiplier*.1)
        

        if self.main_menu_dog_clicks > 0:
            self.entities["actors"].append(py_sprites.Dog().summon(screen=self.screen,target_col=10,target_row=10))
            self.main_menu_dog_clicks = 0

        # -- Apply data
        pass

        # -- Rescale
        can_process_action = time.time() >= self.input_epoch + self.input_cooldown
        if can_process_action:
            
            if inputManager.get_action("upscale", keys):
                self.input_epoch = now
                self.action_screen(scale_increment=1)
            if inputManager.get_action("downscale", keys):
                self.input_epoch = now
                self.action_screen(scale_increment=-1)

    
        # -- Render UI
        onscreen_text = f"""`````~YELLOW{app.app_name} v{self.__BUILD_VER} ~WHITEby ~CYAN{', '.join(app.app_authors)}
``~#Press F1/F2 to toggle debug UI
``~#Press F3 to unlock/lock fps
``~#Press F4 to set custom fps
``~#Press F5 to set custom impact ms
``~GREENPress IO to rescale window: {config.resolution_scale}x ~#
````TRY THIS!
``Connect a controller!
``~(ltsu) ~(ltsr) ~(ltsd) ~(ltsl) ~(rtsu) ~(rtsr) ~(rtsd) ~(rtsl)
`~(return) ~(r) ~(t) ~(u)
"""
        
        
        self.__client_ui_cached_text = self._render_ui_and_prioritise_cache(onscreen_text,self.__client_ui_cached_text)
        pass

    # ========================================================
    # Main Loop
    #region Mainloop
    def mainloop(self):
        running = True

        # create the window
        self.screen = pygame.display.set_mode((config.res_x, config.res_y))

        # update
        app.window_always_on_top(enabled=app.WINDOWS_ALWAYS_ON_TOP) #rea

        # Hide mouse cursor
        pygame.mouse.set_visible(False)

        # load UI setting
        saveGameSettings = os.path.exists(app.filename_gamesettings)
        if not saveGameSettings:
            config.redefine(scale=config.calculate_best_fit_scale(self.desktop_res_x, self.desktop_res_y))
            self.saveGameSettings()

        # Main loop
        while running:

            time.sleep(self.__fps_impact)

            # DEBUG USE ONLY
            if self.debug:
                # --- Calculate fps --- #
                self.main_loop_fps_tracking += 1
                now = time.time()

                if now - self.main_loop_fps_last_epoch >= 1.0:
                    self.main_loop_fps = self.main_loop_fps_tracking
                    self.main_loop_fps_tracking = 0
                    self.main_loop_fps_last_epoch = now

                keys = pygame.key.get_pressed()

                if now >= self.debug_input_epoch:

                    if inputManager.get_debug_action("toggle_whole_ui", keys):
                        self.debug_whole_overlay = not self.debug_whole_overlay
                    if inputManager.get_debug_action("toggle_overlay", keys):
                        self.debug_overlay = not self.debug_overlay
                    if inputManager.get_debug_action("unlock_fps", keys):
                        redefine_task = config.redefine(framerate=9999) if config.frame_rate != 9999 else config.redefine(framerate=60)
                    if inputManager.get_debug_action("custom_fps", keys):
                        config.redefine(framerate=float(input("Enter custom fps (this field is not sanitised):")))
                    if inputManager.get_debug_action("custom_fps_impact", keys):
                        self.__fps_impact = float(input("Enter custom fps impact float (delay) (this field is not sanitised):"))
                if any(keys) > 0:
                    self.debug_input_epoch = now+.3
                

                # If UI rendering is on
                fps_final_text = []
                if not self.debug_whole_overlay and not self.debug_overlay:
                    self.entities["__debug__"].clear()
                    
                else:
                    
                    if self.debug_overlay:
                        fps_final_text = [f"~YELLOWFPS _ {self.main_loop_fps}"]

                    if self.debug_whole_overlay:
                        fps_percent = (self.main_loop_fps / config.frame_rate) * 100
                        fps_final_text.append(
                            f"~YELLOWFPS _ {self.main_loop_fps} ({fps_percent:.0f}P) ({self.main_loop_frame_time}ms)`"
                            f"FPS UNLOCKED _ {config.frame_rate != 60}`"
                            f"VOL _ {config.volume_multiplier}`"

                            f"BUILDVER _ {self.__BUILD_VER}`"
                        )


                    fps_final_text = fps_final_text[0]
                    if fps_final_text != self.__debug_ui_cached_text:
                        self.__debug_ui_cached_text = fps_final_text
                        self.entities["__debug__"] = render_text(fps_final_text,justification="left")

                
                    
            # Increment frame counter
            self.main_loop_frame_count += 1

            # If rescale is detected, update the window
            if self.window_current_scale != config.resolution_scale:
                self.window_current_scale = config.resolution_scale
                self.screen = pygame.display.set_mode((config.res_x, config.res_y))
                self.main_menu_invoke_resolution_changed = True
                self.entities["__internal_mouse__"].clear()
                app.window_always_on_top(enabled=app.WINDOWS_ALWAYS_ON_TOP) #reapplies to the new game window
                self._invalidate_ui_caches()
            
            # If 'mode' changed, update inputManager
            if self.__mode_old != self.mode:
                inputManager.mode = self.mode
                inputManager.debug = self.debug
                self.__mode_old = self.mode

            # Mode dispatch
            self.update_methods.get(self.mode, lambda: print(f"mainloop : ⚠️  Warning: No update method implemented for self.mode: {self.mode}"))()

            self.screen.fill((0, 0, 0))
            for entity in self.entities_return() + self.entities["__internal_mouse__"]:
                entity.draw(self.screen)
                if entity.mark_for_deletion:
                    self.entities[entity.team].remove(entity)

            pygame.display.flip()
            self.clock.tick(config.frame_rate)
            if self.main_loop_frame_count % 60 == 0:
                self.main_loop_frame_time = self.clock.get_time()

            for event in pygame.event.get():
                # --- Track game quit ---
                if event.type == pygame.QUIT:
                    running = False

                # --- Track user's chosen input method ---
                internal = self.entities["__internal_mouse__"]
                current_method_of_input, previous_method_of_input = inputManager.resolve_active_input_method(event=event)
                if current_method_of_input == "Default":
                    
                    # Ensure exactly one Cursor instance exists
                    if not internal:
                        cursor: py_sprites.Cursor
                        cursor = inputManager.initialise_cursor(py_sprites.Cursor(),screen=self.screen)
                        internal.append(cursor)

                    # Update cursor position
                    mouse_x, mouse_y = pygame.mouse.get_pos()

                    # If mouse is outside window, hide cursor
                    deadzone = 0 # eh it's useless, might keep incase of future incompatibility issues
                    if (
                        mouse_x <= deadzone or
                        mouse_x >= config.res_x - deadzone or
                        mouse_y <= deadzone or
                        mouse_y >= config.res_y - deadzone
                    ):
                        self.entities["__internal_mouse__"].clear()
                        continue
                        
                    # print(f"mainloop: mouse_x, mouse_y : {mouse_x}, {mouse_y}")
                    cursor.move_position(dx=mouse_x,dy=mouse_y,set_position=True)
                else:
                    self.entities["__internal_mouse__"].clear()

                # -- Should clear cache to update ui?
                if current_method_of_input != previous_method_of_input:
                    self._invalidate_ui_caches()


                # --- Track mouse clicks ---
                cursor = internal[0] if internal else None
                cursor_state = inputManager.update_mouse_input_state(event=event)
                if cursor and cursor_state == pygame.MOUSEBUTTONDOWN:
                    entity: py_sprites.Sprite
                    for entity in self.entities_return():
                        if (entity.pos_col,entity.pos_row) == (cursor.pos_col,cursor.pos_row):
                            print("match!")
                            if hasattr(entity,"mark_mouse_clicked"):
                                entity.mark_mouse_clicked = True

                    

        pygame.quit()
        # profiler.stop()
        # profiler.open_in_browser()

    # ========================================================
    # Utilities
    #region Utilities
    def newMode(self,new_mode):
        if new_mode != self.mode:
            self._mode_previous = self.mode
            self.mode = new_mode
        else:
            print("py_client : newMode : mode already is", self.mode)

    def rescaleWindow(self, scale_increment=1):

        target_scale = config.calculate_scale_against_pc_resolution(scale_increment, self.desktop_res_x, self.desktop_res_y)
        config.redefine(scale=target_scale)

        # game
        self._game_settings_window_scale = target_scale

        # clear caches
        self._invalidate_ui_caches()
        self._invalidate_entity_caches()

        # apply the scalings to all entities
        for entity in self.entities_return():
            entity.rescale()

        return target_scale
    
    

    def entities_append(self, new_entities):
        """
        Append new_entities: dict[team] -> list[entity].
        Invalidate caches only if something actually changed.
        """
        changed = False

        for team, items in new_entities.items():
            if team in self.ENTITIES_BLACKLIST:
                continue

            if team not in self.entities:
                # keep current behavior: ignore unknown teams
                continue

            target_list = self.entities[team]
            # Fast path: if many items, avoid O(n^2) by using a set
            membership = set(target_list)
            for ent in items:
                if ent not in membership:
                    target_list.append(ent)
                    membership.add(ent)
                    changed = True

            # optional: keep membership sets in sync
            if hasattr(self, "_entity_membership_sets"):
                self._entity_membership_sets[team] = membership

        if changed:
            self._invalidate_entity_caches()

        return self.entities



    def entities_return(self):
        """Flattened list of all entities excluding BLACKLIST teams, cached per frame."""
        if self.__cache_frame__ != self.main_loop_frame_count:
            self.__cache_frame__ = self.main_loop_frame_count
            self.__entitiesAllReturn_cache = [
                e
                for key, lst in self.entities.items()
                if key not in self.ENTITIES_BLACKLIST
                for e in lst
            ]
            # reset per-frame filter caches
            self.__entitiesFilterOutByTeam_cache__ = {}
            self.__entitiesBlacklist_cache__ = {}

        return self.__entitiesAllReturn_cache



    def entities_delete_all(self):
        """Clear all non-blacklisted teams while preserving blacklisted lists."""
        for k in list(self.entities.keys()):
            if k not in self.ENTITIES_BLACKLIST:
                self.entities[k].clear()

        self._invalidate_entity_caches()
        return self.entities



    def entities_filter_by_team(self, entity_list, team):
        key = (id(entity_list), team.lower())

        if key in self.__entitiesFilterOutByTeam_cache__:
            return self.__entitiesFilterOutByTeam_cache__[key]

        result = [e for e in entity_list if e.team == team.lower()]
        self.__entitiesFilterOutByTeam_cache__[key] = result
        return result


    def entities_blacklist(self, entity_list):
        """Return entities not in BLACKLIST teams, cached per-frame by list identity."""
        key = id(entity_list)
        if key in self.__entitiesBlacklist_cache__:
            return self.__entitiesBlacklist_cache__[key]

        result = [e for e in entity_list if getattr(e, "team", "") not in self.ENTITIES_BLACKLIST]
        self.__entitiesBlacklist_cache__[key] = result
        return result

    


    def _render_ui_and_prioritise_cache(self, set_self_entities_ui_text, self_variable, justification: str | None = "centre"):
        if set_self_entities_ui_text != self_variable:
            self.entities["ui"] = render_text(set_self_entities_ui_text,justification=justification)
        return set_self_entities_ui_text

    def _invalidate_entity_caches(self):
        self.__cache_frame__ = -1
        self.__entitiesFilterOutByTeam_cache__.clear()
        self.__entitiesBlacklist_cache__.clear()
        self.__entitiesAllReturn_cache = []
    
    def _invalidate_ui_caches(self):
        self.__debug_ui_cached_text = None
        self.__client_ui_cached_text = None
        print("CLEARED UI CACHE! (Things should appear back on the screen now!)")
    



    # -- Collision Detection
    def check_collision(self, rect_a, rect_b):
        if not rect_a or not rect_b:
            return False
        return rect_a.colliderect(rect_b)
    
    # -- File game setting
    def saveGameSettings(self):

        data = {
            "window_scale": self._game_settings_window_scale,
            "volume": self._game_settings_volume_multiplier
        }

        with open(app.filename_gamesettings, "w") as f:
            for key, value in data.items():
                f.write(f"{key}={value}\n")

    
    def loadGameSettings(self):
        try:
            with open(app.filename_gamesettings, "r") as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    parameter, value = line.split("=")[0], line.split("=")[1]

                    match parameter:
                        case "window_scale":
                            if str(None) in value:
                                value = self.window_best_scale
                                self._game_settings_window_scale = value
                                config.redefine(scale=value)
                                continue
                            else:
                                value = int(value)
                                config.redefine(scale=value)
                                self._game_settings_window_scale = value
                                continue
                        case "volume":
                            config.redefine(volume=float(value))
                            self._game_settings_volume_multiplier = config.volume_multiplier
                            continue


        except Exception as e:
            print(f"loadGameSettings : settings failed to load, making a new file instead) : {e}")
            self.saveGameSettings()
            self.loadGameSettings()


    # ========================================================
    # UI Rendering
    #region UI

    def reserved(self): # // placeholder
        pass



# Entry
if __name__ == "__main__":

    # run the main game
    ClientGame().mainloop()
