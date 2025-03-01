import pygame
import random
import sys
from enum import Enum, auto

from localLibraries.PlayCoreLibraries import ScreenObject, blit_fps  # Assuming you have these

pygame.init()

# ---------------------------------------------------------------------------
# Simple enum for game states
# ---------------------------------------------------------------------------
class GameState(Enum):
    MAIN_MENU = auto()
    TRANSITION = auto()
    DETAIL = auto()

# ---------------------------------------------------------------------------
# Button data structure
# ---------------------------------------------------------------------------
class MenuButton:
    def __init__(self, text, rect, color, font, alpha=255):
        """
        :param text: Button label
        :param rect: pygame.Rect for button position/size
        :param color: (r,g,b) color
        :param font: pygame.Font for text
        :param alpha: initial alpha (0-255)
        """
        self.text = text
        self.rect = rect
        self.color = color
        self.font = font
        self.alpha = alpha
        self.hovered = False  # Will be set True if mouse is over the button

    def update_hover(self, mouse_pos):
        """Check if the mouse is over the button."""
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, screen):
        # If width/height is 0 or negative, skip drawing to avoid errors
        if self.rect.width <= 0 or self.rect.height <= 0:
            return

        # Create a surface with alpha
        button_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        # Fill with RGBA
        button_surface.fill((self.color[0], self.color[1], self.color[2], self.alpha))

        # Draw the surface onto the screen
        screen.blit(button_surface, (self.rect.x, self.rect.y))

        # Render text (centered)
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

        # If hovered, draw a white rounded outline on top
        if self.hovered:
            pygame.draw.rect(
                screen,
                (255, 255, 255),
                self.rect,
                width=3,        # outline thickness
                border_radius=8 # rounded corners
            )

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

# ---------------------------------------------------------------------------
# Floating squares (original code, with dt-based movement)
# ---------------------------------------------------------------------------
class Square:
    def __init__(self, x, size, speed, angle_speed, screen_height):
        self.size = size
        self.x = x
        self.y = screen_height
        self.speed = speed         # upward speed in px/s
        self.angle_speed = angle_speed  # degrees per second
        self.angle = 0
        self.alpha = 15.0
        self.surface = pygame.Surface((size, size), pygame.SRCALPHA)
        self.surface.fill((255, 255, 255, int(self.alpha)))

    def update(self, dt):
        self.y -= self.speed * dt
        self.angle += self.angle_speed * dt
        self.angle %= 360

        fade_per_second = 1.2
        self.alpha -= fade_per_second * dt
        if self.alpha < 0:
            self.alpha = 0

        self.surface.fill((255, 255, 255, int(self.alpha)))

    def draw(self, screen):
        rotated_surface = pygame.transform.rotate(self.surface, self.angle)
        rect = rotated_surface.get_rect(center=(self.x, self.y))
        screen.blit(rotated_surface, rect.topleft)

# ---------------------------------------------------------------------------
# Utility: linear interpolation for Rect
# ---------------------------------------------------------------------------
def lerp_rect(r1, r2, t):
    x = r1.x + (r2.x - r1.x) * t
    y = r1.y + (r2.y - r1.y) * t
    w = r1.width + (r2.width - r1.width) * t
    h = r1.height + (r2.height - r1.height) * t
    return pygame.Rect(int(x), int(y), int(w), int(h))

