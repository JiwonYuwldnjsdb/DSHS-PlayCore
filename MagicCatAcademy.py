import pygame
import sys
import math
import random

from PlayCoreLibraries import ScreenObject, fade_out, blit_fps

class StrokeRecognizer:
    def __init__(self):
        pass

    def bounding_box_size(self, stroke):
        xs = [p[0] for p in stroke]
        ys = [p[1] for p in stroke]
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        return w, h

    def is_horizontal_line(self, stroke):
        if len(stroke) < 2:
            return False
        xs = [p[0] for p in stroke]
        ys = [p[1] for p in stroke]
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        return (width > 100 and height < 0.2 * width)

    def is_vertical_line(self, stroke):
        if len(stroke) < 2:
            return False
        xs = [p[0] for p in stroke]
        ys = [p[1] for p in stroke]
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        return (height > 100 and width < 0.2 * height)

    def is_inverted_v_shape(self, stroke):
        if len(stroke) < 3:
            return False
        w, h = self.bounding_box_size(stroke)
        if w < 50 or h < 50:
            return False
        ys = [p[1] for p in stroke]
        apex_index = ys.index(min(ys))  # 최상단
        if apex_index == 0 or apex_index == len(stroke) - 1:
            return False
        
        first_point = stroke[0]
        apex_point = stroke[apex_index]
        last_point = stroke[-1]
        
        dx1 = apex_point[0] - first_point[0]
        dy1 = apex_point[1] - first_point[1]
        if dx1 == 0:
            return False
        slope1 = dy1 / float(dx1)

        dx2 = last_point[0] - apex_point[0]
        dy2 = last_point[1] - apex_point[1]
        if dx2 == 0:
            return False
        slope2 = dy2 / float(dx2)

        # 왼->꼭짓점 기울기 음수, 꼭짓점->오른쪽 기울기 양수
        if slope1 < -0.3 and slope2 > 0.3:
            return True
        return False

    def is_v_shape(self, stroke):
        if len(stroke) < 3:
            return False
        w, h = self.bounding_box_size(stroke)
        if w < 50 or h < 50:
            return False
        ys = [p[1] for p in stroke]
        apex_index = ys.index(max(ys))  # 최하단
        if apex_index == 0 or apex_index == len(stroke) - 1:
            return False
        
        first_point = stroke[0]
        apex_point = stroke[apex_index]
        last_point = stroke[-1]
        
        dx1 = apex_point[0] - first_point[0]
        dy1 = apex_point[1] - first_point[1]
        if dx1 == 0:
            return False
        slope1 = dy1 / float(dx1)

        dx2 = last_point[0] - apex_point[0]
        dy2 = last_point[1] - apex_point[1]
        if dx2 == 0:
            return False
        slope2 = dy2 / float(dx2)
        
        # 왼->꼭짓점 기울기 양수, 꼭짓점->오른쪽 기울기 음수
        if slope1 > 0.3 and slope2 < -0.3:
            return True
        return False

    def is_lightning_sign(self, stroke):
        """
        '\|\' 모양을 90도 반시계로 회전한 형태:
        - 첫 번째 구간: 대각선(양의 기울기) 혹은 (음의 기울기)
        - 두 번째 구간: 거의 수평
        - 세 번째 구간: 첫 번째 구간과 같은 방향의 대각선
        """
        if len(stroke) < 4:
            return False

        w, h = self.bounding_box_size(stroke)
        if w < 50 and h < 50:
            return False

        n = len(stroke)
        p1 = stroke[0]
        p2 = stroke[n // 3]
        p3 = stroke[2 * n // 3]
        p4 = stroke[-1]

        def slope(a, b):
            dx = b[0] - a[0]
            dy = b[1] - a[1]
            # dx가 0이면 기울기 무한대로 가정(위아래 직선)
            if dx == 0:
                if dy > 0:
                    return float('inf')
                elif dy < 0:
                    return float('-inf')
                else:
                    return 0
            return dy / float(dx)

        s1 = slope(p1, p2)
        s2 = slope(p2, p3)
        s3 = slope(p3, p4)

        pos_threshold = 0.3
        zero_threshold = 0.3  # '거의 0'으로 볼 범위

        # 대각선(양) - 수평 - 대각선(양)
        patternA = (s1 > pos_threshold and abs(s2) < zero_threshold and s3 > pos_threshold)
        # 대각선(음) - 수평 - 대각선(음)
        patternB = (s1 < -pos_threshold and abs(s2) < zero_threshold and s3 < -pos_threshold)

        if patternA or patternB:
            return True
        return False

    def recognize_spell(self, stroke):
        if self.is_horizontal_line(stroke):
            return "horizontal"
        elif self.is_vertical_line(stroke):
            return "vertical"
        elif self.is_v_shape(stroke):
            return "vspell"
        elif self.is_inverted_v_shape(stroke):
            return "ivspell"
        elif self.is_lightning_sign(stroke):
            return "lighting"
        else:
            return ""

#########################################################
# 2) Ghost
#########################################################
class Ghost:
    AVAILABLE_SPELLS = ["horizontal", "vertical", "vspell", "ivspell", "lighting"]
    
    def __init__(self, x, y, spell_length, width, speed=50, direction=1):
        self.x = x
        self.y = y
        
        # 무작위 스펠 목록 (길이=spell_length)
        self.spells = random.choices(Ghost.AVAILABLE_SPELLS, k=spell_length)
        self.spell_idx = 0
        self.alive = True
        
        # 기본 상태 & 애니메이션
        self.state = "moving"
        self.animation_frame_cnt = 0
        
        self.animation_frames = {}
        self.animation_adj = {}
        self.animation_frame_delay = {}
        
        # 예: ghost/frame_delay.txt 로부터 딜레이 읽기
        with open("data/MagicCatAcademy/imgs/ghost/frame_delay.txt", "r") as file:
            lines = file.read().split('\n')
            for line in lines:
                if not line.strip():
                    continue
                a_id, val = line.split()
                self.animation_frame_delay[a_id] = int(val)
        
        # 이미지 로드 예시
        self.animation_frames['moving'] = []
        for i in range(1):
            path = f"data/MagicCatAcademy/imgs/ghost/moving/{i+1}.png"
            self.animation_frames['moving'].append(path)
        
        self.animation_frames['attacked'] = []
        for i in range(4):
            path = f"data/MagicCatAcademy/imgs/ghost/attacked/{i+1}.png"
            self.animation_frames['attacked'].append(path)
        
        self.animation_frames['die'] = []
        for i in range(7):
            path = f"data/MagicCatAcademy/imgs/ghost/die/{i+1}.png"
            self.animation_frames['die'].append(path)
        
        self.animation_frames['attack'] = []
        for i in range(5):
            path = f"data/MagicCatAcademy/imgs/ghost/attack/{i+1}.png"
            self.animation_frames['attack'].append(path)
        
        size_adj = {
            'moving':1,
            'attacked':113/94,
            'die':95/94,
            'attack':85/94
        }
        
        # 실제 로딩 & 스케일
        for anim_id in self.animation_frames:
            new_list = []
            for img_path in self.animation_frames[anim_id]:
                img = pygame.image.load(img_path).convert_alpha()
                
                if direction == 0:
                    img = pygame.transform.flip(img, True, False)
                
                scale_x = int(width * 0.1 * size_adj[anim_id])
                scale_y = int(width * 0.1 * (img.get_height()/img.get_width()) * size_adj[anim_id])
                img_scaled = pygame.transform.scale(img, (scale_x, scale_y))
                new_list.append(img_scaled)
            self.animation_frames[anim_id] = new_list
        
        self.animation_adj['moving'] = (0, 0)
        self.animation_adj['attacked'] = (
            0, -self.animation_frames['attacked'][0].get_height()*0.05
        )
        self.animation_adj['die'] = (
            0, -self.animation_frames['die'][0].get_height()*0.35
        )
        
        self.animation_adj['attack'] = (
            0, 0
        )
    
        self.shift_pos = (
            self.animation_frames['moving'][0].get_width()//2,
            self.animation_frames['moving'][0].get_height()//2
        )
        
        size_adj_spell = {
            'horizontal':1,
            'vertical':20/19,
            'vspell':21/19,
            'ivspell':20/19,
            'lighting':21/19,
        }
        
        self.spell_imgs = {}
        
        self.spell_imgs['horizontal'] = "data/MagicCatAcademy/imgs/ghost/symbol/horizontal.png"
        self.spell_imgs['vertical'] = "data/MagicCatAcademy/imgs/ghost/symbol/vertical.png"
        self.spell_imgs['vspell'] = "data/MagicCatAcademy/imgs/ghost/symbol/vspell.png"
        self.spell_imgs['ivspell'] = "data/MagicCatAcademy/imgs/ghost/symbol/ivspell.png"
        self.spell_imgs['lighting'] = "data/MagicCatAcademy/imgs/ghost/symbol/lighting.png"
        
        for spell_id in self.spell_imgs:
            img_path = self.spell_imgs[spell_id]
            img = pygame.image.load(img_path).convert_alpha()
            
            scale_x = int(width * 0.02 * (img.get_width()/img.get_height()) * size_adj_spell[spell_id])
            scale_y = int(width * 0.02 * size_adj_spell[spell_id])
            
            img_scaled = pygame.transform.scale(img, (scale_x, scale_y))
            self.spell_imgs[spell_id] = img_scaled
        
        self.spell_width = self.spell_imgs['horizontal'].get_width()
        
        # 이동 속도 (웨이브 로직에 따라 조정)
        self.speed = speed
    
    def check_spell(self, spell):
        """플레이어가 사용한 스펠이 내 스펠 목록의 다음 순서와 같으면 진행"""
        if self.alive and self.spell_idx < len(self.spells):
            if spell == self.spells[self.spell_idx]:
                self.spell_idx += 1
                self.state = "attacked"
                self.animation_frame_cnt = 0
                if self.spell_idx == len(self.spells):
                    # 유령 사망
                    self.alive = False
                    self.state = "die"
                    return (True, True)
                return (True, False)
    
    def update(self, dt, player_x, player_y, frame_cnt):
        """플레이어 방향으로 이동 + 애니메이션 진행"""
        if self.state != 'die' and self.state != 'attack':
            dx = player_x - self.x
            dy = player_y - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                nx = dx/dist
                ny = dy/dist
                self.x += nx * self.speed * dt
                self.y += ny * self.speed * dt
        
        # 애니메이션 프레임 갱신
        delay = self.animation_frame_delay.get(self.state, 5)
        
        if frame_cnt % delay == 0:
            self.animation_frame_cnt += 1
            if self.state == "die":
                max_idx = len(self.animation_frames['die']) - 1
                if self.animation_frame_cnt > max_idx:
                    self.animation_frame_cnt = max_idx
            elif self.state == "attacked":
                max_idx = len(self.animation_frames['attacked']) - 1
                if self.animation_frame_cnt > max_idx:
                    self.state = "moving"
            elif self.state == "attack":
                max_idx = len(self.animation_frames['attack']) - 1
                if self.animation_frame_cnt > max_idx:
                    self.state = 'die'
                    self.alive = False
                    self.animation_frame_cnt = 3
            else:
                self.animation_frame_cnt %= len(self.animation_frames[self.state])
    
    def draw(self, screen):
        """유령 이미지 + 남은 스펠 목록 표시"""
        frames = self.animation_frames[self.state]
        idx = min(self.animation_frame_cnt, len(frames) - 1)
        ghost_img = frames[idx]
        
        adj_x, adj_y = self.animation_adj[self.state]
        draw_x = self.x - self.shift_pos[0] + adj_x
        draw_y = self.y - self.shift_pos[1] + adj_y
        screen.blit(ghost_img, (draw_x, draw_y))
    
    def draw_spell(self, screen):
        start_x = -(len(self.spells)-self.spell_idx)/2
        margin_idx = 0
        for i, sp in enumerate(self.spells):
            if i >= self.spell_idx:
                screen.blit(self.spell_imgs[sp], (self.x + (margin_idx+start_x)*self.spell_width, self.y - self.animation_frames['moving'][0].get_height()*0.7))
                margin_idx+=1

    def distance_to_player(self, px, py):
        return math.hypot(self.x - px, self.y - py)


#########################################################
# 3) Player
#########################################################
class Player:
    def __init__(self, x, y, width, hp=5):
        self.x = x
        self.y = y
        self.hp = hp  # 플레이어 체력
        
        self.animation_frame_cnt = 0
        self.state = "waiting"
        
        self.spells = {"horizontal","vertical","vspell","ivspell","lighting"}
        
        self.animation_frames = {}
        self.animation_adj = {}
        self.animation_frame_delay = {}
        
        # frame_delay.txt 로딩
        with open("data/MagicCatAcademy/imgs/momo/frame_delay.txt", "r") as f:
            file_data = f.read().split('\n')
            for d in file_data:
                if not d.strip():
                    continue
                key, val = d.split()
                self.animation_frame_delay[key] = int(val)
        
        # 각 애니메이션 로딩
        self.animation_frames['waiting'] = []
        for i in range(12):
            path = f"data/MagicCatAcademy/imgs/momo/waiting/{i+1}.png"
            self.animation_frames['waiting'].append(path)
        for i in range(11,-1,-1):
            path = f"data/MagicCatAcademy/imgs/momo/waiting/{i+1}.png"
            self.animation_frames['waiting'].append(path)
        
        self.animation_frames['spelling'] = []
        for i in range(6):
            path = f"data/MagicCatAcademy/imgs/momo/spelling/{i+1}.png"
            self.animation_frames['spelling'].append(path)
        for i in range(5,-1,-1):
            path = f"data/MagicCatAcademy/imgs/momo/spelling/{i+1}.png"
            self.animation_frames['spelling'].append(path)
        
        self.animation_frames['horizontal'] = []
        for i in range(5):
            path = f"data/MagicCatAcademy/imgs/momo/horizontal/{i+1}.png"
            self.animation_frames['horizontal'].append(path)
        
        self.animation_frames['vertical'] = []
        for i in range(5):
            path = f"data/MagicCatAcademy/imgs/momo/vertical/{i+1}.png"
            self.animation_frames['vertical'].append(path)
        
        self.animation_frames['vspell'] = []
        for i in range(6):
            path = f"data/MagicCatAcademy/imgs/momo/vspell/{i+1}.png"
            self.animation_frames['vspell'].append(path)
        
        self.animation_frames['ivspell'] = []
        for i in range(6):
            path = f"data/MagicCatAcademy/imgs/momo/ivspell/{i+1}.png"
            self.animation_frames['ivspell'].append(path)
        
        self.animation_frames['lighting'] = []
        for i in range(6):
            path = f"data/MagicCatAcademy/imgs/momo/lighting/{i+1}.png"
            self.animation_frames['lighting'].append(path)
        
        self.animation_frames['attacked'] = []
        for i in range(4):
            path = f"data/MagicCatAcademy/imgs/momo/attacked/{i+1}.png"
            self.animation_frames['attacked'].append(path)
        
        size_adj = {
            'waiting': 1,
            'spelling': 117/89,
            'horizontal': 131/89,
            'vertical': 130/89,
            'vspell': 118/89,
            'ivspell': 148/89,
            'lighting': 141/89,
            'attacked': 110/89
        }
        
        # 이미지 스케일
        for anim_id in self.animation_frames:
            new_list = []
            for path in self.animation_frames[anim_id]:
                img = pygame.image.load(path).convert_alpha()
                scale_x = int(width * 0.1 * size_adj[anim_id])
                scale_y = int(width * 0.1 * (img.get_height()/img.get_width()) * size_adj[anim_id])
                scaled_img = pygame.transform.scale(img, (scale_x, scale_y))
                new_list.append(scaled_img)
            self.animation_frames[anim_id] = new_list
        
        # 위치 보정
        self.animation_adj['waiting'] = (0,0)
        self.animation_adj['spelling'] = (0, -self.animation_frames['spelling'][0].get_height()*0.05)
        self.animation_adj['vertical'] = (0, -self.animation_frames['vertical'][0].get_height()*0.35)
        self.animation_adj['horizontal'] = (-self.animation_frames['horizontal'][0].get_height()*0.2,
                                            -self.animation_frames['horizontal'][0].get_height()*0.35)
        self.animation_adj['vspell'] = (-self.animation_frames['vspell'][0].get_height()*0.1,
                                        -self.animation_frames['vspell'][0].get_height()*0.425)
        self.animation_adj['ivspell'] = (-self.animation_frames['ivspell'][0].get_height()*0.15,
                                         -self.animation_frames['ivspell'][0].get_height()*0.425)
        self.animation_adj['lighting'] = (-self.animation_frames['lighting'][0].get_height()*0.25,
                                          -self.animation_frames['lighting'][0].get_height()*0.4)
        self.animation_adj['attacked'] = (-self.animation_frames['attacked'][0].get_height()*0.25,
                                          -self.animation_frames['attacked'][0].get_height()*0.4)
        
        self.shift_pos = (
            self.animation_frames['waiting'][0].get_width()/2,
            self.animation_frames['waiting'][0].get_height()/2
        )
    
    def update_state(self, state):
        self.state = state
        self.animation_frame_cnt = 0
    
    def update(self, frame_cnt):
        delay = self.animation_frame_delay.get(self.state, 6)
        if frame_cnt % delay == 0:
            self.animation_frame_cnt += 1
            # 스펠 애니메이션 끝나면 waiting으로 복귀
            if (self.state in self.spells or self.state=='attacked') and self.animation_frame_cnt == len(self.animation_frames[self.state]):
                self.update_state('waiting')
                return
            self.animation_frame_cnt %= len(self.animation_frames[self.state])
    
    def draw(self, screen):
        frames = self.animation_frames[self.state]
        idx = min(self.animation_frame_cnt, len(frames) - 1)
        img = frames[idx]
        adj_x, adj_y = self.animation_adj[self.state]
        
        draw_x = self.x - self.shift_pos[0] + adj_x
        draw_y = self.y - self.shift_pos[1] + adj_y
        screen.blit(img, (draw_x, draw_y))


#########################################################
# 4) 세 가지 화면 (TitleScreen, GameScreen, GameOverScreen)
#########################################################
class TitleScreen(ScreenObject):
    """'Click to Start'라고 표시하고 클릭 시 GameScreen으로 이동"""
    def __init__(self, width, height):
        super().__init__(width, height)
        
        self.gray = (32, 33, 36)
        
        self.background_imgs = []
        
        for i in range(2):
            img = pygame.image.load(
                f"data/MagicCatAcademy/imgs/game/menu{i+1}.jpg"
            ).convert_alpha()
            
            img = pygame.transform.scale(
                img,
                (
                    int(self.width),
                    int(self.width * (img.get_height() / img.get_width()))
                )
            )
            
            self.background_imgs.append(img)
        
        self.background_img_pos = (
            (self.width - img.get_width()) / 2,
            (self.height - img.get_height()) / 2
        )
        
        self.text_background_imgs = []
        
        for i in range(2):
            img = pygame.image.load(
                f"data/MagicCatAcademy/imgs/game/text_background{i+1}.png"
            ).convert_alpha()
            
            img = pygame.transform.scale(
                img,
                (
                    int(self.width*0.6),
                    int(self.width*0.6 * (img.get_height() / img.get_width()))
                )
            )
            
            self.text_background_imgs.append(img)
        
        self.fontH1 = pygame.font.Font("data/fonts/jua.ttf", int(self.height // 10))
        self.fontP = pygame.font.Font("data/fonts/jua.ttf", int(self.height // 30))
        
        self.player = Player(width*3/4, height*3/5, width*1.5, hp=5)
        
        self.running = True
    
    def loop(self, screen):
        clock = pygame.time.Clock()
        frame_cnt = 0
        
        mouse_down = False
        mouse_down_frames = 0
        mouse_up_frames = 0
        
        data = []
        with open("data/MagicCatAcademy/playdata/saves.txt", "r") as file:
            lines = file.read().split('\n')
            for line in lines:
                if not line.strip():
                    continue
                data.append(line)
        
        
        self.menu_texts = ['Click to Start', 'Hold to Quit', f'Best {data[0]}']
        
        while self.running:
            dt_ms = clock.tick(60)

            dt = dt_ms / 1000.0
            
            if mouse_down_frames == 240:
                return 'exit', screen
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.player.update_state('spelling')
                        mouse_down = True
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.player.update_state('waiting')
                        if mouse_down == True:
                            if mouse_down_frames < 60:
                                if mouse_up_frames > 10:
                                    return "game", screen

                        mouse_down = False
                        mouse_down_frames = 0
                        mouse_up_frames = 0
            
            self.player.update(frame_cnt)
            
            screen.fill(self.gray)
            screen.blit(self.background_imgs[0], self.background_img_pos)
            
            for i in range(3):
                screen.blit(self.text_background_imgs[i%2], (
                    ((i+1) * (-0.05) - 0.02) * self.width,
                    self.height*(0.25 + i*0.15)
                ))
                
                text_surface = self.fontH1.render(self.menu_texts[i], False, (0, 0, 0))
                screen.blit(text_surface, (self.height // 10, self.height*(0.25 + i*0.15)))
            
            text_surface = self.fontP.render("Original Game by Google Doodle Games. Remade by Jiwon Yu", False, (0, 0, 0))
            screen.blit(text_surface, (10, self.height*0.8))
            
            self.player.draw(screen)
            
            if mouse_down:
                mouse_down_frames += 1
                if mouse_down_frames >= 60:
                    pygame.draw.arc(screen, (255, 255, 255),
                            (pygame.mouse.get_pos()[0]-self.height/60,
                            pygame.mouse.get_pos()[1]-self.height/60, self.height/60*2, self.height/60*2), 
                            math.radians(0), math.radians(min(mouse_down_frames*2-120, 360)), 5)
            else:
                mouse_up_frames += 1
            
            pygame.display.flip()
            
            frame_cnt+=1
        
        return "game", screen  # 혹은 기본값


class GameScreen(ScreenObject):
    """실제 게임 플레이 화면 + 웨이브 방식으로 수정"""
    def __init__(self, width, height):
        super().__init__(width, height)
        
        self.background_imgs = []
        
        for i in range(4):
            img = pygame.image.load(
                f"data/MagicCatAcademy/imgs/game/main_game{i+1}.png"
            ).convert_alpha()
            
            img = pygame.transform.scale(
                img,
                (
                    int(self.height * (img.get_width() / img.get_height())),
                    int(self.height)
                )
            )
            
            self.background_imgs.append(img)
        
        self.background_img_pos = (
            (self.width - img.get_width()) / 2,
            (self.height - img.get_height()) / 2
        )
        
        self.strokeRecognizer = StrokeRecognizer()
        
        self.player = Player(width/2, height/2, width, hp=5)  # 체력 5로 예시
        
        # 웨이브 관련
        self.wave = 0
        self.point = 0
        self.ghosts = []
        
        # 드로잉 관련
        self.is_drawing = False
        self.current_stroke = []
        
        self.fontH1 = pygame.font.Font("data/fonts/jua.ttf", int(self.height // 10))
        
        self.heart_img_filled = pygame.image.load(
                "data/MagicCatAcademy/imgs/game/heart_filled.png"
            ).convert_alpha()
            
        self.heart_img_filled = pygame.transform.scale(
            self.heart_img_filled,
            (
                int(self.width/20),
                int(self.width/20 * (self.heart_img_filled.get_height() / self.heart_img_filled.get_width()))
            )
        )
        
        self.heart_img_blank = pygame.image.load(
                "data/MagicCatAcademy/imgs/game/heart_blank.png"
            ).convert_alpha()
            
        self.heart_img_blank = pygame.transform.scale(
            self.heart_img_blank,
            (
                int(self.width/20),
                int(self.width/20 * (self.heart_img_blank.get_height() / self.heart_img_blank.get_width()))
            )
        )
    
    def reset(self):
        self.player.hp = 5
        self.wave = 0
        self.point = 0
        self.ghosts.clear()
        
        self.is_drawing = False
        self.current_stroke = []
    
    def spawn_ghost_random_edge(self, width, height, spell_length):
        if self.wave//10 == 0:
            side = random.choice(["top","bottom","left","right"])
            if side == "top":
                x = random.randint(int(width/3), int(width*2/3))
                y = 0
            elif side == "bottom":
                x = random.randint(0, width)
                y = height
            elif side == "left":
                x = 0
                y = random.randint(int(height/3), height)
            else:
                x = width
                y = random.randint(int(height/3), height)
        elif self.wave//10 == 1:
            side = random.choice(["bottom","left","right"])
            if side == "bottom":
                x = random.randint(0, width)
                y = height
            elif side == "left":
                x = 0
                y = random.randint(height/2, height)
            else:
                x = width
                y = random.randint(height/2, height)
        else:
            side = random.choice(["bottom","left","right"])
            if side == "bottom":
                x = random.randint(0, width)
                y = height
            elif side == "left":
                x = 0
                y = random.randint(int(height/3), height)
            else:
                x = width
                y = random.randint(int(height/3), height)
        
        # 스펠 길이에 따른 속도 조정
        # 기본 속도 = 50, 스펠 길이 기준 3보다 작으면 좀 더 빠르게, 크면 느리게
        base_speed = 50
        speed = base_speed + (3 - spell_length) * 5
        # 너무 느리거나 빠른 경우 제한
        speed = max(20, min(speed, 80))
        
        direction = 0 if x < width/2 else 1
        
        return Ghost(x, y, spell_length, width, speed=speed, direction=direction)
    
    def spawn_wave(self):
        """현재 wave 값에 따라 새로운 유령들을 소환"""
        wave_ghost_count = min(self.wave//3+1, 12)  # 웨이브가 올라갈수록 수 증가 (적당히 제한)
        wave_max_len = min(self.wave//5+1, 8)       # 웨이브 1이면 길이최대2, 2이면최대3, ... 최대8
        
        for _ in range(wave_ghost_count):
            spell_len = random.randint(1, wave_max_len)
            ghost = self.spawn_ghost_random_edge(self.width, self.height, spell_len)
            self.ghosts.append(ghost)
    
    def draw_stroke(self, surface, stroke, color=(255, 255, 255), width=22):
        if stroke:
            if len(stroke) > 1:
                pygame.draw.lines(surface, color, False, stroke, width)
            
            for point in stroke:
                pygame.draw.circle(surface, color, point, 10)
            
            pygame.draw.circle(surface, (255, 255, 255), stroke[-1], 15)
    
    def loop(self, screen):
        clock = pygame.time.Clock()
        running = True
        frame_cnt = 0
        
        update_enabled = True
        waitng_frame = 60
        
        point_increase_vel = 1
        point_target = 0
        
        spell_color = (0,0,0)
        
        while running:
            dt_ms = clock.tick(60)
            dt = dt_ms / 1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                    
                if update_enabled:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:
                            self.is_drawing = True
                            self.current_stroke = [event.pos]
                            self.player.update_state('spelling')
                    elif event.type == pygame.MOUSEMOTION:
                        if self.is_drawing:
                            self.current_stroke.append(event.pos)
                            spell = self.strokeRecognizer.recognize_spell(self.current_stroke)
                            
                            if spell == 'horizontal':
                                spell_color = (231,51,37)
                            elif spell =='vertical':
                                spell_color = (44,98,204)
                            elif spell == 'vspell':
                                spell_color = (253,245,94)
                            elif spell == 'ivspell':
                                spell_color = (117,250,79)
                            elif spell == 'lighting':
                                spell_color = (247,203,71)
                            else:
                                spell_color = (255,255,255)
                            
                    elif event.type == pygame.MOUSEBUTTONUP:
                        if event.button == 1 and self.is_drawing:
                            self.is_drawing = False
                            # 스펠 인식
                            spell = self.strokeRecognizer.recognize_spell(self.current_stroke)
                            
                            if spell:
                                self.player.update_state(spell)
                                # 살아있는 유령에게 체크
                                for g in self.ghosts:
                                    if g.alive:
                                        res = g.check_spell(spell) # attacked?, dead?
                                        
                                        if res:
                                            if res[1]:
                                                point_target += 10
                                            
                                            if res[0] and spell == 'lighting':
                                                for g_tmp in self.ghosts:
                                                    if g_tmp != g:
                                                        g_tmp.spell_idx += 1
                                                        g_tmp.state = "attacked"
                                                        g_tmp.animation_frame_cnt = 0
                                                        if g_tmp.spell_idx == len(g_tmp.spells):
                                                            # 유령 사망
                                                            g_tmp.alive = False
                                                            g_tmp.state = "die"
                                                            point_target += 10
                                                break
                            else:
                                self.player.update_state('waiting')
                            self.current_stroke = []
            
            for g in self.ghosts:
                g.update(dt, self.player.x, self.player.y, frame_cnt)
                # 'die' 상태에서 마지막 프레임이 끝났다면 제거
                if not g.alive:
                    max_idx = len(g.animation_frames['die']) - 1
                    if g.animation_frame_cnt >= max_idx:
                        self.ghosts.remove(g)
            
            # -- 플레이어 업데이트(애니메이션만) --
            self.player.update(frame_cnt)
            
            if update_enabled:
                for g in self.ghosts:
                    if g.alive:
                        dist = g.distance_to_player(self.player.x, self.player.y)
                        if dist < 50*self.width/1280:  # 거리 50 이하 -> 충돌로 간주
                            self.player.hp -= 1
                            g.state = 'attack'
                            self.player.update_state('attacked')
                            g.alive = False
                            break  # 1초에 최대 1만 깎이므로 break
            
            # -- HP가 0 이하 -> GameOverScreen으로 --
            if self.player.hp <= 0:
                update_enabled = False
                if waitng_frame == 30:
                    for g in self.ghosts:
                        g.animation_frame_cnt = 3
                        g.state = 'die'
                        g.alive = False
                
                waitng_frame -= 1
                
                if waitng_frame == 0:
                    return "gameover", screen, self.point
            
            if update_enabled:
                # -- 웨이브 클리어 체크(살아있는 유령이 하나도 없으면 다음 웨이브) --
                if len(self.ghosts) == 0:
                    # 다음 웨이브로
                    self.wave += 1
                    self.spawn_wave()
            
            self.point = min(self.point+point_increase_vel, point_target)
            
            # ------------------- 그리기 -------------------
            screen.blit(self.background_imgs[min(self.wave//10,3)], self.background_img_pos)
            
            # 플레이어
            self.player.draw(screen)
            
            # 유령들
            for g in self.ghosts:
                g.draw(screen)
            
            for g in self.ghosts:
                g.draw_spell(screen)
            
            # 현재 드로잉 스펠
            self.draw_stroke(screen, self.current_stroke, spell_color)
            
            # HP 표시 + 웨이브 표시
            start_x = self.width/40
            for _ in range(self.player.hp):
                screen.blit(self.heart_img_filled, (start_x, self.width/40))
                start_x+=self.width/20
            
            for _ in range(5-self.player.hp):
                screen.blit(self.heart_img_blank, (start_x, self.width/40))
                start_x+=self.width/20

            wave_text = self.fontH1.render(f"{self.point}", True, (242,169,59))
            text_rect = wave_text.get_rect()
            text_rect.topright = (screen.get_width() - self.width/40, self.width/110)  # 20px padding from the right
            screen.blit(wave_text, text_rect)
            
            pygame.display.flip()
            frame_cnt += 1
        
        return "gameover", screen  # 기본 반환


class GameOverScreen(ScreenObject):
    """'Click to Restart' 표시. 클릭하면 TitleScreen으로 복귀"""
    def __init__(self, width, height):
        super().__init__(width, height)
        self.running = True
                
        self.white = (255, 255, 255)
        
        self.background_img = pygame.image.load(
            "data/MagicCatAcademy/imgs/game/game_over.png"
        ).convert_alpha()
        
        self.background_img = pygame.transform.scale(
            self.background_img,
            (
                int(self.width),
                int(self.width * (self.background_img.get_height() / self.background_img.get_width()))
            )
        )
        self.background_img_pos = (
            (self.width - self.background_img.get_width()) / 2,
            (self.height - self.background_img.get_height()) / 2
        )
        
        self.fontH1 = pygame.font.Font("data/fonts/jua.ttf", int(self.height // 8))
        self.fontP = pygame.font.Font("data/fonts/jua.ttf", int(self.height // 15))
    
    def loop(self, screen, point):
        self.point = point
        
        data = []
        
        with open("data/MagicCatAcademy/playdata/saves.txt", "r") as file:
            lines = file.read().split('\n')
            for line in lines:
                if not line.strip():
                    continue
                data.append(line)
        
        if point > int(data[0]):
            with open("data/MagicCatAcademy/playdata/saves.txt", "w") as file:
                file.write(f"{point}\n")
                file.close()
        
        text_point_surface = self.fontH1.render(f'{point}', False, (255, 255, 255))
        text_point_rect = text_point_surface.get_rect(center = (self.width * 13/18, self.height * 3/7))
        
        text_info_surface = self.fontP.render('Click to Restart', False, (255, 255, 255))
        text_info_rect =text_info_surface.get_rect(center = (self.width * 13/18, self.height * 4/7))
        
        clock = pygame.time.Clock()
        
        while self.running:
            dt = clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # 클릭 -> TitleScreen으로 복귀
                    return "title", screen
            
            screen.fill(self.white)
            
            screen.blit(self.background_img, self.background_img_pos)
            
            screen.blit(text_point_surface, text_point_rect)
            screen.blit(text_info_surface, text_info_rect)
            
            pygame.display.flip()
        
        return "title", screen


#########################################################
# 5) 전체 흐름 관리 (MagicCatAcademyMainScreen)
#########################################################
class MagicCatAcademyMainScreen(ScreenObject):
    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)
        self.show_fps = show_fps
    
    def loop(self, screen):
        running = True
        
        # 화면 state: "title" → "game" → "gameover" → ...
        current_state = "title"
        
        # 화면 클래스들 준비
        title_screen = TitleScreen(self.width, self.height)
        game_screen = GameScreen(self.width, self.height)
        gameover_screen = GameOverScreen(self.width, self.height)
        
        while running:
            if current_state == "title":
                next_state, _ = title_screen.loop(screen)
                current_state = next_state
                game_screen.reset()
            
            elif current_state == "game":
                next_state, _, point = game_screen.loop(screen)
                current_state = next_state
            
            elif current_state == "gameover":
                next_state, _ = gameover_screen.loop(screen, point)
                current_state = next_state
            
            # 필요하다면 fade_out 등 화면 전환 효과도 추가할 수 있음
            
            # 만약 "exit" 같은 상태를 만들어 게임을 완전히 종료하고 싶다면 해당 로직 추가
            if current_state == "exit":
                running = False
        
        return 0, screen


##########################################################
# 로딩 화면 (옵션) - 여기서는 그대로 사용 예시
##########################################################
class MagicCatAcademyLoadingScreen:
    def __init__(self, width, height, show_fps):
        self.width = width
        self.height = height
        self.show_fps = show_fps

        self.white = (255, 255, 255)
        self.dark_gray = (45, 48, 56)
        self.gray = (32, 33, 36)
        
        self.button_color = list(self.dark_gray)

        self.background_img = pygame.image.load(
            "data/MagicCatAcademy/imgs/game/level0_background.png"
        ).convert_alpha()
        self.background_img = pygame.transform.scale(
            self.background_img,
            (
                int(self.width * 0.6),
                int(self.width * 0.6 * (self.background_img.get_height() / self.background_img.get_width()))
            )
        )
        self.background_img_pos = (
            (self.width - self.background_img.get_width()) / 2,
            (self.height - self.background_img.get_height()) / 2
        )
        
        self.button_rect = pygame.Rect(self.width*0.2, self.height*0.2, self.width*0.6, self.height*0.6)

        # 삼각형 모양(예시)
        p1 = self.adj_pos(
            self.background_img_pos,
            self.background_img.get_width() * 97/200,
            self.background_img.get_height() * 1/8
        )
        p2 = self.adj_pos(
            self.background_img_pos,
            self.background_img.get_width() * 97/200,
            self.background_img.get_height() * (1/8 + 35/100)
        )
        p3 = self.adj_pos(
            self.background_img_pos,
            self.background_img.get_width() * 97/200 + self.background_img.get_height()/6 * 1.9,
            self.background_img.get_height() * (1/8 + 35/200)
        )
        self.triangle_points = [p1, p2, p3]

        self.white_alpha = (255, 255, 255, 180)
        self.highlight_thickness = int(self.height/50)
        self.highlight_length = 240
        self.rotation_speed = 100.0
        self.offset = 0.0

        self.perimeter = self.get_perimeter(self.triangle_points)

    def adj_pos(self, A, x, y):
        return (A[0] + x, A[1] + y)

    def distance(self, a, b):
        return math.hypot(b[0] - a[0], b[1] - a[1])

    def get_perimeter(self, points):
        perim = 0.0
        for i in range(len(points)):
            perim += self.distance(points[i], points[(i + 1) % len(points)])
        return perim

    def get_path_points(self, points, offset, highlight_length):
        path = []
        offset %= self.perimeter
        remaining = highlight_length
        idx = 0
        n = len(points)

        # offset 위치 찾기
        for i in range(n):
            seg_len = self.distance(points[i], points[(i+1) % n])
            if offset <= seg_len:
                idx = i
                break
            else:
                offset -= seg_len

        start_seg_len = self.distance(points[idx], points[(idx+1) % n])
        ratio = offset / start_seg_len
        sx = points[idx][0] + (points[(idx+1) % n][0] - points[idx][0]) * ratio
        sy = points[idx][1] + (points[(idx+1) % n][1] - points[idx][1]) * ratio
        path.append((sx, sy))

        while remaining > 0:
            dist_to_corner = self.distance(path[-1], points[(idx+1) % n])
            if dist_to_corner > remaining:
                final_ratio = remaining / dist_to_corner
                ex = path[-1][0] + (points[(idx+1) % n][0] - path[-1][0]) * final_ratio
                ey = path[-1][1] + (points[(idx+1) % n][1] - path[-1][1]) * final_ratio
                path.append((ex, ey))
                remaining = 0
            else:
                corner = points[(idx+1) % n]
                path.append(corner)
                remaining -= dist_to_corner
                idx = (idx + 1) % n

        return path

    def loop(self, screen):
        clock = pygame.time.Clock()
        self.running = True
        self.hovered = False
        
        while self.running:
            dt_ms = clock.tick(60)
            dt = dt_ms / 1000.0
        
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.hovered:
                        self.running = False
                        return "menu", screen

            if self.button_rect.collidepoint(pygame.mouse.get_pos()):
                self.hovered = True
            else:
                self.hovered = False
            
            self.offset += self.rotation_speed * dt

            # 버튼 색 변경 애니메이션
            if self.hovered:
                for i in range(3):
                    self.button_color[i] += (self.white[i] - self.dark_gray[i])*0.05
                    self.button_color[i] = min(self.white[i], self.button_color[i])
            else:
                for i in range(3):
                    self.button_color[i] -= (self.white[i] - self.dark_gray[i])*0.05
                    self.button_color[i] = max(self.dark_gray[i], self.button_color[i])

            screen.fill(self.gray)
            
            # 배경
            screen.blit(self.background_img, self.background_img_pos)
            
            # 삼각형 하이라이트
            highlight_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            path_points = self.get_path_points(self.triangle_points, self.offset, self.highlight_length)
            if len(path_points) >= 2:
                pygame.draw.lines(highlight_surf, self.white_alpha, False, path_points, self.highlight_thickness)
            radius = self.highlight_thickness // 2
            for pt in path_points:
                pygame.draw.circle(highlight_surf, self.white_alpha, (int(pt[0]), int(pt[1])), radius)
            screen.blit(highlight_surf, (0, 0))
            
            # 버튼 모양(삼각형)
            pygame.draw.polygon(screen, self.button_color, self.triangle_points)

            if self.show_fps:
                blit_fps(screen, clock)

            pygame.display.flip()

        return "menu", screen


##########################################################
# 최상위 MagicCatAcademyScreen
##########################################################
class MagicCatAcademyScreen(ScreenObject):
    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)
        self.show_fps = show_fps

    def loop(self, screen):
        running = True
        # 0: 로딩, 1: 메인 메뉴(혹은 본게임)
        curr_magiccat_screen_idx = 1  # 바로 메인으로 넘어가는 예시

        screen_ids = {
            "loading": 0,
            "menu": 1
        }
        
        while running:
            if curr_magiccat_screen_idx == 0:
                curr_magiccat_screen = MagicCatAcademyLoadingScreen(
                    self.width, self.height, show_fps=self.show_fps
                )
                next_screen, curr_screen_surface = curr_magiccat_screen.loop(screen)
                curr_magiccat_screen_idx = screen_ids[next_screen]
                
                pygame.time.wait(1000)
                fade_out(screen, curr_screen_surface, self.width, self.height, 1000)
            
            elif curr_magiccat_screen_idx == 1:
                # 실제 플레이 화면
                curr_magiccat_screen = MagicCatAcademyMainScreen(
                    self.width, self.height, show_fps=self.show_fps
                )
                next_screen, curr_screen_surface = curr_magiccat_screen.loop(screen)
                
                pygame.time.wait(1000)
                fade_out(screen, curr_screen_surface, self.width, self.height, 1000)
                
                # 메인 화면이 끝났다고 가정 -> 종료
                return 0, screen


##########################################################
# 실행 부분
##########################################################
if __name__ == "__main__":
    pygame.init()
    WIDTH, HEIGHT = 1280, 800
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("MagicCatAcademy")

    # 최상위 스크린 실행
    main_screen = MagicCatAcademyScreen(WIDTH, HEIGHT, show_fps=True)
    print(main_screen.loop(screen))
    
    print("Game End")
