import pygame
import random
import math
import sys
from collections import deque

from PlayCoreLibraries import ScreenObject, fade_in, fade_out, blit_fps

pygame.init()

class MessageBox():
    def __init__(self, x, y, text, screen_height, height, padding, offset = 0):
        self.font = pygame.font.Font("SairaCondensed-Light.ttf", int(height))
        self.offset = offset
        self.offset_target = offset
        self.offset_speed = 10
        
        self.screen_height = screen_height
        self.y = y
        
        self.text_surface = self.font.render(text, True, (255,255,255)).convert_alpha()
        self.text_surface.set_alpha(255)
        self.text_rect = self.text_surface.get_rect(center=(x,y))

        self.background_width = self.text_rect.width + 2 * padding
        self.background_height = self.text_rect.height
        self.background_surface = pygame.Surface((self.background_width, self.background_height), pygame.SRCALPHA)
        self.background_surface.fill((0,0,0))
        self.background_surface.set_alpha(70)
        self.background_rect = self.background_surface.get_rect(center=(x,y))
        self.initial_y = self.background_rect.y
    
    def draw(self, screen):
        self.background_rect.y = self.initial_y + self.offset
        screen.blit(self.background_surface, self.background_rect)
        
        self.text_rect.y = self.initial_y + self.offset
        screen.blit(self.text_surface, self.text_rect)
    
    def update(self, offset):
        self.offset_target = offset
        
        if abs(self.offset_target - self.offset) != 0:
            self.offset += (self.offset_target - self.offset) / self.offset_speed
            
            if abs(self.offset_target - self.offset) < 1:
                self.offset = self.offset_target
        
        self.text_surface.set_alpha(255-max(min((abs(self.offset)/(self.screen_height/20))*255, 255), 0))
        self.background_surface.set_alpha(70-max(min((abs(self.offset)/(self.screen_height/20))*70, 70), 0))

class ImageButton:
    def __init__(self, x, y, image, overlay):
        self.image = image
        self.overlay = overlay
        self.rect = self.image.get_rect(center=(x, y))
        self.overlay_rect = self.overlay.get_rect(center=(x, y))
        self.hovered = False
        self.pressed = False
        
        self.mouse_y_init = 0
        self.mouse_y_curr = 0
        
        self.overlayAlpha = 0
        self.overlay.set_alpha(self.overlayAlpha)
        self.overlayAlphaSpeed = 5

    def draw(self, screen):
        if self.overlayAlpha != 0:
            screen.blit(self.overlay, self.overlay_rect)
        
        screen.blit(self.image, self.rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.hovered:
                if not self.pressed:
                    self.mouse_y_init = pygame.mouse.get_pos()[1]
                self.pressed = True
                return 'Down'
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.pressed:
                self.pressed = False
                return 'Up'

    def update(self, mouse_pos):
        if self.pressed == True:
            if self.overlayAlpha != 200:
                self.overlayAlpha += self.overlayAlphaSpeed
                self.overlayAlpha = min(self.overlayAlpha, 200)
                self.overlay.set_alpha(self.overlayAlpha)
                
            self.mouse_y_curr = pygame.mouse.get_pos()[1]
        else:
            if self.rect.collidepoint(mouse_pos):
                self.hovered = True
                if self.overlayAlpha != 100:
                    if self.overlayAlpha < 100:
                        self.overlayAlpha += self.overlayAlphaSpeed
                        self.overlayAlpha = min(self.overlayAlpha, 100)
                        self.overlay.set_alpha(self.overlayAlpha)
                    else:
                        self.overlayAlpha -= self.overlayAlphaSpeed
                        self.overlayAlpha = max(self.overlayAlpha, 100)
                        self.overlay.set_alpha(self.overlayAlpha)
            else:
                self.hovered = False
                if self.overlayAlpha != 0 and self.pressed == False:
                    self.overlayAlpha -= self.overlayAlphaSpeed
                    self.overlayAlpha = max(self.overlayAlpha, 0)
                    self.overlay.set_alpha(self.overlayAlpha)

class ShiftingButton:
    def __init__(self, x, y, image, text, x_shift_distance):
        self.image = image
        self.text = text

        self.image_rect = self.image.get_rect()

        self.height = self.image_rect.height

        self.padding = self.image_rect.width / 3

        self.hovered = False
        
        self.x_target = 0
        self.x_shift_distance = x_shift_distance
        self.x_speed = 10
        self.x_offset = 0
        
        self.font = pygame.font.Font("SairaCondensed-Light.ttf", int(self.height * 0.8))
        
        self.text_surface = self.font.render(self.text, True, (255,255,255))
        self.text_rect = self.text_surface.get_rect()
        
        self.width = self.height * 10
        self.rect = pygame.Rect(x, y, self.width, self.height)

    def draw(self, screen):
        screen.blit(self.image, (self.rect.x + self.x_offset, self.rect.y))
        screen.blit(self.text_surface, (self.rect.x + self.x_offset + self.image_rect.width + self.padding, self.rect.y - (self.text_rect.height - self.rect.height)/2))

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)
        
        if self.hovered:
            self.x_target = self.x_shift_distance
        else:
            self.x_target = 0
        
        if abs(self.x_target - self.x_offset) != 0:
            self.x_offset += (self.x_target - self.x_offset) / self.x_speed
            
            if abs(self.x_target - self.x_offset) < 1:
                self.x_offset = self.x_target

