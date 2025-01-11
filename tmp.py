import pygame
import random
import math
import sys
import os
from collections import deque
import multiprocessing
from multiprocessing import Pool

# We need gfxdraw for textured polygons
import pygame.gfxdraw

##############################################################################
#  HELPERS (taken from your code)
##############################################################################

def fade_in(screen, new_surface, width, height, duration_ms):
    """Simple fade-in of new_surface onto screen."""
    clock = pygame.time.Clock()
    alpha = 0
    step = 255 / (duration_ms / 16.67)  # ~60 FPS
    while alpha < 255:
        dt = clock.tick(60)
        alpha = min(alpha + step, 255)
        screen.fill((0,0,0))
        temp = new_surface.copy()
        temp.set_alpha(int(alpha))
        screen.blit(temp, (0, 0))
        pygame.display.flip()

def fade_out(screen, old_surface, width, height, duration_ms):
    """Simple fade-out of old_surface from screen."""
    clock = pygame.time.Clock()
    alpha = 255
    step = 255 / (duration_ms / 16.67)
    while alpha > 0:
        dt = clock.tick(60)
        alpha = max(alpha - step, 0)
        screen.fill((0,0,0))
        temp = old_surface.copy()
        temp.set_alpha(int(alpha))
        screen.blit(temp, (0, 0))
        pygame.display.flip()

def blit_fps(screen, clock, x=10, y=10):
    """Displays FPS in the top-left corner."""
    font = pygame.font.SysFont("Courier", 20)
    fps_text = font.render(str(int(clock.get_fps())), True, (255, 255, 255))
    screen.blit(fps_text, (x, y))

##############################################################################
#  ASTEROID SHAPE GENERATION
##############################################################################

def generate_random_convex_polygon(center, radius, vertex_count):
    angles = sorted([random.uniform(0, 2 * math.pi) for _ in range(vertex_count)])
    points = []
    for angle in angles:
        x = int(center[0] + radius * math.cos(angle))
        y = int(center[1] + radius * math.sin(angle))
        points.append((x, y))
    return points

