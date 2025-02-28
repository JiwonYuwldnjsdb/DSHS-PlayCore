import pygame
import random
import math
import sys
from collections import deque
from localLibraries.PlayCoreLibraries import ScreenObject, fade_in, fade_out, blit_fps
import numpy as np

class Lines:
    def __init__(self, color_bright, width, radius, circle_width):
        self.lines_list = []
        self.color_bright = color_bright
        self.width =  max(int(width), 1)
        self.radius = radius
        self.circle_width = max(int(circle_width), 1)
    
    def adj_line(self, A, y):
        return ((A[0][0], A[0][1]+y), (A[1][0], A[1][1]+y))
    
    def adj_pos(self, A, x, y):
        return (A[0]-x, A[1]-y)
    
    def draw(self, screen, scrollx, scrolly, height):
        for line in self.lines_list:
            nPos1 = self.adj_pos(line[0], scrollx, scrolly)
            nPos2 = self.adj_pos(line[1], scrollx, scrolly)
            pygame.draw.circle(screen, self.color_bright, nPos1, self.radius,self.circle_width)
            pygame.draw.circle(screen, self.color_bright, nPos2, self.radius,self.circle_width)
            pygame.draw.line(screen, self.color_bright, nPos1, nPos2, self.width)
            
            if nPos1[1] > height * 1.2 + 1000 and nPos2[1] > height * 1.2 + 1000:
                self.lines_list.remove(line)
        
    def draw_dark(self, screen, scrollx, scrolly, color):
        for line in self.lines_list:
            nPos1 = self.adj_pos(line[0], scrollx, scrolly)
            nPos2 = self.adj_pos(line[1], scrollx, scrolly)
            pygame.draw.circle(screen, color, nPos1, self.radius,self.circle_width)
            pygame.draw.circle(screen, color, nPos2, self.radius,self.circle_width)
            pygame.draw.line(screen, color, nPos1, nPos2, self.width)
        
class PlayerParticle:
    def __init__(self, x, y, speedx, speedy, size, dissolve, color):
        self.x = x
        self.y = y
        self.speedx = speedx
        self.speedy = speedy
        self.size = size
        self.dissolve = dissolve
        self.color = color
    
    def update(self):
        self.size -= self.dissolve
        self.x += self.speedx
        self.y -= self.speedy
    
    def draw(self, screen, scrollx, scrolly):
        pygame.draw.circle(screen, self.color,
                        Lines.adj_pos(None, (int(self.x-self.size/4), int(self.y-self.size/4)), scrollx, scrolly),
                        self.size)
    
    def draw_dark(self, screen, scrollx, scrolly, color):
        pygame.draw.circle(screen, color,
                        Lines.adj_pos(None, (int(self.x-self.size/4), int(self.y-self.size/4)), scrollx, scrolly),
                        self.size)
    
