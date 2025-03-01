import pygame
import random
import sys

from localLibraries.PlayCoreLibraries import ScreenObject, blit_fps

pygame.init()

class Square:
    """
    Floating square class with transparency, rotation, and upward movement.
    Movement now uses delta-time (dt) to remain constant across frame rates.
    """
    def __init__(self, x, size, speed, angle_speed, screen_height):
        self.size = size
        self.x = x
        self.y = screen_height
        # Speeds are now in pixels per second
        self.speed = speed         # upward speed
        self.angle_speed = angle_speed  # degrees per second
        self.angle = 0
        # Use float alpha, so we can decrement smoothly
        self.alpha = 15.0  
        self.surface = pygame.Surface((size, size), pygame.SRCALPHA)
        self.surface.fill((255, 255, 255, int(self.alpha)))  # Semi-transparent white

    def update(self, dt):
        """
        Update position, rotation, and alpha fade using delta-time (dt in seconds).
        """
        # Move upward
        self.y -= self.speed * dt

        # Rotate
        self.angle += self.angle_speed * dt
        self.angle %= 360

        # Fade out over time
        # Originally you did 'alpha -= 0.02' each frame;
        # at 60 FPS, that’s 1.2 alpha per second.
        # So let's do alpha -= 1.2 * dt
        fade_per_second = 1.2  
        self.alpha -= fade_per_second * dt
        if self.alpha < 0:
            self.alpha = 0

        # Update surface alpha
        self.surface.fill((255, 255, 255, int(self.alpha)))

    def draw(self, screen):
        # Rotate the square
        rotated_surface = pygame.transform.rotate(self.surface, self.angle)
        # Get the new rectangle bounds after rotation
        rect = rotated_surface.get_rect(center=(self.x, self.y))
        # Draw the rotated square
        screen.blit(rotated_surface, rect.topleft)

