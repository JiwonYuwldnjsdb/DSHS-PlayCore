import pygame

pygame.init()

fps_font = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", 24)

class ScreenObject:
    def __init__(self, width, height):
        self.width = width
        self.height = height

def fade_out(screen, curr_screen, WIDTH, HEIGHT, duration=1000):
    """
    Fades out to black from the current screen over the specified duration.

    Parameters:
    - screen: The main display surface.
    - curr_screen: The surface to fade out (should be the current screen content).
    - WIDTH: Width of the screen.
    - HEIGHT: Height of the screen.
    - duration: Duration of the fade-out effect in milliseconds (default is 1000ms).
    """
    fade_surface = pygame.Surface((WIDTH, HEIGHT))
    fade_surface.fill((0, 0, 0))  # Black surface for fade effect

    clock = pygame.time.Clock()
    alpha = 0  # Start fully transparent
    fade_speed = 255 / duration  # Alpha increment per millisecond

    running = True
    while running and alpha < 255:
        dt = clock.tick(60)  # Limit to 60 FPS and get delta time in milliseconds
        alpha += fade_speed * dt
        if alpha > 255:
            alpha = 255

        fade_surface.set_alpha(int(alpha))

        # Blit the current screen and the fade surface
        screen.blit(curr_screen, (0, 0))
        screen.blit(fade_surface, (0, 0))

        # Update the display
        pygame.display.flip()

    # Ensure the final state is fully covered by the black surface
    fade_surface.set_alpha(255)
    screen.blit(curr_screen, (0, 0))
    screen.blit(fade_surface, (0, 0))
    pygame.display.flip()


def fade_in(screen, curr_screen, WIDTH, HEIGHT, duration=1000):
    fade_surface = pygame.Surface((WIDTH, HEIGHT))
    fade_surface.fill((0, 0, 0))  # Black surface for fade effect

    clock = pygame.time.Clock()
    alpha = 255  # Start fully opaque
    fade_speed = 255 / duration  # Alpha decrement per millisecond

    running = True
    while running and alpha > 0:
        dt = clock.tick(60)  # Limit to 60 FPS and get delta time in milliseconds
        alpha -= fade_speed * dt
        if alpha < 0:
            alpha = 0

        fade_surface.set_alpha(int(alpha))

        # Blit the current screen and the fade surface
        screen.blit(curr_screen, (0, 0))
        screen.blit(fade_surface, (0, 0))

        # Update the display
        pygame.display.flip()

    # Ensure the final state is fully revealed
    screen.blit(curr_screen, (0, 0))
    pygame.display.flip()

def blit_fps(screen, clock):
    fps = clock.get_fps()
    fps_text = fps_font.render(f"FPS: {int(fps)}", True, (255, 255, 255))
    screen.blit(fps_text, (10, 10))