class Particle:
    def __init__(self, x, y, size, offset_x, offset_y):
        self.rect = (x - size/2, y - size/2, size, size)
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.alpha = 100
    
    def draw(self, screen, scroll_x, scroll_y):
        temp_surface = pygame.Surface((self.rect[2], self.rect[3]), pygame.SRCALPHA)  # 투명도를 지원
        temp_surface.set_alpha(self.alpha)  # 투명도 설정
        temp_surface.fill((255,255,255))  # 색상 채우기
        screen.blit(temp_surface, (self.rect[0] - scroll_x + self.offset_x, self.rect[1] - scroll_y + self.offset_y))
    
    def update(self):
        self.alpha -= 2

class Asteroid:
    astroid_imgs_size = [(29, 40), (61, 42), (89, 53), (111, 69), (139, 98), (156, 108), (221, 144), (30, 41), (62, 43), (90, 54), (112, 70), (140, 99), (157, 109), (222, 145), (30, 41), (62, 43), (90, 54), (112, 70), (140, 99), (157, 109), (222, 145)]
    
    def __init__(self, x, y, offset_x, offset_y, type, image, screen_width, screen_height):
        self.x = x
        self.y = y
        self.offset_x = offset_x
        self.offset_y = offset_y
        
        image_size = image.get_size()
        self.image = pygame.transform.smoothscale(image, ((screen_width/25) * (Asteroid.astroid_imgs_size[type][0]/Asteroid.astroid_imgs_size[0][0]), (screen_width/25) * (image_size[1]/image_size[0]) * (Asteroid.astroid_imgs_size[type][0]/Asteroid.astroid_imgs_size[0][0])))
    
    def draw(self, screen, scroll_x, scroll_y):
        image_rect = self.image.get_rect(center=(self.x - scroll_x + self.offset_x, self.y - scroll_y + self.offset_y))
        screen.blit(self.image, image_rect)