class PlayCoreMenu(ScreenObject):
    """
    A menu layout matching your provided diagram with floating squares.
    """
    DARK_BLUE   = (10, 10, 40)   # top color of background
    DARK_PURPLE = (40, 10, 70)   # bottom color of background

    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)
        
        self.show_fps = show_fps

        self.tiles = [
            {"title": "Quick tips", "color": (20, 50, 100)},
            {"title": "Lynez",     "color": (40, 80, 130)},
            {"title": "Magic Cat Academy",     "color": (40, 80, 130)},
            {"title": "Airship",     "color": (40, 80, 130)},
            {"title": "Avoid Mine",     "color": (40, 80, 130)},
        ]
        self.tile_rects = []
        self.hovered_tile_index = None
        self.fontH1 = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", 48)
        self.fontP = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", 24)
        self.layout_tiles()

        # Floating squares
        self.squares = []
        # Spawn squares every 30 frames (or so) – 
        # you could also do time-based spawning if you want absolute consistency
        self.spawn_rate = 30
        self.frame_count = 0

    def layout_tiles(self):
        x_margin = self.height / 10
        y_margin = self.height / 3
        spacing = self.height / 50

        quick_tips_width = self.height / 3
        quick_tips_height = self.height / 3
        quick_tips_rect = pygame.Rect(
            x_margin,
            y_margin,
            quick_tips_width,
            quick_tips_height
        )
        self.tile_rects.append(quick_tips_rect)

        game_width = self.height / 5 * 2 + spacing
        game_height = self.height / 5
        game1_rect = pygame.Rect(
            quick_tips_rect.right + spacing,
            quick_tips_rect.bottom - game_height,
            game_width,
            game_height
        )
        self.tile_rects.append(game1_rect)

        game4_rect = pygame.Rect(
            game1_rect.right + spacing,
            game1_rect.top,
            game_width,
            game_height
        )
        self.tile_rects.append(game4_rect)

        game2_rect = pygame.Rect(
            quick_tips_rect.left,
            game1_rect.bottom + spacing,
            game_width,
            game_height
        )
        self.tile_rects.append(game2_rect)

        game3_rect = pygame.Rect(
            game2_rect.right + spacing,
            game1_rect.bottom + spacing,
            game_width,
            game_height
        )
        self.tile_rects.append(game3_rect)
        
        self.title_text_surface = self.fontH1.render("DSHS PlayCore", True, (255, 255, 255))
        self.title_text_rect = (x_margin, x_margin)
        
        self.small_title_text_surface = self.fontP.render("Made by STATIC Jiwon Yu & Yuseung Jang", True, (255, 255, 255))
        self.small_title_text_rect = (x_margin, x_margin + 48 + spacing)

    def gradient_fill(self, screen, color_top, color_bottom):
        width, height = screen.get_size()
        for y in range(height):
            ratio = y / (height - 1) if height > 1 else 0
            r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
            g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
            b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
            pygame.draw.line(screen, (r, g, b), (0, y), (width, y))

    def draw_tiles(self, screen):
        for i, tile_info in enumerate(self.tiles):
            rect = self.tile_rects[i]
            base_color = tile_info["color"]
            pygame.draw.rect(screen, base_color, rect)
            if i == self.hovered_tile_index:
                pygame.draw.rect(screen, (255, 255, 255), rect, width=2, border_radius=5)
            text_surface = self.fontP.render(tile_info["title"], True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=rect.center)
            screen.blit(text_surface, text_rect)
        
        screen.blit(self.title_text_surface, self.title_text_rect)
        screen.blit(self.small_title_text_surface, self.small_title_text_rect)

    def handle_mouse(self, event):
        if event.type == pygame.MOUSEMOTION:
            mouse_pos = pygame.mouse.get_pos()
            self.hovered_tile_index = None
            for i, rect in enumerate(self.tile_rects):
                if rect.collidepoint(mouse_pos):
                    self.hovered_tile_index = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                mouse_pos = pygame.mouse.get_pos()
                for i, rect in enumerate(self.tile_rects):
                    if rect.collidepoint(mouse_pos):
                        tile_title = self.tiles[i]["title"]
                        return tile_title

    def spawn_squares(self):
        size = random.randint(self.height // 36, self.height // 12)  # must be int
        x = random.randint(0, self.width - size)
        # Speeds in px/second so that dt-based movement is consistent
        speed = random.uniform(20.0, 60.0)     # ~20 to 60 px/s upward
        angle_speed = random.uniform(-45.0, 45.0)  # degrees per second
        self.squares.append(Square(x, size, speed, angle_speed, self.height + self.height // 20))

    def update_squares(self, dt):
        for square in self.squares[:]:
            square.update(dt)
            if square.alpha <= 0:
                self.squares.remove(square)

    def draw_squares(self, screen):
        for square in self.squares:
            square.draw(screen)

    def loop(self, screen):
        clock = pygame.time.Clock()
        running = True
        
        frame_cnt = 0

        while running:
            # Get delta time in seconds
            dt_ms = clock.tick(60)  
            dt = dt_ms / 1000.0
            
            self.frame_count += 1

            if self.frame_count % self.spawn_rate == 0:
                self.spawn_squares()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                if (frame_cnt > 90):
                    selected = self.handle_mouse(event)
                    
                    if selected:
                        return selected, screen

            self.gradient_fill(screen, self.DARK_PURPLE, self.DARK_BLUE)
            self.update_squares(dt)
            self.draw_squares(screen)
            self.draw_tiles(screen)
            
            if self.show_fps:
                blit_fps(screen, clock)

            pygame.display.flip()
            frame_cnt += 1

# Run standalone
if __name__ == "__main__":
    WIDTH, HEIGHT = 1280, 720
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("PlayCoreMenuDemo")

    menu_screen = PlayCoreMenu(WIDTH, HEIGHT, show_fps=True)
    print(menu_screen.loop(screen))