class Player:
    def __init__(self, x, y, speedx, speedy, size, color, height):
        self.x = x
        self.y = y
        self.speedx = speedx
        self.speedy = speedy
        self.size = size
        self.color = color
        self.adj_constant = height/1280
        self.height = height
        self.gravity = 0.15 * self.adj_constant
        self.reaction = 0
    
    def point_line_distance(self, A, B, C):
        A_coeff = B[1] - A[1]
        B_coeff = A[0] - B[0]
        C_coeff = B[0] * A[1] - A[0] * B[1]
        
        if A_coeff == 0 and B_coeff == 0:
            distance = math.hypot(C[1]-A[1], C[0]-A[0])
        else:
            distance = abs(A_coeff * C[0] + B_coeff * C[1] + C_coeff) / math.sqrt(A_coeff**2 + B_coeff**2)
        return distance

    def reflect_velocity(self, A, B, speedx, speedy):
        x1, y1 = A
        x2, y2 = B
        
        dx = x2 - x1
        dy = y2 - y1
        
        length = math.hypot(dx, dy)
        if length == 0:
            raise ValueError("Point A and B should be different")
        
        ux = dx / length
        uy = dy / length
        
        dot = speedx * ux + speedy * uy
        
        v1 = 2 * dot * ux - speedx
        v2 = 11 * self.adj_constant
        
        return v1, v2
    
    def ccw(self, a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def on_segment(self, a, b, c):
        return min(a[0], c[0]) <= b[0] <= max(a[0], c[0]) and \
            min(a[1], c[1]) <= b[1] <= max(a[1], c[1])

    def segments_intersect(self, p1, p2, p3, p4):
        d1 = self.ccw(p1, p2, p3)
        d2 = self.ccw(p1, p2, p4)
        d3 = self.ccw(p3, p4, p1)
        d4 = self.ccw(p3, p4, p2)

        if (d1 * d2 < 0) and (d3 * d4 < 0):
            return True

        if d1 == 0 and self.on_segment(p1, p3, p2):
            return True

        if d2 == 0 and self.on_segment(p1, p4, p2):
            return True

        if d3 == 0 and self.on_segment(p3, p1, p4):
            return True

        if d4 == 0 and self.on_segment(p3, p2, p4):
            return True

        return False
    
    def check_side(self, A, B, prev_player_pos):
        if A[1] == B[1]:
            if self.speedy < 0:
                return True
            return False
        elif A[0] == B[0]:
            return False
        else:
            gradient = (B[1] - A[1]) / (B[0] - A[0])
            lower, higher = (A,B) if B[1] > A[1] else (B,A)
            
            if gradient > 0:
                if self.ccw(higher, lower, prev_player_pos) > 0:
                    return True
                return False
            else:
                if self.ccw(lower, higher, prev_player_pos) > 0:
                    return True
                return False
    
    def check_collitions(self, A, B, prev_player_pos):
        if self.segments_intersect(prev_player_pos, (self.x, self.y), A, B):
            if self.check_side(A, B, prev_player_pos):
                self.x = prev_player_pos[0]
                self.y = prev_player_pos[1]
                self.speedx, self.speedy = self.reflect_velocity(A, B, -1 * self.speedx, self.speedy)
                self.speedx *= -1
                return True
        
        return False
    
    def handle_collision(self, lines, prev_player_pos, lasers):
        for line in lines:
            if self.check_collitions(line[0], line[1], prev_player_pos):
                break
        
        for laser in lasers:
            if laser.charging or laser.frame_count < 180 or laser.frame_count > 200:
                continue
            if self.x > laser.left and self.x < laser.right:
                if self.x < laser.center:
                    self.speedx -= 8 * self.adj_constant
                else:
                    self.speedx += 8 * self.adj_constant
    
    def update(self):
        self.speedy -= self.gravity
        self.speedy = max(self.speedy, -8 * self.adj_constant)
        self.x += self.speedx
        self.y -= self.speedy
    
    def draw(self, screen, scrollx, scrolly):
        pygame.draw.circle(screen, self.color,
                        Lines.adj_pos(None, (int(self.x-self.size/4), int(self.y-self.size/4)), scrollx, scrolly),
                        self.size)
    
    def draw_dark(self, screen, scrollx, scrolly, color):
        pygame.draw.circle(screen, color,
                        Lines.adj_pos(None, (int(self.x-self.size/4), int(self.y-self.size/4)), scrollx, scrolly),
                        self.size)

class CircleEffect:
    def __init__(self, x, y, size, target, color, width, gradient=True, second=(10,17,30)):
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
    
    def update(self, step = 0.1, color_step=0.2):
        self.size += self.target * step
        
        if self.gradient:
            for i in range(3):
                self.color[i] += int((self.second[i]-self.color[i]) * color_step)
                self.color[i] = min(self.color[i], 255)
    
    def draw(self, screen, scrollx = 0, scrolly = 0):
        pygame.draw.circle(screen, self.color, Lines.adj_pos(None, (self.x, self.y), scrollx, scrolly), self.size, self.width)

class Laser:
    def __init__(self, left, width, height, color, target_color, particle_color, screen_width):
        self.right = min((left + width), screen_width)
        self.left = max(self.right - width, 0)
        self.height = height
        self.width = max(int(height/320), 1)
        self.adj_constant = screen_width / 1280
        
        self.center = (self.right + self.left)/2
        self.color = color
        self.target_color = target_color
        self.particle_color = particle_color
        
        self.lines = []
        
        self.frame_count = 0
        
        self.charging = True
        
        self.particles = []
    
    def zap(self):
        cnt = 50
        ramdoms = np.random.randn(1,100) + 1
        size = self.height/80
        margin = self.height/50
        currY = size
        targetx1 = (self.right - self.left) * 1.5 + self.left
        targetx2 = self.left - (self.right - self.left) * 0.5
        
        for i in range(cnt):
            self.particles.append(LaserEffect(self.left + ramdoms[0][i+50]*self.height/100, currY, max(1, size*min(ramdoms[0][i],1.5)),
                                            self.particle_color, targetx1, self.height/200, self.height/2000))
            self.particles.append(LaserEffect(self.right + ramdoms[0][i]*self.height/100, currY, max(1,size*min(ramdoms[0][i+50],1.5)),
                                            self.particle_color, targetx2, self.height/200, self.height/2000))
            currY += margin
    
    def update(self):
        if self.frame_count == 180:
            self.charging = False
            self.zap()
        
        new_lines = []
        
        for line in self.lines:
            line_x, color = line
            new_line = line_x + 3 * self.adj_constant
            
            new_color = (int(color[0] - (self.color[0] - self.target_color[0]) * 0.03),
                        int(color[1] - (self.color[1] - self.target_color[1]) * 0.03),
                        int(color[2] - (self.color[2] - self.target_color[2]) * 0.03))

            if new_color[0] < 10:
                continue
            
            if new_line + self.left <= self.center:
                new_lines.append((new_line, new_color))
        
        self.lines = new_lines
        
        for paricle in self.particles:
            paricle.update()
            if paricle.size <= 0.1:
                self.particles.remove(paricle)
        
        if self.charging:
            if self.frame_count % 10 == 0:
                self.lines.append((0, self.color))
        
        self.frame_count += 1
    
    def draw(self, screen, scrollx, scrolly):
        if self.charging:
            pygame.draw.line(screen, self.color, (self.left-scrollx, 0), (self.left-scrollx, self.height), self.width)
            pygame.draw.line(screen, self.color, (self.right-scrollx, 0), (self.right-scrollx, self.height), self.width)
        
        for line in self.lines:
            pygame.draw.line(screen, line[1], (self.left + line[0]-scrollx, 0),
                            (self.left + line[0]-scrollx, self.height), self.width)
            pygame.draw.line(screen, line[1], (self.right - line[0]-scrollx, 0),
                            (self.right - line[0]-scrollx, self.height), self.width)
        
        for paricle in self.particles:
            paricle.draw(screen, scrollx, scrolly)

class LaserEffect:
    def __init__(self, x, y, size, color, targetx, speedy, gravity):
        self.x = x
        self.y = y
        self.size = size
        self.dissolve_target = 0
        self.color = color
        self.targetx = targetx
        self.speedy = speedy
        self.gravity = gravity
    
    def update(self):
        self.x += (self.targetx - self.x) * 0.025
        self.y -= self.speedy
        self.size += (self.dissolve_target - self.size) * 0.05
        self.speedy -= self.gravity
    
    def draw(self, screen, scrollx, scrolly):
        pygame.draw.circle(screen, self.color, Lines.adj_pos(None, (int(self.x), int(self.y)), scrollx, 0), self.size)

class LynezMainScreen(ScreenObject):
    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)
        
        self.show_fps = show_fps
        
        self.h1 = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", int(height/15))
        self.h1_size = self.h1.size("")
        
        self.p = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", int(height/30))
        self.p_size = self.p.size("")
        
        self.psmall = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", int(height/45))
        self.psmall_size = self.psmall.size("")
        
        ### file data ###
        # 0: highest score
        
        # Reading from a text file
        with open("data/Lynez/playdata/saves.txt", "r") as file:
            file_data = file.read().split('\n')
        
        self.best_score = int(file_data[0])
        self.curr_score = 0
        
        ### Colors ###
        self.white = (255,255,255)
        self.gray = (51,58,69)
        self.dark_gray = (42,48,59)
        self.blue = (90,210,255)
        self.blue_ = (90,140,170)
        self.blue__ = (23, 38, 53)
        self.blue_shadow = (23, 48, 65)
        self.dark_blue = (10,17,30)
        self.darker_blue = (50, 56, 67)
        self.trail_blue = (90, 140, 170)
        self.trail_blue_shadow = (23, 38, 55)
        self.red = (190, 40, 100)
        self.red_particle = (171, 35, 79)
        
        self.player = Player(width/2, height/2, 0, 0, self.height/80, self.blue, height)
        
        self.scrollx = 0
        self.scrolly = 0
        
        self.player_particles = []
        self.circle_effects = []
        
        self.lines = Lines(self.white, self.height/200, self.height/80, self.height/200)
        self.lines.lines_list =[((0,height-self.height/400), (width,height-self.height/400)),
                                ((width/2,height-self.height/400), (width/2,height-self.height/400))]
        
        self.trail = deque()

        self.shake_tick = 0
        
        ### Menu Variables ###
        self.main_menu_scroll = height * 2/5
        
        self.texts = {
            'game_over':[self.h1.render("Game Over", True, self.white),
                        self.h1.size("Game Over")[0]/2],
            
            'restart':[self.p.render("Click to Restart", True, self.white),
                    self.p.size("Click to Restart")[0]/2],
            
            'title':[self.h1.render("Lynez", True, self.white),
                    self.h1.size("Lynez")[0]/2],
            
            'start':[self.p.render("Click to Start", True, self.white),
                    self.p.size("Click to Start")[0]],
            
            'quit':[self.p.render("Hold to Quit", True, self.white)],
            
            'credit1':[self.psmall.render("Original Game by Dafluffypotato", True, self.white),
                    self.psmall.size("Original Game by Dafluffypotato")[0]/2],
            
            'credit2':[self.psmall.render("Remasterd by Jiwon Yu", True, self.white),
                    self.psmall.size("Remasterd by Jiwon Yu")[0]/2]
        }
        
        self.last_platform = 0
        self.last_pos = (width/2,height-self.height/400)
        
        self.lasers = []
        
        self.circle_effects_dead = []
    
    def reset(self):
        self.player = Player(self.width/2, self.height/2, 0, 0, self.height/80, self.blue, self.height)
        
        self.scrollx = 0
        self.scrolly = 0
        
        self.player_particles.clear()
        self.circle_effects.clear()
        
        self.lines.lines_list = [((0,self.height-self.height/400), (self.width,self.height-self.height/400)),
                    ((self.width/2,self.height-self.height/400), (self.width/2,self.height-self.height/400))]

        self.trail.clear()

        self.curr_score = 0
        
        self.shake_tick = 0
        
        self.last_platform = 0
        self.last_pos = (self.width/2,self.height-self.height/400)
        
        self.lasers.clear()
        
        self.circle_effects_dead.clear()
    
    def blit_game_over(self, screen):
        self.main_menu_scroll += (0 - self.main_menu_scroll) * 0.075
        if self.main_menu_scroll < 0.1:
            self.main_menu_scroll = 0
        
        # game over
        screen.blit(self.texts['game_over'][0], (self.width/2 - self.texts['game_over'][1],
                                                self.height/5*2 - self.h1_size[1] - self.main_menu_scroll))
        
        # score
        res_score = self.h1.render(f"{self.curr_score}", True, self.white)
        screen.blit(res_score, (self.width/2 - self.h1.size(f"{self.curr_score}")[0]/2,
                                self.height/2 - self.h1_size[1]/2 - self.main_menu_scroll/2))
        
        # restart game
        screen.blit(self.texts['restart'][0], (self.width/2 - self.texts['restart'][1],
                                                self.height/5*3 + self.main_menu_scroll))
    
    def blit_menu(self, screen):
        self.main_menu_scroll += (0 - self.main_menu_scroll) * 0.075
        if self.main_menu_scroll < 0.1:
            self.main_menu_scroll = 0
        
        # title
        screen.blit(self.texts['title'][0], (self.width/2 - self.texts['title'][1],
                                            self.height/5*2 - self.h1_size[1] - self.main_menu_scroll))
        
        # high score
        high_score = self.p.render(f"Best {self.best_score}", True, self.white)
        screen.blit(high_score, (self.width/2 - self.p.size(f"Best {self.best_score}")[0]/2,
                                self.height/5*3 + self.main_menu_scroll))
        
        # start game
        screen.blit(self.texts['start'][0], (self.width/7*3 - self.texts['start'][1],
                                            self.height/5*3 + self.p_size[1] + self.psmall_size[1]/2 + self.main_menu_scroll))
        
        # quit game
        screen.blit(self.texts['quit'][0], (self.width/7*4,
                                            self.height/5*3 + self.p_size[1] + self.psmall_size[1]/2 + self.main_menu_scroll))
        
        # credits
        screen.blit(self.texts['credit1'][0], (self.width/2 - self.texts['credit1'][1],
                                            self.height/5*3 + self.p_size[1]*3 + self.main_menu_scroll))
        
        screen.blit(self.texts['credit2'][0], (self.width/2 - self.texts['credit2'][1],
                                            self.height/5*3 + self.p_size[1]*3 + self.psmall_size[1] + self.main_menu_scroll))
    
    def blit_ingame(self, screen):
        score = self.h1.render(f"{self.curr_score}", True, self.white)
        screen.blit(score, (self.width/2 - self.h1.size(f"{self.curr_score}")[0]/2,
                            self.height/2 - self.height/5 - self.h1_size[1]/2))
    
    def load_screen(self, target):
        if target == 0:
            self.best_score = max(self.best_score, self.curr_score)
            # Writing to a text file
            with open("data/Lynez/playdata/saves.txt", "w") as file:
                file.write(f"{self.best_score}\n")

            self.reset()
            self.state = 0
            
            self.main_menu_scroll = self.height * 2/5
        
        elif target == 1:
            self.state = 1
            self.log = 'Start'
        
        elif target == 2:
            ### Game Over ###
            self.player_particles.clear()
            self.state = 2
            self.shake_tick = 25 * self.height/1280
            
            self.last_scrollx = self.scrollx
            self.last_scrolly = self.scrolly
            self.prev_scrolly = self.last_scrollx
            self.adjed_scrolly = min(0, self.scrolly+1000)
            
            self.main_menu_scroll = self.height * 2/5
            
            self.circle_effects_dead.append(CircleEffect(self.player.x, self.player.y, self.height/2, self.height*3,
                                                        self.red, self.height/50, False))
            
            self.circle_effects_dead.append(CircleEffect(self.player.x, self.player.y, self.height/4, self.height*3,
                                                        self.red, self.height/50, False))
            
            self.circle_effects_dead.append(CircleEffect(self.player.x, self.player.y, self.height/4, self.height*2,
                                                        self.dark_blue, self.height/50, True, self.red))
            
            self.circle_effects_dead.append(CircleEffect(self.player.x, self.player.y, self.height/16, self.height*2,
                                                        self.dark_blue, self.height/50, True, self.red))
            
            self.circle_effects_dead.append(CircleEffect(self.player.x, self.player.y, self.height/16, self.height,
                                                        self.dark_blue, self.height/50, True, self.red))
    
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
            screen.fill(self.dark_blue)
            
            dt_ms = clock.tick(60)

            dt = dt_ms / 1000.0
            
            if mouse_down:
                mouse_down_frames += 1
                if mouse_down_frames >= 60:
                    pygame.draw.arc(screen, (255, 255, 255),
                            (pygame.mouse.get_pos()[0]-self.height/60,
                            pygame.mouse.get_pos()[1]-self.height/60, self.height/60*2, self.height/60*2), 
                            math.radians(0), math.radians(min(mouse_down_frames*2-120, 360)), self.lines.width)
            else:
                mouse_up_frames += 1
            
            ### Check of Exit ###
            if self.state == 0:
                if mouse_down_frames == 240:
                    return 0, screen
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    curr_pos = pygame.mouse.get_pos()
                    self.circle_effects.append(CircleEffect(curr_pos[0], curr_pos[1], 1, self.height//15, self.white, self.height/200))
                    mouse_down = True
                
                if event.type == pygame.MOUSEBUTTONUP:
                    if mouse_down == True:
                        if mouse_down_frames < 60:
                            if mouse_up_frames > 10:
                                if self.state == 0:
                                    self.load_screen(1)
                                elif self.state == 2:
                                    self.load_screen(0)
                    
                    if self.state == 1:
                        if self.log != 'Start':
                            curr_point = self.lines.adj_pos(pygame.mouse.get_pos(), 0, -1 * self.scrolly)
                            self.lines.lines_list.append((self.last_pos, curr_point))
                            self.last_pos = curr_point
                        else:
                            self.log = None

                    mouse_down = False
                    mouse_down_frames = 0
                    mouse_up_frames = 0
            
            self.player_particles.append(PlayerParticle(self.player.x + random.random()*self.player.size - self.player.size/2,
                                                        self.player.y + random.random()*self.player.size - self.player.size/2,
                                                        (-1 * self.player.speedx*0.5 + random.random() - 0.5)*self.height/1280,
                                                        (-1 * self.player.speedy*0.5 + random.random() - 0.5)*self.height/1280,
                                                        self.player.size,
                                                        self.player.size*0.05,
                                                        self.blue
                                                        ))
            
            if self.state == 0:
                ### Blit background ###
                self.lines.draw_dark(screen, self.scrollx, self.scrolly-self.height/45, self.gray)
                
                for particle in self.player_particles:
                    particle.draw_dark(screen, self.scrollx, self.scrolly-self.height/45, self.blue_shadow)
                
                self.player.draw_dark(screen, self.scrollx, self.scrolly-self.height/45, self.blue_shadow)
                
                ### Blit Effects ###
                
                for circle in self.circle_effects:
                    circle.update()
                    circle.draw(screen)
                    
                    if circle.size > circle.target:
                        self.circle_effects.remove(circle)
                
                self.blit_menu(screen)
                self.lines.draw(screen, self.scrollx, self.scrolly, self.height)
                
                ### Blit Player ###
                
                for particle in self.player_particles:
                    particle.update()
                    particle.draw(screen, self.scrollx, self.scrolly)
                    if particle.size <= 0:
                        self.player_particles.remove(particle)
                
                self.player.draw(screen, self.scrollx, self.scrolly)
            
            elif self.state == 1:
                
                ### Add line ###
                
                if -(self.scrolly) - self.last_platform > self.height/7:
                    if random.randint(1, 3) <= 2:
                        base_y = self.scrolly - self.height/10
                        base_x = random.randint(0, self.width)
                        new_line = [[base_x, base_y], [base_x + (random.random() - 0.5) * self.width*2/3, base_y + (random.random() - 0.5) * self.height/5]]
                        self.lines.lines_list.append(new_line)
                    self.last_platform += self.height/7
                
                ### Update Player State ###
                player_start_pos = (self.player.x, self.player.y)
                self.trail.append(player_start_pos)
                
                self.player.update()
                self.player.handle_collision(self.lines.lines_list, player_start_pos, self.lasers)
                
                self.scrolly = min(self.player.y - self.height / 2, self.scrolly)
                
                self.curr_score = int(-1 * self.scrolly * self.height / 1280)
                
                ### Blit background ###
                self.lines.draw_dark(screen, self.scrollx, self.scrolly-self.height/45, self.gray)
                pygame.draw.line(screen, self.blue__,
                                self.lines.adj_pos(self.last_pos, self.scrollx, self.scrolly-self.height/45),
                                self.lines.adj_pos(pygame.mouse.get_pos(), 0, -self.height/45),
                                int(self.lines.width/2))
                
                for i in range(len(self.trail)-1):
                    pygame.draw.line(screen, self.trail_blue_shadow,
                                        self.lines.adj_pos(self.trail[i], self.scrollx, self.scrolly-self.height/45),
                                        self.lines.adj_pos(self.trail[i+1], self.scrollx, self.scrolly-self.height/45),
                                        max(int(self.lines.width/4), 1))
                
                for particle in self.player_particles:
                    particle.draw_dark(screen, self.scrollx, self.scrolly-self.height/45, self.blue_shadow)
                
                self.player.draw_dark(screen, self.scrollx, self.scrolly-self.height/45, self.blue_shadow)
                
                if self.curr_score > 300:
                    if random.randint(1, int(150 * (1 + len(self.lasers) * 2) * (1-1/self.curr_score))) == 1:
                        self.lasers.append(Laser(random.random() * self.width, self.width/6, 
                                                self.height, self.red, self.dark_blue, self.red_particle, self.width))
                
                for laser in self.lasers:
                    laser.update()
                    laser.draw(screen, self.scrollx, self.scrolly)
                    
                    if len(laser.lines) == 0 and len(laser.particles) == 0:
                        self.lasers.remove(laser)
                
                ### Blit Effects ###
                
                for circle in self.circle_effects:
                    circle.update()
                    circle.draw(screen)
                    
                    if circle.size > circle.target:
                        self.circle_effects.remove(circle)
                
                ### Score ###
                self.blit_ingame(screen)
    
                self.lines.draw(screen, self.scrollx, self.scrolly, self.height)
                pygame.draw.line(screen, self.blue_,
                                self.lines.adj_pos(self.last_pos, self.scrollx, self.scrolly),
                                pygame.mouse.get_pos(),
                                int(self.lines.width/2))
                
                ### Blit Player ###
                
                for i in range(len(self.trail)-1):
                    pygame.draw.line(screen, self.trail_blue,
                                        self.lines.adj_pos(self.trail[i], self.scrollx, self.scrolly),
                                        self.lines.adj_pos(self.trail[i+1], self.scrollx, self.scrolly),
                                        max(int(self.lines.width/4), 1))
                
                if len(self.trail) == 50:
                    self.trail.popleft()
                
                for particle in self.player_particles:
                    particle.update()
                    particle.draw(screen, self.scrollx, self.scrolly)
                    if particle.size <= 0:
                        self.player_particles.remove(particle)
                
                self.player.draw(screen, self.scrollx, self.scrolly)
                
                if self.player.y - self.scrolly > self.height or self.player.x < 0 or self.player.x > self.width:
                    self.load_screen(2)
                    
            elif self.state == 2:
                if self.shake_tick>0:
                    self.scrollx = self.last_scrollx + (random.random()-0.5)*self.shake_tick
                    self.prev_scrolly = self.scrolly
                    self.scrolly = self.prev_scrolly + (random.random()-0.5)*self.shake_tick
                    self.shake_tick -= 0.2
                
                ### Blit background ###
                self.lines.draw_dark(screen, self.scrollx, self.scrolly-self.height/45, self.gray)
                
                ### Blit Effects ###
                
                for circle in self.circle_effects:
                    circle.update()
                    circle.draw(screen)
                    
                    if circle.size > circle.target:
                        self.circle_effects.remove(circle)
                
                cnt = 0 # for effects(more informations in load function)
                for circle in self.circle_effects_dead:
                    cnt += 1
                    if cnt > 2:
                        circle.update(0.015, 0.05)
                    else:
                        circle.update(0.015)
                    
                    circle.draw(screen, self.scrollx, self.scrolly)
                    
                    if circle.size > circle.target:
                        self.circle_effects_dead.remove(circle)
                
                self.lines.draw(screen, self.scrollx, self.scrolly, self.height)
                
                self.scrolly += (self.adjed_scrolly-self.scrolly)*0.03 if (self.adjed_scrolly-self.scrolly)*0.03 >= 0.1 else 0
                
                self.blit_game_over(screen)
            
            # Show FPS if needed
            if self.show_fps:
                blit_fps(screen, clock)

            pygame.display.flip()

class LynezLoadingScreen(ScreenObject):
    def __init__(self, width, height):
        super().__init__(width, height)
        
        self.dark_blue = (10,17,30)
        self.white = (255,255,255)
        
    def loop(self, screen):
        surface = pygame.Surface((self.width, self.height))
        surface.fill(self.dark_blue)

        title_font = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", int(self.height // 10))
        title_text = title_font.render("Lynez", True, self.white)
        
        title_text_rect = title_text.get_rect()
        title_text_rect.center = (self.width / 2, self.height / 2)
        
        surface.blit(title_text, title_text_rect)
        
        fade_in(screen, surface, self.width, self.height, 2000)
        
        return "menu", screen

class LynezScreen(ScreenObject):
    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)
        self.show_fps = show_fps

    def loop(self, screen):
        running = True
        curr_lynez_screen_idx = 0

        screen_ids = {
            "loading": 0,
            "menu": 1
        }
        
        while running:
            if curr_lynez_screen_idx == 0:
                curr_lynez_screen = LynezLoadingScreen(self.width, self.height)
                next_screen, curr_screen_surface = curr_lynez_screen.loop(screen)
                curr_lynez_screen_idx = screen_ids[next_screen]
                pygame.time.wait(2000)
                fade_out(screen, curr_screen_surface, self.width, self.height, 2000)
            
            elif curr_lynez_screen_idx == 1:
                curr_lynez_screen = LynezMainScreen(self.width, self.height, show_fps=self.show_fps)
                next_screen, curr_screen_surface = curr_lynez_screen.loop(screen)
                pygame.time.wait(2000)
                fade_out(screen, curr_screen_surface, self.width, self.height, 2000)
                return 0, screen

if __name__ == "__main__":
    pygame.init()
    WIDTH, HEIGHT = 1280, 720
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Lynez")

    menu_screen = LynezScreen(WIDTH, HEIGHT, show_fps=False)
    menu_screen.loop(screen)
    print("out")
