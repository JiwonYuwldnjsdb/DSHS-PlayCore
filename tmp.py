import pygame
import sys
import math
import random

# PlayCoreLibraries에서 ScreenObject, fade_out, blit_fps를 가져온다고 가정
from PlayCoreLibraries import ScreenObject, fade_out, blit_fps

#########################################################
# 1) 전역 스펠 목록 & 간단한 StrokeRecognizer
#########################################################
AVAILABLE_SPELLS = ["horizontal", "vertical", "vspell", "ivspell", "lighting"]

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
            if dx == 0:
                return 0
            return dy / float(dx)

        s1 = slope(p1, p2)
        s2 = slope(p2, p3)
        s3 = slope(p3, p4)

        neg_threshold = -0.3
        pos_threshold = 0.3
        patternA = (s1 < neg_threshold and s2 > pos_threshold and s3 < neg_threshold)
        patternB = (s1 > pos_threshold and s2 < neg_threshold and s3 > pos_threshold)

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
# 2) Ghost: 화면 밖에서 스폰 → 플레이어 향해 이동
#           스펠을 순서대로 맞춰야 사망
#########################################################
class Ghost:
    def __init__(self, x, y, spell_length, width):
        self.x = x
        self.y = y
        
        # 무작위 스펠 목록 (길이=spell_length)
        self.spells = random.choices(AVAILABLE_SPELLS, k=spell_length)
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
        
        size_adj = {
            'moving':1,
            'attacked':113/94,
            'die':95/94
        }
        
        # 실제 로딩 & 스케일
        for anim_id in self.animation_frames:
            new_list = []
            for img_path in self.animation_frames[anim_id]:
                img = pygame.image.load(img_path).convert_alpha()
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
        
        self.shift_pos = (
            self.animation_frames['moving'][0].get_width()//2,
            self.animation_frames['moving'][0].get_height()//2
        )
        
        # 이동 속도
        self.speed = 50
    
    def check_spell(self, spell):
        """플레이어가 사용한 스펠이 내 스펠 목록의 다음 순서와 같으면 진행"""
        if self.alive and self.spell_idx < len(self.spells):
            if spell == self.spells[self.spell_idx]:
                self.spell_idx += 1
                if self.spell_idx == len(self.spells):
                    # 유령 사망
                    self.alive = False
                    self.state = "die"
    
    def update(self, dt, player_x, player_y, frame_cnt):
        """플레이어 방향으로 이동 + 애니메이션 진행"""
        if self.alive:
            dx = player_x - self.x
            dy = player_y - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                nx = dx/dist
                ny = dy/dist
                self.x += nx * self.speed * dt
                self.y += ny * self.speed * dt
            
            self.state = "moving"
        else:
            self.state = "die"
        
        # 애니메이션 프레임 갱신
        delay = self.animation_frame_delay.get(self.state, 6)
        if frame_cnt % delay == 0:
            self.animation_frame_cnt += 1
            if self.state == "die":
                max_idx = len(self.animation_frames['die']) - 1
                if self.animation_frame_cnt > max_idx:
                    self.animation_frame_cnt = max_idx
            else:
                self.animation_frame_cnt %= len(self.animation_frames[self.state])
    
    def draw(self, screen, font):
        """유령 이미지 + 남은 스펠 목록 표시"""
        frames = self.animation_frames[self.state]
        idx = min(self.animation_frame_cnt, len(frames) - 1)
        ghost_img = frames[idx]
        
        adj_x, adj_y = self.animation_adj[self.state]
        draw_x = self.x - self.shift_pos[0] + adj_x
        draw_y = self.y - self.shift_pos[1] + adj_y
        screen.blit(ghost_img, (draw_x, draw_y))
        
        # 남은/전체 스펠 표시
        spell_text = ""
        for i, sp in enumerate(self.spells):
            if i < self.spell_idx:
                spell_text += f"({sp}) "
            else:
                spell_text += f"[{sp}] "
        text_surf = font.render(spell_text, True, (255, 255, 255))
        screen.blit(text_surf, (self.x - text_surf.get_width()//2, self.y - 70))

    def distance_to_player(self, px, py):
        return math.hypot(self.x - px, self.y - py)


#########################################################
# 3) Player: HP 추가
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
        
        size_adj = {
            'waiting': 1,
            'spelling': 117/89,
            'horizontal': 131/89,
            'vertical': 130/89,
            'vspell': 118/89,
            'ivspell': 148/89,
            'lighting': 141/89
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
            if self.state in self.spells and self.animation_frame_cnt == len(self.animation_frames[self.state]):
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
        self.font = pygame.font.SysFont(None, 80)
        self.running = True
    
    def loop(self, screen):
        clock = pygame.time.Clock()
        while self.running:
            dt = clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # 아무 곳이나 클릭 -> 다음 화면(GameScreen)
                    return "game", screen
            
            screen.fill((30, 30, 30))
            text_surf = self.font.render("CLICK TO START", True, (255, 255, 255))
            rect = text_surf.get_rect(center=(self.width//2, self.height//2))
            screen.blit(text_surf, rect)
            
            pygame.display.flip()
        
        return "game", screen  # 혹은 기본값


class GameScreen(ScreenObject):
    """실제 게임 플레이 화면"""
    def __init__(self, width, height):
        super().__init__(width, height)
        
        self.bg_color = (45, 48, 56)
        self.strokeRecognizer = StrokeRecognizer()
        
        self.player = Player(width/2, height/2, width, hp=5)  # 체력 5로 예시
        self.ghosts = []
        # 몇 마리 스폰해볼지
        for _ in range(4):
            ghost = self.spawn_ghost_random_edge(width, height, spell_length=3)
            self.ghosts.append(ghost)
        
        self.is_drawing = False
        self.current_stroke = []
        
        # 체력 깎이는 것은 "1초에 최대 1씩" -> 시간 체크
        self.last_damage_time = 0.0
        
        self.font_hp = pygame.font.SysFont(None, 40)
        self.font_ghost = pygame.font.SysFont(None, 24)
    
    def spawn_ghost_random_edge(self, width, height, spell_length):
        side = random.choice(["top","bottom","left","right"])
        if side == "top":
            x = random.randint(0, width)
            y = 0
        elif side == "bottom":
            x = random.randint(0, width)
            y = height
        elif side == "left":
            x = 0
            y = random.randint(0, height)
        else:
            x = width
            y = random.randint(0, height)
        return Ghost(x, y, spell_length, width)
    
    def draw_stroke(self, surface, stroke, color=(255, 0, 0), width=4):
        if len(stroke) > 1:
            pygame.draw.lines(surface, color, False, stroke, width)
    
    def loop(self, screen):
        clock = pygame.time.Clock()
        running = True
        frame_cnt = 0
        
        while running:
            dt_ms = clock.tick(60)
            dt = dt_ms / 1000.0
            now_sec = pygame.time.get_ticks()/1000.0  # 현재 초 단위
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.is_drawing = True
                        self.current_stroke = [event.pos]
                        self.player.update_state('spelling')
                elif event.type == pygame.MOUSEMOTION:
                    if self.is_drawing:
                        self.current_stroke.append(event.pos)
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
                                    g.check_spell(spell)
                        else:
                            self.player.update_state('waiting')
                        self.current_stroke = []
            
            # -- 유령 업데이트 --
            for g in self.ghosts:
                g.update(dt, self.player.x, self.player.y, frame_cnt)
            
            # -- 플레이어 업데이트(애니메이션만) --
            self.player.update(frame_cnt)
            
            # -- 유령과 플레이어의 거리 체크 -> HP 깎기(1초에 최대 1만큼) --
            #    (예: 거리 50 이하인 유령이 하나라도 있으면 체력 1 깎음)
            if now_sec - self.last_damage_time >= 1.0:
                for g in self.ghosts:
                    if g.alive:
                        dist = g.distance_to_player(self.player.x, self.player.y)
                        if dist < 50:  # 거리 50 이하 -> 충돌로 간주
                            self.player.hp -= 1
                            self.last_damage_time = now_sec
                            break  # 1초에 최대 1만 깎이므로 break
            
            # -- HP가 0 이하 -> GameOverScreen으로 --
            if self.player.hp <= 0:
                return "gameover", screen
            
            # ------------------- 그리기 -------------------
            screen.fill(self.bg_color)
            
            # 유령들
            for g in self.ghosts:
                g.draw(screen, self.font_ghost)
            
            # 플레이어
            self.player.draw(screen)
            
            # 현재 드로잉 스펠
            self.draw_stroke(screen, self.current_stroke)
            
            # HP 표시
            hp_text = self.font_hp.render(f"HP: {self.player.hp}", True, (255,255,255))
            screen.blit(hp_text, (20, 20))
            
            pygame.display.flip()
            frame_cnt += 1
        
        return "gameover", screen  # 기본 반환


class GameOverScreen(ScreenObject):
    """'Click to Restart' 표시. 클릭하면 TitleScreen으로 이동"""
    def __init__(self, width, height):
        super().__init__(width, height)
        self.font = pygame.font.SysFont(None, 80)
        self.running = True
    
    def loop(self, screen):
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
            
            screen.fill((50, 0, 0))
            text_surf = self.font.render("CLICK TO RESTART", True, (255,255,255))
            rect = text_surf.get_rect(center=(self.width//2, self.height//2))
            screen.blit(text_surf, rect)
            
            pygame.display.flip()
        
        return "title", screen


#########################################################
# 5) 전체 흐름 관리 (MagicCatAcademyMainScreen)
#    - title → game → gameover → title ...
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
            
            elif current_state == "game":
                next_state, _ = game_screen.loop(screen)
                current_state = next_state
            
            elif current_state == "gameover":
                next_state, _ = gameover_screen.loop(screen)
                current_state = next_state
            
            # 필요하다면 fade_out 등 화면 전환 효과도 추가할 수 있음
            
            # 만약 "exit" 같은 상태를 만들어 게임을 완전히 종료하고 싶다면 해당 로직 추가
            if current_state == "exit":
                running = False
        
        return 0, screen


#########################################################
# 실제 실행부
#########################################################
if __name__ == "__main__":
    pygame.init()
    WIDTH, HEIGHT = 1280, 800
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("MagicCatAcademy")

    main_screen = MagicCatAcademyMainScreen(WIDTH, HEIGHT, show_fps=False)
    main_screen.loop(screen)
    print("Exiting game.")