class Player:
    def __init__(self, x, y, speed, turning, inertia, image, offset_player_x, offset_player_y):
        self.x = x
        self.y = y
        self.speed_x = 0
        self.speed_y = 0
        self.speed = speed
        
        self.angle = 90
        self.angle_speed = turning
        self.angle_prev = 0
        self.angle_target = 0
        
        self.image = pygame.transform.rotate(image, 90)
        self.image_curr = self.image
        
        self.inertia = inertia
        self.offset_x = offset_player_x
        self.offset_y = offset_player_y
        
        self.size = self.image.get_rect().width
    
    def draw(self, screen, scroll_x, scroll_y):
        image_rect = self.image_curr.get_rect(center=(self.x - scroll_x + self.offset_x, self.y - scroll_y + self.offset_y))
        screen.blit(self.image_curr, image_rect)

    def handle_colllision(self, rects, ground_y):
        if self.y > ground_y:
            self.y = ground_y
            self.speed_y *= -2/3
            if abs(self.speed_y) < self.speed / 10:
                self.speed_y = (self.speed / abs(self.speed)) * (self.speed / 5)

    def update(self, mouse_pos, scroll_x=0, scroll_y=0):
        # Calculate the distance from the object to the mouse position
        x_dist = mouse_pos[0] - (self.x - scroll_x + self.offset_x)
        y_dist = mouse_pos[1] - (self.y - scroll_y + self.offset_y)

        # Calculate the angle to the mouse position
        self.angle_target = math.degrees(math.atan2(-y_dist, x_dist))

        # Normalize the angles to prevent sudden jumps
        angle_diff = (self.angle_target - self.angle + 180) % 360 - 180

        # Adjust the angle with decreasing speed
        if abs(angle_diff) > 0:
            # Smooth the rotation speed (fast initially, slower near the target)
            self.angle += angle_diff / self.angle_speed

            # Snap to target angle if close enough
            if abs(angle_diff) < 1:
                self.angle = self.angle_target
        
        # Rotate the image only if the angle has changed
        if self.angle_prev != self.angle:
            self.image_curr = pygame.transform.rotate(self.image, self.angle - 90)
            self.angle_prev = self.angle

        # Calculate the total distance
        distance = math.hypot(x_dist, y_dist)

        if distance > 0:  # Prevent division by zero
            # Normalize direction
            direction_x = x_dist / distance
            direction_y = y_dist / distance

            # Calculate target speeds
            target_speed_x = direction_x * self.speed
            target_speed_y = direction_y * self.speed

            # Gradually adjust speed_x and speed_y with inertia
            self.speed_x += (target_speed_x - self.speed_x) / self.inertia
            self.speed_y += (target_speed_y - self.speed_y) / self.inertia

            # Normalize speeds to ensure the total does not exceed self.speed
            current_total_speed = math.hypot(self.speed_x, self.speed_y)
            if current_total_speed > self.speed:
                scale = self.speed / current_total_speed
                self.speed_x *= scale
                self.speed_y *= scale

            # Update position
            self.x += self.speed_x
            self.y += self.speed_y

