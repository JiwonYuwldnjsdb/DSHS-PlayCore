import pygame
import random
import sys
import math
from enum import Enum, auto
from collections import deque
from typing import Dict, Tuple

from localLibraries.PlayCoreLibraries import ScreenObject, blit_fps  # 그대로 사용

pygame.init()

# ---------------------------------------------------------------------------
# Game states
# ---------------------------------------------------------------------------
class GameState(Enum):
    MAIN_MENU = auto()
    TRANSITION = auto()
    ENLARGED = auto()

# ----------------------------- Helpers / Easing ----------------------------

def clamp01(x):
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

def ease_out_cubic(t):
    t = clamp01(t); return 1 - (1 - t) ** 3

def ease_in_out_quad(t):
    t = clamp01(t); return 2*t*t if t < 0.5 else 1 - (-2*t + 2) ** 2 / 2

def ease_out_back(t, s=1.70158):
    t = clamp01(t); return 1 + (s + 1)*(t-1)**3 + s*(t-1)**2

def lerp(a, b, t):
    return a + (b - a) * t

def lerp_rect(r1, r2, t):
    x = lerp(r1.x, r2.x, t)
    y = lerp(r1.y, r2.y, t)
    w = lerp(r1.width, r2.width, t)
    h = lerp(r1.height, r2.height, t)
    return pygame.Rect(int(x), int(y), int(w), int(h))

# ----------------------------- Background Squares --------------------------
class Square:
    def __init__(self, x, size, speed, angle_speed, screen_height):
        self.size = size
        self.x = x
        self.y = screen_height
        self.speed = speed
        self.angle_speed = angle_speed
        self.angle = 0
        self.alpha = 15.0
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((255, 255, 255, int(self.alpha)))
        self.surface = surf.convert_alpha()

    def update(self, dt):
        self.y -= self.speed * dt
        self.angle = (self.angle + self.angle_speed * dt) % 360
        self.alpha = max(0.0, self.alpha - 1.2 * dt)
        self.surface.fill((255, 255, 255, int(self.alpha)))

    def draw(self, screen):
        rotated_surface = pygame.transform.rotate(self.surface, self.angle)
        rect = rotated_surface.get_rect(center=(self.x, self.y))
        screen.blit(rotated_surface, rect.topleft)

# ----------------------------- Cards & Caches ------------------------------
class Card:
    def __init__(self, title, color):
        self.title = title
        self.color = color

class ShadowCache:
    def __init__(self):
        self.cache: Dict[Tuple[int,int,int], pygame.Surface] = {}
    def get(self, w, h, radius):
        key = (w, h, radius)
        img = self.cache.get(key)
        if img is None:
            s = pygame.Surface((w+18, h+18), pygame.SRCALPHA)
            pygame.draw.rect(s, (0,0,0,90), s.get_rect(), border_radius=radius+4)
            img = s.convert_alpha()
            self.cache[key] = img
        return img

class CardBodyCache:
    def __init__(self):
        self.cache: Dict[Tuple[int,int,int,Tuple[int,int,int],int], pygame.Surface] = {}
    def get(self, w, h, radius, color, alpha=230):
        key = (w, h, radius, color, alpha)
        img = self.cache.get(key)
        if img is None:
            body = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(body, (*color, alpha), body.get_rect(), border_radius=radius)
            pygame.draw.rect(body, (255, 255, 255, int(alpha*0.14)), body.get_rect(), width=2, border_radius=radius)
            img = body.convert_alpha()
            self.cache[key] = img
        return img

