import pygame
import sys
from localLibraries.PlayCoreLibraries import fade_out

from scenes import Lynez, MagicCatAcademy, Airship, AvoidMine
import PlayCore

def main():
    pygame.init()
    WIDTH, HEIGHT = 1280, 720   
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("DSHS PlayCore")
    
    running = True
    
    curr_screen_idx = 0
    
    games = {
        0:0,
        "Lynez" : 1,
        "Magic Cat Academy" : 2,
        "Airship" : 3,
        "Avoid Mine" : 4
    }
    
    """
    0 : Main Menu
    1 : Lynez
    2 : Magic Cat Academy
    3 : Airship
    4 : Avoid Mine
    """
    
    while running:
        if curr_screen_idx == 0:
            curr_screen = PlayCore.PlayCoreMenu(WIDTH,HEIGHT)
            
            next_screen, curr_screen_surface = curr_screen.loop(screen)
            
            curr_screen_idx = games[next_screen]
            
            pygame.time.wait(1200)
            fade_out(screen, curr_screen_surface, WIDTH, HEIGHT)
        
        elif curr_screen_idx == 1:
            curr_screen = Lynez.LynezScreen(WIDTH, HEIGHT)
            
            next_screen, curr_screen_surface = curr_screen.loop(screen)
            
            curr_screen_idx = games[next_screen]
            
            pygame.time.wait(500)
            fade_out(screen, curr_screen_surface, WIDTH, HEIGHT)
        
        elif curr_screen_idx == 2:
            curr_screen = MagicCatAcademy.MagicCatAcademyScreen(WIDTH, HEIGHT)
            
            next_screen, curr_screen_surface = curr_screen.loop(screen)
            
            curr_screen_idx = games[next_screen]
            
            pygame.time.wait(500)
            fade_out(screen, curr_screen_surface, WIDTH, HEIGHT)
        
        elif curr_screen_idx == 3:
            curr_screen = Airship.AirshipScreen(WIDTH, HEIGHT)
            
            next_screen, curr_screen_surface = curr_screen.loop(screen)
            
            curr_screen_idx = games[next_screen]
            
            pygame.time.wait(500)
            fade_out(screen, curr_screen_surface, WIDTH, HEIGHT)
        
        elif curr_screen_idx == 4:
            curr_screen = AvoidMine.AvoidMineScreen(WIDTH, HEIGHT)
            
            next_screen, curr_screen_surface = curr_screen.loop(screen)
            
            curr_screen_idx = games[next_screen]
            
            pygame.time.wait(500)
            fade_out(screen, curr_screen_surface, WIDTH, HEIGHT)
    
    pygame.quit()
    sys.exit()
    
if __name__ == "__main__":
    main()