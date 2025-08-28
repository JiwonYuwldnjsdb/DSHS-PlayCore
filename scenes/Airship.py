import pygame
import random
import sys
import math

from collections import deque
from localLibraries.PlayCoreLibraries import ScreenObject, fade_out, blit_fps

class AirshipMainScreen(ScreenObject):
    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)

        self.show_fps = show_fps

        self.h1 = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", int(height / 15))
        self.h1_size = self.h1.size("")

        self.p = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", int(height / 30))
        self.p_size = self.p.size("")

        self.psmall = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", int(height / 45))
        self.psmall_size = self.psmall.size("")

        ### file data ###
        # 0: highest score

        # Reading from a text file
        with open("data/Airship/playdata/saves.txt", "r") as file:
            file_data = file.read().split('\n')

        self.best_score = int(file_data[0])
        self.curr_score = 0

        ### Colors ###
        self.white = (255, 255, 255)
        self.gray = (51, 58, 69)
        self.dark_gray = (42, 48, 59)
        self.blue = (90, 210, 255)
        self.blue_ = (90, 140, 170)
        self.blue__ = (23, 38, 53)
        self.blue_shadow = (23, 48, 65)
        self.dark_blue = (10, 17, 30)
        self.darker_blue = (50, 56, 67)
        self.trail_blue = (90, 140, 170)
        self.trail_blue_shadow = (23, 38, 55)
        self.red = (190, 40, 100)
        self.red_particle = (171, 35, 79)
        self.text_color = (75, 75, 75)
        self.title_color = (75, 75, 75)

        self.main_color = (20, 20, 30)
        self.side_color = (50, 50, 50)
        self.base_color = (80, 80, 120)

        self.background = Background(self.width, self.height, 20, (self.width // 2, self.height // 2), 1, self.main_color, self.side_color, self.base_color)
        self.background.change_areas()
        self.airship = Airship(self.width, self.height, 5, 3, 200)
        self.walls = []
        self.wall_cooldown = 0
        self.background_cooldown = 30
        self.wall_make_cycle = 3
        self.speed_constant = 3000
        self.screen_shake = ScreenShake()
        self.after_crash = 0
        self.after_crash_wait_time = 90

        self.signalLight = SignalLight((self.background.background_line[0][1], self.background.background_line[0][-2]), [self.width / 5, self.width / 16],
                                       (70, 70, 70), (60, 60, 60), (80, 150, 80), 0.05, 0.1)
        self.time = 0

        self.surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.surface_alpha = 180
        self.surface_delta_alpha = 4
        self.surface_max_alpha = 180
        self.surface_cooldown = 0
        self.surface.fill((0, 0, 0, self.surface_alpha))

        self.level = 1


        self.menu_state = 0


        self.scrollx = 0
        self.scrolly = 0

        self.circle_effects = []

        self.trail = deque()

        self.shake_tick = 0
        self.score_cooldown = 0


        ### Menu Variables ###
        self.main_menu_scroll = height * 2 / 5

        self.texts = {
            'game_over': [self.h1.render("Game Over", True, self.white),
                          self.h1.size("Game Over")[0] / 2],

            'restart': [self.p.render("Click to Restart", True, self.white),
                        self.p.size("Click to Restart")[0] / 2],

            'title': [self.h1.render("Airship", True, self.white),
                      self.h1.size("Airship")[0] / 2],

            'start': [self.p.render("Click to Start", True, self.white),
                      self.p.size("Click to Start")[0]],

            'quit': [self.p.render("Hold to Quit", True, self.white)],

            'credit1': [self.psmall.render("Original Game by blob8108", True, self.white),
                        self.psmall.size("Original Game by blob8108")[0] / 2],

            'credit2': [self.psmall.render("Remasterd by Yuseung Jang", True, self.white),
                        self.psmall.size("Remasterd by Yuseung Jang")[0] / 2]
        }
        self.high_score = 0 #선언만 하는 것임
        self.texts_index = ['game_over', 'restart', 'title', 'start', 'quit', 'credit1', 'credit2']

    def reset(self):
        self.time = 0
        self.background = Background(self.width, self.height, 20, (self.width // 2, self.height // 2), 1,
                                     self.main_color, self.side_color, self.base_color)
        self.background.change_areas()
        self.airship = Airship(self.width, self.height, 5, 3, 200)
        self.walls = []
        self.wall_cooldown = 0
        self.background_cooldown = 30
        self.wall_make_cycle = 3
        self.speed_constant = 3000
        self.screen_shake = ScreenShake()
        self.after_crash = 0
        self.after_crash_wait_time = 90

        self.signalLight = SignalLight((self.background.background_line[0][1], self.background.background_line[0][-2]),
                                       [self.width / 5, self.width / 16],
                                       (80, 80, 80), (60, 60, 60), (80, 150, 80), 0.05, 0.1)


        self.circle_effects.clear()

        self.trail.clear()

        self.curr_score = 0

        self.shake_tick = 0
        self.score_cooldown = 0

    def update_screen_shake(self):
        """ 화면 흔들림 적용 """
        self.screen_shake.update()
        return self.screen_shake.offset_x, self.screen_shake.offset_y

    def blit_game_over(self, screen):
        self.main_menu_scroll += (0 - self.main_menu_scroll) * 0.075
        if self.main_menu_scroll < 0.1:
            self.main_menu_scroll = 0

        # game over
        screen.blit(self.texts['game_over'][0], (self.width / 2 - self.texts['game_over'][1],
                                                 self.height / 5 * 2 - self.h1_size[1] - self.main_menu_scroll))

        # score
        res_score = self.h1.render(f"{self.curr_score}", True, self.white)
        screen.blit(res_score, (self.width / 2 - self.h1.size(f"{self.curr_score}")[0] / 2,
                                self.height / 2 - self.h1_size[1] / 2 - self.main_menu_scroll / 2))

        # restart game
        screen.blit(self.texts['restart'][0], (self.width / 2 - self.texts['restart'][1],
                                               self.height / 5 * 3 + self.main_menu_scroll))

    def blit_menu(self, screen):

        self.main_menu_scroll = 0

        # title
        screen.blit(self.texts['title'][0], (self.width / 2 - self.texts['title'][1],
                                             self.height / 5.5 * 2 - self.h1_size[1] - self.main_menu_scroll))

        # high score
        high_score = self.p.render(f"Best {self.best_score}", True, self.white)
        screen.blit(high_score, (self.width / 2 - self.p.size(f"Best {self.best_score}")[0] / 2,
                                 self.height / 5.5 * 2 + self.main_menu_scroll))

        # start game
        screen.blit(self.texts['start'][0], (self.width / 7 * 3 - self.texts['start'][1],
                                             self.height / 2 + self.p_size[1] + self.psmall_size[
                                                 1] / 2 + self.main_menu_scroll))

        # quit game
        screen.blit(self.texts['quit'][0], (self.width / 7 * 4,
                                            self.height / 2 + self.p_size[1] + self.psmall_size[
                                                1] / 2 + self.main_menu_scroll))

        # credits
        screen.blit(self.texts['credit1'][0], (self.width / 2 - self.texts['credit1'][1],
                                               self.height / 5 * 3.4 + self.p_size[1] * 3 + self.main_menu_scroll))

        screen.blit(self.texts['credit2'][0], (self.width / 2 - self.texts['credit2'][1],
                                               self.height / 5 * 3.4 + self.p_size[1] * 3 + self.psmall_size[
                                                   1] + self.main_menu_scroll))

    def blit_ingame(self, screen):
        score = self.h1.render(f"{self.curr_score}", True, self.white)
        screen.blit(score, (self.width / 2 - self.h1.size(f"{self.curr_score}")[0] / 2, self.height / 5 - self.h1_size[1] / 2))

    def load_screen(self, target):
        if target == 0:
            self.best_score = max(self.best_score, self.curr_score)
            # Writing to a text file
            with open("data/airship/playdata/saves.txt", "w") as file:
                file.write(f"{self.best_score}\n")

            self.reset()
            self.state = 0

            self.main_menu_scroll = self.height * 2 / 5

        elif target == 1:
            self.state = 0.5
            self.log = 'Start'

        elif target == 2:
            ### Game Over ###
            self.state = 2
            self.shake_tick = 25 * self.height / 1280

            self.last_scrollx = self.scrollx
            self.last_scrolly = self.scrolly
            self.prev_scrolly = self.last_scrollx
            self.adjed_scrolly = min(0, self.scrolly + 1000)

            self.main_menu_scroll = self.height * 2 / 5

    def loop(self, screen):
        clock = pygame.time.Clock()
        self.running = True

        self.state = 0
        self.log = None

        mouse_down = False
        mouse_down_frames = 0
        mouse_up_frames = 0

        """
        0: main menu
        0.5: game start
        1: gameplay
        2: gameover
        """

        while self.running:
            screen.fill(self.main_color)
            if self.state == 0:
                self.background.change_areas()
                self.background.make_stripe(3, self.speed_constant, self.background_cooldown)
                self.background.move_stripe()
                self.background.draw(screen)

                self.signalLight.draw(screen)

                self.airship.draw(screen, 0, 0)

                screen.blit(self.surface, (0, 0))

            dt_ms = clock.tick(60)

            dt = dt_ms / 1000.0


            if mouse_down:
                mouse_down_frames += 1
                if mouse_down_frames >= 60:
                    pygame.draw.arc(screen, (255, 255, 255),
                                    (pygame.mouse.get_pos()[0] - self.height / 60,
                                     pygame.mouse.get_pos()[1] - self.height / 60, self.height / 60 * 2, self.height / 60 * 2),
                                    math.radians(0), math.radians(min(mouse_down_frames * 2 - 120, 360)), max(int(self.height/200), 1))
            else:
                mouse_up_frames += 1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    curr_pos = pygame.mouse.get_pos()
                    self.circle_effects.append(CircleEffect(curr_pos[0], curr_pos[1], 1, self.height // 15, self.white, self.height / 200))
                    mouse_down = True

                    if self.state == 1:
                        self.airship.angle+=5


                if event.type == pygame.MOUSEBUTTONUP:
                    if mouse_down == True:
                        if mouse_down_frames < 60:
                            if mouse_up_frames > 10:
                                if self.state == 0:
                                    self.load_screen(1)
                                elif self.state == 2:
                                    self.load_screen(0)

                        if self.state == 0:
                            if mouse_down_frames > 240:
                                return 0, screen

                    mouse_down = False
                    mouse_down_frames = 0
                    mouse_up_frames = 0


            if self.state == 0:
                ### Blit background ###

                ### Blit Effects ###

                for circle in self.circle_effects:
                    circle.update()
                    circle.draw(screen)

                    if circle.size > circle.target:
                        self.circle_effects.remove(circle)

                self.blit_menu(screen)


                ### Blit Player ###

            elif self.state == 0.5:
                self.background.change_areas()
                self.background.make_stripe(3, self.speed_constant, self.background_cooldown)
                self.background.move_stripe()
                self.background.draw(screen)

                self.time += 1
                if self.signalLight.update(self.time, 60):
                    self.signalLight.move()
                self.signalLight.draw(screen)

                self.airship.move(5)
                self.airship.turn(3)
                self.airship.draw(screen, 0, 0)

                self.surface_cooldown += 1
                if self.surface_cooldown >= 1 and self.surface_alpha > self.surface_delta_alpha:
                    self.surface_cooldown = 0
                    self.surface_alpha -= self.surface_delta_alpha
                    self.surface.fill((0, 0, 0, self.surface_alpha))
                screen.blit(self.surface, (0, 0))

                if self.signalLight.check():
                    self.state = 1

            elif self.state == 1:
                self.screen_shake.update()
                shake_x, shake_y = self.screen_shake.offset_x, self.screen_shake.offset_y

                if not self.airship.crash:
                    self.background.serve_area_cooldown += 1
                    self.background.change_areas()
                    self.background.make_stripe(3, self.speed_constant, self.background_cooldown)
                    self.background.move_stripe()
                self.background.draw(screen)


                self.wall_cooldown += 1
                if self.wall_cooldown >= self.background_cooldown * self.wall_make_cycle:
                    self.wall_cooldown = 0

                    self.walls.append(Wall(self.width, self.height, random.randint(0,1), self.level, (self.background.left_up, self.background.right_up, self.background.right_down, self.background.left_down),
                                           self.side_color, speed_constant= self.speed_constant))


                for i in range(len(self.walls)):
                    if not self.airship.crash:
                        self.walls[-i-1].make_parts()
                        self.walls[-i-1].move(self.background.lines, self.background.middle_lines)
                        self.walls[-i-1].change()
                    self.walls[-i-1].draw(screen)
                    if self.walls[-i-1].edge[0].middle_point[1] <= 0:
                        crash_part = self.airship.crash_check(self.walls[-i-1])
                        if not all(item in self.walls[-i-1].void_number for item in crash_part):
                            self.airship.crash = True
                            self.screen_shake.start_shake(20)

                if not self.airship.crash:
                    self.walls = [wall for wall in self.walls if not wall.edge[0].middle_point[1] <= 0]

                if not self.airship.crash:
                    self.airship.move(5)
                    self.airship.turn(3)
                self.airship.draw(screen, shake_x, shake_y)
                self.airship.crash_effect()

                if self.airship.crash:
                    self.after_crash += 1
                    if self.after_crash >= self.after_crash_wait_time:
                        self.load_screen(2)

                self.score_cooldown += 1
                if self.score_cooldown >= 20 and not self.airship.crash:
                    self.score_cooldown = 0
                    self.curr_score += 1

                self.blit_ingame(screen)

            elif self.state == 2:
                self.surface_cooldown += 1
                if self.shake_tick > 0:
                    self.scrollx = self.last_scrollx + (random.random() - 0.5) * self.shake_tick
                    self.prev_scrolly = self.scrolly
                    self.scrolly = self.prev_scrolly + (random.random() - 0.5) * self.shake_tick
                    self.shake_tick -= 0.2


                self.scrolly += (self.adjed_scrolly - self.scrolly) * 0.03 if (self.adjed_scrolly - self.scrolly) * 0.03 >= 0.1 else 0

                if self.surface_cooldown >= 1 and self.surface_max_alpha > self.surface_alpha:
                    self.surface_cooldown = 0
                    self.surface_alpha += self.surface_delta_alpha
                    self.surface.fill((0, 0, 0, self.surface_alpha))


                self.background.draw(screen)
                for i in range(len(self.walls)):
                    self.walls[-i-1].draw(screen)
                self.airship.draw(screen, 0, 0)
                screen.blit(self.surface, (0, 0))

                self.blit_game_over(screen)

            # Show FPS if needed
            if self.show_fps:
                blit_fps(screen, clock)

            pygame.display.flip()

class AirshipScreen(ScreenObject):
    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)
        self.show_fps = show_fps

    def loop(self, screen):
        running = True

        while running:
            curr_AvoidMine_screen = AirshipMainScreen(self.width, self.height, show_fps=self.show_fps)
            next_screen, curr_screen_surface = curr_AvoidMine_screen.loop(screen)
            pygame.time.wait(2000)
            fade_out(screen, curr_screen_surface, self.width, self.height, 2000)
            return 0, screen



class CircleEffect:
    def __init__(self, x, y, size, target, color, width, gradient=True, second=(10, 17, 30)):
        self.x = x
        self.y = y
        self.size = size
        self.target = target
        self.width = int(width)
        self.gradient = gradient

        if gradient:
            self.color = list(second)
            self.second = color
        else:
            self.color = list(color)
            self.second = second

    def update(self, step=0.1, color_step=0.2):
        self.size += self.target * step

        if self.gradient:
            for i in range(3):
                self.color[i] += int((self.second[i] - self.color[i]) * color_step)
                self.color[i] = min(self.color[i], 255)

    def draw(self, screen, scrollx=0, scrolly=0):
        pygame.draw.circle(screen, self.color, (self.x - scrollx, self.y - scrolly), self.size, self.width)



class Airship:
    def __init__(self, screen_width, screen_height, speed, life, size):
        self.width, self.height = screen_width, screen_height
        self.speed, self.life, self.size = speed, life, size
        self.moved_distance, self.location, self.angle = 0, (screen_width / 2, screen_height / 4 * 3), 0
        self.x, self.y = size * 2, size
        self.crash = False

        self.original_image, self.image = pygame.transform.scale(pygame.image.load("data/Airship/imgs/1.png"),(self.x, self.y)), pygame.transform.scale(pygame.image.load("data/Airship/imgs/1.png"), (self.x, self.y))
        self.rect = self.image.get_rect(center=(screen_width / 2, screen_height / 4 * 3))
        self.mask = pygame.mask.from_surface(self.image)
        self.mask_image = self.mask.to_surface()

        self.Explosion_size = 150
        self.explosion = Explosion(self.rect.center[0], self.rect.center[1], self.Explosion_size)

    def move(self, move_proportion):
        self.moved_distance += self.speed

        mouse_pos = pygame.mouse.get_pos()
        delta_x, delta_y = (self.location[0] - mouse_pos[0]) / move_proportion, (self.location[1] - mouse_pos[1]) / move_proportion
        self.location = (self.location[0] - delta_x, self.location[1] - delta_y)

        self.rect = self.image.get_rect(center=self.location)
        self.mask = pygame.mask.from_surface(self.image)
        self.mask_image = self.mask.to_surface()

    def turn(self, turn_proportion):
        mouse_pos = pygame.mouse.get_pos()
        delta_x = mouse_pos[0] - self.location[0]
        self.angle = - delta_x / self.width * 90 * turn_proportion
        if self.angle <= -80: self.angle = -80
        elif self.angle >= 80: self.angle = 80

        self.image = pygame.transform.rotate(self.original_image, self.angle)

    def crash_check(self, wall):
        crash_part = []
        for i in range(len(wall.parts_mask)):
            if wall.parts_mask[i].overlap(self.mask, (self.rect.x - wall.parts[i].x, self.rect.y - wall.parts[i].y)):
                crash_part.append(i)

        if wall.kind_number == 1:
            for i in range(len(wall.parts_mask_2)):
                if wall.parts_mask_2[i].overlap(self.mask,
                                              (self.rect.x - wall.parts_2[i].x, self.rect.y - wall.parts_2[i].y)):
                    crash_part.append(i)

        return crash_part

    def crash_effect(self):
        if self.crash:
            self.explosion.update()
        else:
            self.explosion = Explosion(self.location[0], self.location[1], self.Explosion_size)

    def smoke_effect(self):
        pass

    def draw(self, screen, shake_x, shake_y):
        screen.blit(self.image, (self.rect.topleft[0] - shake_x, self.rect.topleft[1] - shake_y))
        if self.crash:
            self.explosion.draw(screen, shake_x, shake_y)



class Wall:
    def __init__(self, screen_width, screen_height, kind_number, level, points, color, speed_constant = 3000):
        self.level = level
        self.color = color
        self.kind_number = kind_number
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.edge = {
            0: Line(screen_width, screen_height, 0, points[0], points[1], points, color = color, speed_constant = speed_constant),
            1: Line(screen_width, screen_height, 1, points[1], points[2], points, color = color, speed_constant = speed_constant),
            2: Line(screen_width, screen_height, 2, points[2], points[3], points, color = color, speed_constant = speed_constant),
            3: Line(screen_width, screen_height, 3, points[3], points[0], points, color = color, speed_constant = speed_constant)
        }
        self.parts, self.frame_points, self.frame, self.parts_surface, self.parts_mask, self.parts_mask_image = {}, {}, {}, {}, {}, {}
        self.void_number = []
        if kind_number == 1:
            self.parts_surface_2, self.parts_mask_2, self.parts_mask_image_2 = {}, {}, {}
            self.speed, self.direction_1, self.direction_2, self.parts_2, self.frame_2 = {}, {}, {}, {}, {}
            self.location_1, self.location_2 = {}, {}
            self.width, self.height, self.proportion, self.cooldown = 0, 0, 100, 0
            for i in range(1):
                self.direction_1[i] = 0
                self.direction_2[i] = 0
                self.frame[i] = Line(screen_width, screen_height, 8, (0, 0), (1, 1))
                self.frame_2[i] = Line(screen_width, screen_height, 8, (0, 0), (1, 1))

    def make_parts(self, number = 1):
        if self.kind_number == 0: #구멍에 들어가기
            width = 3
            if len(self.void_number) == 0:
                a = [i for i in range(9)]
                for i in range(number):
                    self.void_number.append(a.pop(random.randint(0, len(a) - 1)))

            self.frame = {
                3 : Line(self.screen_width, self.screen_height, 3, [self.edge[0].start_point[0] * 2 / 3 + self.edge[0].end_point[0] * 1 / 3, self.edge[0].middle_point[1]],
                                [self.edge[0].start_point[0] * 2 / 3 + self.edge[0].end_point[0] * 1 / 3, self.edge[2].middle_point[1]],
                                self.edge[0].points, color=self.color, width= width),
                1 : Line(self.screen_width, self.screen_height, 1, [self.edge[0].start_point[0] * 1 / 3 + self.edge[0].end_point[0] * 2 / 3,self.edge[0].middle_point[1]],
                                [self.edge[0].start_point[0] * 1 / 3 + self.edge[0].end_point[0] * 2 / 3,self.edge[2].middle_point[1]],
                                self.edge[0].points, color=self.color, width=width),
                0 : Line(self.screen_width, self.screen_height, 0, [self.edge[3].middle_point[0],self.edge[1].start_point[1] * 2 / 3 + self.edge[1].end_point[1] * 1 / 3],
                                [self.edge[1].middle_point[0],self.edge[1].start_point[1] * 2 / 3 + self.edge[1].end_point[1] * 1 / 3],
                                self.edge[0].points, color=self.color, width=width),
                2 : Line(self.screen_width, self.screen_height, 2, [self.edge[3].middle_point[0],self.edge[1].start_point[1] * 1 / 3 + self.edge[1].end_point[1] * 2 / 3],
                                [self.edge[1].middle_point[0],self.edge[1].start_point[1] * 1 / 3 + self.edge[1].end_point[1] * 2 / 3],
                                self.edge[0].points, color=self.color, width=width)
        }
            self.frame_points = {
                0: self.edge[0].start_point,
                1: (self.frame[3].middle_point[0], self.edge[0].equation(self.frame[3].middle_point[0], None)),
                2: (self.frame[1].middle_point[0], self.edge[0].equation(self.frame[1].middle_point[0], None)),
                3: self.edge[0].end_point,

                4: (self.edge[3].middle_point[0], self.frame[0].equation(self.edge[3].middle_point[0], None)),
                5: (self.frame[3].middle_point[0], self.frame[0].equation(self.frame[3].middle_point[0], None)),
                6: (self.frame[1].middle_point[0], self.frame[0].equation(self.frame[1].middle_point[0], None)),
                7: (self.edge[1].middle_point[0], self.frame[0].equation(self.edge[1].middle_point[0], None)),

                8: (self.edge[3].middle_point[0], self.frame[2].equation(self.edge[3].middle_point[0], None)),
                9: (self.frame[3].middle_point[0], self.frame[2].equation(self.frame[3].middle_point[0], None)),
                10: (self.frame[1].middle_point[0], self.frame[2].equation(self.frame[1].middle_point[0], None)),
                11: (self.edge[1].middle_point[0], self.frame[2].equation(self.edge[1].middle_point[0], None)),

                12: self.edge[2].end_point,
                13: (self.frame[3].middle_point[0], self.edge[2].equation(self.frame[3].middle_point[0], None)),
                14: (self.frame[1].middle_point[0], self.edge[2].equation(self.frame[1].middle_point[0], None)),
                15: self.edge[2].start_point,
            }
            self.parts = {
                0: pygame.Rect(*self.frame_points[0], self.frame_points[1][0] - self.frame_points[0][0], self.frame_points[5][1] - self.frame_points[1][1]),
                1: pygame.Rect(*self.frame_points[1], self.frame_points[1][0] - self.frame_points[0][0], self.frame_points[5][1] - self.frame_points[1][1]),
                2: pygame.Rect(*self.frame_points[2], self.frame_points[1][0] - self.frame_points[0][0], self.frame_points[5][1] - self.frame_points[1][1]),

                3: pygame.Rect(*self.frame_points[4], self.frame_points[1][0] - self.frame_points[0][0], self.frame_points[5][1] - self.frame_points[1][1]),
                4: pygame.Rect(*self.frame_points[5], self.frame_points[1][0] - self.frame_points[0][0], self.frame_points[5][1] - self.frame_points[1][1]),
                5: pygame.Rect(*self.frame_points[6], self.frame_points[1][0] - self.frame_points[0][0], self.frame_points[5][1] - self.frame_points[1][1]),

                6: pygame.Rect(*self.frame_points[8], self.frame_points[1][0] - self.frame_points[0][0], self.frame_points[5][1] - self.frame_points[1][1]),
                7: pygame.Rect(*self.frame_points[9], self.frame_points[1][0] - self.frame_points[0][0], self.frame_points[5][1] - self.frame_points[1][1]),
                8: pygame.Rect(*self.frame_points[10], self.frame_points[1][0] - self.frame_points[0][0], self.frame_points[5][1] - self.frame_points[1][1]),
            }
            for i in range(len(self.parts)):
                self.parts_surface[i] = pygame.Surface(self.parts[i].size, pygame.SRCALPHA)
                self.parts_surface[i].fill((0, 0, 0, 200))
            for i in range(len(self.parts_surface)):
                self.parts_mask[i] = pygame.mask.from_surface(self.parts_surface[i])
            for i in range(len(self.parts_mask)):
                self.parts_mask_image[i] = self.parts_mask[i].to_surface()

        elif self.kind_number == 1: # 움직이는 레이저 피하기
            line_width = 1
            direction_1 = random.randint(1,2)
            direction_2 = random.randint(1,2)
            if self.frame[0].number != 8 and self.frame_2[0].number != 8:
                direction_1 = -1
                direction_2 = -1

            self.width = self.edge[0].end_point[0] - self.edge[0].start_point[0]
            self.height = - (self.edge[0].start_point[1] - self.edge[2].end_point[1])


            for i in range(number):
                self.speed[i] = random.uniform(1, 3)
                if direction_1 == 1 or self.direction_1[i] == 1: #왼쪽 시작
                    if self.frame[i].number == 8:
                        self.direction_1[i] = 1
                        self.location_1[i] = 0
                elif direction_1 == 2 or self.direction_1[i] == -1: #오른쪽 시작
                    if self.frame[i].number == 8:
                        self.direction_1[i] = -1
                        self.location_1[i] = self.screen_width
                self.frame[i] = Line(self.screen_width, self.screen_height, 5, (self.edge[0].start_point[0] + self.location_1[i] * self.width, self.edge[0].start_point[1]),
                                     (self.edge[2].end_point[0] + self.location_1[i] * self.width, self.edge[2].end_point[1]), color=(100, 50, 50), width=line_width)
                self.parts[i] = pygame.Rect(self.frame[i].start_point[0], self.frame[i].start_point[1], self.width / self.proportion * 2, self.height)

            for i in range(len(self.parts)):
                self.parts_surface[i] = pygame.Surface(self.parts[i].size, pygame.SRCALPHA)
                self.parts_surface[i].fill((0, 0, 0, 200))
            for i in range(len(self.parts_surface)):
                self.parts_mask[i] = pygame.mask.from_surface(self.parts_surface[i])
            for i in range(len(self.parts_mask)):
                self.parts_mask_image[i] = self.parts_mask[i].to_surface()


            for i in range(number):
                self.speed[i] = random.uniform(1, 3)
                if direction_2 == 1 or self.direction_2[i] == 1: #위쪽 시작
                    if self.frame_2[i].number == 8:
                        self.direction_2[i] = 1
                        self.location_2[i] = 0
                elif direction_2 == 2 or self.direction_2[i] == -1: #아래쪽 시작
                    if self.frame_2[i].number == 8:
                        self.direction_2[i] = -1
                        self.location_2[i] = self.screen_height
                self.frame_2[i] = Line(self.screen_width, self.screen_height, 5, (self.edge[0].start_point[0], self.edge[0].start_point[1] + self.location_2[i] * self.height),
                                       (self.edge[0].end_point[0], self.edge[0].end_point[1] + self.location_2[i] * self.height), color=(100, 50, 50), width=line_width)
                self.parts_2[i] = pygame.Rect(self.frame_2[i].start_point[0], self.frame_2[i].start_point[1], self.width, self.width / self.proportion * 2)

            for i in range(len(self.parts_2)):
                self.parts_surface_2[i] = pygame.Surface(self.parts_2[i].size, pygame.SRCALPHA)
                self.parts_surface_2[i].fill((0, 0, 0, 200))
            for i in range(len(self.parts_surface_2)):
                self.parts_mask_2[i] = pygame.mask.from_surface(self.parts_surface_2[i])
            for i in range(len(self.parts_mask_2)):
                self.parts_mask_image_2[i] = self.parts_mask_2[i].to_surface()



        elif self.kind_number == 2:
            pass

    def move(self, lines, middle_lines):
        for i in range(4):
            self.edge[i % 4].update(lines[i % 4], middle_lines[i % 4], lines[(i + 1) % 4])

    def change(self):
        if self.kind_number == 0:
            pass
        elif self.kind_number == 1:
            self.cooldown += 1
            if self.cooldown >= 1:
                self.cooldown = 0

                for i in range(len(self.frame)):
                    self.location_1[i] += self.direction_1[i] / self.proportion * self.speed[i]
                    if self.location_1[i] >= 1:
                        self.location_1[i] = 1
                        self.direction_1[i] = -1
                    if self.location_1[i] <= 0:
                        self.location_1[i] = 0
                        self.direction_1[i] = 1

                for i in range(len(self.frame_2)):
                    self.location_2[i] += self.direction_2[i] / self.proportion * self.speed[i]
                    if self.location_2[i] >= 1:
                        self.location_2[i] = 1
                        self.direction_2[i] = -1
                    elif self.location_2[i] <= 0:
                        self.location_2[i] = 0
                        self.direction_2[i] = 1

    def draw(self, screen):
        for i in range(len(self.edge)):
            self.edge[i].draw(screen)

        if self.kind_number == 1:
            for i in range(len(self.parts)):
                pygame.draw.rect(screen, (100, 50, 50), self.parts[i])
            for i in range(len(self.parts_2)):
                pygame.draw.rect(screen, (100, 50, 50), self.parts_2[i])


        elif self.kind_number == 0:
            for i in range(len(self.parts_surface)):
                if not i in self.void_number:
                    screen.blit(self.parts_surface[i], self.parts[i].topleft)
            for i in range(len(self.frame)):
                self.frame[i].draw(screen)





class Line:
    def __init__(self, screen_width, screen_height, number, start_point, end_point, points = (), color = (255, 255, 255), width = 3, speed_constant = 3000):
        self.number, self.width, self.height = number, screen_width, screen_height
        self.start_point, self.end_point = start_point, end_point
        self.middle_point = [(start_point[0] + end_point[0]) / 2 , (start_point[1] + end_point[1]) / 2]
        self.x, self.y = 0, 0
        if not start_point[0] - end_point[0] == 0:
            self.slope = (start_point[1] - end_point[1]) / (start_point[0] - end_point[0])
        else: self.slope = 2147483647
        if self.slope == 0: self.slope = 0.00000000001
        self.y_intercept = start_point[1] - self.slope * start_point[0]
        self.speed_constant, self.speed = speed_constant, 0
        self.acceleration_cooldown = 0
        self.color = color
        self.points = points #흰색 화면의 4개의 꼭짓점
        self.line_width = width

        if self.number == 0:
            self.acceleration = self.points[0][1] / self.speed_constant
        elif self.number == 1:
            self.acceleration = (self.width - self.points[1][0]) / self.speed_constant
        elif self.number == 2:
            self.acceleration = (self.height - self.points[2][1]) / self.speed_constant
        elif self.number == 3:
            self.acceleration = self.points[3][0] / self.speed_constant

    def equation(self, x, y):
        self.y_intercept = self.start_point[1] - self.slope * self.start_point[0]
        self.x, self.y = x, y

        if self.x == None and self.y != None:
            return (self.y - self.y_intercept) / self.slope
        elif self.x != None and self.y == None:
            return self.slope * self.x + self.y_intercept

    def update(self, start_line, middle_line, end_line): # start_line -> middle_line -> end_line 시계방향으로 정함
        self.acceleration_cooldown += 1
        if self.acceleration_cooldown >= 1:
            self.speed += self.acceleration
            self.acceleration_cooldown = 0

        if self.number == 0:
            self.middle_point[1] -= self.speed
            self.middle_point[0] = middle_line.equation(None, self.middle_point[1])

            self.start_point[1], self.end_point[1] = self.middle_point[1], self.middle_point[1]
            self.start_point[0] = start_line.equation(None, self.start_point[1])
            self.end_point[0] = end_line.equation(None, self.end_point[1])

        elif self.number == 1:
            self.middle_point[0] += self.speed
            self.middle_point[1] = middle_line.equation(self.middle_point[0], None)

            self.start_point[0], self.end_point[0] = self.middle_point[0], self.middle_point[0]
            self.start_point[1] = start_line.equation(self.start_point[0], None)
            self.end_point[1] = end_line.equation(self.end_point[0], None)

        elif self.number == 2:
            self.middle_point[1] += self.speed
            self.middle_point[0] = middle_line.equation(None, self.middle_point[1])

            self.start_point[1], self.end_point[1] = self.middle_point[1], self.middle_point[1]
            self.start_point[0] = start_line.equation(None, self.start_point[1])
            self.end_point[0] = end_line.equation(None, self.end_point[1])

        elif self.number == 3:
            self.middle_point[0] -= self.speed
            self.middle_point[1] = middle_line.equation(self.middle_point[0], None)

            self.start_point[0], self.end_point[0] = self.middle_point[0], self.middle_point[0]
            self.start_point[1] = start_line.equation(self.start_point[0], None)
            self.end_point[1] = end_line.equation(self.end_point[0], None)

    def draw(self, screen):
        pygame.draw.line(screen, self.color, self.start_point, self.end_point, self.line_width)



class Background:
    def __init__(self, width, height, proportion, vanishing_point, speed, main_color, side_color, base_color):
        self.width, self.height, self.vp_x, self.vp_y = width, height, vanishing_point[0], vanishing_point[1]
        self.speed, self.main_color, self.side_color, self.base_color = speed, main_color, side_color, base_color
        self.size_proportion = proportion
        self.size_x, self.size_y = self.width // (2 * self.size_proportion), self.height // (2 * self.size_proportion)
        self.edge, self.main_areas, self.lines, self.middle_lines, self.side_areas = [], [], [], [], [[] for i in range(4)]
        self.serve_area_cooldown = 0
        self.left_up, self.right_up, self.right_down, self.left_down, self.left_middle, self.right_middle, self.up_middle, self.down_middle = None, None, None, None, None, None, None, None
        self.points = [self.left_up, self.right_up, self.right_down, self.left_down, self.left_middle, self.right_middle, self.up_middle, self.down_middle]
        self.background_line_number = 5
        self.background_line = [[] for i in range(4)]

    def change_areas(self):

        '''mouse_pos = pygame.mouse.get_pos()
        self.vp_x = mouse_pos[0]
        self.vp_y = mouse_pos[1]'''
        self.vp_x, self.vp_y = self.width // 2, self.height // 2 * 5/4

        self.left_up = [self.vp_x - self.size_x, self.vp_y - self.size_y]
        self.right_up = [self.vp_x + self.size_x, self.vp_y - self.size_y]
        self.right_down = [self.vp_x + self.size_x, self.vp_y + self.size_y]
        self.left_down = [self.vp_x - self.size_x, self.vp_y + self.size_y]
        self.left_middle = [self.vp_x - self.size_x, self.vp_y]
        self.right_middle = [self.vp_x + self.size_x, self.vp_y]
        self.up_middle = [self.vp_x, self.vp_y - self.size_y]
        self.down_middle = [self.vp_x, self.vp_y + self.size_y]
        self.points = [self.left_up, self.right_up, self.right_down, self.left_down, self.left_middle, self.right_middle, self.up_middle, self.down_middle]

        width = 3
        self.edge = [
            Line(self.width, self.height, 5, self.left_up, self.right_up, color= self.base_color, width= width),
            Line(self.width, self.height, 5, self.right_up, self.right_down, color=self.base_color, width= width),
            Line(self.width, self.height, 5, self.right_down, self.left_down, color=self.base_color, width= width),
            Line(self.width, self.height, 5, self.left_down, self.left_up, color=self.base_color, width= width)
        ]
        self.lines = [
            Line(self.width, self.height, 5, [0, 0], self.left_up, color = self.base_color, width= width),
            Line(self.width, self.height, 5, [self.width, 0], self.right_up, color = self.base_color, width= width),
            Line(self.width, self.height, 5, [self.width, self.height], self.right_down, color = self.base_color, width= width),
            Line(self.width, self.height, 5, [0, self.height], self.left_down, color = self.base_color, width= width)
        ]
        self.main_areas = [
            ((0, 0), (self.width, 0), self.right_up, self.left_up),
            ((self.width, 0), (self.width, self.height), self.right_down, self.right_up),
            ((self.width, self.height), (0, self.height), self.left_down, self.right_down),
            ((0, self.height), (0, 0), self.left_up, self.left_down)
        ]
        self.middle_lines = [
            Line(self.width, self.height, 5, (self.width // 2, 0), self.up_middle),
            Line(self.width, self.height, 5, (self.width, self.height // 2), self.right_middle),
            Line(self.width, self.height, 5, (self.width // 2, self.height), self.down_middle),
            Line(self.width, self.height, 5, (0, self.height // 2), self.left_middle)

        ]
        self.background_line = [[] for i in range(4)]
        for i in range(1, self.background_line_number):
            self.background_line[0].append(Line(self.width, self.height, 5, [self.lines[0].start_point[0] + (self.lines[1].start_point[0] - self.lines[0].start_point[0]) / self.background_line_number * i, self.lines[0].start_point[1]],
                                                [self.lines[0].end_point[0] + (self.lines[1].end_point[0] - self.lines[0].end_point[0]) / self.background_line_number * i, self.lines[0].end_point[1]], color= self.side_color))
        for i in range(1, self.background_line_number - 1):
            self.background_line[1].append(Line(self.width, self.height, 5, [self.lines[1].start_point[0], self.lines[1].start_point[1] + (self.lines[2].start_point[1] - self.lines[1].start_point[1]) / (self.background_line_number - 1) * i],
                                                [self.lines[1].end_point[0], self.lines[1].end_point[1] + (self.lines[2].end_point[1] - self.lines[1].end_point[1]) / (self.background_line_number - 1) * i], color= self.side_color))
        for i in range(1, self.background_line_number):
            self.background_line[2].append(Line(self.width, self.height, 5, [self.lines[2].start_point[0] + (self.lines[3].start_point[0] - self.lines[2].start_point[0]) / self.background_line_number * i, self.lines[2].start_point[1]],
                                                [self.lines[2].end_point[0] + (self.lines[3].end_point[0] - self.lines[2].end_point[0]) / self.background_line_number * i, self.lines[2].end_point[1]], color= self.side_color))
        for i in range(1, self.background_line_number - 1):
            self.background_line[3].append(Line(self.width, self.height, 5, [self.lines[3].start_point[0], self.lines[3].start_point[1] + (self.lines[0].start_point[1] - self.lines[3].start_point[1]) / (self.background_line_number - 1) * i],
                                                [self.lines[3].end_point[0], self.lines[3].end_point[1] + (self.lines[0].end_point[1] - self.lines[3].end_point[1]) / (self.background_line_number - 1) * i], color= self.side_color))

    def make_stripe(self, thickness, speed_constant, cooldown):
        if self.serve_area_cooldown >= cooldown:
            self.serve_area_cooldown = 0

            # 0 area (윗 부분)
            front_line_0 = Line(self.width, self.height, 0, [self.lines[0].equation(None,  self.left_up[1]), self.left_up[1]],
                            [self.lines[1].equation(None, self.right_up[1]), self.right_up[1]],
                                (self.left_up, self.right_up, self.right_down, self.left_down),
                                speed_constant = speed_constant)
            behind_line_0 = Line(self.width, self.height, 0, [self.lines[0].equation(None,  self.left_up[1] + thickness), self.left_up[1] + thickness],
                            [self.lines[1].equation(None, self.right_up[1] + thickness), self.right_up[1] + thickness],
                                 (self.left_up, self.right_up, self.right_down, self.left_down),
                                 speed_constant = speed_constant)

            # 1 area (오른쪽)
            front_line_1  = Line(self.width, self.height, 1, [self.right_up[0], self.lines[1].equation(self.right_up[0], None)],
                                 [self.right_down[0], self.lines[2].equation(self.right_down[0], None)],
                                 (self.left_up, self.right_up, self.right_down, self.left_down),
                                 speed_constant = speed_constant)
            behind_line_1 = Line(self.width, self.height, 1, [self.right_up[0] - thickness, self.lines[1].equation(self.right_up[0] - thickness, None)],
                                 [self.right_down[0] - thickness, self.lines[2].equation(self.right_down[0] - thickness, None)],
                                 (self.left_up, self.right_up, self.right_down, self.left_down),
                                 speed_constant = speed_constant)


            # 2 area (아래)
            front_line_2 = Line(self.width, self.height, 2, [self.lines[2].equation(None, self.right_down[1]), self.right_down[1]],
                                [self.lines[3].equation(None, self.left_down[1]), self.left_down[1]],
                                (self.left_up, self.right_up, self.right_down, self.left_down),
                                speed_constant = speed_constant)
            behind_line_2 = Line(self.width, self.height, 2, [self.lines[2].equation(None, self.right_down[1] - thickness), self.right_down[1] - thickness],
                                [self.lines[3].equation(None, self.left_down[1] - thickness), self.left_down[1] - thickness],
                                 (self.left_up, self.right_up, self.right_down, self.left_down),
                                 speed_constant = speed_constant)


            # 3 area (왼쪽)
            front_line_3 = Line(self.width, self.height, 3, [self.left_down[0], self.lines[3].equation(self.left_down[0], None)],
                                 [self.left_up[0], self.lines[0].equation(self.left_up[0], None)],
                                (self.left_up, self.right_up, self.right_down, self.left_down),
                                speed_constant = speed_constant)
            behind_line_3 = Line(self.width, self.height, 3, [self.left_down[0] + thickness, self.lines[3].equation(self.left_down[0] + thickness, None)],
                                 [self.left_up[0] + thickness, self.lines[0].equation(self.left_up[0] + thickness, None)],
                                 (self.left_up, self.right_up, self.right_down, self.left_down),
                                 speed_constant = speed_constant)


            self.side_areas[0].append((front_line_0, behind_line_0))
            self.side_areas[1].append((front_line_1, behind_line_1))
            self.side_areas[2].append((front_line_2, behind_line_2))
            self.side_areas[3].append((front_line_3, behind_line_3))

        self.side_areas[0] = [i for i in self.side_areas[0] if not (i[1].start_point[1] < 0 and i[1].end_point[1] < 0)]
        self.side_areas[1] = [i for i in self.side_areas[1] if not (i[1].start_point[0] > self.width and i[1].end_point[0] > self.width)]
        self.side_areas[2] = [i for i in self.side_areas[2] if not (i[1].start_point[1] > self.height and i[1].end_point[1] > self.height)]
        self.side_areas[3] = [i for i in self.side_areas[3] if not (i[1].start_point[0] < 0 and i[1].end_point[0] < 0)]

    def move_stripe(self):
        for number in range(4):
            for area in self.side_areas[number]:
                area[0].update(self.lines[number % 4], self.middle_lines[number % 4], self.lines[(number + 1) % 4])
                area[1].update(self.lines[number % 4], self.middle_lines[number % 4], self.lines[(number + 1) % 4])

    def draw(self, screen):
        for area in self.main_areas:
            pygame.draw.polygon(screen, self.main_color, area)
        for lines in self.background_line:
            for line in lines:
                line.draw(screen)
        for areas in self.side_areas:
            for area in areas:
                pygame.draw.polygon(screen, self.side_color, (area[0].start_point, area[0].end_point, area[1].end_point, area[1].start_point))
        pygame.draw.polygon(screen, (150, 150, 150), (self.left_up, self.right_up, self.right_down, self.left_down))
        for line in self.lines:
            line.draw(screen)
        for line in self.edge:
            line.draw(screen)



class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.lifetime = random.randint(30, 60)  # 파편 수명
        self.angle = random.uniform(0, 2 * math.pi)  # 방사형 방향
        self.speed = random.uniform(2, 6)  # 파편 속도
        self.color = random.choice([(255, 100, 0), (255, 200, 50), (200, 50, 0)])  # 불꽃 색상
        self.radius = random.randint(2, 5)

    def update(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.lifetime -= 1  # 수명 감소

    def draw(self, screen, shake_x, shake_y):
        if self.lifetime > 0:
            pygame.draw.circle(screen, self.color, (int(self.x + shake_x), int(self.y + shake_y)), self.radius)



class Explosion:
    def __init__(self, x, y, number):
        self.particles = [Particle(x, y) for _ in range(number)]  # 50개의 파편 생성

    def update(self):
        self.particles = [p for p in self.particles if p.lifetime > 0]  # 살아있는 파편만 유지
        for p in self.particles:
            p.update()

    def draw(self, screen, shake_x, shake_y):
        for p in self.particles:
            p.draw(screen, shake_x, shake_y)



class ScreenShake:
    def __init__(self):
        self.shake_duration = 0  # 흔들림 지속 시간
        self.shake_intensity = 5  # 흔들림 강도
        self.offset_x = 0
        self.offset_y = 0

    def start_shake(self, duration):
        """ 흔들림 시작 """
        self.shake_duration = duration

    def update(self):
        """ 흔들림 업데이트 (지속 시간 동안 화면을 랜덤 이동) """
        if self.shake_duration > 0:
            self.offset_x = random.randint(-self.shake_intensity, self.shake_intensity)
            self.offset_y = random.randint(-self.shake_intensity, self.shake_intensity)
            self.shake_duration -= 1  # 흔들림 지속 시간 감소
        else:
            self.offset_x = 0
            self.offset_y = 0



class SignalLight:
    def __init__(self, lines, size, frame_color, light_color_1, light_color_2, speed_constant, speed):
        self.lines = lines
        self.frame_size, self.supports_size, self.light_size = size, [size[0] / 9, size[1] / 2], size[0] / 4
        self.frame_size_proportion, self.supports_size_proportion = self.frame_size[1] / self.frame_size[0], self.supports_size[1] / self.supports_size[0]
        self.frame_color, self.light_color_1, self.light_color_2 = frame_color, light_color_1, light_color_2
        self.speed_constant, self.speed = speed_constant, speed

        self.supports = [
            pygame.Rect(self.lines[0].start_point[0] - (self.lines[0].start_point[0] - self.lines[0].end_point[0]) / 3 - self.supports_size[0],
                         self.lines[0].start_point[1] - (self.lines[0].start_point[1] - self.lines[0].end_point[1]) / 3,
                        self.supports_size[0], self.supports_size[1]),
            pygame.Rect(self.lines[1].start_point[0] - (self.lines[1].start_point[0] - self.lines[1].end_point[0]) / 3,
                        self.lines[1].start_point[1] - (self.lines[1].start_point[1] - self.lines[1].end_point[1]) / 3,
                        self.supports_size[0], self.supports_size[1])
        ]
        self.frame = pygame.Rect(self.supports[0].left - self.supports_size[0] / 2, self.supports[0].top + self.supports_size[1], self.frame_size[0], self.frame_size[1])
        self.lights = [[self.light_color_1, [self.frame.left + self.frame_size[0] / 6 + self.frame_size[0] / 3 * i, self.frame.top + self.frame_size[1] / 2]] for i in range(3)]

        self.supports_space_proportion = self.supports_size[0] / (self.supports[1].left - self.supports[0].right)

    def move(self):
        self.speed += self.speed_constant

        self.supports = [
            pygame.Rect(self.lines[0].equation(None, self.supports[0].top - self.speed) - self.supports_size[0], self.supports[0].top - self.speed,
                        self.supports_size[0], self.supports_size[1]),
            pygame.Rect(self.lines[1].equation(None, self.supports[1].top - self.speed), self.supports[1].top - self.speed,
                        self.supports_size[0], self.supports_size[1])
        ]

        self.supports_size[0] = self.supports_space_proportion * (self.supports[1].left - self.supports[0].right)
        self.supports_size[1] = self.supports_size_proportion * self.supports_size[0]

        self.frame_size[0] = (self.supports[1].right + self.supports_size[0] / 2) - (self.supports[0].left - self.supports_size[0] / 2)
        self.frame_size[1] = self.frame_size[0] * self.frame_size_proportion

        self.light_size = self.frame_size[0] / 4

        self.frame = pygame.Rect(self.supports[0].left - self.supports_size[0] / 2, self.supports[0].top + self.supports_size[1], self.frame_size[0], self.frame_size[1])
        self.lights = [[self.lights[i][0], [self.frame.left + self.frame_size[0] / 6 + self.frame_size[0] / 3 * i, self.frame.top + self.frame_size[1] / 2]] for i in range(3)]

    def update(self, time, standard):
        if time >= standard * 3:
            self.lights[1][0] = self.light_color_2

            return True
        elif time >= standard * 2:
            self.lights[2][0] = self.light_color_2
        elif time >= standard * 1:
            self.lights[0][0] = self.light_color_2

    def check(self):
        if self.frame.bottom < 0:
            return True

    def draw(self, screen):
        pygame.draw.rect(screen, self.frame_color, self.frame)
        for support in self.supports:
            pygame.draw.rect(screen, self.frame_color, support)
        for light in self.lights:
            pygame.draw.circle(screen, light[0], light[1], self.light_size / 2)









# Run standalone
if __name__ == "__main__":
    pygame.init()
    WIDTH, HEIGHT = 1280, 720
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Airship")

    menu_screen = AirshipScreen(WIDTH, HEIGHT, show_fps=False)
    menu_screen.loop(screen)