# ---------------------------------------------------------------------------
# Main menu class with transitions
# ---------------------------------------------------------------------------
class PlayCoreMenu(ScreenObject):
    DARK_BLUE   = (10, 10, 40)
    DARK_PURPLE = (40, 10, 70)

    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)
        self.show_fps = show_fps

        # For simplicity, define a font size based on screen height
        font_size = int(self.height * 0.05)
        self.font = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", font_size)

        # Game state
        self.current_state = GameState.MAIN_MENU
        self.detail_index = None  # which button leads to detail

        # Transition control
        self.transition_in_progress = False
        self.transition_time = 0.0
        self.transition_duration = 1.0
        self.clicked_button_index = None

        # We'll store these to interpolate
        self.start_rects = []
        self.end_rects = []
        self.start_alphas = []
        self.end_alphas = []

        # Setup main menu buttons
        self.menu_buttons = []
        self.setup_buttons()

        # Floating squares
        self.squares = []
        self.spawn_rate = 30
        self.frame_count = 0

        # For "long press to go back" from detail screen
        self.mouse_down_time = 0.0
        self.mouse_held_threshold = 1.0

    # -----------------------------------------------------------------------
    # Create/Reset the main menu buttons to their initial layout
    # -----------------------------------------------------------------------
    def setup_buttons(self):
        """Define the layout so buttons nearly fill the screen:
           - top button: 10% height, color (20,50,100)
           - next 4 buttons: 22.5% each, color (40,80,130)
        """
        self.menu_buttons.clear()

        # Texts
        texts = ["Instructions", "Game 1", "Game 2", "Game 3", "Game 4"]
        # Colors (top is different, rest are the same)
        colors = [
            (20, 50, 100),
            (40, 80, 130),
            (40, 80, 130),
            (40, 80, 130),
            (40, 80, 130),
        ]
        # Percentage of total screen height
        top_percs = [0.0, 0.1, 0.325, 0.55, 0.775]
        height_percs = [0.1, 0.225, 0.225, 0.225, 0.225]

        # We'll use 90% width, centered
        x_margin = 0.05 * self.width
        w_margin = 0.9 * self.width

        for i in range(5):
            top_px = int(top_percs[i] * self.height)
            h_px = int(height_percs[i] * self.height)
            rect = pygame.Rect(x_margin, top_px, w_margin, h_px)
            btn = MenuButton(texts[i], rect, colors[i], self.font, alpha=255)
            self.menu_buttons.append(btn)

    # -----------------------------------------------------------------------
    # Start the transition animation when a button is clicked
    # -----------------------------------------------------------------------
    def start_transition(self, clicked_index):
        self.transition_in_progress = True
        self.transition_time = 0.0
        self.clicked_button_index = clicked_index
        self.current_state = GameState.TRANSITION

        self.start_rects = [b.rect.copy() for b in self.menu_buttons]
        self.end_rects = []
        self.start_alphas = [b.alpha for b in self.menu_buttons]
        self.end_alphas = [0 for _ in self.menu_buttons]  # all fade to alpha=0

        # Pressed button expands to full screen
        full_rect = pygame.Rect(0, 0, self.width, self.height)
        # Others shrink to height=0
        for i, b in enumerate(self.menu_buttons):
            if i == clicked_index:
                self.end_rects.append(full_rect)
            else:
                # Shrink from the same top-left to zero height
                # (so it "collapses" upward)
                self.end_rects.append(pygame.Rect(
                    b.rect.x,
                    b.rect.y,
                    b.rect.width,
                    0
                ))

    # -----------------------------------------------------------------------
    # Update the transition animation
    # -----------------------------------------------------------------------
    def update_transition(self, dt):
        self.transition_time += dt
        t = self.transition_time / self.transition_duration
        if t > 1.0:
            t = 1.0

        # Interpolate each button's rect + alpha
        for i, b in enumerate(self.menu_buttons):
            b.rect = lerp_rect(self.start_rects[i], self.end_rects[i], t)
            start_a = self.start_alphas[i]
            end_a = self.end_alphas[i]
            b.alpha = int(start_a + (end_a - start_a) * t)

        # If transition finished, go to detail
        if t >= 1.0:
            self.transition_in_progress = False
            self.current_state = GameState.DETAIL
            self.detail_index = self.clicked_button_index

    # -----------------------------------------------------------------------
    # Draw the detail screen
    # -----------------------------------------------------------------------
    def draw_detail_screen(self, screen, title):
        # Title
        title_surf = self.font.render(title, True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.width // 2, self.height // 6))
        screen.blit(title_surf, title_rect)

        # Lorem ipsum text
        lorem_text = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n"
            "Suspendisse potenti. Quisque volutpat odio at enim suscipit.\n\n"
            "Press and hold (1s) to return to the main menu."
        )
        lines = lorem_text.split('\n')
        y_offset = title_rect.bottom + 40
        for line in lines:
            line_surf = self.font.render(line, True, (230, 230, 230))
            line_rect = line_surf.get_rect(midtop=(self.width // 2, y_offset))
            screen.blit(line_surf, line_rect)
            y_offset += line_surf.get_height() + 10

    # -----------------------------------------------------------------------
    # Gradient fill background
    # -----------------------------------------------------------------------
    def gradient_fill(self, screen, color_top, color_bottom):
        width, height = screen.get_size()
        for y in range(height):
            ratio = y / (height - 1) if height > 1 else 0
            r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
            g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
            b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
            pygame.draw.line(screen, (r, g, b), (0, y), (width, y))

    # -----------------------------------------------------------------------
    # Floating squares
    # -----------------------------------------------------------------------
    def spawn_squares(self):
        size = random.randint(self.height // 36, self.height // 12)
        x = random.randint(0, self.width - size)
        speed = random.uniform(20.0, 60.0)
        angle_speed = random.uniform(-45.0, 45.0)
        self.squares.append(Square(x, size, speed, angle_speed, self.height + self.height // 20))

    def update_squares(self, dt):
        for sq in self.squares[:]:
            sq.update(dt)
            if sq.alpha <= 0:
                self.squares.remove(sq)

    def draw_squares(self, screen):
        for sq in self.squares:
            sq.draw(screen)

    # -----------------------------------------------------------------------
    # Main loop
    # -----------------------------------------------------------------------
    def loop(self, screen):
        clock = pygame.time.Clock()
        running = True

        while running:
            dt_ms = clock.tick(60)
            dt = dt_ms / 1000.0

            self.frame_count += 1
            if self.frame_count % self.spawn_rate == 0:
                self.spawn_squares()

            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse_down_time = 0.0  # reset press timer

                    if self.current_state == GameState.MAIN_MENU:
                        # Check if any button was clicked
                        for i, btn in enumerate(self.menu_buttons):
                            if btn.is_clicked(pygame.mouse.get_pos()):
                                self.start_transition(i)
                                break

                elif event.type == pygame.MOUSEBUTTONUP:
                    self.mouse_down_time = 0.0

            # Track long press
            if pygame.mouse.get_pressed()[0]:
                self.mouse_down_time += dt
            else:
                self.mouse_down_time = 0.0

            # Background
            self.gradient_fill(screen, self.DARK_PURPLE, self.DARK_BLUE)
            self.update_squares(dt)
            self.draw_squares(screen)

            # State handling
            if self.current_state == GameState.MAIN_MENU:
                # Update hover for each button
                mouse_pos = pygame.mouse.get_pos()
                for btn in self.menu_buttons:
                    btn.update_hover(mouse_pos)
                    btn.draw(screen)

            elif self.current_state == GameState.TRANSITION:
                # Update transition
                self.update_transition(dt)
                # Draw menu in its transitional state
                mouse_pos = pygame.mouse.get_pos()
                for btn in self.menu_buttons:
                    btn.update_hover(mouse_pos)
                    btn.draw(screen)

            elif self.current_state == GameState.DETAIL:
                # Show detail screen
                if self.detail_index == 0:
                    self.draw_detail_screen(screen, "Instructions")
                else:
                    self.draw_detail_screen(screen, f"Game {self.detail_index}")

                # Long press to go back
                if self.mouse_down_time >= self.mouse_held_threshold:
                    self.current_state = GameState.MAIN_MENU
                    self.setup_buttons()  # reset main menu layout

            # Optional: show FPS
            if self.show_fps:
                blit_fps(screen, clock)

            pygame.display.flip()

# ---------------------------------------------------------------------------
# Run standalone
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    WIDTH, HEIGHT = 1280, 720
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("PlayCoreMenuDemo")

    menu_screen = PlayCoreMenu(WIDTH, HEIGHT, show_fps=True)
    menu_screen.loop(screen)
