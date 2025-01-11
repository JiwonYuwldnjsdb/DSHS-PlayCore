import pygame
import random
import math
import sys
from collections import deque
from PlayCoreLibraries import ScreenObject, fade_in, fade_out, blit_fps

# We need gfxdraw for textured polygons
import pygame.gfxdraw

# ---------------------------------------------------------------------------
#  POLYGON-GENERATION + ASTEROID STYLES
# ---------------------------------------------------------------------------

def generate_random_convex_polygon(center, radius, vertex_count):
    """
    Returns a list of (x, y) vertices for a random convex polygon
    with 'vertex_count' vertices, roughly within a circle of 'radius'
    around 'center'.
    """
    angles = sorted([random.uniform(0, 2 * math.pi) for _ in range(vertex_count)])
    points = []
    for angle in angles:
        x = int(center[0] + radius * math.cos(angle))
        y = int(center[1] + radius * math.sin(angle))
        points.append((x, y))
    return points

def create_random_asteroid_surface(size=100, style="striped"):
    """
    Creates a random convex shape on a transparent background, 
    with one of 3 styles:
      1) "striped"    : semi-transparent diagonal stripes
      2) "white_fill" : filled solid white
      3) "outline"    : only an outline, no fill
    Returns a pygame.Surface.
    """
    # 1) Prepare a square Surface with alpha
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))

    # 2) Generate random polygon
    vertex_count = random.randint(5, 9)
    center = (size // 2, size // 2)
    # Increase radius so polygon is reasonably large
    radius = random.randint(size // 3, size // 2)
    polygon_points = generate_random_convex_polygon(center, radius, vertex_count)
    
    # 3) Depending on style, draw the interior differently
    if style == "striped":
        # Create a “stripe pattern” surface
        stripe_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        stripe_color = (255, 255, 255)  # semi-transparent white
        stripe_width = 2
        stripe_spacing = 10
        
        # Draw "\" diagonal stripes
        for x in range(-size, size, stripe_spacing):
            start_pos = (x, 0)
            end_pos = (x + size, size)
            pygame.draw.line(stripe_surf, stripe_color, start_pos, end_pos, stripe_width)
        
        # Clip stripes to the polygon using gfxdraw.textured_polygon
        pygame.gfxdraw.textured_polygon(surf, polygon_points, stripe_surf, 0, 0)
    
    elif style == "white_fill":
        # Fill the polygon fully with opaque white
        pygame.gfxdraw.filled_polygon(surf, polygon_points, (255,255,255,255))
    
    elif style == "outline":
        # No interior. Just an outline below.
        pass

    # 4) Draw a thin white outline around the polygon (common to all styles)
    pygame.draw.polygon(surf, (255, 255, 255), polygon_points, width=1)

    return surf


# ---------------------------------------------------------------------------
#  COLLISION UTIL
# ---------------------------------------------------------------------------

def rect_mask_collision(player_rect, asteroid_mask, asteroid_rect):
    """
    Returns True if the player's rectangular bounding box (player_rect)
    collides with the asteroid's pixel mask (asteroid_mask) at asteroid_rect.
    """    
    # 1) Quick bounding-box check
    if not player_rect.colliderect(asteroid_rect):
        return False
    
    # 2) If bounding boxes collide, do mask-based overlap
    offset_x = asteroid_rect.x - player_rect.x
    offset_y = asteroid_rect.y - player_rect.y

    # Create a "filled" Mask the size of the player_rect
    rect_mask = pygame.mask.Mask((player_rect.width, player_rect.height), fill=True)

    overlap_point = rect_mask.overlap(asteroid_mask, (offset_x, offset_y))
    return (overlap_point is not None)


# ---------------------------------------------------------------------------
#  UI CLASSES
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
#  PARTICLE, ASTEROID, PLAYER CLASSES
# ---------------------------------------------------------------------------

class Particle:
    def __init__(self, x, y, size, offset_x, offset_y):
        self.rect = (x - size/2, y - size/2, size, size)
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.alpha = 100
    
    def draw(self, screen, scroll_x, scroll_y):
        temp_surface = pygame.Surface((self.rect[2], self.rect[3]), pygame.SRCALPHA)
        temp_surface.set_alpha(self.alpha)
        temp_surface.fill((255,255,255))
        screen.blit(temp_surface, (
            self.rect[0] - scroll_x + self.offset_x,
            self.rect[1] - scroll_y + self.offset_y
        ))
    
    def update(self):
        self.alpha -= 2


class Asteroid:
    """
    Each asteroid has:
      - A dynamically generated polygon image
      - A pygame.mask.Mask for pixel-perfect collision
      - A rect that is updated when drawn
      - Velocity and rotation attributes for movement and turning
    """
    def __init__(self, x, y, offset_x, offset_y, image, image_mask, screen_width, screen_height):
        self.x = x
        self.y = y
        self.offset_x = offset_x
        self.offset_y = offset_y
        
        self.original_image = image
        self.image = self.original_image.copy()
        
        # Use the pre-generated mask (instead of creating a new one)
        self.mask = image_mask
        self.rect = self.image.get_rect()
        
        # Movement attributes
        self.speed_x = random.uniform(-2, 2)   # Random horizontal speed
        self.speed_y = random.uniform(-5, -1)  # Random vertical speed (moving upwards)
        
        # Rotation attributes
        self.rotation_speed = random.uniform(-1, 1)  # Degrees per frame
        self.angle = 0  # Current rotation angle

    def update(self):
        # Update position based on velocity
        self.x += self.speed_x
        self.y += self.speed_y
        
        # Update rotation
        self.angle = (self.angle + self.rotation_speed) % 360
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        
        # If you want the mask to rotate as well:
        self.mask = pygame.mask.from_surface(self.image)

    def draw(self, screen, scroll_x, scroll_y):
        # Calculate on-screen position
        image_rect = self.image.get_rect(center=(
            self.x - scroll_x + self.offset_x,
            self.y - scroll_y + self.offset_y
        ))
        screen.blit(self.image, image_rect)
        self.rect = image_rect


class Player:
    """
    Player uses a simple bounding pygame.Rect for collisions (not pixel-perfect).
    """
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

        # Player bounding rect for collisions
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)

    def draw(self, screen, scroll_x, scroll_y):
        image_rect = self.image_curr.get_rect(center=(
            self.x - scroll_x + self.offset_x,
            self.y - scroll_y + self.offset_y
        ))
        screen.blit(self.image_curr, image_rect)
        
        # Update bounding rect center
        self.rect.center = image_rect.center

    def handle_collision(self, ground_y):
        if self.y > ground_y:
            self.y = ground_y
            self.speed_y *= -2/3
            if abs(self.speed_y) < self.speed / 10:
                # Give a small bounce if it nearly stops
                self.speed_y = (self.speed / abs(self.speed)) * (self.speed / 5)

    def update(self, mouse_pos, scroll_x=0, scroll_y=0):
        # Calculate the distance from the player to mouse
        x_dist = mouse_pos[0] - (self.x - scroll_x + self.offset_x)
        y_dist = mouse_pos[1] - (self.y - scroll_y + self.offset_y)

        # Calculate the angle to the mouse
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


# ---------------------------------------------------------------------------
#  EXTRA OBJECTS: LINE, GROUND
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
#  MAIN STARSHIP SCREEN (MENU / GAMEPLAY)
# ---------------------------------------------------------------------------

class StarshipMainScreen(ScreenObject):
    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)
        
        self.show_fps = show_fps
        
        self.margin_x = self.height * 1/7
        self.margin_y = self.height * 2/7
        
        self.height_font = pygame.font.Font("SairaCondensed-Light.ttf", int(height/30))
        
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

        self.paticles = []
        self.trail = deque()
        self.ground = Ground(0, img_player.get_size()[0] / 2, width, height, self.offset_player_x, self.offset_player_y)
        
        # We'll store active asteroids here
        self.astroids = []
        
        # -------------------------------------------------------------------
        # PRE-GENERATE ASTEROID SURFACES + MASKS
        # -------------------------------------------------------------------
        self.cached_asteroids = []
        NUM_PREGEN = 50  # Number of (surface, mask) pairs to generate
        for _ in range(NUM_PREGEN):
            image_size = random.randint(200, 250)
            style = random.choice(["striped", "white_fill", "outline"])
            
            # Create the polygon surface
            asteroid_surface = create_random_asteroid_surface(image_size, style=style)
            
            # Create mask once (so we don't have to do it on every spawn)
            asteroid_mask = pygame.mask.from_surface(asteroid_surface)
            
            # Store in the list
            self.cached_asteroids.append((asteroid_surface, asteroid_mask))
        
        # Asteroid spawning control
        self.asteroid_spawn_timer = 0
        self.asteroid_spawn_interval = 500  # spawn more frequently
        self.max_asteroids = 20  # maximum active asteroids

    def spawn_asteroid(self):
        """
        Spawn an asteroid in the direction the player is moving, outside
        the visible screen, using a pre-generated random polygon.
        """
        spawn_distance = 700
        spawn_variation = 100

        movement_speed = math.hypot(self.player.speed_x, self.player.speed_y)
        if movement_speed == 0:
            # Player is stationary; spawn asteroids randomly around
            spawn_side = random.choice(['top', 'bottom', 'left', 'right'])
            margin = 100
            if spawn_side == 'top':
                x = random.uniform(self.player.x - self.width / 2 - margin, 
                                   self.player.x + self.width / 2 + margin)
                y = self.player.y - self.height - margin
            elif spawn_side == 'bottom':
                x = random.uniform(self.player.x - self.width / 2 - margin, 
                                   self.player.x + self.width / 2 + margin)
                y = self.player.y + self.height + margin
            elif spawn_side == 'left':
                x = self.player.x - self.width / 2 - margin
                y = random.uniform(self.player.y - self.height / 2 - margin, 
                                   self.player.y + self.height / 2 + margin)
            else:  # right
                x = self.player.x + self.width / 2 + margin
                y = random.uniform(self.player.y - self.height / 2 - margin, 
                                   self.player.y + self.height / 2 + margin)
        else:
            # Player is moving; spawn asteroids ahead in the movement direction
            direction_x = self.player.speed_x / movement_speed
            direction_y = self.player.speed_y / movement_speed

            x = (self.player.x 
                 + direction_x * spawn_distance 
                 + random.uniform(-spawn_variation, spawn_variation))
            y = (self.player.y 
                 + direction_y * spawn_distance 
                 + random.uniform(-spawn_variation, spawn_variation))
        
        # Instead of generating a new surface + mask, pick a random one from the cache
        asteroid_surface, asteroid_mask = random.choice(self.cached_asteroids)
        
        new_asteroid = Asteroid(
            x, y,
            self.offset_player_x, self.offset_player_y,
            asteroid_surface,
            asteroid_mask,
            self.width, self.height
        )
        self.astroids.append(new_asteroid)

    def blit_mainmenu(self, screen, state):
        screen.blit(self.img_title, (self.margin_x, self.margin_y))
        
        mouse_pos = pygame.mouse.get_pos()
        
        for button in self.buttons:
            button.update(mouse_pos)
            button.draw(screen)
        
        self.start_button.update(mouse_pos)
        self.start_button.draw(screen)
        
        # Shift the MessageBox offsets depending on how far user drags up
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
        
        # If user releases mouse after dragging up a certain distance => start game
        if state == 'Up' and self.start_button.mouse_y_init - self.start_button.mouse_y_curr >= self.height / 5:
            self.screen_state = 1

    def loop(self, screen):
        clock = pygame.time.Clock()
        self.running = True

        """
        0: main menu
        1: gameplay
        """
        self.screen_state = 0
        
        self.scroll_x = 0
        self.scroll_y = -1 * self.height / 10
        
        self.lerp_speed = 0
        frame_count = 0
        self.score = 0
        
        self.line = Line(-1 * 100 * 10, '100', self.width, self.width, self.height_font, self.offset_player_y)
        
        while self.running:
            screen.fill((105, 133, 162))
            
            dt_ms = clock.tick(60)
            dt = dt_ms / 1000.0

            self.asteroid_spawn_timer += dt_ms
            if self.screen_state == 1 and self.asteroid_spawn_timer >= self.asteroid_spawn_interval:
                if len(self.astroids) < self.max_asteroids:
                    self.spawn_asteroid()
                self.asteroid_spawn_timer = 0  # Reset timer

            state = None
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                if self.screen_state == 0:
                    state = self.start_button.handle_event(event)
            
            # Draw ground if needed
            if self.player.y > -1 * self.height * 2:
                self.ground.draw(screen, self.scroll_y)
            
            # MAIN MENU
            if self.screen_state == 0:
                self.blit_mainmenu(screen, state)
            
            # GAMEPLAY
            if self.screen_state == 1:
                # Update & draw asteroids
                for asteroid in self.astroids:
                    asteroid.update()
                    asteroid.draw(screen, self.scroll_x, self.scroll_y)
                
                # Remove asteroids based on y or distance from player
                self.astroids = [
                    asteroid for asteroid in self.astroids
                    if asteroid.y > self.player.y - 900 and
                       math.hypot(asteroid.x - self.player.x, asteroid.y - self.player.y) < 1500
                ]
                
                # Update player
                if self.player_inertia != self.player.inertia:
                    self.player_inertia = max(self.player.inertia - 2, self.player_inertia)
                
                if self.lerp_speed != 0.1:
                    self.lerp_speed = min(self.lerp_speed + 0.0005, 0.1)
                
                self.player.update(pygame.mouse.get_pos(), self.scroll_x, self.scroll_y)
                self.player.handle_collision(self.ground.y)
                
                target_x = self.player.x + (self.player.speed_x * 20)
                target_y = self.player.y + (self.player.speed_y * 20)

                self.scroll_x += (target_x - self.scroll_x) * self.lerp_speed
                self.scroll_y += (target_y - self.scroll_y) * self.lerp_speed
                
                # Particles
                if frame_count % 3 == 0:
                    self.paticles.append(Particle(
                        self.player.x + random.randint(-self.height//80, self.height//80),
                        self.player.y + random.randint(-self.height//80, self.height//80),
                        random.randint(self.height//180, self.height//60),
                        self.offset_player_x, self.offset_player_y
                    ))
                
                for particle in self.paticles[:]:
                    particle.update()
                    particle.draw(screen, self.scroll_x, self.scroll_y)
                    if particle.alpha <= 0:
                        self.paticles.remove(particle)
                
                # Trail
                if frame_count % 3 == 0:
                    self.trail.append((self.player.x, self.player.y))
                
                if len(self.trail) > 45:
                    self.trail.popleft()
                
                trail_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
                for i in range(len(self.trail)-1):
                    start_pos = (
                        self.trail[i][0] - self.scroll_x + self.offset_player_x,
                        self.trail[i][1] - self.scroll_y + self.offset_player_y
                    )
                    end_pos = (
                        self.trail[i+1][0] - self.scroll_x + self.offset_player_x,
                        self.trail[i+1][1] - self.scroll_y + self.offset_player_y
                    )
                    pygame.draw.line(trail_surface, (255,255,255), start_pos, end_pos, max(i // 4, 1))
                trail_surface.set_alpha(50)
                screen.blit(trail_surface, (0,0))
                
                # Score
                self.score = max((-1 * int(self.player.y)) // 30, 0)
                
                height_range = max(round(self.score / 100) * 100, 100)
                if self.line.y != height_range:
                    self.line.update(str(height_range))
                    self.line.y = -1 * height_range * 30
                self.line.draw(screen, self.scroll_x, self.scroll_y)
                
                # Blit Score
                height_score = self.height_font.render(str(self.score), True, (255, 255, 255))
                height_score_rect = height_score.get_rect(center = (self.width/2, self.height * 7/8))
                screen.blit(height_score, height_score_rect)

                # COLLISION RESPONSE: Player vs Asteroids
                for asteroid in self.astroids:
                    if math.hypot(asteroid.rect.x - self.player.rect.x, asteroid.rect.y - self.player.rect.y) >= self.height / 2:
                        continue
                    
                    # Actual mask-based check
                    if rect_mask_collision(self.player.rect, pygame.mask.from_surface(asteroid.image), asteroid.rect):
                        # Decompose velocity into normal & tangential components
                        dx = self.player.x - asteroid.x
                        dy = self.player.y - asteroid.y
                        dist = math.hypot(dx, dy)
                        if dist == 0:
                            dist = 1.0
                        nx = dx / dist
                        ny = dy / dist

                        vx, vy = self.player.speed_x, self.player.speed_y

                        dot = vx * nx + vy * ny  # how much velocity is along the normal
                        # normal component
                        vnx = dot * nx
                        vny = dot * ny
                        # tangential component
                        vtx = vx - vnx
                        vty = vy - vny

                        # new normal: reverse sign, half magnitude
                        vnx_new = -0.5 * vnx
                        vny_new = -0.5 * vny
                        # new tangential: keep sign, half magnitude
                        vtx_new = 0.5 * vtx
                        vty_new = 0.5 * vty

                        # combine
                        vx_new = vnx_new + vtx_new
                        vy_new = vny_new + vty_new

                        self.player.speed_x = vx_new
                        self.player.speed_y = vy_new

                        # push out so we don't remain inside
                        push_dist = 10
                        self.player.x += nx * push_dist
                        self.player.y += ny * push_dist
                        
                        self.player.inertia = 400
            
            # Draw Player
            self.player.draw(screen, self.scroll_x, self.scroll_y)
            
            # Show FPS if needed
            if self.show_fps:
                blit_fps(screen, clock)

            frame_count += 1
            pygame.display.flip()


# ---------------------------------------------------------------------------
#  LOADING SCREEN
# ---------------------------------------------------------------------------

class StarshipLoadingScreen(ScreenObject):
    def __init__(self, width, height):
        super().__init__(width, height)
        
    def loop(self, screen):
        surface = pygame.Surface((self.width, self.height))
        surface.fill((26, 33, 46))
        
        image = pygame.image.load("imgs/Starship/main_menu_title.png").convert_alpha()
        image = pygame.transform.smoothscale(
            image, 
            (int(self.height // 20 * (425 / 58)), int(self.height // 20))
        )
        image_rect = image.get_rect()
        image_rect.center = (self.width / 2, self.height / 2)
        
        surface.blit(image, image_rect)
        
        fade_in(screen, surface, self.width, self.height, 2000)
        return "menu", screen


# ---------------------------------------------------------------------------
#  COMPOSITE SCREEN (ENTRY POINT)
# ---------------------------------------------------------------------------

class StarshipScreen(ScreenObject):
    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)
        self.show_fps = show_fps

    def loop(self, screen):
        running = True
        # If you want a loading screen first, set curr_starship_screen_idx = 0
        # If you want to skip straight to the menu, set it = 1
        curr_starship_screen_idx = 1

        screen_ids = {
            "loading": 0,
            "menu": 1
        }
        
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


# ---------------------------------------------------------------------------
#  STANDALONE RUN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pygame.init()
    WIDTH, HEIGHT = 1280, 720
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Starship Demo with 3 Asteroid Styles")

    menu_screen = StarshipScreen(WIDTH, HEIGHT, show_fps=True)
    menu_screen.loop(screen)