def create_random_asteroid_surface(size=100, style="striped"):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))

    vertex_count = random.randint(5, 9)
    center = (size // 2, size // 2)
    radius = random.randint(size // 3, size // 2)
    polygon_points = generate_random_convex_polygon(center, radius, vertex_count)
    
    if style == "striped":
        stripe_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        stripe_color = (255, 255, 255)
        stripe_width = 2
        stripe_spacing = 10
        
        # Draw "\" diagonal stripes
        for x in range(-size, size, stripe_spacing):
            start_pos = (x, 0)
            end_pos = (x + size, size)
            pygame.draw.line(stripe_surf, stripe_color, start_pos, end_pos, stripe_width)
        
        pygame.gfxdraw.textured_polygon(surf, polygon_points, stripe_surf, 0, 0)
    
    elif style == "white_fill":
        pygame.gfxdraw.filled_polygon(surf, polygon_points, (255,255,255,255))
    
    elif style == "outline":
        pass

    pygame.draw.polygon(surf, (255, 255, 255), polygon_points, width=1)
    return surf

def rect_mask_collision(player_rect, asteroid_mask, asteroid_rect):
    if not player_rect.colliderect(asteroid_rect):
        return False
    
    offset_x = asteroid_rect.x - player_rect.x
    offset_y = asteroid_rect.y - player_rect.y
    rect_mask = pygame.mask.Mask((player_rect.width, player_rect.height), fill=True)
    overlap_point = rect_mask.overlap(asteroid_mask, (offset_x, offset_y))
    return (overlap_point is not None)

##############################################################################
#  UI CLASSES
##############################################################################

class MessageBox:
    def __init__(self, x, y, text, screen_height, height, padding, offset=0):
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
        
        alpha_factor = max(min((abs(self.offset)/(self.screen_height/20))*255, 255), 0)
        self.text_surface.set_alpha(255 - alpha_factor)
        self.background_surface.set_alpha(70 - (70 * alpha_factor/255))


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
            if event.button == 1 and self.rect.collidepoint(pygame.mouse.get_pos()):
                if not self.pressed:
                    self.mouse_y_init = pygame.mouse.get_pos()[1]
                self.pressed = True
                return 'Down'
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.pressed:
                self.pressed = False
                return 'Up'

    def update(self, mouse_pos):
        if self.pressed:
            if self.overlayAlpha != 200:
                self.overlayAlpha += self.overlayAlphaSpeed
                self.overlayAlpha = min(self.overlayAlpha, 200)
                self.overlay.set_alpha(self.overlayAlpha)
            self.mouse_y_curr = mouse_pos[1]
        else:
            self.hovered = self.rect.collidepoint(mouse_pos)
            if self.hovered:
                if self.overlayAlpha < 100:
                    self.overlayAlpha += self.overlayAlphaSpeed
                    self.overlayAlpha = min(self.overlayAlpha, 100)
                    self.overlay.set_alpha(self.overlayAlpha)
                else:
                    self.overlayAlpha -= self.overlayAlphaSpeed
                    self.overlayAlpha = max(self.overlayAlpha, 100)
                    self.overlay.set_alpha(self.overlayAlpha)
            else:
                if self.overlayAlpha != 0 and not self.pressed:
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
        screen.blit(self.text_surface, (
            self.rect.x + self.x_offset + self.image_rect.width + self.padding,
            self.rect.y - (self.text_rect.height - self.rect.height)/2
        ))

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

##############################################################################
#  PLAYER AND RELATED CLASSES
##############################################################################

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
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)

    def draw(self, screen, scroll_x, scroll_y):
        image_rect = self.image_curr.get_rect(center=(
            self.x - scroll_x + self.offset_x,
            self.y - scroll_y + self.offset_y
        ))
        screen.blit(self.image_curr, image_rect)
        self.rect.center = image_rect.center

    def handle_collision(self, ground_y):
        if self.y > ground_y:
            self.y = ground_y
            self.speed_y *= -2/3
            if abs(self.speed_y) < self.speed / 10:
                self.speed_y = (self.speed / abs(self.speed)) * (self.speed / 5)

    def update(self, mouse_pos, scroll_x=0, scroll_y=0):
        x_dist = mouse_pos[0] - (self.x - scroll_x + self.offset_x)
        y_dist = mouse_pos[1] - (self.y - scroll_y + self.offset_y)
        self.angle_target = math.degrees(math.atan2(-y_dist, x_dist))
        angle_diff = (self.angle_target - self.angle + 180) % 360 - 180

        if abs(angle_diff) > 0:
            self.angle += angle_diff / self.angle_speed
            if abs(angle_diff) < 1:
                self.angle = self.angle_target
        
        if self.angle_prev != self.angle:
            self.image_curr = pygame.transform.rotate(self.image, self.angle - 90)
            self.angle_prev = self.angle

        distance = math.hypot(x_dist, y_dist)
        if distance > 0:
            direction_x = x_dist / distance
            direction_y = y_dist / distance

            target_speed_x = direction_x * self.speed
            target_speed_y = direction_y * self.speed

            self.speed_x += (target_speed_x - self.speed_x) / self.inertia
            self.speed_y += (target_speed_y - self.speed_y) / self.inertia

            current_total_speed = math.hypot(self.speed_x, self.speed_y)
            if current_total_speed > self.speed:
                scale = self.speed / current_total_speed
                self.speed_x *= scale
                self.speed_y *= scale

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

        self.text_surface = self.font.render(text, True, (255, 255, 255))
        self.text_width = self.text_surface.get_width()
        self.text_height = self.text_surface.get_height()
            
        self.padding = self.text_height / 2
        self.pattern_width = self.width + self.text_width + self.padding * 2
    
    def draw(self, screen, scroll_x, scroll_y):
        start_x = scroll_x + (0 - scroll_x) % self.pattern_width - self.pattern_width
        end_x = start_x + (self.screen_width // self.pattern_width + 2) * self.pattern_width
        
        while start_x < end_x:
            pygame.draw.line(screen, (255,255,255),
                             (start_x - scroll_x, self.y - scroll_y + self.offset_y),
                             (start_x + self.width - scroll_x, self.y - scroll_y + self.offset_y),
                             1)
            screen.blit(self.text_surface, (
                start_x + self.width + self.padding - scroll_x,
                self.y - self.text_height/2 - scroll_y + self.offset_y
            ))
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

##############################################################################
#  MULTIPROCESSING ASTEROID LOGIC
##############################################################################

def boxes_intersect(a, b):
    """
    Simple bounding-box intersection check.
    a, b = (x, y, w, h)
    """
    return not (a[0] + a[2] < b[0] or
                a[0] > b[0] + b[2] or
                a[1] + a[3] < b[1] or
                a[1] > b[1] + b[3])

def worker_update_asteroid(data_tuple):
    """
    Runs inside a worker process.
    data_tuple = (
      x, y, speed_x, speed_y, angle, rotation_speed,
      player_rect (x, y, w, h),
      dt_ms,  # time since last frame in ms
    )
    """
    (x, y, speed_x, speed_y, angle, rotation_speed,
     player_x, player_y, player_w, player_h,
     dt_ms) = data_tuple

    dt = dt_ms / 1000.0

    # 1) Update position
    x += speed_x * dt
    y += speed_y * dt

    # 2) Update angle
    angle = (angle + rotation_speed) % 360

    # 3) Do a quick bounding-box collision check with the player
    #    We do not do pixel-perfect here.
    #    If there's a collision, let's do a simple bounce.
    asteroid_bbox = (x - 50, y - 50, 100, 100)  # Example bounding box
    player_bbox = (player_x - player_w//2, player_y - player_h//2, player_w, player_h)
    if boxes_intersect(asteroid_bbox, player_bbox):
        # Simple bounce
        speed_x = -speed_x * 0.8
        speed_y = -speed_y * 0.8

    return (x, y, speed_x, speed_y, angle, rotation_speed)

class AsteroidMP:
    """
    Multiprocessing-compatible Asteroid container:
      - We store only the minimal numeric data that we can pickle.
      - The actual surfaces and masks remain in the main process.
    """
    def __init__(self, x, y, speed_x, speed_y, angle, rotation_speed, asteroid_surface, asteroid_mask):
        # numeric
        self.x = x
        self.y = y
        self.speed_x = speed_x
        self.speed_y = speed_y
        self.angle = angle
        self.rotation_speed = rotation_speed

        # references to surfaces/masks in main thread
        self.original_image = asteroid_surface
        self.image = self.original_image.copy()
        self.mask = asteroid_mask
        self.rect = self.image.get_rect()

    def pack_for_worker(self, player_x, player_y, player_w, player_h, dt_ms):
        """Prepare data to send to the worker."""
        return (
            self.x,
            self.y,
            self.speed_x,
            self.speed_y,
            self.angle,
            self.rotation_speed,
            player_x, player_y, player_w, player_h,
            dt_ms
        )

    def unpack_worker_result(self, result_tuple):
        """
        Take the result from worker_update_asteroid(...)
        and update self in the main thread.
        """
        (self.x, self.y, self.speed_x, self.speed_y, self.angle, self.rotation_speed) = result_tuple

        # Re-rotate image in main thread if you want the rotated sprite
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        # If you need pixel-perfect collision, recreate the mask:
        self.mask = pygame.mask.from_surface(self.image)

    def draw(self, screen, scroll_x, scroll_y, offset_x, offset_y):
        image_rect = self.image.get_rect(center=(self.x - scroll_x + offset_x, 
                                                 self.y - scroll_y + offset_y))
        screen.blit(self.image, image_rect)
        self.rect = image_rect

##############################################################################
#  MAIN SCREEN WITH ASTEROIDS (USING MULTIPROCESSING)
##############################################################################

class StarshipMainScreen:
    def __init__(self, width, height, show_fps=False):
        self.width = width
        self.height = height
        self.show_fps = show_fps
        
        self.margin_x = self.height * 1/7
        self.margin_y = self.height * 2/7
        self.height_font = pygame.font.Font("SairaCondensed-Light.ttf", int(height/30))
        
        # Title image
        img_title = pygame.image.load("imgs/Starship/main_menu_title.png").convert_alpha()
        self.img_title = pygame.transform.smoothscale(
            img_title, 
            (int(self.height / 20 * (425 / 58)), int(self.height / 20))
        )
        
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
        img_start_button = pygame.transform.smoothscale(img_start_button, (int(height/10), int(height/10)))
        img_start_button_overlay = pygame.image.load("imgs/Starship/main_menu_start_blur.png").convert_alpha()
        img_start_button_overlay = pygame.transform.smoothscale(img_start_button_overlay, (int(height/4), int(height/4)))
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
        img_player = pygame.transform.smoothscale(img_player, (height//30, height//30))
        
        self.offset_player_x = width / 2
        self.offset_player_y = height / 2
        
        self.player_inertia = 100
        self.player = Player(0, 0, 10, 20, 500, img_player, self.offset_player_x, self.offset_player_y)

        self.ground = Ground(0, img_player.get_size()[0] / 2, width, height, self.offset_player_x, self.offset_player_y)
        
        # We'll store active asteroids here (as AsteroidMP objects)
        self.asteroids = []

        # Pre-generate a list of (surface, mask) pairs
        self.cached_asteroids = []
        NUM_PREGEN = 20
        for _ in range(NUM_PREGEN):
            image_size = random.randint(100, 150)
            style = random.choice(["striped", "white_fill", "outline"])
            asteroid_surface = create_random_asteroid_surface(image_size, style=style)
            asteroid_mask = pygame.mask.from_surface(asteroid_surface)
            self.cached_asteroids.append((asteroid_surface, asteroid_mask))

        self.asteroid_spawn_timer = 0
        self.asteroid_spawn_interval = 500
        self.max_asteroids = 15
        
        self.scroll_x = 0
        self.scroll_y = -1 * self.height / 10
        
        self.screen_state = 0  # 0 => main menu, 1 => gameplay
        self.score = 0
        
        self.trail = deque()
        self.particles = []
        
        # For dynamic line
        self.line = Line(-1000, '100', self.width, self.width, self.height_font, self.offset_player_y)

        # Multiprocessing Pool: 
        # You can tweak the number of processes. By default, cpu_count() is used.
        self.pool = Pool(processes=multiprocessing.cpu_count())

    def spawn_asteroid(self):
        spawn_distance = 700
        spawn_variation = 100
        movement_speed = math.hypot(self.player.speed_x, self.player.speed_y)
        
        if movement_speed == 0:
            # random spawn around screen edges
            spawn_side = random.choice(['top','bottom','left','right'])
            margin = 100
            if spawn_side == 'top':
                x = random.uniform(self.player.x - self.width/2 - margin, self.player.x + self.width/2 + margin)
                y = self.player.y - self.height - margin
            elif spawn_side == 'bottom':
                x = random.uniform(self.player.x - self.width/2 - margin, self.player.x + self.width/2 + margin)
                y = self.player.y + self.height + margin
            elif spawn_side == 'left':
                x = self.player.x - self.width/2 - margin
                y = random.uniform(self.player.y - self.height/2 - margin, self.player.y + self.height/2 + margin)
            else:
                x = self.player.x + self.width/2 + margin
                y = random.uniform(self.player.y - self.height/2 - margin, self.player.y + self.height/2 + margin)
        else:
            # spawn ahead of the player's movement
            direction_x = self.player.speed_x / movement_speed
            direction_y = self.player.speed_y / movement_speed
            x = self.player.x + direction_x * spawn_distance + random.uniform(-spawn_variation, spawn_variation)
            y = self.player.y + direction_y * spawn_distance + random.uniform(-spawn_variation, spawn_variation)

        (surf, msk) = random.choice(self.cached_asteroids)
        angle = 0
        rotation_speed = random.uniform(-1,1)
        speed_x = random.uniform(-2, 2)
        speed_y = random.uniform(-5, -1)

        asteroid = AsteroidMP(x, y, speed_x, speed_y, angle, rotation_speed, surf, msk)
        self.asteroids.append(asteroid)

    def blit_mainmenu(self, screen, state):
        # Title
        screen.blit(self.img_title, (self.margin_x, self.margin_y))
        mouse_pos = pygame.mouse.get_pos()
        
        for button in self.buttons:
            button.update(mouse_pos)
            button.draw(screen)
        
        self.start_button.update(mouse_pos)
        self.start_button.draw(screen)
        
        # MessageBoxes
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
        
        # If user swiped up enough before releasing
        if state == 'Up' and (self.start_button.mouse_y_init - self.start_button.mouse_y_curr >= self.height / 5):
            self.screen_state = 1

    def run_gameplay(self, screen, dt_ms):
        # Spawn new asteroids
        self.asteroid_spawn_timer += dt_ms
        if self.asteroid_spawn_timer >= self.asteroid_spawn_interval:
            if len(self.asteroids) < self.max_asteroids:
                self.spawn_asteroid()
            self.asteroid_spawn_timer = 0

        # 1) Prepare data for each asteroid to go to the worker
        #    We'll do a bounding-box collision approach in worker.
        player_w = self.player.rect.width
        player_h = self.player.rect.height
        player_x = self.player.x
        player_y = self.player.y

        asteroid_job_data = [
            a.pack_for_worker(player_x, player_y, player_w, player_h, dt_ms)
            for a in self.asteroids
        ]

        # 2) Process them in parallel
        results = self.pool.map(worker_update_asteroid, asteroid_job_data)

        # 3) Unpack results
        for asteroid, res in zip(self.asteroids, results):
            asteroid.unpack_worker_result(res)

        # 4) Remove off-screen or too-distant asteroids
        self.asteroids = [
            a for a in self.asteroids
            if a.y > self.player.y - 900 and
               math.hypot(a.x - self.player.x, a.y - self.player.y) < 2000
        ]

        # 5) Update Player
        self.player.update(pygame.mouse.get_pos(), self.scroll_x, self.scroll_y)
        self.player.handle_collision(self.ground.y)

        # 6) Camera scroll
        #    We do a slow "lerp" towards player's position
        lerp_speed = 0.06
        target_x = self.player.x + (self.player.speed_x * 20)
        target_y = self.player.y + (self.player.speed_y * 20)
        self.scroll_x += (target_x - self.scroll_x) * lerp_speed
        self.scroll_y += (target_y - self.scroll_y) * lerp_speed

        # 7) Draw everything
        #    Clear background
        screen.fill((105, 133, 162))

        # Ground
        if self.player.y > -1 * self.height * 2:
            self.ground.draw(screen, self.scroll_y)

        # Asteroids
        for a in self.asteroids:
            a.draw(screen, self.scroll_x, self.scroll_y, self.offset_player_x, self.offset_player_y)

        # Player
        self.player.draw(screen, self.scroll_x, self.scroll_y)

        # Score
        self.score = max((-1 * int(self.player.y)) // 30, 0)
        height_score = self.height_font.render(str(self.score), True, (255, 255, 255))
        height_score_rect = height_score.get_rect(center = (self.width/2, self.height * 7/8))
        screen.blit(height_score, height_score_rect)

        # Dynamic line, for demonstration
        height_range = max(round(self.score / 100) * 100, 100)
        if self.line.y != height_range:
            self.line.update(str(height_range))
            self.line.y = -1 * height_range * 30
        self.line.draw(screen, self.scroll_x, self.scroll_y)

    def loop(self, screen):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            dt_ms = clock.tick(60)
            state = None

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # Must terminate pool before sys.exit
                    self.pool.terminate()
                    self.pool.join()
                    pygame.quit()
                    sys.exit()

                if self.screen_state == 0:
                    # Main menu
                    button_state = self.start_button.handle_event(event)
                    if button_state is not None:
                        state = button_state

            if self.screen_state == 0:
                # MAIN MENU
                self.blit_mainmenu(screen, state)
            else:
                # GAMEPLAY
                self.run_gameplay(screen, dt_ms)

            if self.show_fps:
                blit_fps(screen, clock)

            pygame.display.flip()

##############################################################################
#  LOADING SCREEN (OPTIONAL)
##############################################################################

class StarshipLoadingScreen:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        
    def loop(self, screen):
        surface = pygame.Surface((self.width, self.height))
        surface.fill((26, 33, 46))
        
        image = pygame.image.load("imgs/Starship/main_menu_title.png").convert_alpha()
        image = pygame.transform.smoothscale(
            image, 
            (int(self.height // 20 * (425 / 58)), int(self.height // 20))
        )
        image_rect = image.get_rect(center=(self.width / 2, self.height / 2))
        surface.blit(image, image_rect)
        
        fade_in(screen, surface, self.width, self.height, 2000)
        return "menu", screen

##############################################################################
#  COMPOSITE SCREEN (ENTRY POINT)
##############################################################################

class StarshipScreen:
    def __init__(self, width, height, show_fps=False):
        self.width = width
        self.height = height
        self.show_fps = show_fps

    def loop(self, screen):
        running = True
        curr_starship_screen_idx = 1  # 0 => loading, 1 => main menu/gameplay
        screen_ids = {"loading": 0, "menu": 1}
        
        while running:
            if curr_starship_screen_idx == 0:
                # Optional loading screen
                curr_starship_screen = StarshipLoadingScreen(self.width, self.height)
                next_screen, curr_screen_surface = curr_starship_screen.loop(screen)
                curr_starship_screen_idx = screen_ids[next_screen]
                pygame.time.wait(2000)
                fade_out(screen, curr_screen_surface, self.width, self.height, 2000)
            
            elif curr_starship_screen_idx == 1:
                # Main / gameplay screen with multiprocessing
                curr_starship_screen = StarshipMainScreen(self.width, self.height, show_fps=self.show_fps)
                curr_starship_screen.loop(screen)

##############################################################################
#  STANDALONE RUN
##############################################################################

if __name__ == "__main__":
    # On Windows, multiprocessing requires this guard.
    multiprocessing.freeze_support()
    
    pygame.init()
    WIDTH, HEIGHT = 1280, 720
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Starship Demo with Multiprocessing")

    # Start composite screen
    starship_screen = StarshipScreen(WIDTH, HEIGHT, show_fps=True)
    starship_screen.loop(screen)