class Line:
    def __init__(self, y, text, width, screen_width, font, offset_y):
        self.y = y
        self.text = text
        self.width = width
        self.screen_width = screen_width
        self.font = font
        self.offset_y = offset_y

        # 텍스트 서피스 미리 렌더링
        self.text_surface = self.font.render(text, True, (255, 255, 255))
        self.text_width = self.text_surface.get_width()
        self.text_height = self.text_surface.get_height()
            
        self.padding = self.text_height / 2
        self.pattern_width = self.width + self.text_width + self.padding * 2
    
    def draw(self, screen, scroll_x, scroll_y):
        start_x = scroll_x + (0 - scroll_x) % self.pattern_width - self.pattern_width
        end_x = start_x + (self.screen_width // self.pattern_width + 2) * self.pattern_width
        
        while start_x < end_x:
            pygame.draw.line(screen, (255,255,255), (start_x - scroll_x, self.y - scroll_y + self.offset_y), (start_x + self.width - scroll_x, self.y - scroll_y + self.offset_y), 1)

            screen.blit(self.text_surface, (start_x + self.width + self.padding - scroll_x, self.y - self.text_height/2 - scroll_y + self.offset_y))
            
            start_x += self.pattern_width
    
    def update(self, text):
        self.text = text
        self.text_surface = self.font.render(text, True, (255, 255, 255))
        self.text_width = self.text_surface.get_width()
        self.text_height = self.text_surface.get_height()

class Ground:
    def __init__(self, x, y, width, height, offset_player_x, offset_player_y):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.offset_x = offset_player_x
        self.offset_y = offset_player_y
    
    def draw(self, screen, scroll_y):
        rect = (self.x, self.y - scroll_y + self.offset_y, self.width, self.height)
        pygame.draw.rect(screen, (66, 62, 79), rect)

class StarshipMainScreen(ScreenObject):
    def __init__(self, width, height, show_fps = False):
        super().__init__(width, height)
        
        self.show_fps = show_fps
        
        self.margin_x = self.height * 1/7
        self.margin_y = self.height * 2/7
        
        self.height_font = pygame.font.Font("SairaCondensed-Light.ttf", int(height/30))
        
        img_title = pygame.image.load("imgs/Starship/main_menu_title.png").convert_alpha()
        self.img_title = pygame.transform.smoothscale(img_title, (self.height / 20 * (425 / 58), self.height / 20))
        
        self.buttons = []
        
        desired_size = int(self.height / 27)

        img_info = pygame.image.load("imgs/Starship/info.png").convert_alpha()
        img_info = pygame.transform.smoothscale(img_info, (desired_size, desired_size))

        button_info = ShiftingButton(
            self.margin_x,
            self.margin_y + self.height * (1/10 + 1/60),
            img_info,
            "HELP",
            int(self.height / 30 * 2/3)
        )
        self.buttons.append(button_info)

        img_nut = pygame.image.load("imgs/Starship/nut.png").convert_alpha()
        img_nut = pygame.transform.smoothscale(img_nut, (desired_size, desired_size))

        button_nut = ShiftingButton(
            self.margin_x,
            self.margin_y + self.height * (1/10 + 1/60 * 2 + 1/30),
            img_nut,
            "OPTIONS",
            int(self.height / 30 * 2/3)
        )
        self.buttons.append(button_nut)

        img_credit = pygame.image.load("imgs/Starship/credit.png").convert_alpha()
        img_credit = pygame.transform.smoothscale(img_credit, (desired_size, desired_size))

        button_credit = ShiftingButton(
            self.margin_x,
            self.margin_y + self.height * (1/10 + 1/60 * 3 + 1/30*2),
            img_credit,
            "CREDITS",
            int(self.height / 30 * 2/3)
        )
        self.buttons.append(button_credit)
        
        img_start_button = pygame.image.load("imgs/Starship/main_menu_start_button.png").convert_alpha()
        img_start_button = pygame.transform.smoothscale(img_start_button, (height/10, height/10))
        
        img_start_button_overlay = pygame.image.load("imgs/Starship/main_menu_start_blur.png").convert_alpha()
        img_start_button_overlay = pygame.transform.smoothscale(img_start_button_overlay, (height/4, height/4))
        
        self.start_button = ImageButton(width/2, height * 3/4, img_start_button, img_start_button_overlay)
        
        self.message_boxes = []
        self.offset = [0, height/20, height/20 * 2]
        
        press = MessageBox(width/2, height * 7/8, "TO LAUNCH, HOLD THE BUTTON", height, height/40, height/80, self.offset[0])
        self.message_boxes.append(press)
        
        swipe = MessageBox(width/2, height * 7/8, "SWIPE UP TO LAUNCH", height, height/40, height/80, self.offset[1])
        self.message_boxes.append(swipe)
        
        release = MessageBox(width/2, height * 7/8, "RELEASE", height, height/40, height/80, self.offset[2])
        self.message_boxes.append(release)
        
        img_player = pygame.image.load("imgs/Starship/ship_1.png").convert_alpha()
        img_player = pygame.transform.smoothscale(img_player, (height/30, height/30))
        
        self.offset_player_x = width / 2
        self.offset_player_y = height / 2
        
        self.player_inertia = 100
        self.player = Player(0, 0, 10, 20, 500, img_player, self.offset_player_x, self.offset_player_y)

        self.paticles = []
        
        self.trail = deque()
        
        self.ground = Ground(0, img_player.get_size()[0] / 2, width, height, self.offset_player_x, self.offset_player_y)
        
        self.astroid_imgs = []
        
        for i in range(1, 22):
            self.astroid_imgs.append(pygame.image.load(f"imgs/Starship/asteroid/asteroid{i}.png").convert_alpha())
        
        self.astroids = []
        
    def blit_mainmenu(self, screen, state):
        screen.blit(self.img_title, (self.margin_x, self.margin_y))
        
        mouse_pos = pygame.mouse.get_pos()
        
        for button in self.buttons:
            button.update(mouse_pos)
            button.draw(screen)
        
        self.start_button.update(mouse_pos)
        self.start_button.draw(screen)
        
        for i in range(3):
            message_box = self.message_boxes[i]
            if self.start_button.pressed:
                if self.start_button.mouse_y_init - self.start_button.mouse_y_curr >= self.height / 5:
                    self.offset[i] = self.height/20 * (i - 2)
                else:
                    self.offset[i] = self.height/20 * (i - 1)
            else:
                self.offset[i] = self.height/20 * i
            message_box.update(self.offset[i])
            message_box.draw(screen)
        
        if state == 'Up' and self.start_button.mouse_y_init - self.start_button.mouse_y_curr >= self.height / 5:
            self.screen_state = 1
    
    def loop(self, screen):
        clock = pygame.time.Clock()
        self.running = True

        """
        0: mainmenu
        1: gameplay
        """
        self.screen_state = 0
        
        self.scroll_x = 0
        self.scroll_y = -1 * self.height / 10
        
        self.lerp_speed = 0
        
        frame_count = 0
        
        self.score = 0
        
        self.line = Line(-1 * 100 * 30, '100', self.width, self.width, self.height_font, self.offset_player_y)
        
        # self.astroids.append(Asteroid(0, -1 * 20 * 30, self.offset_player_x, self.offset_player_y, 6, self.astroid_imgs[6], self.width, self.height))
        
        for i in range(21):
            self.astroids.append(Asteroid(500 * i, -1 * 20 * 30, self.offset_player_x, self.offset_player_y, i, self.astroid_imgs[i], self.width, self.height))
        
        while self.running:
            screen.fill((105, 133, 162))
            # screen.fill((255,0,0)) # for testing
            
            # Get delta time in seconds
            dt_ms = clock.tick(60)
            dt = dt_ms / 1000.0

            state = None
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                if self.screen_state == 0:
                    state = self.start_button.handle_event(event)
            
            if self.player.y > -1 * self.height * 2:
                self.ground.draw(screen, self.scroll_y)
            
            if self.screen_state == 0:
                self.blit_mainmenu(screen, state)
            
            if self.screen_state == 1:
                
                ### Collision with asteroid and player ###
                ### inore collision between asteroids
                
                ### Blit Asteroid ###
                
                for asteroid in self.astroids:
                    asteroid.draw(screen, self.scroll_x, self.scroll_y)
                
                ### Update Player ###
                
                if self.player_inertia != self.player.inertia and self.lerp_speed != 0.1:
                    self.player.inertia = max(self.player.inertia - 2, self.player_inertia)
                    
                    self.lerp_speed = min(self.lerp_speed + 0.0005, 0.1)
                
                self.player.update(pygame.mouse.get_pos(), self.scroll_x, self.scroll_y)
                
                self.player.handle_colllision([], self.ground.y)
                
                target_x = self.player.x + (self.player.speed_x * 20)  # 속도에 따라 앞서 이동
                target_y = self.player.y + (self.player.speed_y * 20)  # 속도에 따라 앞서 이동

                self.scroll_x += (target_x - self.scroll_x) * self.lerp_speed
                self.scroll_y += (target_y - self.scroll_y) * self.lerp_speed
                
                ### Particle ###
                
                if frame_count % 3 == 0:
                    self.paticles.append(Particle(self.player.x + random.randint(int(-1 * self.height / 80), int(self.height / 80)), self.player.y + random.randint(int(-1 * self.height / 80), int(self.height / 80)), random.randint(int(self.height/180), int(self.height/60)), self.offset_player_x, self.offset_player_y))
                
                for particle in self.paticles:
                    particle.update()
                    particle.draw(screen, self.scroll_x, self.scroll_y)
                    
                    if particle.alpha <= 0:
                        self.paticles.remove(particle)
                
                ### Trail ###
                
                if frame_count % 3 == 0:
                    self.trail.append((self.player.x, self.player.y))
                
                if len(self.trail) > 45:
                    self.trail.popleft()
                
                trail_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
                for i in range(len(self.trail)-1):
                    start_pos = (self.trail[i][0] - self.scroll_x + self.offset_player_x, self.trail[i][1] - self.scroll_y + self.offset_player_y)
                    end_pos = (self.trail[i+1][0] - self.scroll_x + self.offset_player_x, self.trail[i+1][1] - self.scroll_y + self.offset_player_y)
                    pygame.draw.line(trail_surface, (255,255,255), start_pos, end_pos, max(i // 4, 1))
                    
                trail_surface.set_alpha(50)
                screen.blit(trail_surface, ((0,0)))
                
                ### Calculate Score ###
                
                self.score = max((-1 * int(self.player.y)) // 30, 0)
                
                ### Update & Blit Line ###
                
                height_range = max(round(self.score / 100) * 100, 100)
                
                if self.line.y != height_range:
                    self.line.update(str(height_range))
                    self.line.y = -1 * height_range * 30
                
                self.line.draw(screen, self.scroll_x, self.scroll_y)
                
                ### Blit Score ###
                
                height_score = self.height_font.render(str(self.score), True, (255, 255, 255))
                height_score_rect = height_score.get_rect(center = (self.width/2, self.height * 7/8))
                screen.blit(height_score, height_score_rect)
            
            ### Blit Player ###
            
            self.player.draw(screen, self.scroll_x, self.scroll_y)
        
            if self.show_fps:
                blit_fps(screen, clock)

            frame_count += 1
            pygame.display.flip()

class StarshipLoadingScreen(ScreenObject):
    def __init__(self, width, height):
        super().__init__(width, height)
        
    def loop(self, screen):        
        surface = pygame.Surface((self.width, self.height))  # Width=200, Height=150
        surface.fill((26, 33, 46))
        
        image = pygame.image.load("imgs/Starship/main_menu_title.png").convert_alpha()
        image = pygame.transform.smoothscale(image, (self.height / 20 * (425 / 58), self.height / 20))
        image_rect = image.get_rect()
        image_rect.center = (self.width / 2, self.height / 2)
        
        surface.blit(image, image_rect)
        
        fade_in(screen, surface, self.width, self.height, 2000)
        
        return "menu", screen

class StarshipScreen(ScreenObject):
    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)

        self.show_fps = show_fps

    def loop(self, screen):
        running = True

        curr_starship_screen_idx = 1 # change to 0
        
        screen_ids = {
            "loading": 0,
            "menu": 1
        }
        
        """
        0 : Loading screen
        1 : Starship
        """

        while running:
            if curr_starship_screen_idx == 0:
                curr_starship_screen = StarshipLoadingScreen(self.width, self.height)
                
                next_screen, curr_screen_surface = curr_starship_screen.loop(screen)
            
                curr_starship_screen_idx = screen_ids[next_screen]
                
                pygame.time.wait(2000)
                fade_out(screen, curr_screen_surface, self.width, self.height, 2000)
            
            elif curr_starship_screen_idx == 1:
                curr_starship_screen = StarshipMainScreen(self.width, self.height, show_fps=self.show_fps)
                curr_starship_screen.loop(screen)

# Run standalone
if __name__ == "__main__":
    WIDTH, HEIGHT = 1280, 720
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("StarshipDemo")

    menu_screen = StarshipScreen(WIDTH, HEIGHT, show_fps=True)
    menu_screen.loop(screen)