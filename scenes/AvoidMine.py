import pygame
import random
import sys
import math

from collections import deque
from localLibraries.PlayCoreLibraries import ScreenObject, fade_out, blit_fps

class AvoidMineMainScreen(ScreenObject):
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
        with open("data/AvoidMine/playdata/saves.txt", "r") as file:
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

        self.areas = [((0, 0), (width, 0), (width // 2, height // 2)),
                 ((width, 0), (width, height), (width // 2, height // 2)),
                 ((width // 2, height // 2), (width, height), (0, height)),
                 ((0, 0), (width // 2, height // 2), (0, height))]

        self.menu_state = 0


        self.scrollx = 0
        self.scrolly = 0

        self.circle_effects = []
        self.trap_mines = []
        self.score_mines = []
        self.categories = self.divide_screen(self.width, self.height, self.areas, self.width // 40, self.height // 40)
        self.light = Light(self.width, self.height, 1, 5, 1, 50, 30)
        self.angle = 25

        self.trail = deque()

        self.shake_tick = 0
        self.lay_cooldown = 0
        self.score_cooldown = 0


        ### Menu Variables ###
        self.main_menu_scroll = height * 2 / 5

        self.texts = {
            'game_over': [self.h1.render("Game Over", True, self.white),
                          self.h1.size("Game Over")[0] / 2],

            'restart': [self.p.render("Click to Restart", True, self.white),
                        self.p.size("Click to Restart")[0] / 2],

            'title': [self.h1.render("Avoid Mine", True, self.title_color),
                      self.h1.size("Avoid Mine")[0] / 2],

            'start': [self.p.render("Click to Start", True, self.text_color),
                      self.p.size("Click to Start")[0]],

            'quit': [self.p.render("Hold to Quit", True, self.text_color)],

            'credit1': [self.psmall.render("Original Game by Adri_0211", True, self.text_color),
                        self.psmall.size("Original Game by Adri_0211")[0] / 2],

            'credit2': [self.psmall.render("Remasterd by Yuesung Jang", True, self.text_color),
                        self.psmall.size("Remasterd by Yuesung Jang")[0] / 2]
        }
        self.high_score = 0 #선언만 하는 것임
        self.texts_index = ['game_over', 'restart', 'title', 'start', 'quit', 'credit1', 'credit2']

    def reset(self):

        areas = [((0, 0), (self.width, 0), (self.width // 2, self.height // 2)),
                 ((self.width, 0), (self.width, self.height), (self.width // 2, self.height // 2)),
                 ((self.width // 2, self.height // 2), (self.width, self.height), (0, self.height)),
                 ((0, 0), (self.width // 2, self.height // 2), (0, self.height))]

        self.circle_effects.clear()

        self.trap_mines = []
        self.score_mines = []
        self.categories = self.divide_screen(self.width, self.height, areas, self.width // 40, self.height // 40)
        self.light = Light(self.width, self.height, 1, 5, 1, 50, 30)
        self.angle = 25
        self.menu_state = 0

        self.trail.clear()

        self.curr_score = 0

        self.shake_tick = 0
        self.lay_cooldown = 0
        self.score_cooldown = 0

        self.text_color = (75, 75, 75)
        self.title_color = (75, 75, 75)
        self.texts = {
            'game_over': [self.h1.render("Game Over", True, self.text_color),
                          self.h1.size("Game Over")[0] / 2],

            'restart': [self.p.render("Click to Restart", True, self.text_color),
                        self.p.size("Click to Restart")[0] / 2],

            'title': [self.h1.render("AvoidMine", True, self.title_color),
                      self.h1.size("AvoidMine")[0] / 2],

            'start': [self.p.render("Click to Start", True, self.text_color),
                      self.p.size("Click to Start")[0]],

            'quit': [self.p.render("Hold to Quit", True, self.text_color)],

            'credit1': [self.psmall.render("Original Game by Adri_0211", True, self.text_color),
                        self.psmall.size("Original Game by Adri_0211")[0] / 2],

            'credit2': [self.psmall.render("Remasterd by Yuseung Jang", True, self.text_color),
                        self.psmall.size("Remasterd by Yuseung Jang")[0] / 2]
        }
    
    
    def point_in_triangle(self, point, areas): #삼각형들 중 내의 마우스 위치 인식
        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

        result = []
        for area in areas:
            d1 = sign(point, area[0], area[1])
            d2 = sign(point, area[1], area[2])
            d3 = sign(point, area[2], area[0])

            has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
            has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)

            result.append(not (has_neg and has_pos))

        return result
        
    def divide_screen(self, screen_width, screen_height, areas, cols, rows):
        """
        주어진 화면 크기 (screen_width, screen_height)를 가로 cols개, 세로 rows개로 나누고
        나누어진 구역이 areas의 원소인 구역과 겹치는 것들을 분류한다.
        """
        categories = [[] for i in range(len(areas))]
        cell_width = screen_width // cols
        cell_height = screen_height // rows

        for row in range(rows):
            for col in range(cols):
                x = col * cell_width
                y = row * cell_height
                rect = ((x, y, cell_width, cell_height))
                rect_center = (x + cell_width // 2, y + cell_height // 2)
                area = self.point_in_triangle(rect_center, areas).index(True)
                categories[area].append(rect)

        return categories

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
        self.light.turn(0)
        self.light.speed /= 1.028
        self.light.draw(screen)

        if self.light.speed <= 0.13:
            self.light.speed = 0

        self.main_menu_scroll = 0

        # title
        screen.blit(self.texts['title'][0], (self.width / 2 - self.texts['title'][1],
                                             self.height / 7 * 2 - self.h1_size[1] - self.main_menu_scroll))

        # high score
        self.high_score = self.p.render(f"Best {self.best_score}", True, (75, 75, 75))
        screen.blit(self.high_score, (self.width / 2 - self.p.size(f"Best {self.best_score}")[0] / 2,
                                 self.height / 10 * 3 + self.main_menu_scroll))

        # start game
        screen.blit(self.texts['start'][0], (self.width / 8 * 3 - self.texts['start'][1],
                                             self.height / 6 * 3 + self.p_size[1] + self.psmall_size[
                                                 1] / 2 + self.main_menu_scroll))

        # quit game
        screen.blit(self.texts['quit'][0], (self.width / 8 * 5,
                                            self.height / 6 * 3 + self.p_size[1] + self.psmall_size[
                                                1] / 2 + self.main_menu_scroll))

        # credits
        screen.blit(self.texts['credit1'][0], (self.width / 2 - self.texts['credit1'][1],
                                               self.height / 4.5 * 3 + self.p_size[1] * 3 + self.main_menu_scroll))

        screen.blit(self.texts['credit2'][0], (self.width / 2 - self.texts['credit2'][1],
                                               self.height / 4.5 * 3 + self.p_size[1] * 3 + self.psmall_size[
                                                   1] + self.main_menu_scroll))

        if self.light.speed == 0:
            self.menu_state += 1
            if self.menu_state == 40:
                self.text_color = (255, 255, 255)
                self.title_color = (0, 0, 0)
                self.texts = {
                    'game_over': [self.h1.render("Game Over", True, self.text_color),
                                  self.h1.size("Game Over")[0] / 2],

                    'restart': [self.p.render("Click to Restart", True, self.text_color),
                                self.p.size("Click to Restart")[0] / 2],

                    'title': [self.h1.render("AvoidMine", True, self.title_color),
                              self.h1.size("AvoidMine")[0] / 2],

                    'start': [self.p.render("Click to Start", True, self.text_color),
                              self.p.size("Click to Start")[0]],

                    'quit': [self.p.render("Hold to Quit", True, self.text_color)],

                    'credit1': [self.psmall.render("Original Game by Dafluffypotato", True, self.text_color),
                                self.psmall.size("Original Game by Dafluffypotato")[0] / 2],

                    'credit2': [self.psmall.render("Remasterd by Jiwon Yu", True, self.text_color),
                                self.psmall.size("Remasterd by Jiwon Yu")[0] / 2]
                }

    def blit_ingame(self, screen):
        score = self.h1.render(f"{self.curr_score}", True, (0, 0, 0))
        screen.blit(score, (self.width / 2 - self.h1.size(f"{self.curr_score}")[0] / 2, self.height / 2 - self.h1_size[1] / 2))

    def load_screen(self, target):
        if target == 0:
            self.best_score = max(self.best_score, self.curr_score)
            # Writing to a text file
            with open("data/AvoidMine/playdata/saves.txt", "w") as file:
                file.write(f"{self.best_score}\n")

            self.reset()
            self.state = 0

            self.main_menu_scroll = self.height * 2 / 5

        elif target == 1:
            self.state = 1
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

            self.text_color = (75, 75, 75)
            self.title_color = (75, 75, 75)
            self.texts = {
                'game_over': [self.h1.render("Game Over", True, self.white),
                              self.h1.size("Game Over")[0] / 2],

                'restart': [self.p.render("Click to Restart", True, self.white),
                            self.p.size("Click to Restart")[0] / 2],

                'title': [self.h1.render("AvoidMine", True, self.title_color),
                          self.h1.size("AvoidMine")[0] / 2],

                'start': [self.p.render("Click to Start", True, self.text_color),
                          self.p.size("Click to Start")[0]],

                'quit': [self.p.render("Hold to Quit", True, self.text_color)],

                'credit1': [self.psmall.render("Original Game by Adri_0211", True, self.text_color),
                            self.psmall.size("Original Game by Adri_0211")[0] / 2],

                'credit2': [self.psmall.render("Remasterd by Yuseung Jang", True, self.text_color),
                            self.psmall.size("Remasterd by Yuseung Jang")[0] / 2]
            }

    def lay_mine(self, trap_mines, score_mines, size, areas, divided_areas):
        chance = random.random()
        mouse_pos = pygame.mouse.get_pos()
        area = self.point_in_triangle(mouse_pos, areas).index(True) #area는 마우스가 위치한 구역
        area = (area + 2) % 4 #area를 마우스가 위치한 구역 반대편으로 설정
        location_1 = random.choice(divided_areas[area])
        divided_areas[area].remove(location_1)

        if chance <= 0.1:
            location_2 = random.choice(divided_areas[area])
            divided_areas[area].remove(location_2)

            new_score_mine = ScoreMine((location_2[0] - random.randint(-4, 4), location_2[1] - random.randint(-4, 4)), size)
            score_mines.append(new_score_mine)

            location_3 = random.choice(divided_areas[area])
            new_trap_mine = TrapMine((location_3[0] - random.randint(-4, 4), location_3[1] - random.randint(-4, 4)), size)
            trap_mines.append(new_trap_mine)

        new_trap_mine = TrapMine((location_1[0] - random.randint(-4, 4), location_1[1] - random.randint(-4, 4)), size)
        trap_mines.append(new_trap_mine)

        return (trap_mines, score_mines)
    
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
        1: gameplay
        2: gameover
        """

        while self.running:
            screen.fill((75, 75, 75))

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


            elif self.state == 1:

                # 지뢰 설치 쿨타임
                self.lay_cooldown += 1

                #score 주는 쿨타임
                self.score_cooldown += 1

                # 회전하는 구역 그림
                self.light.change_speed(self.curr_score)
                self.light.turn(0.2)
                self.light.mouse_check(self.light.return_distance())
                self.light.draw(screen)

                #mines
                for trap_mine in self.trap_mines:
                    trap_mine.draw(screen)
                for score_mine in self.score_mines:
                    score_mine.draw(screen)
                    self.curr_score = score_mine.give_score(self.curr_score, score_mine)

                self.score_mines = [mine for mine in self.score_mines if not mine.check()] #점수 준 score_mine 삭제

                #mine 설치
                if self.lay_cooldown >= 300 and self.curr_score <= 10: #약 6초 마다 지뢰 설치
                    self.trap_mines, self.score_mines = self.lay_mine(self.trap_mines, self.score_mines, 30, self.areas, self.categories)
                    self.lay_cooldown = 0
                elif self.lay_cooldown >= 240 and self.curr_score > 10: #약 5초 마다 지뢰 설치
                    self.trap_mines, self.score_mines = self.lay_mine(self.trap_mines, self.score_mines, 30, self.areas, self.categories)
                    self.lay_cooldown = 0

                #score
                if self.score_cooldown * max((self.light.return_distance() // 60), 1) >= 60:
                    if self.light.return_distance() > self.light.size:
                        self.curr_score += 1
                    self.score_cooldown = 0

                self.blit_ingame(screen)

                #gamevoer 조건
                if self.light.life == 135:
                    self.load_screen(2)
                for mine in self.trap_mines:
                    if mine.check():
                        self.load_screen(2)


            elif self.state == 2:
                if self.shake_tick > 0:
                    self.scrollx = self.last_scrollx + (random.random() - 0.5) * self.shake_tick
                    self.prev_scrolly = self.scrolly
                    self.scrolly = self.prev_scrolly + (random.random() - 0.5) * self.shake_tick
                    self.shake_tick -= 0.2


                self.scrolly += (self.adjed_scrolly - self.scrolly) * 0.03 if (self.adjed_scrolly - self.scrolly) * 0.03 >= 0.1 else 0

                self.blit_game_over(screen)

            # Show FPS if needed
            if self.show_fps:
                blit_fps(screen, clock)

            pygame.display.flip()

class AvoidMineScreen(ScreenObject):
    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)
        self.show_fps = show_fps

    def loop(self, screen):
        running = True

        while running:
            curr_AvoidMine_screen = AvoidMineMainScreen(self.width, self.height, show_fps=self.show_fps)
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



class Mine:
    def __init__(self, location, size):
        self.location, self.size = location, size
        self.distance, self.image_number = 0, 1
        self.image_1 = pygame.transform.scale(pygame.image.load("data/AvoidMine/imgs/trap_mine.png"), (self.size, self.size))
        self.image_2 = pygame.transform.scale(pygame.image.load("data/AvoidMine/imgs/trap_mine.png"), (self.size, self.size))

    def check(self):
        mouse_pos_x, mouse_pos_y = pygame.mouse.get_pos()
        self.distance = ((mouse_pos_x - self.location[0]) ** 2 + (mouse_pos_y - self.location[1]) ** 2) ** 0.5
        if self.distance <= self.size:
            return True
        else:
            return False

    def draw(self, screen):
        if self.image_number == 1:
            screen.blit(self.image_1, self.location)
            self.image_number = 2
        else:
            screen.blit(self.image_2, self.location)
            self.image_number = 1



class TrapMine(Mine): #건들면 게임 오버
    def __init__(self, location, size):
        super().__init__(location, size)
        self.image_1 = pygame.transform.scale(pygame.image.load("data/AvoidMine/imgs/trap_mine.png"), (self.size, self.size))
        self.image_2 = pygame.transform.scale(pygame.image.load("data/AvoidMine/imgs/trap_mine.png"), (self.size, self.size))



class ScoreMine(Mine): #건들면 점수 얻음
    def __init__(self, screen_width, screen_height, location, size):
        self.scscreen_width = screen_width
        self.screen_height = screen_height
        super().__init__(location, size)
        self.image_1 = pygame.transform.scale(pygame.image.load("data/AvoidMine/imgs/score_mine.png"), (self.size, self.size))
        self.image_2 = pygame.transform.scale(pygame.image.load("data/AvoidMine/imgs/score_mine.png"), (self.size, self.size))

    def give_score(self, score, mine):
        if mine.check():
            mouse_pos_x, mouse_pos_y = pygame.mouse.get_pos()
            distance = ((mouse_pos_x - self.screen_width // 2) ** 2 + (mouse_pos_y - self.screen_height // 2) ** 2) ** 0.5
            score += int(distance // 30 + 2)

        return score



class Light:
    def __init__(self, screen_width, screen_height, default_speed, speed, diameter, size, angle):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.default_speed, self.speed, self.diameter, self.size = default_speed, speed, diameter, size #1은 시계, -1은 반시계
        self.angle, self.life, self.direction = 0, 255, 1
        self.trapezoid_points = [(-size, 0), (size, 0), (math.sin(math.radians(angle)) * screen_width + size, screen_width), (- math.sin(math.radians(angle)) * screen_width - size, screen_width)]
        self.rotated_points = self.trapezoid_points

    def change_speed(self, score): #마우스와 중심의 거리에 따른 속도 변화
        mouse_pos = pygame.mouse.get_pos()
        distance = ((self.screen_width//2 - mouse_pos[0]) ** 2 + (self.screen_height//2 - mouse_pos[1]) ** 2) ** (1/2)
        if score <= 200:
            self.speed = (distance / 1000 + self.default_speed) * self.diameter
        else:
            self.speed = (distance / 800 + self.default_speed * 1.2) * self.diameter

    def return_distance(self):
        mouse_pos = pygame.mouse.get_pos()
        distance = ((self.screen_width // 2 - mouse_pos[0]) ** 2 + (self.screen_height // 2 - mouse_pos[1]) ** 2) ** (1 / 2)

        return distance

    def triangle_check(self, point, p1, p2, p3): # 삼각현 내 점 확인
        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

        d1 = sign(point, p1, p2)
        d2 = sign(point, p2, p3)
        d3 = sign(point, p3, p1)

        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)

        return not (has_neg and has_pos)

    def quadrangl_check(self, point, p1, p2, p3, p4): # 사각형 내 점 확인
        result = []
        result.append(self.triangle_check(point, p1, p2, p3))
        result.append(self.triangle_check(point, p1, p3, p4))

        return True in result

    def mouse_check(self, distance): #life 계산
        mouse_pos = pygame.mouse.get_pos()
        if self.quadrangl_check(mouse_pos, *self.rotated_points) and self.life < 255 and distance >= self.size:
            self.life += 1  # 60fps 기준 2초 후에 life 135(life == 135일때 gameover)
        elif not self.quadrangl_check(mouse_pos, *self.rotated_points) and self.life > 75 and distance >= self.size:
            self.life -= 1

    def turn(self, chance): #chance는 1초에 발생활 확율 ex)0.3
        return_chance = random.random()
        if return_chance < chance / 60:
            self.direction *= -1
        self.angle += self.speed * self.direction
        self.rotated_points = []
        for x, y in self.trapezoid_points:
            rotated_x = x * math.cos(math.radians(self.angle)) - y * math.sin(math.radians(self.angle))
            rotated_y = x * math.sin(math.radians(self.angle)) + y * math.cos(math.radians(self.angle))
            self.rotated_points.append((rotated_x + self.screen_width//2, rotated_y + self.screen_height//2))

    def draw(self, screen):
        pygame.draw.polygon(screen, (self.life, self.life, self.life), self.rotated_points)
        pygame.draw.circle(screen, (self.life, self.life, self.life), (self.screen_width // 2, self.screen_height // 2), self.size)






# Run standalone
if __name__ == "__main__":
    pygame.init()
    WIDTH, HEIGHT = 1280, 720
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("AvoidMine")

    menu_screen = AvoidMineScreen(WIDTH, HEIGHT, show_fps=False)
    menu_screen.loop(screen)