class GradOverlayCache:
    def __init__(self):
        self.cache: Dict[Tuple[int,int,int], pygame.Surface] = {}
    def get(self, w, h, radius):
        key = (w, h, radius)
        g = self.cache.get(key)
        if g is None:
            grad = pygame.Surface((w, h), pygame.SRCALPHA)
            for y in range(h):
                a = int(70 * (1 - y / max(1, h)))
                pygame.draw.line(grad, (255, 255, 255, a), (0, y), (w, y))
            mask = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255,255,255,255), mask.get_rect(), border_radius=radius)
            grad.blit(mask, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
            g = grad.convert_alpha()
            self.cache[key] = g
        return g

# ---------------------------------------------------------------------------
# Particles
# ---------------------------------------------------------------------------
class Spark:
    """Open transition burst (outwards)"""
    def __init__(self, pos, color):
        ang = random.uniform(0, 6.28318)
        speed = random.uniform(240, 520)
        v = pygame.math.Vector2(speed, 0).rotate_rad(ang)
        self.vx, self.vy = v.x, v.y
        self.x, self.y = pos
        self.life = random.uniform(0.25, 0.55)
        self.age = 0.0
        self.size = random.randint(2, 4)
        self.color = color
    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 300 * dt
    def alive(self): return self.age < self.life
    def draw(self, screen):
        alpha = int(255 * (1 - (self.age / self.life)))
        col = (*self.color, alpha)
        pygame.draw.circle(screen, col, (int(self.x), int(self.y)), self.size)

class ImplodeSpark:
    """Close transition: from edges imploding toward the card"""
    def __init__(self, start_pos, target_pos, color=(255,255,255)):
        self.x, self.y = start_pos
        tx, ty = target_pos
        vec = pygame.math.Vector2(tx - self.x, ty - self.y)
        if vec.length() == 0:
            vec = pygame.math.Vector2(1, 0)
        dirv = vec.normalize()
        speed = random.uniform(260, 540)
        self.vx, self.vy = dirv.x * speed, dirv.y * speed
        self.life = random.uniform(0.28, 0.5)
        self.age = 0.0
        self.size = random.randint(2, 3)
        self.color = color
    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= (0.90 ** (dt * 60))
        self.vy *= (0.90 ** (dt * 60))
    def alive(self): return self.age < self.life
    def draw(self, screen):
        a = int(255 * (1 - (self.age / self.life)))
        pygame.draw.circle(screen, (*self.color, a), (int(self.x), int(self.y)), self.size)

class RingPulse:
    def __init__(self, center, max_radius, dur=0.35):
        self.center = (int(center[0]), int(center[1]))
        self.max_r = int(max_radius)
        self.dur = dur
        self.t = 0.0
    def update(self, dt): self.t += dt
    def alive(self): return self.t < self.dur
    def draw(self, screen):
        p = clamp01(self.t / self.dur)
        r = int(self.max_r * ease_out_cubic(p))
        a = int(180 * (1 - p))
        if r > 0 and a > 0:
            pygame.draw.circle(screen, (255, 255, 255, a), self.center, r, width=3)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
class PlayCoreMenu(ScreenObject):
    DARK_BLUE   = (10, 10, 40)
    DARK_PURPLE = (40, 10, 70)

    # Inertia tuning
    INERTIA_DECEL = 2000.0   # px/s^2 (감속 더 빠르게)
    INERTIA_START_V = 300.0  # px/s 이상일 때만 관성 시작
    INERTIA_CAP = 1400.0     # 초기 관성 속도 최대치
    SNAP_NEAR = 18           # px 이내면 스냅
    CENTER_OPEN_EPS = 0.5    # 클릭 후 '중앙 도달' 판정 허용 오차(px)

    # Vertical positions (tweakable)
    CAROUSEL_VPOS = 0.50     # 0.50 = 정확히 세로 중앙
    ENLARGED_VPOS = 0.50     # 확대 카드 중앙 위치

    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)
        self.show_fps = show_fps

        font_size = int(self.height * 0.05)
        # body font (smaller)
        
        try:
            self.font = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", font_size)
        except:
            self.font = pygame.font.SysFont("arial", font_size)
        
        try:
            self.body_font = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", int(self.height * 0.028))
        except:
            self.body_font = pygame.font.SysFont("arial", int(self.height * 0.028))

        # game descriptions (EN only, plain)
        self.game_desc = {
            "Lynez": (
                "How to Play:\n"
                "Click to connect lines from the last point.\nThe ball bounces off lines. "
                "Avoid lasers. Touching a wall or falling off the screen is game over.\n\n"
                "Original: DaFluffyPotato\n"
                "Remastered: Jiwon Yu"
            ),
            "Magic Cat Academy": (
                "How to Play:\n"
                "Draw the exact rune shown above each ghost with your mouse or finger. "
                "Each correct stroke damages the ghost. Survive as long as possible.\n\n"
                "Original: Google Doodles\n"
                "Remastered: Jiwon Yu"
            ),
            "Airship": (
                "How to Play:\n"
                "Guide the airship with your finger.\nAvoid obstacles.\n\n"
                "Original: Blob8108\n"
                "Remastered: Yuseung Jang"
            ),
            # Optional: Home에 아무 내용 없을 때 기본 안내
            "Home": (
                "Select a card to read its description.\n"
                "Click outside to go back."
            ),
        }

        # State
        self.current_state = GameState.MAIN_MENU

        # Background floaters
        self.squares = []
        self.spawn_rate = 30
        self.frame_count = 0

        # Carousel
        self.setup_cards()

        # Transition
        self.transition_time = 0.0
        self.transition_duration = 0.9
        self.transition_mode = "open"  # or "close"
        self.selected_index = None
        self.transition_start_rect = None
        self.transition_end_rect = None

        # Effects
        self.sparks = []
        self.implode_sparks = []

        # Caches
        self._shadow_cache = ShadowCache()
        self._card_cache = CardBodyCache()
        self._grad_cache = GradOverlayCache()
        self._title_cache = [self.font.render(c.title, True, (255,255,255)) for c in self.cards]

        # Vignette & background gradient (pre-render)
        self.vignette = self._build_vignette()
        self._bg = pygame.Surface((self.width, self.height)).convert()
        self._gradient_fill(self._bg, self.DARK_PURPLE, self.DARK_BLUE)

        # Inertia samples
        self._vel_samples = deque(maxlen=8)
        self._last_drag_dir = 0

        # Back flag (첫 번째 카드 클릭 시 되돌아가기)
        self.go_back_requested = False

        # Long-press (Lynez 스타일 씬 탈출)
        self.longpress_down = False
        self.longpress_frames = 0
        self.LONGPRESS_THRESHOLD = 240  # 60fps 기준 약 4초

    def _wrap_text(self, text, font, max_width):
        """Returns list of wrapped lines for the given width (keeps manual newlines)."""
        lines = []
        for raw_line in text.split("\n"):
            words = raw_line.split(" ")
            if not words:
                lines.append("")
                continue
            cur = words[0]
            for w in words[1:]:
                test = cur + " " + w
                if font.size(test)[0] <= max_width:
                    cur = test
                else:
                    lines.append(cur)
                    cur = w
            lines.append(cur)
        return lines

    def _draw_text_in_rect(self, screen, text, rect, font, color=(245, 245, 250)):
        """Draw wrapped text inside rect; stops at bottom edge to keep inside the card."""
        line_h = int(font.get_linesize() * 1.1)
        y = rect.top
        wrapped = self._wrap_text(text, font, rect.width)
        for ln in wrapped:
            if y + line_h > rect.bottom:
                break  # prevent overflow
            surf = font.render(ln, True, color)
            screen.blit(surf, (rect.left, y))
            y += line_h

    # ---------------------------- Setup -------------------------------------
    def setup_cards(self):
        titles = ["Home", "Lynez", "Magic Cat Academy", "Airship"]
        base_colors = [
            (35, 90, 160),
            (190, 120, 60),
            (60, 150, 110),
            (120, 80, 180),
            (180, 70, 120),
            (80, 140, 200),
            (140, 140, 70),
        ]
        self.cards = [Card(t, base_colors[i % len(base_colors)]) for i, t in enumerate(titles)]

        # Tall cards
        self.card_h = int(self.height * 0.70)
        self.card_w = int(self.height * 0.42)
        self.slot_gap = int(self.width * 0.04)
        self.slot = self.card_w + self.slot_gap

        # Scroll state
        self.scroll = 0.0
        self.velocity = 0.0   # px/s
        self.dragging = False
        self.mouse_down = False
        self.click_start_time = 0.0
        self.total_drag_dist = 0.0
        self.target_index = None
        self.pending_open_index = None

        self.min_scroll = 0.0
        self.max_scroll = max(0.0, (len(self.cards) - 1) * self.slot)

        self.card_screen_rects = [pygame.Rect(0, 0, 0, 0) for _ in self.cards]

    # ------------------------- Background / Vignette ------------------------
    def _gradient_fill(self, screen, color_top, color_bottom):
        w, h = screen.get_size()
        for y in range(h):
            ratio = y / (h - 1) if h > 1 else 0
            r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
            g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
            b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
            pygame.draw.line(screen, (r, g, b), (0, y), (w, y))

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

    def _build_vignette(self):
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        cx, cy = self.width/2, self.height/2
        maxd = (cx**2 + cy**2) ** 0.5
        for y in range(self.height):
            for x in range(self.width):
                d = ((x-cx)**2 + (y-cy)**2) ** 0.5
                t = clamp01((d - maxd*0.55) / (maxd*0.45))
                a = int(160 * t)
                surf.set_at((x, y), (0, 0, 0, a))
        return surf.convert_alpha()

    # ----------------------------- Card visuals -----------------------------
    def _apply_round_mask(self, surf, radius):
        mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    def _shine(self, target_surf, t):
        if t <= 0.0 or t >= 1.0: return
        w, h = target_surf.get_size()
        band_w = int(max(12, w * 0.12))
        grad = pygame.Surface((band_w, h*2), pygame.SRCALPHA)
        for x in range(band_w):
            a = int(140 * (1 - abs((x - band_w/2) / (band_w/2))))
            pygame.draw.line(grad, (255, 255, 255, a), (x, 0), (x, h*2))
        grad = pygame.transform.rotate(grad, -25)
        pos_x = int(lerp(-w, w*1.2, t))
        rect = grad.get_rect(center=(pos_x, h//2))
        target_surf.blit(grad, rect)

    def _diagonal_pattern(self, size, phase):
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        gap = max(12, w//18)
        offset = int((phase % 1.0) * gap)
        for x in range(-h, w + h, gap):
            pygame.draw.line(surf, (255, 255, 255, 16), (x + offset, 0), (x - h + offset, h), 2)
        return surf.convert_alpha()

    def draw_card(self, screen, rect, color, title, alpha=220, hovered=False):
        radius = 28
        # shadow (cache)
        screen.blit(self._shadow_cache.get(rect.w, rect.h, radius), (rect.x-9, rect.y-6))
        # body (cache)
        body = self._card_cache.get(rect.w, rect.h, radius, color, alpha=alpha)
        screen.blit(body, rect.topleft)
        # title (cache)
        title_surf = self.font.render(title, True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(rect.centerx, rect.bottom - int(rect.h*0.12)))
        screen.blit(title_surf, title_rect)
        if hovered:
            pygame.draw.rect(screen, (255, 255, 255), rect, width=3, border_radius=24)

    # ----------------------------- Carousel ---------------------------------
    def draw_carousel(self, screen, mouse_pos):
        center_x = self.width // 2
        center_y = int(self.height * self.CAROUSEL_VPOS)

        order = []
        for i in range(len(self.cards)):
            cx = (i * self.slot - self.scroll) + center_x
            dist = abs(cx - center_x)
            t = max(0.0, 1.0 - dist / (self.slot))
            scale = 0.9 + 0.2 * t
            order.append((scale, i))
        order.sort()

        hovered_index = None
        for _, i in order:
            card = self.cards[i]
            cx = (i * self.slot - self.scroll) + center_x
            dist = abs(cx - center_x)
            t = max(0.0, 1.0 - dist / (self.slot))
            scale = 0.9 + 0.2 * t
            alpha = int(150 + 105 * t)
            w = int(self.card_w * scale)
            h = int(self.card_h * scale)
            rect = pygame.Rect(0, 0, w, h)
            rect.center = (int(cx), center_y)
            self.card_screen_rects[i] = rect

            hovered = rect.collidepoint(mouse_pos)
            if t < 0.65:
                trail = self._card_cache.get(w, h, 28, card.color, alpha=int(alpha*0.35))
                screen.blit(trail, (rect.x + 6, rect.y + 2))
            self.draw_card(screen, rect, card.color, card.title, alpha=alpha, hovered=hovered)
            if hovered: hovered_index = i

        return hovered_index

    # ----------------------------- Transitions ------------------------------
    def _enlarged_target_rect(self):
        final_h = int(self.height * 0.86)
        final_w = int(self.height * 0.52)
        rect = pygame.Rect(0, 0, final_w, final_h)
        rect.center = (self.width // 2, int(self.height * self.ENLARGED_VPOS))
        return rect

    def start_transition(self, index, mode="open"):
        self.current_state = GameState.TRANSITION
        self.transition_mode = mode
        self.selected_index = index
        self.transition_time = 0.0

        if mode == "open":
            self.transition_start_rect = self.card_screen_rects[index].copy()
            self.transition_end_rect = self._enlarged_target_rect()
            r = self.transition_start_rect
            cx, cy = r.center
            burst_color = tuple(min(255, c+40) for c in self.cards[index].color)
            for _ in range(48):
                self.sparks.append(Spark((cx + random.uniform(-r.w*0.25, r.w*0.25),
                                          cy + random.uniform(-r.h*0.25, r.h*0.25)), burst_color))
        else:
            self.transition_start_rect = self._enlarged_target_rect()
            self.transition_end_rect = self.card_screen_rects[index].copy()
            self.implode_sparks.clear()
            end_c = self.transition_end_rect.center
            edge_points = []
            M, N = self.width, self.height
            for _ in range(18):
                edge = random.choice(("top","bottom","left","right"))
                if edge == "top":
                    edge_points.append((random.uniform(-40, M+40), -30))
                elif edge == "bottom":
                    edge_points.append((random.uniform(-40, M+40), N+30))
                elif edge == "left":
                    edge_points.append((-30, random.uniform(-40, N+40)))
                else:
                    edge_points.append((M+30, random.uniform(-40, N+40)))
            col = tuple(min(255, c+30) for c in self.cards[index].color)
            for p in edge_points:
                self.implode_sparks.append(ImplodeSpark(p, end_c, color=col))

    def _draw_others_fade(self, screen, t):
        fade = 1.0 - clamp01(t * 1.2)
        for i, card in enumerate(self.cards):
            if i == self.selected_index: continue
            rect = self.card_screen_rects[i]
            if rect.w <= 0 or rect.h <= 0: continue
            dir_sign = -1 if rect.centerx < self.width//2 else 1
            offset = int(lerp(0, dir_sign * self.width*0.25, ease_out_cubic(1-fade)))
            trail = self._card_cache.get(rect.w, rect.h, 24, card.color, alpha=int(160*fade))
            screen.blit(trail, (rect.x + offset + 10, rect.y + 4))
            body = self._card_cache.get(rect.w, rect.h, 24, card.color, alpha=int(220*fade))
            screen.blit(body, (rect.x + offset, rect.y))

    def update_transition(self, dt, screen):
        self.transition_time += dt
        t = clamp01(self.transition_time / self.transition_duration)

        screen.blit(self._bg, (0, 0))
        self.update_squares(dt)
        self.draw_squares(screen)

        if self.transition_mode == "open":
            t_pop = clamp01(t / 0.22)
            t_morph = clamp01((t - 0.22) / 0.78)
            self._draw_others_fade(screen, t)

            if t < 0.22:
                start = self.transition_start_rect
                scale = 1.0 + 0.08 * ease_out_back(t_pop)
                rot = lerp(-6.0, 4.0, ease_out_cubic(t_pop))
                w = int(start.w * scale)
                h = int(start.h * scale)
                rect = pygame.Rect(0, 0, w, h)
                rect.center = start.center
                body = self._card_cache.get(w, h, 24, self.cards[self.selected_index].color, alpha=240)
                tmp = body.copy()
                self._shine(tmp, t_pop*0.7)
                tmp = pygame.transform.rotate(tmp, rot)
                screen.blit(tmp, tmp.get_rect(center=rect.center))
            else:
                start = self.transition_start_rect
                end = self.transition_end_rect
                et = ease_in_out_quad(t_morph)
                now_rect = lerp_rect(start, end, et)
                radius = max(12, int(24 * (1 - et*0.85)))
                body = self._card_cache.get(now_rect.w, now_rect.h, radius, self.cards[self.selected_index].color, alpha=240)
                tmp = body.copy()
                self._shine(tmp, clamp01((t_morph - 0.15) / 0.6))
                phase = (pygame.time.get_ticks()/1000.0) * 0.25
                tmp.blit(self._diagonal_pattern((now_rect.w, now_rect.h), phase), (0, 0))
                screen.blit(tmp, now_rect.topleft)
        else:
            self.draw_carousel(screen, (-1, -1))
            start = self.transition_start_rect
            end = self.transition_end_rect
            t_lift = clamp01(t / 0.18)
            t_morph = clamp01((t - 0.18) / 0.82)
            et = ease_in_out_quad(t_morph)
            now_rect = lerp_rect(start, end, et)
            lift = int(lerp(-self.height * 0.035, 0, et))
            now_rect.centery += lift
            radius = max(12, int(24 * (1 - (et * 0.85))))
            base = self._card_cache.get(now_rect.w, now_rect.h, radius, self.cards[self.selected_index].color, alpha=240)
            tmp = base.copy()
            self._shine(tmp, 1.0 - clamp01((t_morph - 0.05) / 0.55))
            phase = (pygame.time.get_ticks()/1000.0) * 0.16
            self._apply_round_mask(tmp, radius)
            tmp.blit(self._diagonal_pattern((now_rect.w, now_rect.h), phase), (0, 0))
            for g in range(1, 4):
                gt = clamp01(et - g * 0.06)
                if gt <= 0: continue
                gr = lerp_rect(start, end, gt)
                ghost = self._card_cache.get(gr.w, gr.h, max(12, int(24 * (1 - (gt * 0.85)))), self.cards[self.selected_index].color, alpha=int(80 * (1 - g/4)))
                screen.blit(ghost, (gr.x + (4-g)*4, gr.y + (4-g)*2))
            screen.blit(tmp, now_rect.topleft)
            for sp in self.implode_sparks[:]:
                sp.update(dt)
                if sp.alive(): sp.draw(screen)
                else: self.implode_sparks.remove(sp)
            vig_alpha = int(160 * (1.0 - t))
            if vig_alpha > 0:
                v = self.vignette.copy(); v.set_alpha(vig_alpha); screen.blit(v, (0, 0))

        for sp in self.sparks[:]:
            sp.update(dt)
            if not sp.alive(): self.sparks.remove(sp)
            else: sp.draw(screen)

        if t >= 1.0:
            self.current_state = GameState.ENLARGED if self.transition_mode == "open" else GameState.MAIN_MENU
            if self.current_state == GameState.MAIN_MENU:
                self.sparks.clear(); self.implode_sparks.clear()

    # --------------------------- Enlarged mode -------------------------------
    def _pulse_border(self, screen, rect, t, radius=28):
        glow = int(80 + 60 * (0.5 + 0.5 * math.sin(t*2.2)))
        stroke = pygame.Surface((rect.w+20, rect.h+20), pygame.SRCALPHA)
        pygame.draw.rect(stroke, (255, 255, 255, glow), stroke.get_rect(), width=4, border_radius=radius)
        screen.blit(stroke, (rect.x-10, rect.y-10))

    def draw_enlarged(self, screen):
        # dim background
        dim = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 120))
        screen.blit(dim, (0, 0))

        rect = self._enlarged_target_rect()
        card = self.cards[self.selected_index]

        # subtle breathing
        t = pygame.time.get_ticks() / 1000.0
        breathe = 1.0 + 0.012 * math.sin(t * 2.2)
        bw, bh = int(rect.w * breathe), int(rect.h * breathe)
        brect = pygame.Rect(0, 0, bw, bh); brect.center = rect.center

        # border pulse
        glow = int(80 + 60 * (0.5 + 0.5 * math.sin(t*2.2)))
        stroke = pygame.Surface((brect.w+20, brect.h+20), pygame.SRCALPHA)
        pygame.draw.rect(stroke, (255, 255, 255, glow), stroke.get_rect(), width=4, border_radius=28)
        screen.blit(stroke, (brect.x-10, brect.y-10))

        # card body
        body = self._card_cache.get(bw, bh, 28, card.color, alpha=240).copy()
        # light pattern & grad (은은하게만)
        diag = self._diagonal_pattern((bw, bh), (t * 0.18) % 1.0)
        body.blit(diag, (0, 0))
        body.blit(self._grad_cache.get(bw, bh, 28), (0, 0))
        self._shine(body, (math.sin(t*1.0) * 0.5 + 0.5))
        self._apply_round_mask(body, radius=28)
        screen.blit(body, brect.topleft)

        # title
        title_surf = self.font.render(card.title, True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(brect.centerx, brect.top + int(bh*0.10)))
        screen.blit(title_surf, title_rect)

        # content area (카드 밖으로 나가지 않도록 패딩)
        pad_x = int(bw * 0.08)
        pad_top = int(bh * 0.15)
        content_rect = pygame.Rect(
            brect.left + pad_x,
            title_rect.bottom + int(bh * 0.04),
            bw - pad_x*2,
            brect.bottom - (title_rect.bottom + int(bh * 0.04)) - pad_top
        )

        # description text (plain EN)
        text = self.game_desc.get(card.title, "No description.")
        self._draw_text_in_rect(screen, text, content_rect, self.body_font, (245, 245, 250))

        # small hint at bottom inside the card (간단하게)
        hint = "Click outside or press Esc to close"
        hint_surf = self.body_font.render(hint, True, (230, 230, 235))
        hint_rect = hint_surf.get_rect()
        hint_rect.midbottom = (brect.centerx, brect.bottom - int(bh * 0.04))
        # 카드 밖으로 나가지 않도록 체크
        if hint_rect.left < brect.left + 8:
            hint_rect.left = brect.left + 8
        if hint_rect.right > brect.right - 8:
            hint_rect.right = brect.right - 8
        screen.blit(hint_surf, hint_rect)

    # ------------------------------- Scrollbar ------------------------------
    def _draw_scrollbar(self, screen):
        if self.max_scroll <= 1: return
        track_w = int(self.width * 0.46)
        track_h = 6
        track_x = (self.width - track_w) // 2
        track_y = int(self.height * 0.945)
        bar = pygame.Surface((track_w, track_h), pygame.SRCALPHA)
        TRACK_RGBA = (255, 255, 255, 24)
        KNOB_RGBA  = (220, 230, 240, 110)
        pygame.draw.rect(bar, TRACK_RGBA, (0, 0, track_w, track_h), border_radius=track_h//2)
        # viewport/contents estimation
        content_w = self.max_scroll + self.slot
        view_w = self.slot
        knob_w = max(40, int(track_w * (view_w / max(content_w, 1))))
        p = 0.0 if self.max_scroll <= 0 else (self.scroll / self.max_scroll)
        p = max(0.0, min(1.0, p))
        knob_x = int((track_w - knob_w) * p)
        pygame.draw.rect(bar, KNOB_RGBA, (knob_x, 0, knob_w, track_h), border_radius=track_h//2)
        screen.blit(bar, (track_x, track_y))

    # ------------------------------- Input ----------------------------------
    def handle_input(self, event, dt):
        # ----- 공통: 롱프레스 상태 처리 -----
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.longpress_down = True
            self.longpress_frames = 0

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # 롱프레스가 이미 발동된 상태라면, 클릭/드래그 로직은 막고 리셋만
            if self.longpress_frames >= self.LONGPRESS_THRESHOLD:
                self.longpress_down = False
                self.longpress_frames = 0
                return
            self.longpress_down = False
            self.longpress_frames = 0

        # ----- 상태별 입력 처리 -----
        if self.current_state == GameState.MAIN_MENU:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mouse_down = True
                self.dragging = True
                self.click_start_time = pygame.time.get_ticks() / 1000.0
                self.total_drag_dist = 0.0
                self._vel_samples.clear()
                self._vel_samples.append((self.click_start_time, pygame.mouse.get_pos()[0]))
                self.velocity = 0.0
                self.pending_open_index = None

            elif event.type == pygame.MOUSEMOTION and self.dragging and self.mouse_down:
                dx, _ = event.rel
                self.scroll -= dx
                self.total_drag_dist += abs(dx)
                self._vel_samples.append((pygame.time.get_ticks()/1000.0, pygame.mouse.get_pos()[0]))

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.mouse_down = False
                was_drag = self.total_drag_dist > 6
                click_time = pygame.time.get_ticks() / 1000.0 - self.click_start_time
                self.dragging = False

                if not was_drag and click_time < 0.25:
                    mx, my = pygame.mouse.get_pos()
                    clicked = None
                    for i, r in enumerate(self.card_screen_rects):
                        if r.collidepoint(mx, my):
                            clicked = i; break
                    if clicked is None:
                        clicked = round(self.scroll / self.slot)

                    # 첫 번째 카드 → 되돌아가기 즉시 요청
                    if clicked == 0:
                        self.go_back_requested = True
                        return

                    # 클릭한 카드가 중앙에 정확히 오면 바로 오픈, 아니면 먼저 중앙으로 이동
                    center_off = abs(self.scroll - clicked * self.slot)
                    if center_off > self.CENTER_OPEN_EPS:
                        self.target_index = clicked
                        self.pending_open_index = clicked
                        self.velocity = 0.0  # 중앙 이동 즉시 시작 (딜레이 제거)
                    else:
                        self.start_transition(clicked, mode="open")
                else:
                    # compute release velocity (px/s)
                    v = 0.0
                    if len(self._vel_samples) >= 2:
                        t0, x0 = self._vel_samples[0]
                        t1, x1 = self._vel_samples[-1]
                        dtv = max(1e-4, t1 - t0)
                        v_mouse = (x1 - x0) / dtv
                        v = -v_mouse  # scroll 좌표계 반전
                    self._last_drag_dir = 1 if v > 0 else (-1 if v < 0 else 0)
                    if abs(v) > self.INERTIA_START_V:
                        self.velocity = max(-self.INERTIA_CAP, min(self.INERTIA_CAP, v))
                        self.target_index = None
                    else:
                        # 느린 드래그는 근처에서만 스냅
                        nearest = round(self.scroll / self.slot)
                        target = nearest * self.slot
                        if abs(self.scroll - target) <= self.SNAP_NEAR:
                            self.target_index = nearest
                        else:
                            self.target_index = None

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.target_index = min(len(self.cards) - 1, round(self.scroll / self.slot) + 1)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.target_index = max(0, round(self.scroll / self.slot) - 1)

        elif self.current_state == GameState.ENLARGED:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.start_transition(self.selected_index, mode="close")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self._enlarged_target_rect().collidepoint(pygame.mouse.get_pos()):
                    self.start_transition(self.selected_index, mode="close")

    # -------------------------------- Loop ----------------------------------
    def loop(self, screen):
        clock = pygame.time.Clock()
        running = True

        while running:
            dt_ms = clock.tick(60)
            dt = dt_ms / 1000.0

            # ----- 롱프레스 카운트 & 씬 탈출 트리거 -----
            if self.longpress_down:
                self.longpress_frames += 1
                if (self.current_state == GameState.MAIN_MENU and
                    self.longpress_frames >= self.LONGPRESS_THRESHOLD):
                    self.go_back_requested = True

            self.frame_count += 1
            if self.frame_count % self.spawn_rate == 0:
                self.spawn_squares()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                self.handle_input(event, dt)

            # 되돌아가기 즉시 반환
            if self.go_back_requested:
                return (0, screen)

            # inertial scroll + snap (main only)
            if self.current_state == GameState.MAIN_MENU:
                prev_scroll = self.scroll
                if not self.dragging:
                    # inertia motion
                    if abs(self.velocity) > 0:
                        self.scroll += self.velocity * dt
                        # constant decel (빠르게 죽음, 역방향 튐 방지)
                        if self.velocity > 0:
                            self.velocity = max(0.0, self.velocity - self.INERTIA_DECEL * dt)
                        else:
                            self.velocity = min(0.0, self.velocity + self.INERTIA_DECEL * dt)
                    # snap to target if set
                    if self.target_index is not None:
                        target = self.target_index * self.slot
                        speed = 18.0 if self.pending_open_index is not None else 10.0
                        self.scroll = lerp(self.scroll, target, min(speed * dt, 1.0))
                        if abs(self.scroll - target) <= self.CENTER_OPEN_EPS:
                            # 즉시 중앙 정렬 + 바로 오픈 (딜레이 제거)
                            self.scroll = target
                            idx_to_open = self.pending_open_index
                            self.target_index = None
                            if idx_to_open is not None:
                                self.start_transition(idx_to_open, mode="open")
                                self.pending_open_index = None
                    elif abs(self.velocity) < 1.0:
                        # no inertia → gentle near-snap only when close
                        nearest = round(self.scroll / self.slot)
                        target = nearest * self.slot
                        if abs(self.scroll - target) <= self.SNAP_NEAR:
                            self.scroll = lerp(self.scroll, target, min(8.0 * dt, 1.0))
                else:
                    # update velocity sample derivative continuously if needed
                    if dt > 0:
                        self.velocity = (self.scroll - prev_scroll) / dt

                # bounds with easing & stop inertia at edges
                if self.scroll < self.min_scroll:
                    self.scroll = lerp(self.scroll, self.min_scroll, min(12.0 * dt, 1.0))
                    if not self.dragging: self.velocity = 0.0
                if self.scroll > self.max_scroll:
                    self.scroll = lerp(self.scroll, self.max_scroll, min(12.0 * dt, 1.0))
                    if not self.dragging: self.velocity = 0.0

            # background
            screen.blit(self._bg, (0, 0))
            self.update_squares(dt)
            self.draw_squares(screen)

            # render by state
            if self.current_state == GameState.MAIN_MENU:
                self.draw_carousel(screen, pygame.mouse.get_pos())
                self._draw_scrollbar(screen)
            elif self.current_state == GameState.TRANSITION:
                self.update_transition(dt, screen)
            elif self.current_state == GameState.ENLARGED:
                self.draw_carousel(screen, (-1, -1))
                self.draw_enlarged(screen)

            # 롱프레스 진행 원 (Lynez 스타일)
            if self.longpress_down and self.longpress_frames >= 60:
                mx, my = pygame.mouse.get_pos()
                radius = self.height / 60
                rect = (mx - radius, my - radius, radius * 2, radius * 2)
                start_angle = math.radians(0)
                end_angle = math.radians(min(self.longpress_frames * 2 - 120, 360))
                pygame.draw.arc(
                    screen,
                    (255, 255, 255),
                    rect,
                    start_angle,
                    end_angle,
                    max(int(self.height / 200), 2)
                )

            if self.show_fps:
                blit_fps(screen, clock)
            pygame.display.flip()

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    WIDTH, HEIGHT = 1280, 720
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.DOUBLEBUF, vsync=1)
    except TypeError:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("PlayCoreMenu — Card Enlarged Mode (Optimized)")

    menu_screen = PlayCoreMenu(WIDTH, HEIGHT, show_fps=True)
    result = menu_screen.loop(screen)
    # result가 ("BACK", screen) 이면 상위에서 이전 화면으로 전환 처리하면 됩니다.
